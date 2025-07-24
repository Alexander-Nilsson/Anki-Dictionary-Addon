#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Dictionary Application
Extracted from Anki Dictionary Addon to run independently
"""

import os
import sys
import sqlite3
import json
import requests
import re
import hashlib
import io
from PIL import Image
from flask import Flask, render_template, request, jsonify, send_from_directory
import threading
import webbrowser
from urllib.parse import quote_plus

class StandaloneDictDB:
    """Standalone version of the dictionary database"""
    
    def __init__(self, db_path="dictionaries.sqlite"):
        self.db_path = db_path
        self.conn = None
        self.c = None
        self.init_db()
    
    def init_db(self):
        """Initialize the database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.c = self.conn.cursor()
            self.c.execute("PRAGMA foreign_keys = ON")
            self.c.execute("PRAGMA case_sensitive_like=ON;")
            self.create_tables_if_not_exist()
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    def create_tables_if_not_exist(self):
        """Create basic tables if they don't exist"""
        try:
            # Create a basic dictionary table structure
            self.c.execute('''
                CREATE TABLE IF NOT EXISTS dictionaries (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    language TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.c.execute('''
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY,
                    dictionary_id INTEGER,
                    term TEXT NOT NULL,
                    definition TEXT,
                    pronunciation TEXT,
                    frequency INTEGER,
                    FOREIGN KEY (dictionary_id) REFERENCES dictionaries (id)
                )
            ''')
            
            self.conn.commit()
        except Exception as e:
            print(f"Table creation error: {e}")
    
    def search_term(self, term, limit=10):
        """Search for a term in the dictionary"""
        try:
            self.c.execute('''
                SELECT e.term, e.definition, e.pronunciation, d.name as dict_name
                FROM entries e
                JOIN dictionaries d ON e.dictionary_id = d.id
                WHERE e.term LIKE ? OR e.definition LIKE ?
                LIMIT ?
            ''', (f'%{term}%', f'%{term}%', limit))
            
            results = []
            for row in self.c.fetchall():
                results.append({
                    'term': row[0],
                    'definition': row[1],
                    'pronunciation': row[2],
                    'dictionary': row[3]
                })
            return results
        except Exception as e:
            print(f"Search error: {e}")
            return []

class StandaloneImageSearch:
    """Standalone image search using DuckDuckGo"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_images(self, term, max_results=10):
        """Search for images using DuckDuckGo"""
        try:
            # DuckDuckGo image search endpoint
            url = "https://duckduckgo.com/"
            params = {
                'q': term,
                'iax': 'images',
                'ia': 'images'
            }
            
            response = self.session.get(url, params=params)
            
            # Extract image URLs using regex (simplified approach)
            image_pattern = r'"image":"([^"]+)"'
            matches = re.findall(image_pattern, response.text)
            
            # Clean and limit results
            image_urls = []
            for match in matches[:max_results]:
                # Decode URL
                url = match.replace('\\u002F', '/').replace('\\', '')
                if url.startswith('http'):
                    image_urls.append(url)
            
            return image_urls[:max_results]
        
        except Exception as e:
            print(f"Image search error: {e}")
            return []

class StandaloneDictionary:
    """Main standalone dictionary application"""
    
    def __init__(self):
        self.db = StandaloneDictDB()
        self.image_search = StandaloneImageSearch()
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/search')
        def search():
            term = request.args.get('term', '')
            if not term:
                return jsonify({'error': 'No search term provided'})
            
            # Search dictionary
            dict_results = self.db.search_term(term)
            
            # Search images
            image_results = self.image_search.search_images(term, max_results=6)
            
            return jsonify({
                'term': term,
                'dictionary_results': dict_results,
                'image_results': image_results
            })
        
        @self.app.route('/static/<path:filename>')
        def static_files(filename):
            return send_from_directory('static', filename)
    
    def run(self, host='0.0.0.0', port=12000, debug=False):
        """Run the Flask application"""
        print(f"Starting Standalone Dictionary on http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_html_template():
    """Create the HTML template for the web interface"""
    template_dir = 'templates'
    os.makedirs(template_dir, exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Standalone Dictionary</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .search-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .search-box {
            width: 100%;
            padding: 12px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        .search-button {
            background: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        .search-button:hover {
            background: #0056b3;
        }
        .results-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .dictionary-results, .image-results {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .result-item {
            border-bottom: 1px solid #eee;
            padding: 15px 0;
        }
        .result-item:last-child {
            border-bottom: none;
        }
        .term {
            font-weight: bold;
            font-size: 18px;
            color: #333;
        }
        .definition {
            margin: 8px 0;
            color: #666;
        }
        .pronunciation {
            font-style: italic;
            color: #888;
        }
        .dictionary-name {
            font-size: 12px;
            color: #999;
        }
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }
        .image-item img {
            width: 100%;
            height: 120px;
            object-fit: cover;
            border-radius: 4px;
            cursor: pointer;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .no-results {
            text-align: center;
            padding: 20px;
            color: #999;
        }
        @media (max-width: 768px) {
            .results-container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Standalone Dictionary</h1>
        <p>Dictionary lookup with image search - No Anki required!</p>
    </div>
    
    <div class="search-container">
        <input type="text" id="searchInput" class="search-box" placeholder="Enter a word to search..." onkeypress="handleKeyPress(event)">
        <button class="search-button" onclick="performSearch()">Search</button>
    </div>
    
    <div class="results-container" id="resultsContainer" style="display: none;">
        <div class="dictionary-results">
            <h3>Dictionary Results</h3>
            <div id="dictionaryResults"></div>
        </div>
        
        <div class="image-results">
            <h3>Image Results</h3>
            <div id="imageResults" class="image-grid"></div>
        </div>
    </div>

    <script>
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                performSearch();
            }
        }

        function performSearch() {
            const term = document.getElementById('searchInput').value.trim();
            if (!term) return;

            const resultsContainer = document.getElementById('resultsContainer');
            const dictionaryResults = document.getElementById('dictionaryResults');
            const imageResults = document.getElementById('imageResults');

            // Show loading
            dictionaryResults.innerHTML = '<div class="loading">Searching dictionary...</div>';
            imageResults.innerHTML = '<div class="loading">Searching images...</div>';
            resultsContainer.style.display = 'grid';

            // Perform search
            fetch(`/search?term=${encodeURIComponent(term)}`)
                .then(response => response.json())
                .then(data => {
                    displayDictionaryResults(data.dictionary_results);
                    displayImageResults(data.image_results);
                })
                .catch(error => {
                    console.error('Search error:', error);
                    dictionaryResults.innerHTML = '<div class="no-results">Error occurred during search</div>';
                    imageResults.innerHTML = '<div class="no-results">Error occurred during search</div>';
                });
        }

        function displayDictionaryResults(results) {
            const container = document.getElementById('dictionaryResults');
            
            if (results.length === 0) {
                container.innerHTML = '<div class="no-results">No dictionary results found</div>';
                return;
            }

            let html = '';
            results.forEach(result => {
                html += `
                    <div class="result-item">
                        <div class="term">${escapeHtml(result.term)}</div>
                        <div class="definition">${escapeHtml(result.definition || 'No definition available')}</div>
                        ${result.pronunciation ? `<div class="pronunciation">[${escapeHtml(result.pronunciation)}]</div>` : ''}
                        <div class="dictionary-name">From: ${escapeHtml(result.dictionary || 'Unknown')}</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }

        function displayImageResults(results) {
            const container = document.getElementById('imageResults');
            
            if (results.length === 0) {
                container.innerHTML = '<div class="no-results">No images found</div>';
                return;
            }

            let html = '';
            results.forEach(url => {
                html += `
                    <div class="image-item">
                        <img src="${escapeHtml(url)}" alt="Search result" onclick="openImage('${escapeHtml(url)}')" onerror="this.style.display='none'">
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }

        function openImage(url) {
            window.open(url, '_blank');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Focus search input on page load
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('searchInput').focus();
        });
    </script>
</body>
</html>'''
    
    with open(os.path.join(template_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    """Main function to run the standalone dictionary"""
    print("Setting up Standalone Dictionary...")
    
    # Create HTML template
    create_html_template()
    
    # Create and run the application
    app = StandaloneDictionary()
    
    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open('http://localhost:12000')
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the Flask app
    try:
        app.run(host='0.0.0.0', port=12000, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down Standalone Dictionary...")

if __name__ == '__main__':
    main()