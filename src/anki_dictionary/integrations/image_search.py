# Image Search with Load More Functionality
# =======================================
#
# The image search now supports loading more images dynamically:
# 1. Initial search displays first 15 images in horizontal layout
# 2. "Load More" button triggers a new search with pagination
# 3. Additional images are appended to existing container
# 4. Horizontal scrolling support for better UX on mobile devices
#
# Technical Implementation:
# - DuckDuckGo API pagination using offset parameter
# - Persistent search instances to maintain state across load more requests
# - Synchronous image downloading with ThreadPoolExecutor for better performance
# - CSS flexbox layout with responsive design

# -*- coding: utf-8 -*-
import argparse
import os
from os.path import dirname, join
import requests
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# Reorders TLS cipher suites to match Chrome 120's ordering.
# Python's default OpenSSL cipher order produces a well-known JA3 fingerprint
# that DuckDuckGo's bot detector blocks on macOS. This adapter changes that
# fingerprint without requiring any new dependencies.
CHROME_CIPHERS = (
    "TLS_AES_128_GCM_SHA256:"
    "TLS_AES_256_GCM_SHA384:"
    "TLS_CHACHA20_POLY1305_SHA256:"
    "ECDHE-ECDSA-AES128-GCM-SHA256:"
    "ECDHE-RSA-AES128-GCM-SHA256:"
    "ECDHE-ECDSA-AES256-GCM-SHA384:"
    "ECDHE-RSA-AES256-GCM-SHA384:"
    "ECDHE-ECDSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-CHACHA20-POLY1305:"
    "ECDHE-RSA-AES128-SHA:"
    "ECDHE-RSA-AES256-SHA:"
    "AES128-GCM-SHA256:"
    "AES256-GCM-SHA384:"
    "AES128-SHA:"
    "AES256-SHA"
)

class ChromeTLSAdapter(HTTPAdapter):
    """Mount this on a requests.Session to replace Python's default OpenSSL
    cipher ordering with Chrome 120's ordering, changing the JA3 fingerprint."""
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ciphers=CHROME_CIPHERS)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.set_alpn_protocols(["h2", "http/1.1"])
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)

try:
    from aqt.qt import QRunnable, QObject, pyqtSignal, QImage, QSize, Qt
except ImportError:
    # Fallback to standard PyQt6 for standalone testing/development
    from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, QSize, Qt
    from PyQt6.QtGui import QImage

import io
import hashlib
try:
    from aqt import mw
except ImportError:
    mw = None
import concurrent.futures
import json
import ssl
import urllib3
import warnings
from ..utils.constants import COUNTRY_TO_DDG
from ..utils.common import prefer_ipv4

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Map country names and ISO language codes to DuckDuckGo region codes
# Sorted alphabetically for easier maintenance
countryToDuckDuckGo = COUNTRY_TO_DDG

# Get the root addon directory (4 levels up from this file)
addon_path = dirname(dirname(dirname(dirname(__file__))))
temp_dir = join(addon_path, "temp")
os.makedirs(temp_dir, exist_ok=True)

########################################
# DuckDuckGo Search Engine Implementation
########################################


class DuckDuckGoSignals(QObject):
    resultsFound = pyqtSignal(list)
    noResults = pyqtSignal(str)
    finished = pyqtSignal()


def log_debug(message):
    """Log debug messages to both console and a temporary file."""
    print(message)
    try:
        log_file = os.path.join(temp_dir, "image_search_debug.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except:
        pass

    VQD_PATTERNS = [
        re.compile(r'vqd=([0-9a-zA-Z\-]+)'),
        re.compile(r'vqd["\s]*[:=]["\s]*([0-9a-zA-Z\-]+)'),
        re.compile(r'"vqd"\s*:\s*"([^"]+)"'),
    ]

    def _extract_vqd(self, html: str):
        for pattern in self.VQD_PATTERNS:
            m = pattern.search(html)
            if m:
                return m.group(1)
        log_debug("[ImageSearch] All vqd patterns failed. Response snippet:")
        log_debug(html[:2000])
        return None

    def __init__(self):
        super().__init__()
        self.signals = DuckDuckGoSignals()
        self.term = ""
        self.idName = ""
        self.language = "us-en"  # Default to US English
        self.search_offset = 0  # Track search pagination

    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName
        # Reset offset for new searches (but not for load more)
        if idName != "load_more":
            self.search_offset = 0

    def setSearchRegion(self, region_or_code):
        """Set search language/region. Can accept country names or ISO codes like 'zh-CN'"""
        # Try to find the region/code in our unified mapping
        if region_or_code in countryToDuckDuckGo:
            self.language = countryToDuckDuckGo[region_or_code]
        else:
            log_debug(
                f"Warning: Unsupported region/language '{region_or_code}', using default US English"
            )
            self.language = "us-en"

    def getCleanedUrls(self, urls):
        return [x.replace("\\", "\\\\") for x in urls]

    def search(self, term, maximum=15, offset=0):
        session = requests.Session()
        session.mount("https://", ChromeTLSAdapter())

        # Browser-accurate headers for the initial page load phase
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        })

        try:
            import urllib.parse

            # Single request: establishes cookies AND gets the vqd token in one step
            log_debug(f"[ImageSearch] Fetching vqd token for term: {term}")
            with prefer_ipv4():
                response = session.get(
                    "https://duckduckgo.com/",
                    params={"q": term},
                    timeout=30,
                )
            response.raise_for_status()

            vqd = self._extract_vqd(response.text)
            if not vqd:
                return []

            log_debug(f"[ImageSearch] Found vqd token: {vqd}")

            # Switch to XHR-appropriate headers for the API call.
            quoted_term = urllib.parse.quote(term)
            api_headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": f"https://duckduckgo.com/?q={quoted_term}&iax=images&ia=images",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }

            params = {
                "l": self.language,
                "o": "json",
                "q": term,
                "vqd": vqd,
                "f": ",,,",
                "p": "1",
                "s": str(offset),
            }

            log_debug(f"[ImageSearch] Fetching i.js with offset={offset}")
            with prefer_ipv4():
                response = session.get(
                    "https://duckduckgo.com/i.js",
                    params=params,
                    headers=api_headers,
                    timeout=30,
                )

            if response.status_code == 200:
                data = response.json()
                results = [img["image"] for img in data.get("results", [])]
                return results[:maximum]

            elif response.status_code == 403:
                log_debug("[ImageSearch] 403 on i.js — re-fetching fresh vqd and retrying once")
                with prefer_ipv4():
                    retry_resp = session.get(
                        "https://duckduckgo.com/",
                        params={"q": term},
                        timeout=30,
                    )
                fresh_vqd = self._extract_vqd(retry_resp.text)
                if fresh_vqd:
                    params["vqd"] = fresh_vqd
                    params.pop("l", None)
                    params.pop("f", None)
                    with prefer_ipv4():
                        retry_api = session.get(
                            "https://duckduckgo.com/i.js",
                            params=params,
                            headers=api_headers,
                            timeout=30,
                        )
                    if retry_api.status_code == 200:
                        data = retry_api.json()
                        results = [img["image"] for img in data.get("results", [])]
                        return results[:maximum]
                log_debug("[ImageSearch] Retry also failed")
                return []

            else:
                log_debug(f"[ImageSearch] Unexpected status: {response.status_code}")
                return []

        except Exception as e:
            log_debug(f"[ImageSearch] Error in search: {str(e)}")
        return []

    def process_image(self, url: str, content: bytes) -> str:
        """Process the image: open, resize, and save to disk using QImage."""
        try:
            if not content:
                log_debug(f"[ImageSearch] Empty content for {url}")
                return ""
                
            image = QImage()
            if not image.loadFromData(content):
                # Try to detect if it's a known format issue
                log_debug(f"[ImageSearch] QImage failed to load data from {url}. Length: {len(content)}")
                return ""
            
            # Resize image maintaining aspect ratio
            image = image.scaled(
                QSize(200, 200),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Generate a unique filename based on the URL
            img_hash = hashlib.md5(url.encode()).hexdigest()
            filename = f"dict_img_{img_hash}.jpg"
            filepath = os.path.join(temp_dir, filename)
            
            if image.save(filepath, "JPG", 85):
                return filename
            else:
                log_debug(f"[ImageSearch] Failed to save image to {filepath}")
        except Exception as e:
            # Only log serious errors
            log_debug(f"[ImageSearch] Error processing image from {url}: {e}")
        return ""

    def download_and_process_image_sync(self, url: str, session: requests.Session = None) -> str:
        """Download and process an image synchronously (to be run in thread)."""

        try:
            # Use provided session or a temporary one
            fetcher = session if session else requests
            
            with prefer_ipv4():
                response = fetcher.get(
                    url,
                    timeout=30,
                    verify=False,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    },
                )
            if response.status_code == 200:
                return self.process_image(url, response.content)
        except Exception as e:
            # Only log serious connection errors, not common SSL issues
            error_str = str(e)
            if not any(
                x in error_str.lower()
                for x in [
                    "certificate verify failed",
                    "ssl:",
                    "server disconnected",
                    "cannot connect to host",
                    "timeout",
                ]
            ):
                log_debug(f"[ImageSearch] Error downloading image from {url}: {e}")
        return ""

    def download_all_images(self, urls: list) -> list:
        """Download and process all images concurrently using threads."""
        # Use a single session for all images in this search to enable connection reuse
        session = requests.Session()
        session.verify = False
        
        # Create a thread pool for parallel downloading and processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self.download_and_process_image_sync, url, session): url
                for url in urls
            }

            results = []
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    filename = future.result()
                    if filename:
                        results.append(filename)
                except Exception as e:
                    log_debug(f"[ImageSearch] Error processing image: {e}")

            return results

    def _image_to_html(self, filename: str) -> str:
        import base64
        image_path = os.path.join(temp_dir, filename)
        try:
            with open(image_path, "rb") as f:
                data_url = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
            return (
                '<div class="imgBox">'
                f'<div onclick="toggleImageSelect(this)" data-url="{data_url}" class="imageHighlight"></div>'
                f'<img class="searchImage" src="{data_url}" ankiDict="{image_path}">'
                '</div>'
            )
        except Exception as e:
            log_debug(f"[ImageSearch] Error reading image {filename}: {e}")
            return '<div class="imgBox">Error loading image</div>'

    def getHtml(self, term, is_load_more=False):
        """
        Generate HTML using the images from the search results.
        Downloads images to the temp folder.
        """
        images = self.search(term, offset=self.search_offset)  # Get image URLs
        if not images or len(images) < 1:
            log_debug(f"[ImageSearch] No images found for term: {term}")
            return "No Images Found. This is likely due to a connectivity error."

        # Download images concurrently
        try:
            local_images = self.download_all_images(images)
        except Exception as e:
            log_debug(f"[ImageSearch] Error in image download: {e}")
            return "Error downloading images"

        if not local_images:
            log_debug(f"[ImageSearch] Failed to download/process any images for term: {term}")
            return "Failed to download or process images. Check connectivity or logs."

        # Create horizontal layout with all images in one container
        html = '<div class="imageCont horizontal-layout">'
        html += "".join(self._image_to_html(img) for img in local_images)
        html += "</div>"

        # Add Load More button that triggers a new search
        escaped_term = json.dumps(term).replace('"', "&quot;")
        html += f'<button class="imageLoader" onclick="loadMoreImages(this, {escaped_term})">Load More</button>'

        return html

    def getMoreImages(self, term):
        """
        Get more images for the load more functionality.
        Returns HTML for additional images without container wrapper.
        """
        images = self.search(term, offset=self.search_offset)  # Get image URLs
        if not images or len(images) < 1:
            return ""  # Return empty if no more images

        # Download images concurrently
        try:
            local_images = self.download_all_images(images)
        except Exception as e:
            log_debug(f"[ImageSearch] Error in image download: {e}")
            return ""

        # Just return the image HTML without container wrapper
        html = "".join(self._image_to_html(img) for img in local_images)
        return html

    def getPreparedResults(self, term, idName):
        html = self.getHtml(term)
        return [html, idName]

    def run(self):
        try:
            if self.term:
                is_load_more = self.idName == "load_more"
                if is_load_more:
                    # For load more, just get more images
                    html = self.getMoreImages(self.term)
                    resultList = [html, self.idName]
                else:
                    # For initial search, get normal results
                    resultList = self.getPreparedResults(self.term, self.idName)
                self.signals.resultsFound.emit(resultList)
        except Exception as e:
            print(f"DuckDuckGo run error: {e}")
            self.signals.noResults.emit(
                "No Images Found. This is likely due to a connectivity error."
            )
        finally:
            self.signals.finished.emit()


########################################
# Search Function (using duckduckgo by default)
########################################


def search(target, number):
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument("-t", "--target", help="target name", type=str, required=True)
    parser.add_argument(
        "-n", "--number", help="number of images", type=int, required=True
    )
    parser.add_argument(
        "-d", "--directory", help="download location", type=str, default="./data"
    )
    parser.add_argument(
        "-f",
        "--force",
        help="download overwrite existing file",
        type=bool,
        default=False,
    )
    args = parser.parse_args()

    data_dir = "./data"
    target_name = target

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, target_name), exist_ok=args.force)

    duckduckgo = DuckDuckGo()
    results = duckduckgo.search(target_name, maximum=number)
    return results
