# -*- coding: utf-8 -*-
"""
Forvo Integration for Anki Dictionary.
Scrapes pronunciations from Forvo.com.
"""

import os
import re
import json
import base64
import requests
import hashlib
import urllib3
from typing import Optional, Dict, Any, List, Union
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
import urllib.parse

try:
    from aqt.qt import QObject, pyqtSignal, QRunnable
except ImportError:
    from PyQt6.QtCore import QObject, pyqtSignal, QRunnable

from ..utils.common import prefer_ipv4
from ..utils.logger import get_logger

logger = get_logger("Forvo")


class ForvoWorkerSignals(QObject):
    """Signals for Forvo worker."""

    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(dict)
    finished = pyqtSignal()


class ForvoWorker(QRunnable):
    """Worker for scraping Forvo in a separate thread."""

    def __init__(
        self, term: str, language_code: str, config: Dict[str, Any], idName: str = ""
    ):
        super().__init__()
        self.term = term
        self.language_code = language_code
        self.config = config
        self.idName = idName
        self.signals = ForvoWorkerSignals()
        self.session = self._make_session()
        self.search_url = "https://forvo.com/word/"

    def _make_session(self):
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = requests.Session()

        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://forvo.com/",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
        )
        return session

    def run(self):
        """Execute the scrape."""
        logger.debug(
            f"Starting Forvo search for term: '{self.term}' (lang: {self.language_code})"
        )
        try:
            url = self.search_url + urllib.parse.quote(self.term)
            logger.debug(f"Forvo URL: {url}")

            with prefer_ipv4():
                response = self.session.get(url, timeout=15)
            logger.debug(f"Forvo response status: {response.status_code}")

            if response.status_code == 404:
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

            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, "html.parser")

            # Find the language container
            # Forvo uses IDs like "language-container-ja" or "language-container-en"
            container_id = f"language-container-{self.language_code}"
            container = soup.find(id=container_id)
            logger.debug(
                f"Language container '{container_id}' found: {container is not None}"
            )

            if not container:
                # Try with underscores (some languages use them)
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
                        # Forvo audio links are base64 encoded in the Play() function call
                        # Pattern 1: Play(id, 'base64_mp3', 'base64_ogg', ...)
                        # Pattern 2: Play(id, 'base64_ogg', ...)

                        audio_url = ""
                        is_ogg = False

                        # Try MP3 first
                        mp3_match = re.search(
                            r"Play\(\d+,'[^']*','[^']*',\w+,'([^']+)'", onclick
                        )
                        if mp3_match:
                            audio_url = "https://audio00.forvo.com/audios/mp3/" + str(
                                base64.b64decode(mp3_match.group(1)), "utf-8"
                            )
                        else:
                            # Fallback to OGG
                            ogg_match = re.search(
                                r"Play\(\d+,'[^']*','([^']+)'", onclick
                            )
                            if ogg_match:
                                audio_url = "https://audio00.forvo.com/ogg/" + str(
                                    base64.b64decode(ogg_match.group(1)), "utf-8"
                                )
                                is_ogg = True

                        if not audio_url:
                            continue

                        # Extract metadata
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

            # Sort by votes descending
            results.sort(key=lambda x: x["votes"], reverse=True)

            # Limit to 15 results
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
