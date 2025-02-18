# -*- coding: utf-8 -*-
import argparse
import json
import os
import urllib
from aqt.utils import showInfo
from bs4 import BeautifulSoup
import requests
import time
import re
from aqt.qt import QRunnable, QObject, pyqtSignal
from urllib.parse import quote_plus

from PIL import Image
import io

import hashlib
from aqt import mw
from typing import List, Optional

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

########################################
# DuckDuckGo Search Engine Implementation
########################################

class DuckDuckGoSignals(QObject):
    resultsFound = pyqtSignal(list)  # Changed from tuple to list
    noResults = pyqtSignal(str)      # Changed to emit string like Google
    finished = pyqtSignal()          # Added finished signal

class DuckDuckGo(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = DuckDuckGoSignals()
        self.term = ""
        self.idName = ""
        self.language = "us-en"  # Default to US English

        # Get media directory
        try:
            self.media_dir = mw.col.media.dir()
        except Exception as e:
            print(f"Error initializing media directory: {e}")
            self.media_dir = None

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
        # Escape backslashes as done in Google
        return [x.replace('\\', '\\\\') for x in urls]
    
    def download_to_media(self, url: str) -> Optional[str]:
        """Download image to Anki media folder and return filename"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Create image from bytes
                img = Image.open(io.BytesIO(response.content))
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'): 
                    img = img.convert('RGB')
                
                # Resize maintaining aspect ratio
                img.thumbnail((200, 200))
                
                # Generate filename and path
                img_hash = hashlib.md5(url.encode()).hexdigest()
                filename = f"dict_img_{img_hash}.jpg"
                filepath = os.path.join(mw.col.media.dir(), filename) #TODO change this to be the temp folder
                
                # Save resized image
                img.save(filepath, 'JPEG', quality=85)
                return filename
                
        except Exception as e:
            print(f"Error downloading image: {str(e)}")
        return None

    def search(self, term, maximum=10):
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

    def getHtml(self, term):
        """
        Generate HTML using the images from the search results.
        Uses a similar approach as in the Google class 
        """
        images = self.search(term) # Limiting to 10 images
        if not images or len(images) < 1:
            return 'No Images Found. This is likely due to a connectivity error.'
        
        # Download images to media folder
        local_images = []
        for img_url in images:
            if filename := self.download_to_media(img_url):
                # use full path
                full_path = os.path.join(self.media_dir, filename)
                local_images.append(full_path)
        
        firstImages = []
        tempImages = []

        # Splitting images into two groups for display
        for idx, image in enumerate(local_images):
            tempImages.append(image)
            if len(tempImages) > 2 and len(firstImages) < 1:
                firstImages += tempImages
                tempImages = []
            if len(tempImages) > 2 and len(firstImages) > 1:
                break
        html = '<div class="googleCont">'
        for img in firstImages:
            html += (
                '<div class="imgBox">'
                f'<div onclick="toggleImageSelect(this)" data-url="{img}" class="googleHighlight"></div>'
                f'<img class="googleImage" src="{img}" ankiDict="{img}">'
                '</div>'
            )
        html += '</div><div class="googleCont">'
        for img in tempImages:
            html += (
                '<div class="imgBox">'
                f'<div onclick="toggleImageSelect(this)" data-url="{img}" class="googleHighlight"></div>'
                f'<img class="googleImage" src="{img}" ankiDict="{img}">'
                '</div>'
            )
        
        #button that calls the loadMoreImages JS function 
        html += (
            '</div><button class="imageLoader" onclick="loadMoreImages(this, \\\'' +
            '\\\' , \\\''.join(self.getCleanedUrls(images)) +
            '\\\')">Load More</button>'
        )
        return html

    def getPreparedResults(self, term, idName):
        html = self.getHtml(term)
        return [html, idName]
    
    '''
    def run(self):
        try:
            prepared = self.getPreparedResults(self.term, self.idName)
            # Check if the generated HTML indicates a failure
            if prepared and "No Images Found" not in prepared[0]:
                self.signals.resultsFound.emit(tuple(prepared))
            else:
                self.signals.noResults.emit()
        except Exception as e:
            print(f"DuckDuckGo run error: {e}")
            self.signals.noResults.emit()
    '''
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


