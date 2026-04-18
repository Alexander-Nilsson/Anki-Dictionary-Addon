# -*- coding: utf-8 -*-
import argparse
import os
import platform
from os.path import dirname, join
import requests
import re
import ssl
import hashlib
import concurrent.futures
import json
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import urllib.parse

try:
    from aqt.qt import QRunnable, QObject, pyqtSignal, QImage, QSize, Qt
except ImportError:
    from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, QSize, Qt
    from PyQt6.QtGui import QImage

from ..utils.constants import COUNTRY_TO_DDG
from ..utils.common import prefer_ipv4
from ..utils.logger import get_logger

logger = get_logger("ImageSearch")

# Suppress insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

addon_path = dirname(dirname(dirname(dirname(__file__))))
temp_dir = join(addon_path, "temp")
os.makedirs(temp_dir, exist_ok=True)

# Detect if the OS is macOS
_ON_MAC = platform.system() == "Darwin"

def log_debug(message):
    logger.debug(message)
    try:
        with open(os.path.join(temp_dir, "image_search_debug.log"), "a", encoding="utf-8") as f:
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
    - Mac: curl_cffi (impersonates Chrome HTTP/2 + BoringSSL)
    - Win/Linux: requests + TLSAdapter
    """
    if _ON_MAC:
        try:
            from curl_cffi import requests as curl_requests
        except ImportError:
            # Inject vendor paths manually using our known addon_path
            import sys
            
            machine = platform.machine().lower()
            # Handle both arm64 and x86_64 naming conventions
            if machine == "arm64":
                mac_vendor = os.path.join(addon_path, "vendor", "mac_arm64")
            else:
                mac_vendor = os.path.join(addon_path, "vendor", "mac_x86_64")
                
            if os.path.exists(mac_vendor) and mac_vendor not in sys.path:
                sys.path.insert(0, mac_vendor)
            
            try:
                from curl_cffi import requests as curl_requests
            except ImportError as e:
                # Log the exact error to diagnose C-extension mismatches (e.g., Python 3.9 vs 3.12)
                log_debug(f"[ImageSearch] curl_cffi import failed: {e}")
                curl_requests = None

        if curl_requests:
            # Impersonate Chrome to bypass Cloudflare/DDG WAF
            return curl_requests.Session(impersonate="safari15_5")
    
    # Windows/Linux (or Mac fallback)
    session = requests.Session()
    session.verify = False
    session.mount("https://", TLSAdapter())
    return session


class DuckDuckGoSignals(QObject):
    resultsFound = pyqtSignal(list)
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

    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName
        if idName != "load_more":
            self.search_offset = 0

    def setSearchRegion(self, region_or_code):
        self.language = COUNTRY_TO_DDG.get(region_or_code, "us-en")

    def _fetch_vqd(self, term: str):
        try:
            response = self.session.post(
                "https://duckduckgo.com",
                data={"q": term},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://duckduckgo.com/"
                },
                timeout=15
            )

            if vqd := response.headers.get("x-vqd-4"):
                return vqd

            patterns = [
                r"vqd=([0-9a-zA-Z\-]+)",
                r'vqd["\s]*[:=]["\s]*([0-9a-zA-Z\-]+)',
                r'"vqd"\s*:\s*"([^"]+)"',
                r"vqd='([0-9a-zA-Z\-]+)'"
            ]
            for pattern in patterns:
                if match := re.search(pattern, response.text):
                    return match.group(1)
        except Exception as e:
            log_debug(f"[ImageSearch] Error fetching VQD: {e}")
        return None

    def search(self, term, maximum=15, offset=0):
        try:
            with prefer_ipv4():
                vqd = self._fetch_vqd(term)

            if not vqd:
                return []

            params = {
                "l": self.language, "o": "json", "q": term,
                "vqd": vqd, "f": ",,,", "p": "1", "s": str(offset),
            }
            headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": f"https://duckduckgo.com/?q={urllib.parse.quote(term)}&iax=images&ia=images",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            with prefer_ipv4():
                response = self.session.get(
                    "https://duckduckgo.com/i.js", params=params, headers=headers, timeout=30
                )

            if response.status_code == 200:
                # Some curl_cffi versions return JSON directly, fallback to .json()
                data = response.json() if hasattr(response.json, '__call__') else response.json
                return [img["image"] for img in data.get("results", [])][:maximum]
        except Exception as e:
            log_debug(f"[ImageSearch] Error in search: {e}")
        return []

    def process_image(self, url: str, content: bytes) -> str:
        if not content: return ""
        
        image = QImage()
        if not image.loadFromData(content): return ""
        
        image = image.scaled(QSize(200, 200), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        filename = f"dict_img_{hashlib.md5(url.encode()).hexdigest()}.jpg"
        filepath = join(temp_dir, filename)
        
        return filename if image.save(filepath, "JPG", 85) else ""

    def download_and_process_image_sync(self, url: str, dl_session: requests.Session) -> str:
        try:
            with prefer_ipv4():
                # Use the dedicated download session instead of self.session
                response = dl_session.get(url, timeout=10)
            if getattr(response, "status_code", 0) == 200:
                return self.process_image(url, response.content)
        except Exception:
            pass # Suppress noisy individual download errors
        return ""

    def download_all_images(self, urls: list) -> list:
        # Create a fast, standard session strictly for image downloading
        dl_session = requests.Session()
        dl_session.verify = False
        dl_session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        # Optimize the connection pool to handle all 8 threads simultaneously
        adapter = HTTPAdapter(pool_connections=15, pool_maxsize=15)
        dl_session.mount("https://", adapter)
        dl_session.mount("http://", adapter)

        # Download the images in true parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_url = {
                executor.submit(self.download_and_process_image_sync, url, dl_session): url
                for url in urls
            }
            
            results = []
            for future in concurrent.futures.as_completed(future_to_url):
                if filename := future.result():
                    results.append(filename)
            return results

    def _image_to_html(self, filename: str) -> str:
        import base64
        image_path = join(temp_dir, filename)
        try:
            with open(image_path, "rb") as f:
                data_url = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
            return (
                f'<div class="imgBox">'
                f'<div onclick="toggleImageSelect(this)" data-url="{data_url}" class="imageHighlight"></div>'
                f'<img class="searchImage" src="{data_url}" ankiDict="{image_path}">'
                f'</div>'
            )
        except Exception:
            return '<div class="imgBox">Error loading image</div>'

    def get_images_html(self, term, is_load_more=False):
        images = self.search(term, offset=self.search_offset)
        if not images:
            return "" if is_load_more else "No Images Found. This is likely due to a connectivity error."

        local_images = self.download_all_images(images)
        inner_html = "".join(self._image_to_html(img) for img in local_images)

        if is_load_more:
            return inner_html

        escaped_term = json.dumps(term).replace('"', "&quot;")
        return (
            f'<div class="imageCont horizontal-layout">{inner_html}</div>'
            f'<button class="imageLoader" onclick="loadMoreImages(this, {escaped_term})">Load More</button>'
        )

    def run(self):
        try:
            if self.term:
                # CREATE A FRESH HYBRID SESSION FOR EVERY SEARCH
                self.session = _make_session()
                
                is_load_more = self.idName == "load_more"
                html = self.get_images_html(self.term, is_load_more)
                self.signals.resultsFound.emit([html, self.idName])
        except Exception as e:
            log_debug(f"DuckDuckGo run error: {e}")
            self.signals.noResults.emit("No Images Found.")
        finally:
            self.signals.finished.emit()


def search(target, number):
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument("-t", "--target", type=str, required=True)
    parser.add_argument("-n", "--number", type=int, required=True)
    parser.add_argument("-f", "--force", type=bool, default=False)
    args = parser.parse_args()

    data_dir = "./data"
    os.makedirs(os.path.join(data_dir, target), exist_ok=args.force)

    ddg = DuckDuckGo()
    ddg.session = _make_session() # Required since run() isn't called here
    return ddg.search(target, maximum=number)
