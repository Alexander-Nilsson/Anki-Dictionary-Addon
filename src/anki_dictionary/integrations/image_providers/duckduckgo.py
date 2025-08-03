# DuckDuckGo Image Provider
# =========================
#
# This module provides image search functionality using DuckDuckGo's image search API.
# It implements the ImageProvider interface to allow easy integration with the 
# dictionary addon's image search system.

import argparse
import os
from os.path import dirname, join
import requests
import re
import hashlib
from aqt import mw
import io
import asyncio
import aiohttp
import concurrent.futures
from PIL import Image
import json
import ssl
import urllib3
import warnings
from typing import List

from .base import ImageProvider

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Suppress PIL warnings globally
warnings.filterwarnings("ignore", category=UserWarning, module="PIL")
warnings.filterwarnings("ignore", message=".*Palette images with Transparency.*")
warnings.filterwarnings("ignore", message=".*should be converted to RGBA images.*")

# Get the temp directory for storing images
temp_dir = join(dirname(dirname(dirname(__file__))), '..', '..', '..', 'temp')
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

# Map country names and ISO language codes to DuckDuckGo region codes
countryToDuckDuckGo = {
    "Afghanistan": "af-fa",
    "Algeria": "dz-ar",
    "Argentina": "ar-es",
    "Armenia": "am-hy",
    "Australia": "au-en",
    "Austria": "at-de",
    "Azerbaijan": "az-az",
    "Bangladesh": "bd-bn",
    "Belarus": "by-be",
    "Belgium": "be-fr",
    "Brazil": "br-pt",
    "Bulgaria": "bg-bg",
    "Cambodia": "kh-km",
    "Canada": "ca-en",
    "Chile": "cl-es",
    "China": "cn-zh",
    "Colombia": "co-es",
    "Croatia": "hr-hr",
    "Croatia (Hrvatska)": "hr-hr",
    "Czech Republic": "cz-cs",
    "Denmark": "dk-da",
    "Egypt": "eg-ar",
    "Estonia": "ee-et",
    "Finland": "fi-fi",
    "France": "fr-fr",
    "Georgia": "ge-ka",
    "Germany": "de-de",
    "Greece": "gr-el",
    "Hong Kong": "hk-tzh",
    "Hungary": "hu-hu",
    "India": "in-en",
    "Indonesia": "id-id",
    "Iran, Islamic Republic of": "ir-fa",
    "Iraq": "iq-ar",
    "Ireland": "ie-en",
    "Israel": "il-he",
    "Italy": "it-it",
    "Japan": "jp-ja",
    "Jordan": "jo-ar",
    "Kazakhstan": "kz-kk",
    "Korea, Republic of": "kr-ko",
    "Kyrgyzstan": "kg-ky",
    "Laos": "la-lo",
    "Latvia": "lv-lv",
    "Lebanon": "lb-ar",
    "Lithuania": "lt-lt",
    "Malaysia": "my-ms",
    "Mexico": "mx-es",
    "Mongolia": "mn-mn",
    "Morocco": "ma-ar",
    "Myanmar": "mm-my",
    "Netherlands": "nl-nl",
    "New Zealand": "nz-en",
    "Norway": "no-no",
    "Pakistan": "pk-ur",
    "Peru": "pe-es",
    "Philippines": "ph-en",
    "Poland": "pl-pl",
    "Portugal": "pt-pt",
    "Romania": "ro-ro",
    "Russia": "ru-ru",
    "Russian Federation": "ru-ru",
    "Saudi Arabia": "sa-ar",
    "Singapore": "sg-en",
    "Slovakia": "sk-sk",
    "Slovenia": "si-sl",
    "South Africa": "za-en",
    "South Korea": "kr-ko",
    "Spain": "es-es",
    "Sri Lanka": "lk-si",
    "Sweden": "se-sv",
    "Switzerland": "ch-de",
    "Taiwan": "tw-zh",
    "Tajikistan": "tj-tg",
    "Thailand": "th-th",
    "Tunisia": "tn-ar",
    "Turkey": "tr-tr",
    "Turkmenistan": "tm-tk",
    "Ukraine": "ua-uk",
    "United Arab Emirates": "ae-ar",
    "United Kingdom": "uk-en",
    "United States": "us-en",
    "Uzbekistan": "uz-uz",
    "Venezuela": "ve-es",
    "Vietnam": "vn-vi",
    # ISO language codes for backward compatibility
    "de-DE": "de-de",  # German
    "en-GB": "uk-en",  # English (UK)
    "en-US": "us-en",  # English (US)
    "es-ES": "es-es",  # Spanish
    "fr-FR": "fr-fr",  # French
    "ja-JP": "jp-ja",  # Japanese
    "ko-KR": "kr-ko",  # Korean
    "ru-RU": "ru-ru",  # Russian
    "zh-CN": "cn-zh",  # Chinese (China)
    "zh-TW": "tw-zh",  # Chinese (Taiwan)
}


class DuckDuckGoProvider(ImageProvider):
    """DuckDuckGo image search provider"""
    
    def __init__(self):
        super().__init__()
        self.language = "us-en"  # Default to US English
        self.search_offset = 0  # Track search pagination

    def setTermIdName(self, term: str, idName: str) -> None:
        """Set the search term and ID name for this search"""
        self.term = term
        self.idName = idName
        # Reset offset for new searches (but not for load more)
        if idName != "load_more":
            self.search_offset = 0

    def setSearchRegion(self, region_or_code: str) -> None:
        """Set search language/region. Can accept country names or ISO codes like 'zh-CN'"""
        if region_or_code in countryToDuckDuckGo:
            self.language = countryToDuckDuckGo[region_or_code]
        else:
            # Default to US English if region not found
            self.language = "us-en"

    def getCleanedUrls(self, urls: List[str]) -> List[str]:
        """Clean and filter image URLs"""
        cleaned = []
        for url in urls:
            if url and isinstance(url, str):
                # Remove query parameters and fragments
                clean_url = re.sub(r'[?#].*$', '', url)
                if clean_url:
                    cleaned.append(clean_url)
        return cleaned

    def search(self, term: str, maximum: int = 15, offset: int = 0) -> List[str]:
        """
        Search for images using DuckDuckGo
        Args:
        term: Search term string
        maximum: Maximum number of images to return (default: 15)
        offset: Pagination offset for getting more results
        Returns:
        List of image URLs
        """
        session = requests.Session()
        # Disable SSL verification to handle problematic certificates
        session.verify = False
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://duckduckgo.com",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        try:
            # Get the initial token
            search_url = "https://duckduckgo.com/"
            response = session.get(search_url, timeout=30)
            session.cookies.update(response.cookies)

            # Perform the search
            params = {
                "q": term,
                "iax": "images",
                "ia": "images",
                "kl": self.language,  # Add language/region parameter
            }

            response = session.get(search_url, params=params, timeout=30)

            # Extract the vqd token using regex
            vqd = re.search(r"vqd=[\d-]+", response.text)
            if not vqd:
                return []

            # Build the API URL request
            api_url = "https://duckduckgo.com/i.js"
            params = {
                "l": "wt-wt",
                "o": "json",
                "q": term,
                "vqd": vqd.group().split("=")[1],
                "f": ",,,",
                "p": str(offset),  # Use offset for pagination
            }

            response = session.get(api_url, params=params, timeout=30)
            if response.status_code == 200:
                results = [img["image"] for img in response.json().get("results", [])]
                return results[
                    :maximum
                ]  # Limit results to maximum TODO: check if this is a legit way to do it

        except Exception as e:
            print(f"Error in DuckDuckGo search: {str(e)}")
        return []

    def process_image(self, url: str, content: bytes) -> str:
        """Process the image: open, convert, resize, and save to disk."""
        import warnings
        
        # Suppress all PIL warnings at the beginning
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="PIL")
            warnings.filterwarnings("ignore", message=".*Palette images with Transparency.*")
            
            try:
                img = Image.open(io.BytesIO(content))
                # Convert image if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                # Resize image maintaining aspect ratio
                img.thumbnail((200, 200))
                # Generate a unique filename based on the URL
                img_hash = hashlib.md5(url.encode()).hexdigest()
                filename = f"dict_img_{img_hash}.jpg"
                filepath = os.path.join(temp_dir, filename)
                img.save(filepath, "JPEG", quality=85)
                return filename
            except Exception as e:
                # Only log serious errors, not common issues like corrupted images
                if "cannot identify image file" not in str(e):
                    print(f"Error processing image from {url}: {e}")
        return ""

    async def download_and_process_image(
        self,
        url: str,
        session: aiohttp.ClientSession,
        executor: concurrent.futures.Executor,
    ) -> str:
        """Download an image asynchronously and process it using a thread pool."""
        try:
            # Create a specific timeout for this request
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    content = await response.read()
                    loop = asyncio.get_running_loop()
                    # Offload the synchronous image processing to the executor
                    filename = await loop.run_in_executor(
                        executor, self.process_image, url, content
                    )
                    return filename
        except Exception as e:
            # Only log serious connection errors, not common SSL issues
            error_str = str(e)
            if not any(x in error_str.lower() for x in [
                'certificate verify failed', 
                'ssl:', 
                'server disconnected',
                'cannot connect to host',
                'timeout'
            ]):
                print(f"Error downloading image from {url}: {e}")
        return ""

    async def download_all_images(self, urls: List[str]) -> List[str]:
        """Download and process all images concurrently."""
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create connector with SSL context and increased timeout
        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        # Create timeout configuration
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        # Create a thread pool for image processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            async with aiohttp.ClientSession(
                connector=connector, 
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            ) as session:
                tasks = [
                    self.download_and_process_image(url, session, executor)
                    for url in urls
                ]
                # Gather all tasks concurrently
                results = await asyncio.gather(*tasks)
                # Filter out any None results
                return [filename for filename in results if filename]

    def getHtml(self, term: str, is_load_more: bool = False) -> str:
        """
        Generate HTML using the images from the search results.
        Downloads images to the temp folder.
        """
        # Note: search_offset is now controlled by the dictionary class
        # and is set before this method is called
        images = self.search(term, offset=self.search_offset)  # Get image URLs
        if not images or len(images) < 1:
            return "No Images Found. This is likely due to a connectivity error."

        # Download images asynchronously
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            local_images = loop.run_until_complete(self.download_all_images(images))
            loop.close()
        except Exception as e:
            print(f"Error in async image download: {e}")
            return "Error downloading images"

        def generate_image_html(filename):
            # Use base64 data URL to embed the image directly in HTML
            import base64

            image_path = os.path.join(temp_dir, filename)
            try:
                with open(image_path, "rb") as img_file:
                    img_data = img_file.read()
                    img_base64 = base64.b64encode(img_data).decode("utf-8")
                    data_url = f"data:image/jpeg;base64,{img_base64}"
                    return (
                        '<div class="imgBox">'
                        f'<div onclick="toggleImageSelect(this)" data-url="{data_url}" class="imageHighlight"></div>'
                        f'<img class="imageImg" src="{data_url}" ankiDict="{image_path}">'
                        "</div>"
                    )
            except Exception as e:
                print(f"Error reading image {filename}: {e}")
                return '<div class="imgBox">Error loading image</div>'
        # Create horizontal layout with all images in one container
        html = '<div class="imageCont horizontal-layout">'
        html += "".join(generate_image_html(img) for img in local_images)
        html += "</div>"

        # Add Load More button that triggers a new search
        # Use JSON encoding to properly escape the term for JavaScript
        # But we need to escape the quotes for HTML attribute
        escaped_term = json.dumps(term).replace('"', "&quot;")
        html += f'<button class="imageLoader" onclick="loadMoreImages(this, {escaped_term})">Load More</button>'

        return html

    def getMoreImages(self, term: str) -> str:
        """
        Get more images for the load more functionality.
        Returns HTML for additional images without container wrapper.
        """
        # Note: search_offset is now controlled by the dictionary class
        # and is set before this method is called
        images = self.search(term, offset=self.search_offset)  # Get image URLs
        if not images or len(images) < 1:
            return ""  # Return empty if no more images

        # Download images asynchronously
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            local_images = loop.run_until_complete(self.download_all_images(images))
            loop.close()
        except Exception as e:
            print(f"Error in async image download: {e}")
            return ""

        def generate_image_html(filename):
            # Use base64 data URL to embed the image directly in HTML (same as initial search)
            import base64

            image_path = os.path.join(temp_dir, filename)
            try:
                with open(image_path, "rb") as img_file:
                    img_data = img_file.read()
                    img_base64 = base64.b64encode(img_data).decode("utf-8")
                    data_url = f"data:image/jpeg;base64,{img_base64}"
                    return (
                        '<div class="imgBox">'
                        f'<div onclick="toggleImageSelect(this)" data-url="{data_url}" class="imageHighlight"></div>'
                        f'<img class="imageImg" src="{data_url}" ankiDict="{image_path}">'
                        "</div>"
                    )
            except Exception as e:
                print(f"Error reading image {filename}: {e}")
                return '<div class="imgBox">Error loading image</div>'
        # Just return the image HTML without container wrapper
        html = "".join(generate_image_html(img) for img in local_images)
        return html


# Legacy function for backward compatibility
def search(target, number):
    """Legacy search function for backward compatibility"""
    provider = DuckDuckGoProvider()
    results = provider.search(target, maximum=number)
    return results
