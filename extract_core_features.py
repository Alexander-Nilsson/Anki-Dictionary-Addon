#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract core features from Anki Dictionary Addon
This script creates standalone versions of key components
"""

import os
import shutil
import re

def create_standalone_image_search():
    """Create a standalone version of the image search functionality"""
    
    # Read the original file
    original_path = "/workspace/Anki-Dictionary-Addon/duckduckgoimages.py"
    
    if not os.path.exists(original_path):
        print("Original duckduckgoimages.py not found")
        return
    
    with open(original_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove Anki-specific imports and replace with standard alternatives
    standalone_content = '''#!/usr/bin/env python3
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
    print("\\nGenerated HTML:")
    print(html[:200] + "..." if len(html) > 200 else html)

if __name__ == '__main__':
    main()
'''
    
    # Write the standalone version
    with open('/workspace/standalone_image_search.py', 'w', encoding='utf-8') as f:
        f.write(standalone_content)
    
    print("Created standalone_image_search.py")

def create_demo_dictionary_data():
    """Create some demo dictionary data for testing"""
    
    demo_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create demo dictionary data for testing
"""

import sqlite3
import os

def create_demo_data():
    """Create demo dictionary data"""
    
    # Create database
    db_path = "dictionaries.sqlite"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS dictionaries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            dictionary_id INTEGER,
            term TEXT NOT NULL,
            definition TEXT,
            pronunciation TEXT,
            frequency INTEGER,
            FOREIGN KEY (dictionary_id) REFERENCES dictionaries (id)
        )
    """)
    
    # Insert demo dictionaries
    c.execute("INSERT OR IGNORE INTO dictionaries (id, name, language) VALUES (1, 'English Dictionary', 'en')")
    c.execute("INSERT OR IGNORE INTO dictionaries (id, name, language) VALUES (2, 'Japanese Dictionary', 'ja')")
    
    # Insert demo entries
    demo_entries = [
        (1, "hello", "A greeting used when meeting someone", "həˈloʊ", 100),
        (1, "world", "The earth and all its inhabitants", "wɜːrld", 95),
        (1, "dictionary", "A book or electronic resource that lists words in alphabetical order", "ˈdɪkʃəˌnɛri", 80),
        (1, "search", "To look for something", "sɜːrtʃ", 90),
        (1, "language", "A system of communication used by humans", "ˈlæŋɡwɪdʒ", 85),
        (1, "computer", "An electronic device for processing data", "kəmˈpjuːtər", 88),
        (1, "internet", "A global network of interconnected computers", "ˈɪntərˌnɛt", 92),
        (1, "software", "Computer programs and applications", "ˈsɔːftˌwɛr", 75),
        (2, "こんにちは", "Hello (formal greeting)", "konnichiwa", 100),
        (2, "ありがとう", "Thank you", "arigatou", 98),
        (2, "さようなら", "Goodbye", "sayounara", 85),
        (2, "辞書", "Dictionary", "jisho", 70),
        (2, "勉強", "Study", "benkyou", 90),
    ]
    
    for entry in demo_entries:
        c.execute("""
            INSERT OR IGNORE INTO entries (dictionary_id, term, definition, pronunciation, frequency)
            VALUES (?, ?, ?, ?, ?)
        """, entry)
    
    conn.commit()
    conn.close()
    
    print(f"Created demo database: {db_path}")
    print("Demo entries added successfully!")

if __name__ == '__main__':
    create_demo_data()
'''
    
    with open('/workspace/create_demo_data.py', 'w', encoding='utf-8') as f:
        f.write(demo_script)
    
    print("Created create_demo_data.py")

def main():
    """Main function to extract core features"""
    print("Extracting core features from Anki Dictionary Addon...")
    
    create_standalone_image_search()
    create_demo_dictionary_data()
    
    print("\\nCore features extracted successfully!")
    print("\\nFiles created:")
    print("- standalone_dictionary.py (Main web application)")
    print("- standalone_image_search.py (Image search functionality)")
    print("- create_demo_data.py (Demo dictionary data)")
    print("- requirements.txt (Python dependencies)")

if __name__ == '__main__':
    main()