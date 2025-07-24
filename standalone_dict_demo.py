#!/usr/bin/env python3
"""
Standalone Dictionary Demo - Extracted from Anki Dictionary Addon

This demonstrates how core dictionary functionality could be extracted
from the Anki addon to work independently.
"""

import sqlite3
import os
import json
import requests
import re
from typing import List, Dict, Optional, Tuple
import sys

class StandaloneDictDB:
    """Simplified version of the dictionary database without Anki dependencies"""
    
    def __init__(self, db_path: str = "dictionaries.sqlite"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.c = self.conn.cursor()
        self.c.execute("PRAGMA foreign_keys = ON")
        self.c.execute("PRAGMA case_sensitive_like=ON;")
        self._init_tables()
    
    def _init_tables(self):
        """Initialize basic database tables"""
        # Create basic tables if they don't exist
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS langnames (
                id INTEGER PRIMARY KEY,
                langname TEXT UNIQUE
            )
        ''')
        
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS dictnames (
                id INTEGER PRIMARY KEY,
                dictname TEXT,
                lid INTEGER,
                fields TEXT,
                addtype TEXT,
                termHeader TEXT,
                duplicateHeader INTEGER,
                FOREIGN KEY (lid) REFERENCES langnames (id)
            )
        ''')
        
        # Add some sample languages
        languages = ['English', 'Japanese', 'Chinese', 'Spanish', 'French']
        for lang in languages:
            self.c.execute('INSERT OR IGNORE INTO langnames (langname) VALUES (?)', (lang,))
        
        self.conn.commit()
    
    def get_lang_id(self, lang: str) -> Optional[int]:
        """Get language ID by name"""
        self.c.execute('SELECT id FROM langnames WHERE langname = ?', (lang,))
        result = self.c.fetchone()
        return result[0] if result else None
    
    def search_term(self, term: str, language: str = None) -> List[Dict]:
        """Search for a term in dictionaries"""
        # This is a simplified version - in the real addon this would
        # search across multiple dictionary tables
        results = []
        
        # Mock some results for demonstration
        if term.lower() in ['hello', 'world', 'test']:
            results.append({
                'term': term,
                'definition': f'Definition of {term}',
                'language': language or 'English',
                'dictionary': 'Sample Dictionary'
            })
        
        return results

class StandaloneImageSearch:
    """Simplified image search without Qt dependencies"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_duckduckgo(self, term: str, max_results: int = 10) -> List[str]:
        """Search for images using DuckDuckGo"""
        try:
            # Get the token first
            response = self.session.get('https://duckduckgo.com/')
            token_match = re.search(r'vqd=([\d-]+)', response.text)
            if not token_match:
                return []
            
            token = token_match.group(1)
            
            # Search for images
            params = {
                'l': 'us-en',
                'o': 'json',
                'q': term,
                'vqd': token,
                'f': ',,,',
                'p': '1'
            }
            
            response = self.session.get('https://duckduckgo.com/i.js', params=params)
            data = response.json()
            
            image_urls = []
            for result in data.get('results', [])[:max_results]:
                if 'image' in result:
                    image_urls.append(result['image'])
            
            return image_urls
            
        except Exception as e:
            print(f"Error searching images: {e}")
            return []
    
    def generate_html_gallery(self, image_urls: List[str], term: str) -> str:
        """Generate HTML gallery for images"""
        if not image_urls:
            return f"<p>No images found for '{term}'</p>"
        
        html = f"<h3>Images for '{term}'</h3><div class='image-gallery'>"
        for i, url in enumerate(image_urls):
            html += f'<img src="{url}" alt="{term} {i+1}" style="max-width:200px;margin:5px;" />'
        html += "</div>"
        
        return html

class StandaloneDictionary:
    """Main standalone dictionary class"""
    
    def __init__(self, db_path: str = "dictionaries.sqlite"):
        self.db = StandaloneDictDB(db_path)
        self.image_search = StandaloneImageSearch()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration (simplified version)"""
        default_config = {
            'maxSearch': 1000,
            'dictSearch': 50,
            'maxHeight': 400,
            'maxWidth': 400,
            'safeSearch': True,
            'searchMode': 'Forward'
        }
        
        # Try to load from config file
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
        
        return default_config
    
    def lookup_word(self, term: str, language: str = None) -> Dict:
        """Look up a word and return comprehensive results"""
        results = {
            'term': term,
            'definitions': [],
            'images': [],
            'audio': None  # Would need audio implementation
        }
        
        # Search dictionary
        definitions = self.db.search_term(term, language)
        results['definitions'] = definitions
        
        # Search images
        image_urls = self.image_search.search_duckduckgo(term, 5)
        results['images'] = image_urls
        
        return results
    
    def export_to_html(self, lookup_result: Dict) -> str:
        """Export lookup result to HTML"""
        term = lookup_result['term']
        definitions = lookup_result['definitions']
        images = lookup_result['images']
        
        html = f"<html><head><title>Dictionary: {term}</title></head><body>"
        html += f"<h1>{term}</h1>"
        
        # Add definitions
        if definitions:
            html += "<h2>Definitions</h2>"
            for defn in definitions:
                html += f"<p><strong>{defn['dictionary']}:</strong> {defn['definition']}</p>"
        else:
            html += "<p>No definitions found.</p>"
        
        # Add images
        if images:
            html += self.image_search.generate_html_gallery(images, term)
        
        html += "</body></html>"
        return html

def main():
    """Command line interface for standalone dictionary"""
    if len(sys.argv) < 2:
        print("Usage: python standalone_dict_demo.py <word_to_lookup>")
        print("Example: python standalone_dict_demo.py hello")
        return
    
    term = sys.argv[1]
    
    print(f"Looking up: {term}")
    print("-" * 40)
    
    # Initialize dictionary
    dictionary = StandaloneDictionary()
    
    # Perform lookup
    result = dictionary.lookup_word(term)
    
    # Display results
    print(f"Term: {result['term']}")
    
    if result['definitions']:
        print("\nDefinitions:")
        for defn in result['definitions']:
            print(f"  - {defn['definition']} ({defn['dictionary']})")
    else:
        print("\nNo definitions found in local database.")
    
    if result['images']:
        print(f"\nFound {len(result['images'])} images:")
        for i, url in enumerate(result['images'][:3], 1):
            print(f"  {i}. {url}")
    else:
        print("\nNo images found.")
    
    # Export to HTML
    html_output = dictionary.export_to_html(result)
    output_file = f"{term}_lookup.html"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print(f"\nResults exported to: {output_file}")

if __name__ == "__main__":
    main()