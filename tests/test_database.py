"""
Tests for the database module
"""

import unittest
import tempfile
import os
import sqlite3
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.database import DictionaryDatabase, DatabaseError


class TestDictionaryDatabase(unittest.TestCase):
    """Test cases for DictionaryDatabase class"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_dict.sqlite")
        self.db = DictionaryDatabase(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Clean up any remaining files in temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_database_initialization(self):
        """Test database initialization"""
        self.assertTrue(os.path.exists(self.db_path))
        self.assertIsNotNone(self.db.conn)
        self.assertIsNotNone(self.db.cursor)
    
    def test_table_creation(self):
        """Test that required tables are created"""
        tables = ['langnames', 'dictionaries', 'definitions', 'search_history']
        
        for table in tables:
            self.db.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                (table,)
            )
            result = self.db.cursor.fetchone()
            self.assertIsNotNone(result, f"Table {table} should exist")
    
    def test_add_language(self):
        """Test adding a new language"""
        lang_id = self.db.add_language("Japanese")
        self.assertIsInstance(lang_id, int)
        self.assertGreater(lang_id, 0)
        
        # Test duplicate language
        lang_id2 = self.db.add_language("Japanese")
        self.assertEqual(lang_id, lang_id2)
    
    def test_get_language_id(self):
        """Test getting language ID"""
        # Non-existent language
        lang_id = self.db.get_language_id("NonExistent")
        self.assertIsNone(lang_id)
        
        # Add and retrieve language
        added_id = self.db.add_language("Spanish")
        retrieved_id = self.db.get_language_id("Spanish")
        self.assertEqual(added_id, retrieved_id)
    
    def test_add_definition(self):
        """Test adding definitions"""
        success = self.db.add_definition(
            "Test Dictionary", 
            "hello", 
            "a greeting", 
            "heh-loh", 
            100
        )
        self.assertTrue(success)
        
        # Verify definition was added
        results = self.db.search_definitions("hello")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['term'], "hello")
        self.assertEqual(results[0]['definition'], "a greeting")
        self.assertEqual(results[0]['reading'], "heh-loh")
        self.assertEqual(results[0]['frequency'], 100)
    
    def test_search_definitions(self):
        """Test searching definitions"""
        # Add test data
        self.db.add_definition("Dict1", "cat", "a feline animal", "kat", 50)
        self.db.add_definition("Dict1", "dog", "a canine animal", "dawg", 60)
        self.db.add_definition("Dict2", "catalog", "a list of items", "kat-uh-log", 30)
        
        # Test exact match
        results = self.db.search_definitions("cat")
        self.assertGreaterEqual(len(results), 1)
        
        # Test partial match
        results = self.db.search_definitions("cat")
        self.assertGreaterEqual(len(results), 2)  # Should match "cat" and "catalog"
        
        # Test no match
        results = self.db.search_definitions("xyz")
        self.assertEqual(len(results), 0)
    
    def test_search_history(self):
        """Test search history functionality"""
        # Perform some searches
        self.db.search_definitions("test1")
        self.db.search_definitions("test2")
        
        # Get history
        history = self.db.get_search_history(10)
        self.assertGreaterEqual(len(history), 2)
        
        # Check that both terms are in history (order may vary due to timing)
        terms = [h['term'] for h in history]
        self.assertIn("test1", terms)
        self.assertIn("test2", terms)
    
    def test_get_dictionaries(self):
        """Test getting dictionary information"""
        # Add some definitions to create dictionaries
        self.db.add_definition("English Dict", "word1", "definition1")
        self.db.add_definition("Japanese Dict", "word2", "definition2")
        
        dictionaries = self.db.get_dictionaries()
        self.assertGreaterEqual(len(dictionaries), 2)
        
        # Check dictionary names
        dict_names = [d['name'] for d in dictionaries]
        self.assertIn("English Dict", dict_names)
        self.assertIn("Japanese Dict", dict_names)
    
    def test_context_manager(self):
        """Test database as context manager"""
        temp_path = os.path.join(self.temp_dir, "context_test.sqlite")
        
        with DictionaryDatabase(temp_path) as db:
            self.assertIsNotNone(db.conn)
            db.add_definition("Test", "word", "definition")
        
        # Database should be closed after context
        # We can't directly test if connection is closed, but we can verify the file exists
        self.assertTrue(os.path.exists(temp_path))
    
    def test_database_error_handling(self):
        """Test error handling"""
        # Test with a path that will cause sqlite3 to fail
        # Use a directory as the database file path (this should fail)
        invalid_path = self.temp_dir  # This is a directory, not a file
        
        # This should raise a DatabaseError because sqlite3 can't open a directory as a database
        with self.assertRaises(DatabaseError):
            DictionaryDatabase(invalid_path)
    
    def test_foreign_key_constraints(self):
        """Test that foreign key constraints are enabled"""
        # This should work
        lang_id = self.db.add_language("Test Language")
        self.db.cursor.execute(
            "INSERT INTO dictionaries (name, language_id) VALUES (?, ?)",
            ("Test Dict", lang_id)
        )
        self.db.conn.commit()
        
        # This should fail due to foreign key constraint
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.cursor.execute(
                "INSERT INTO dictionaries (name, language_id) VALUES (?, ?)",
                ("Invalid Dict", 99999)  # Non-existent language_id
            )
            self.db.conn.commit()


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integration_test.sqlite")
        self.db = DictionaryDatabase(self.db_path)
    
    def tearDown(self):
        """Clean up"""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Clean up any remaining files in temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_workflow(self):
        """Test complete dictionary workflow"""
        # Add multiple dictionaries and definitions
        definitions = [
            ("English Dictionary", "apple", "a red fruit", "ap-uhl", 80),
            ("English Dictionary", "banana", "a yellow fruit", "buh-nan-uh", 70),
            ("Japanese Dictionary", "りんご", "apple in Japanese", "ringo", 60),
            ("Spanish Dictionary", "manzana", "apple in Spanish", "man-sa-na", 50),
        ]
        
        for dict_name, term, definition, reading, frequency in definitions:
            success = self.db.add_definition(dict_name, term, definition, reading, frequency)
            self.assertTrue(success)
        
        # Test search functionality
        apple_results = self.db.search_definitions("apple")
        self.assertGreaterEqual(len(apple_results), 2)  # English and Japanese
        
        # Test frequency ordering (higher frequency first)
        fruit_results = self.db.search_definitions("fruit")
        if len(fruit_results) >= 2:
            self.assertGreaterEqual(fruit_results[0]['frequency'], fruit_results[1]['frequency'])
        
        # Test dictionary information
        dictionaries = self.db.get_dictionaries()
        self.assertEqual(len(dictionaries), 3)  # English, Japanese, Spanish
        
        # Test search history
        history = self.db.get_search_history()
        self.assertGreaterEqual(len(history), 2)  # apple, fruit searches


if __name__ == '__main__':
    unittest.main()