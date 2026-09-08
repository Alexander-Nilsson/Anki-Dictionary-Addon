import concurrent.futures
import hashlib
import json
import os
import platform
import re
import ssl
import urllib.parse
import uuid
from os.path import dirname, join

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

try:
    from aqt.qt import QImage, QObject, QRunnable, QSize, Qt, pyqtSignal
except ImportError:
    from PyQt6.QtCore import QObject, QRunnable, QSize, Qt, pyqtSignal
    from PyQt6.QtGui import QImage

from ..utils.common import prefer_ipv4
from ..utils.constants import COUNTRY_TO_DDG
from ..utils.logger import get_logger
from ..utils.media_manager import preferred_image_ext, qt_format_for_ext

logger = get_logger("ImageSearch")

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

addon_path = dirname(dirname(dirname(dirname(__file__))))
temp_dir = join(addon_path, "temp")
os.makedirs(temp_dir, exist_ok=True)

# Detect if the OS is macOS
_ON_MAC = platform.system() == "Darwin"

# Set by _make_session(): False once we have proven curl_cffi cannot be
# imported. DuckDuckGo's i.js endpoint answers plain `requests` sessions with
# HTTP 403, so a missing curl_cffi is the single most common cause of an empty
# image search - keep it visible instead of reporting "connectivity error".
_CURL_CFFI_AVAILABLE = True

_EXT_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "avif": "image/avif",
    "bmp": "image/bmp",
    "svg": "image/svg+xml",
}

_EXT_TO_SAVE = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "png": "png",
    "gif": "gif",
    "webp": "webp",
    "avif": "avif",
    "bmp": "bmp",
}


def _guess_extension(url: str) -> str:
    """Extract image extension from URL, defaulting to 'jpg'."""
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in _EXT_TO_MIME:
        return ext
    # Try to get from query params or just default
    return "jpg"


def log_debug(message):
    logger.debug(message)
    try:
        with open(
            os.path.join(temp_dir, "image_search_debug.log"), "a", encoding="utf-8"
        ) as f:
            f.write(f"{message}\n")
    except Exception:
        pass


class TLSAdapter(HTTPAdapter):
    """Pure-Python TLS spoofing for Windows and Linux."""

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers(
            "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:"
            "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:"
            "DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384"
        )
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def _make_session():
    """
    Hybrid Session Generator:
    - Prefer curl_cffi (impersonates Safari HTTP/2 + TLS fingerprint) on
      every OS. DuckDuckGo's i.js endpoint now fingerprint-blocks plain
      requests sessions (HTTP 403), so the requests path below is only a
      fallback for environments without curl_cffi.
    - Fallback: requests + TLSAdapter (Windows/Linux legacy path).
    """
    from typing import Any

    curl_mod: Any = None
    try:
        from curl_cffi import (  # ty:ignore[unresolved-import]
            requests as _curl_requests,
        )

        curl_mod = _curl_requests
    except ImportError:
        # Inject vendor paths manually using our known addon_path
        import sys

        machine = platform.machine().lower()
        candidates: list[str] = []
        if _ON_MAC:
            # Handle both arm64 and x86_64 naming conventions
            if machine == "arm64":
                candidates.append(os.path.join(addon_path, "vendor", "mac_arm64"))
            else:
                candidates.append(os.path.join(addon_path, "vendor", "mac_x86_64"))
        elif sys.platform.startswith("win"):
            candidates.append(os.path.join(addon_path, "vendor", "win_amd64"))
        else:
            candidates.append(os.path.join(addon_path, "vendor", "linux_x86_64"))

        for vendor_dir in candidates:
            if os.path.exists(vendor_dir) and vendor_dir not in sys.path:
                sys.path.insert(0, vendor_dir)

        try:
            from curl_cffi import (  # ty:ignore[unresolved-import]
                requests as _curl_requests_fallback,
            )

            curl_mod = _curl_requests_fallback
        except ImportError as e:
            # Log the exact error to diagnose C-extension mismatches (e.g., Python 3.9 vs 3.12)
            log_debug(f"[ImageSearch] curl_cffi import failed: {e}")
            curl_mod = None

    global _CURL_CFFI_AVAILABLE
    _CURL_CFFI_AVAILABLE = curl_mod is not None

    if curl_mod:
        # safari15_5 impersonation bypasses DDG's WAF; chrome targets
        # currently get HTTP 403 on i.js.
        return curl_mod.Session(impersonate="safari15_5")

    # Fallback (no curl_cffi available): plain requests. Note DDG may
    # answer i.js with HTTP 403 to this fingerprint.
    session = requests.Session()
    session.verify = False
    session.mount("https://", TLSAdapter())
    return session


class DuckDuckGoSignals(QObject):
    # [html, idName] — the grid shell (placeholder tiles + "Load More"), sent
    # as soon as the DuckDuckGo query returns rather than after every image
    # has been downloaded.
    resultsFound = pyqtSignal(list)
    # [slotId, tileHtml] — one downloaded image, ready to replace its slot.
    imageReady = pyqtSignal(list)
    # [token, renderedCount] — every download for `token` has settled.
    imagesFinished = pyqtSignal(list)
    noResults = pyqtSignal(str)
    finished = pyqtSignal()


class DuckDuckGo(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = DuckDuckGoSignals()
        self.term = ""
        self.idName = ""
        self.language = "us-en"
        self.search_offset = 0
        self.session = None
        self.auto_convert = True
        self.last_error = ""
        # Unique per run so two overlapping searches cannot fill each other's
        # placeholder tiles.
        self.token = uuid.uuid4().hex[:12]

    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName
        if idName != "load_more":
            self.search_offset = 0

    def setSearchRegion(self, region_or_code):
        self.language = COUNTRY_TO_DDG.get(region_or_code, "us-en")

    def _fetch_vqd(self, term: str):
        try:
            response = self.session.post(  # ty:ignore[unresolved-attribute]
                "https://duckduckgo.com",
                data={"q": term},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://duckduckgo.com/",
                },
                timeout=15,
            )

            if vqd := response.headers.get("x-vqd-4"):
                return vqd

            patterns = [
                r"vqd=([0-9a-zA-Z\-]+)",
                r'vqd["\s]*[:=]["\s]*([0-9a-zA-Z\-]+)',
                r'"vqd"\s*:\s*"([^"]+)"',
                r"vqd='([0-9a-zA-Z\-]+)'",
            ]
            for pattern in patterns:
                if match := re.search(pattern, response.text):
                    return match.group(1)
        except Exception as e:
            log_debug(f"[ImageSearch] Error fetching VQD: {e}")
        return None

    def search(self, term, maximum=15, offset=0):
        """Return [(display_url, original_url)] for `term`."""
        self.last_error = ""
        try:
            with prefer_ipv4():
                vqd = self._fetch_vqd(term)

            if not vqd:
                self.last_error = "could not obtain a DuckDuckGo search token (vqd)"
                return []

            params = {
                "l": self.language,
                "o": "json",
                "q": term,
                "vqd": vqd,
                "f": ",,,",
                "p": "1",
                "s": str(offset),
            }
            headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": f"https://duckduckgo.com/?q={urllib.parse.quote(term)}&iax=images&ia=images",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            with prefer_ipv4():
                response = self.session.get(  # ty:ignore[unresolved-attribute]
                    "https://duckduckgo.com/i.js",
                    params=params,
                    headers=headers,
                    timeout=30,
                )

            if response.status_code == 200:
                # Some curl_cffi versions return JSON directly, fallback to .json()
                data = response.json() if callable(response.json) else response.json
                # Grid thumbnails come from DuckDuckGo's own CDN and are about
                # a tenth the size of the originals, which the add-on would
                # scale down to 200x200 anyway. The original URL rides along so
                # exporting a card still uses the full-resolution image.
                results = []
                for img in data.get("results", []):
                    full = img.get("image")
                    if not full:
                        continue
                    results.append((img.get("thumbnail") or full, full))
                return results[:maximum]

            self.last_error = f"DuckDuckGo returned HTTP {response.status_code}"
            if response.status_code == 403 and not _CURL_CFFI_AVAILABLE:
                self.last_error += (
                    " and curl_cffi is not bundled, so the request could not use a "
                    "browser TLS fingerprint"
                )
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"
            log_debug(f"[ImageSearch] Error in search: {e}")
        return []

    def process_image(self, url: str, content: bytes) -> str:
        if not content:
            return ""

        img_hash = hashlib.md5(url.encode()).hexdigest()

        if self.auto_convert:
            image = QImage()
            if not image.loadFromData(content):
                return ""

            image = image.scaled(
                QSize(200, 200),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            ext = preferred_image_ext()
            filename = f"dict_img_{img_hash}.{ext}"
            filepath = join(temp_dir, filename)

            return filename if image.save(filepath, qt_format_for_ext(ext)) else ""
        else:
            ext = _guess_extension(url)
            filename = f"dict_img_{img_hash}.{ext}"
            filepath = join(temp_dir, filename)
            try:
                with open(filepath, "wb") as f:
                    f.write(content)
                return filename
            except Exception:
                return ""

    def download_and_process_image_sync(
        self, url: str, dl_session: requests.Session
    ) -> str:
        try:
            with prefer_ipv4():
                # Use the dedicated download session instead of self.session
                response = dl_session.get(url, timeout=10)
            if getattr(response, "status_code", 0) == 200:
                return self.process_image(url, response.content)
        except Exception:
            pass  # Suppress noisy individual download errors
        return ""

    def download_all_images(self, urls: list) -> list:
        """Download each (display_url, original_url) pair in parallel.

        Returns [(local filename, original_url)] in completion order; failed
        downloads are dropped.
        """
        # Create a fast, standard session strictly for image downloading
        dl_session = requests.Session()
        dl_session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )

        # Optimize the connection pool to handle all 8 threads simultaneously
        adapter = HTTPAdapter(pool_connections=15, pool_maxsize=15)
        dl_session.mount("https://", adapter)
        dl_session.mount("http://", adapter)

        # Download the images in true parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_pair = {
                executor.submit(
                    self.download_and_process_image_sync, display_url, dl_session
                ): (display_url, full_url)
                for display_url, full_url in urls
            }

            results = []
            for future in concurrent.futures.as_completed(future_to_pair):
                if filename := future.result():
                    results.append((filename, future_to_pair[future][1]))
            return results

    @staticmethod
    def _mime_for(filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webp"
        return _EXT_TO_MIME.get(ext, "image/webp")

    def _image_to_html(self, filename: str, full_url: str = "") -> str:
        import base64
        import html as html_mod

        image_path = join(temp_dir, filename)
        mime = self._mime_for(filename)
        try:
            with open(image_path, "rb") as f:
                data_url = f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"
            # `data-url` keeps the inlined thumbnail (what the grid shows and
            # what older builds exported); `data-full-url` is the original
            # image, which the export path prefers so cards are not built from
            # a 200x200 preview.
            full_attr = (
                f' data-full-url="{html_mod.escape(full_url, quote=True)}"'
                if full_url
                else ""
            )
            return (
                f'<div class="imgBox">'
                f'<div onclick="toggleImageSelect(this)" data-url="{data_url}"'
                f'{full_attr} class="imageHighlight"></div>'
                f'<img class="searchImage" src="{data_url}" ankiDict="{image_path}">'
                f"</div>"
            )
        except Exception:
            return '<div class="imgBox">Error loading image</div>'

    def _empty_state_reason(self) -> str:
        """Explain *why* the search came back empty, so users and the debug log
        can tell a real connectivity problem apart from a missing/blocked
        curl_cffi (DuckDuckGo answers plain requests with HTTP 403)."""
        if not _CURL_CFFI_AVAILABLE:
            return (
                "The bundled curl_cffi module is missing, so DuckDuckGo blocks "
                "the request. Reinstall the add-on to restore it."
            )
        if self.last_error:
            return f"Search failed: {self.last_error}"
        return "This is likely due to a connectivity error."

    # ── grid markup ───────────────────────────────────────────

    def _slot_id(self, index: int) -> str:
        return f"imgslot-{self.token}-{index}"

    def _slots_html(self, count: int) -> str:
        """Placeholder tiles, one per pending image.

        Rendering these up front reserves the grid's final layout, so images
        popping in as they arrive do not reflow the tiles already on screen.
        """
        return "".join(
            f'<div class="imgBox imgPending" id="{self._slot_id(i)}" '
            f'data-img-token="{self.token}"></div>'
            for i in range(count)
        )

    def _empty_state_html(self) -> str:
        # Uniform empty state: rendered inside the standard definitionBlock, so
        # it sits exactly where any other dictionary's definition box sits.
        return (
            '<div class="image-empty">'
            f"No Images Found. {self._empty_state_reason()}"
            "</div>"
        )

    def _grid_html(self, term: str, inner_html: str) -> str:
        escaped_term = json.dumps(term).replace('"', "&quot;")
        return (
            f'<div class="imageCont horizontal-layout">{inner_html}'
            f'<div class="imgBox imageLoader" onclick="loadMoreImages(this, {escaped_term})">'
            f'<div class="imageHighlight"></div>'
            f'<div class="loadMoreIcon">+</div>'
            f'<div class="loadMoreText">Load More</div>'
            f"</div></div>"
        )

    def get_images_html(self, term, is_load_more=False):
        """Blocking variant: the complete grid, every image already inlined.

        The UI uses the streaming path in :meth:`run`; this stays for callers
        that want one finished string (and for tests).
        """
        images = self.search(term, offset=self.search_offset)
        if not images:
            return "" if is_load_more else self._empty_state_html()

        local_images = self.download_all_images(images)
        inner_html = "".join(
            self._image_to_html(img, full_url) for img, full_url in local_images
        )
        if is_load_more:
            return inner_html
        return self._grid_html(term, inner_html)

    # ── streaming ─────────────────────────────────────────────

    def _stream_images(self, images: list) -> int:
        """Download in parallel, emitting each tile the moment it is ready.

        Returns how many tiles were actually emitted; the rest of the slots are
        dropped by the UI when ``imagesFinished`` arrives.
        """
        dl_session = requests.Session()
        dl_session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        adapter = HTTPAdapter(pool_connections=15, pool_maxsize=15)
        dl_session.mount("https://", adapter)
        dl_session.mount("http://", adapter)

        rendered = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_slot = {
                executor.submit(
                    self.download_and_process_image_sync, display_url, dl_session
                ): (index, full_url)
                for index, (display_url, full_url) in enumerate(images)
            }
            for future in concurrent.futures.as_completed(future_to_slot):
                index, full_url = future_to_slot[future]
                try:
                    filename = future.result()
                except Exception:  # noqa: BLE001 - one bad image must not stop the rest
                    filename = ""
                if not filename:
                    continue
                self.signals.imageReady.emit(
                    [self._slot_id(index), self._image_to_html(filename, full_url)]
                )
                rendered += 1
        return rendered

    def run(self):
        """Search, then stream the images in as they download.

        The grid shell is emitted as soon as DuckDuckGo answers — roughly half
        the total time — so results appear while the thumbnails are still
        arriving, instead of after the slowest one.
        """
        try:
            if not self.term:
                return
            # CREATE A FRESH HYBRID SESSION FOR EVERY SEARCH
            self.session = _make_session()

            is_load_more = self.idName == "load_more"
            images = self.search(self.term, offset=self.search_offset)

            if not images:
                html = "" if is_load_more else self._empty_state_html()
                self.signals.resultsFound.emit([html, self.idName])
                self.signals.imagesFinished.emit([self.token, 0])
                return

            # Shell first (placeholders + "Load More"), tiles after. Both are
            # queued to the UI thread in emission order.
            self.signals.resultsFound.emit(
                [
                    self._slots_html(len(images))
                    if is_load_more
                    else self._grid_html(self.term, self._slots_html(len(images))),
                    self.idName,
                ]
            )
            rendered = self._stream_images(images)
            self.signals.imagesFinished.emit([self.token, rendered])
        except Exception as e:
            log_debug(f"DuckDuckGo run error: {e}")
            self.signals.noResults.emit("No Images Found.")
        finally:
            self.signals.finished.emit()
