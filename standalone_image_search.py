#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Image Search
Extracted from Anki Dictionary Addon
"""

import argparse
import os
from os.path import dirname, join
import requests
import re
from PIL import Image
import io
import hashlib
import asyncio
import aiohttp
import concurrent.futures
import threading
import time

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

temp_dir = join(dirname(__file__), 'temp')
os.makedirs(temp_dir, exist_ok=True)

class StandaloneImageSearch:
    """Standalone image search class"""
    
    def __init__(self):
        self.term = ""
        self.idName = ""
        self.searchRegion = "us-en"
        self.safeSearch = True
        self.results = []
    
    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName
    
    def setSearchRegion(self, region):
        if region in languageCodes.values():
            self.searchRegion = region
        else:
            # Try to find matching region
            for key, value in languageCodes.items():
                if region.lower() in key.lower():
                    self.searchRegion = value
                    break
    
    def setSafeSearch(self, safe):
        self.safeSearch = safe
    
    def search(self, term, maximum=20):
        """Search for images using DuckDuckGo"""
        self.term = term
        self.results = []
        
        try:
            # DuckDuckGo search
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # Get search token
            response = session.get('https://duckduckgo.com/')
            
            # Search for images
            params = {
                'q': term,
                'iax': 'images',
                'ia': 'images'
            }
            
            response = session.get('https://duckduckgo.com/', params=params)
            
            # Extract image URLs (simplified)
            image_pattern = r'"image":"([^"]+)"'
            matches = re.findall(image_pattern, response.text)
            
            for match in matches[:maximum]:
                url = match.replace('\\u002F', '/').replace('\\\\', '\\')
                if url.startswith('http'):
                    self.results.append(url)
            
            return self.results[:maximum]
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def getHtml(self, term):
        """Generate HTML for image results"""
        if not self.results:
            self.search(term)
        
        html = f'<div class="image-search-results" id="{self.idName}">'
        html += f'<h3>Images for "{term}"</h3>'
        html += '<div class="image-grid">'
        
        for i, url in enumerate(self.results):
            html += f'<div class="image-item">'
            html += f'<img src="{url}" alt="{term}" onclick="window.open(\'{url}\', \'_blank\')" '
            html += f'style="width: 150px; height: 150px; object-fit: cover; margin: 5px; cursor: pointer;">'
            html += f'</div>'
        
        html += '</div></div>'
        return html
    
    def getPreparedResults(self, term, idName):
        """Get prepared results with HTML and metadata"""
        self.setTermIdName(term, idName)
        results = self.search(term)
        html = self.getHtml(term)
        
        return {
            'term': term,
            'idName': idName,
            'results': results,
            'html': html,
            'count': len(results)
        }

# For backward compatibility
DuckDuckGo = StandaloneImageSearch

def main():
    """Test the standalone image search"""
    print("Testing Standalone Image Search...")
    
    search_engine = StandaloneImageSearch()
    search_engine.setTermIdName("cats", "test_search")
    search_engine.setSearchRegion("US")
    search_engine.setSafeSearch(True)
    
    results = search_engine.search("cats", maximum=5)
    print(f"Found {len(results)} images:")
    for i, url in enumerate(results, 1):
        print(f"{i}. {url}")
    
    html = search_engine.getHtml("cats")
    print("\nGenerated HTML:")
    print(html[:200] + "..." if len(html) > 200 else html)

if __name__ == '__main__':
    main()
