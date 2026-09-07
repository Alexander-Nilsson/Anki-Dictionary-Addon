"""
Forvo Integration for Anki Dictionary.
Scrapes pronunciations from Forvo.com.
"""

import base64
import re
import subprocess
import sys
import time
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup

try:
    from aqt.qt import QObject, QRunnable, pyqtSignal
except ImportError:
    from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from ..utils.logger import get_logger

logger = get_logger("Forvo")

SEARCH_URL = "https://forvo.com/word/"

CURL_HEADERS = [
    "-H",
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "-H",
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H",
    "Accept-Language: en-US,en;q=0.9",
    "-H",
    "Accept-Encoding: gzip, deflate, br",
    "-H",
    "Referer: https://forvo.com/",
    "-H",
    "DNT: 1",
    "-H",
    "Sec-Fetch-Dest: document",
    "-H",
    "Sec-Fetch-Mode: navigate",
    "-H",
    "Sec-Fetch-Site: same-origin",
    "-H",
    "Sec-Fetch-User: ?1",
    "-H",
    "Upgrade-Insecure-Requests: 1",
    "-H",
    'Sec-Ch-Ua: "Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "-H",
    "Sec-Ch-Ua-Mobile: ?0",
    "-H",
    'Sec-Ch-Ua-Platform: "Windows"',
]

if sys.platform == "win32":
    CURL_BIN = "curl.exe"
else:
    CURL_BIN = "curl"


class ForvoWorkerSignals(QObject):
    """Signals for Forvo worker."""

    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(dict)
    finished = pyqtSignal()


# Curl exit code reported as the "status" when we never got an HTTP reply at
# all (DNS failure, timeout, curl missing). Distinct from any real status so
# callers can tell "could not reach Forvo" from "Forvo answered with an error".
NO_HTTP_RESPONSE = 0

# How many times to re-issue a request that failed in a way a retry might fix.
_MAX_ATTEMPTS = 3


def _is_cloudflare_challenge(html: str) -> bool:
    """True when Cloudflare served an interstitial instead of the page."""
    return "Just a moment" in html or "cf-browser-verification" in html


def _fetch_url(url: str, timeout: int = 15) -> tuple[int, str]:
    """Fetch a Forvo page using curl, whose TLS fingerprint Cloudflare accepts.

    Returns ``(http_status, html)``. The status is the real HTTP status code —
    curl's ``%{http_code}`` — not curl's exit code, so a word Forvo simply does
    not have (404) is distinguishable from being blocked (403) or from never
    reaching the site at all (:data:`NO_HTTP_RESPONSE`).

    Only failures a retry could plausibly fix are retried: a Cloudflare
    challenge, rate limiting, a server error, or a curl-level failure. A 404 is
    a final answer and returns immediately.
    """
    last_exit = NO_HTTP_RESPONSE
    for attempt in range(_MAX_ATTEMPTS):
        try:
            result = subprocess.run(
                [
                    CURL_BIN,
                    "-s",
                    "-L",
                    "--compressed",
                    "--connect-timeout",
                    str(timeout),
                    "--max-time",
                    str(timeout),
                    # Append the status so one call yields both body and code.
                    "-w",
                    "\n%{http_code}",
                    *CURL_HEADERS,
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
            )
        except subprocess.TimeoutExpired:
            logger.debug("Forvo fetch timed out (attempt %d)", attempt + 1)
            status, html = NO_HTTP_RESPONSE, ""
        except FileNotFoundError:
            # No curl on this machine — retrying cannot help.
            logger.error("curl not found (%s); Forvo needs it to fetch pages", CURL_BIN)
            raise
        else:
            if result.returncode != 0:
                last_exit = result.returncode
                logger.debug(
                    "curl exited %d for Forvo (attempt %d)", last_exit, attempt + 1
                )
                status, html = NO_HTTP_RESPONSE, ""
            else:
                html, _, code = result.stdout.rpartition("\n")
                try:
                    status = int(code.strip())
                except ValueError:
                    status, html = NO_HTTP_RESPONSE, ""

        if status == 200 and _is_cloudflare_challenge(html):
            logger.debug("Cloudflare challenge from Forvo (attempt %d)", attempt + 1)
            status, html = 403, ""

        retryable = status in (NO_HTTP_RESPONSE, 403, 429) or status >= 500
        if not retryable:
            return status, html
        if attempt < _MAX_ATTEMPTS - 1:
            # Back off progressively; hammering a rate limiter only extends it.
            time.sleep(attempt + 1)

    if status == NO_HTTP_RESPONSE and last_exit:
        logger.warning("Could not reach Forvo; curl exit %d", last_exit)
    return status, html


class ForvoWorker(QRunnable):
    """Worker for scraping Forvo in a separate thread."""

    def __init__(
        self, term: str, language_code: str, config: dict[str, Any], idName: str = ""
    ):
        super().__init__()
        self.term = term
        self.language_code = language_code
        self.config = config
        self.idName = idName
        self.signals = ForvoWorkerSignals()

    @staticmethod
    def _failure_message(status: int) -> str:
        """Say what actually went wrong, not just "HTTP 403"."""
        if status == NO_HTTP_RESPONSE:
            return "Could not reach forvo.com (network error or curl unavailable)"
        if status == 403:
            return (
                "Forvo returned HTTP 403 - Cloudflare is challenging the request. "
                "It usually clears on its own; searching more slowly helps."
            )
        if status == 429:
            return "Forvo returned HTTP 429 - too many requests, try again shortly"
        if status >= 500:
            return f"Forvo is unavailable (HTTP {status})"
        return f"Forvo returned HTTP {status}"

    def run(self):
        """Execute the scrape."""
        logger.debug(
            f"Starting Forvo search for term: '{self.term}' (lang: {self.language_code})"
        )
        try:
            url = SEARCH_URL + urllib.parse.quote(self.term)
            logger.debug(f"Forvo URL: {url}")

            status, html = _fetch_url(url)
            logger.debug(f"Forvo response status: {status}")

            if status == 404:
                logger.debug("Forvo term not found (404)")
                self.signals.result_ready.emit(
                    {
                        "term": self.term,
                        "items": [],
                        "dictName": "Forvo",
                        "idName": self.idName,
                    }
                )
                return

            if status != 200:
                raise RuntimeError(self._failure_message(status))

            soup = BeautifulSoup(html, "html.parser")

            container_id = f"language-container-{self.language_code}"
            container = soup.find(id=container_id)
            logger.debug(
                f"Language container '{container_id}' found: {container is not None}"
            )

            if not container:
                container = soup.find(
                    id=re.compile(f"language-container-{self.language_code}.*")
                )
                if container:
                    logger.debug(f"Found alternative container: {container.get('id')}")

            results = []
            if container:
                pronunciation_list = container.find(class_="pronunciations-list")
                if pronunciation_list:
                    items = pronunciation_list.find_all("li")
                    logger.debug(f"Found {len(items)} pronunciation items")
                    for item in items:
                        play_button = item.find(id=re.compile(r"play_\d+"))
                        if not play_button:
                            continue

                        onclick = play_button.get("onclick", "")
                        audio_url = ""
                        is_ogg = False

                        mp3_match = re.search(
                            r"Play\(\d+,'[^']*','[^']*',\w+,'([^']+)'", onclick
                        )  # ty:ignore[no-matching-overload]
                        if mp3_match:
                            audio_url = "https://audio00.forvo.com/audios/mp3/" + str(
                                base64.b64decode(mp3_match.group(1)), "utf-8"
                            )
                        else:
                            ogg_match = re.search(
                                r"Play\(\d+,'[^']*','([^']+)'", onclick
                            )  # ty:ignore[no-matching-overload]
                            if ogg_match:
                                audio_url = "https://audio00.forvo.com/ogg/" + str(
                                    base64.b64decode(ogg_match.group(1)), "utf-8"
                                )
                                is_ogg = True

                        if not audio_url:
                            continue

                        username = ""
                        of_link = item.find(class_="ofLink")
                        if of_link:
                            username = of_link.get_text().strip()

                        from_info = item.find(class_="from")
                        origin = from_info.get_text().strip() if from_info else ""

                        votes = 0
                        votes_info = item.find(class_="num_votes")
                        if votes_info:
                            vote_text = votes_info.get_text()
                            vote_match = re.search(r"(-?\d+)", vote_text)
                            if vote_match:
                                votes = int(vote_match.group(1))

                        results.append(
                            {
                                "user": username,
                                "origin": origin,
                                "votes": votes,
                                "audio_url": audio_url,
                                "is_ogg": is_ogg,
                                "word": self.term,
                            }
                        )

            results.sort(key=lambda x: x["votes"], reverse=True)
            results = results[:15]

            logger.debug(f"Emitting {len(results)} Forvo results")

            self.signals.result_ready.emit(
                {
                    "term": self.term,
                    "items": results,
                    "dictName": "Forvo",
                    "idName": self.idName,
                }
            )

        except Exception as e:
            error_msg = f"Forvo Error: {str(e)}"
            logger.error(error_msg)
            self.signals.error_occurred.emit(
                {"error": error_msg, "idName": self.idName}
            )
        finally:
            logger.debug("Forvo worker finished")
            self.signals.finished.emit()
