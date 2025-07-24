#!/usr/bin/env python3
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
