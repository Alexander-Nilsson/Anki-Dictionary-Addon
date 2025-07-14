# -*- coding: utf-8 -*-
import argparse
import os
from os.path import dirname, join
import requests
import re
from aqt.qt import QRunnable, QObject, pyqtSignal
from PIL import Image
import io
import hashlib
from aqt import mw
import os
import io
import asyncio
import aiohttp
import hashlib
import concurrent.futures
from PIL import Image

# Add comprehensive language/region codes for DuckDuckGo
languageCodes = {
    'zh-CN': 'cn-zh',  # Chinese (China)
    'zh-TW': 'tw-zh',  # Chinese (Taiwan) 
    'ja-JP': 'jp-ja',  # Japanese
    'ko-KR': 'kr-ko',  # Korean
    'en-US': 'us-en',  # English (US)
    'en-GB': 'uk-en',  # English (UK)
    'es-ES': 'es-es',  # Spanish
    'fr-FR': 'fr-fr',  # French
    'de-DE': 'de-de',  # German
    'ru-RU': 'ru-ru',  # Russian
}

temp_dir = join(dirname(__file__), 'temp') #TODO put this somwhere good
os.makedirs(temp_dir, exist_ok=True)

########################################
# DuckDuckGo Search Engine Implementation
########################################

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
        self.language = "cn-zh"  # Default to US English

    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName

    def setSearchRegion(self, lang_code):
        """Set search language/region. Use ISO codes like 'zh-CN' for Chinese"""
        if lang_code in languageCodes:
            self.language = languageCodes[lang_code]
        else:
            print(f"Warning: Unsupported language code {lang_code}, using default")
            self.language = "us-en"

    def getCleanedUrls(self, urls):
        return [x.replace('\\', '\\\\') for x in urls]
    
    def search(self, term, maximum=15):
        """
        Search for images using DuckDuckGo
        Args:
        term: Search term string
        maximum: Maximum number of images to return (default: 10)
        Returns:
        List of image URLs
        """
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://duckduckgo.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        try:
            # Get the initial token
            search_url = "https://duckduckgo.com/"
            response = session.get(search_url, timeout=10)
            session.cookies.update(response.cookies)
            
            # Perform the search
            params = {
                'q': term,
                'iax': 'images',
                'ia': 'images',
                'kl': self.language,  # Add language/region parameter
            }

            response = session.get(search_url, params=params, timeout=10)
            
            # Extract the vqd token using regex
            vqd = re.search(r'vqd=[\d-]+', response.text)
            if not vqd:
                return []
                
            # Build the API URL request
            api_url = "https://duckduckgo.com/i.js"
            params = {
                'l': 'wt-wt',
                'o': 'json',
                'q': term,
                'vqd': vqd.group().split('=')[1],
                'f': ',,,',
                'p': '-1',
            }
            
            response = session.get(api_url, params=params, timeout=10)
            if response.status_code == 200:
                results = [img['image'] for img in response.json().get('results', [])]
                return results[:maximum]  # Limit results to maximum TODO: check if this is a legit way to do it
                
        except Exception as e:
            print(f"Error in DuckDuckGo search: {str(e)}")
        return []

    def process_image(self, url: str, content: bytes) -> str:
        """Process the image: open, convert, resize, and save to disk."""
        try:
            img = Image.open(io.BytesIO(content))
            # Convert image if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            # Resize image maintaining aspect ratio
            img.thumbnail((200, 200))
            # Generate a unique filename based on the URL
            img_hash = hashlib.md5(url.encode()).hexdigest()
            filename = f"dict_img_{img_hash}.jpg"
            filepath = os.path.join(temp_dir, filename)
            img.save(filepath, 'JPEG', quality=85)
            return filename
        except Exception as e:
            print(f"Error processing image from {url}: {e}")
        return None

    async def download_and_process_image(self, url: str, session: aiohttp.ClientSession, 
                                       executor: concurrent.futures.Executor) -> str:
        """Download an image asynchronously and process it using a thread pool."""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    content = await response.read()
                    loop = asyncio.get_running_loop()
                    # Offload the synchronous image processing to the executor
                    filename = await loop.run_in_executor(
                        executor, self.process_image, url, content)
                    return filename
        except Exception as e:
            print(f"Error downloading image from {url}: {e}")
        return None

    async def download_all_images(self, urls: list) -> list:
        """Download and process all images concurrently."""
        # Create a thread pool for image processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            async with aiohttp.ClientSession() as session:
                tasks = [
                    self.download_and_process_image(url, session, executor)
                    for url in urls
                ]
                # Gather all tasks concurrently
                results = await asyncio.gather(*tasks)
                # Filter out any None results
                return [filename for filename in results if filename]

    def getHtml(self, term):
        """
        Generate HTML using the images from the search results.
        Downloads images to the temp folder.
        """
        images = self.search(term) # Get image URLs
        if not images or len(images) < 1:
            return 'No Images Found. This is likely due to a connectivity error.'
        
        # Download images asynchronously
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            local_images = loop.run_until_complete(self.download_all_images(images))
            loop.close()
        except Exception as e:
            print(f"Error in async image download: {e}")
            return 'Error downloading images'

        # Split images into two groups for better layout
        IMAGES_PER_GROUP = 5
        first_group = local_images[:IMAGES_PER_GROUP]
        second_group = local_images[IMAGES_PER_GROUP:IMAGES_PER_GROUP*2]

        def generate_image_html(filename):
            image_path = os.path.join(temp_dir, filename)
            return (
                '<div class="imgBox">'
                f'<div onclick="toggleImageSelect(this)" data-url="{image_path}" class="googleHighlight"></div>'
                f'<img class="googleImage" src="{image_path}" ankiDict="{image_path}">'
                '</div>'
            )

        html = '<div class="googleCont">'
        html += ''.join(generate_image_html(img) for img in first_group)
        html += '</div><div class="googleCont">'
        html += ''.join(generate_image_html(img) for img in second_group)
        html += (
            '</div><button class="imageLoader" onclick="loadMoreImages(this, \\\'' +
            '\\\' , \\\''.join(self.getCleanedUrls([os.path.join(temp_dir, img) for img in local_images])) +
            '\\\')">Load More</button>'
        )

        return html
    
    def getPreparedResults(self, term, idName):
        html = self.getHtml(term)
        return [html, idName]
    
    def run(self):
        try:
            if self.term:
                resultList = self.getPreparedResults(self.term, self.idName)
                self.signals.resultsFound.emit(resultList)  # Changed from tuple to list
        except Exception as e:
            print(f"DuckDuckGo run error: {e}")
            self.signals.noResults.emit('No Images Found. This is likely due to a connectivity error.')
        finally:
            self.signals.finished.emit()


########################################
# Search Function (using duckduckgo by default)
########################################

def search(target, number):
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument("-t", "--target", help="target name", type=str, required=True)
    parser.add_argument("-n", "--number", help="number of images", type=int, required=True)
    parser.add_argument("-d", "--directory", help="download location", type=str, default="./data")
    parser.add_argument("-f", "--force", help="download overwrite existing file", type=bool, default=False)
    args = parser.parse_args()

    data_dir = "./data"
    target_name = target

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, target_name), exist_ok=args.force)

    duckduckgo = DuckDuckGo()
    results = duckduckgo.search(target_name, maximum=number)
    return results


