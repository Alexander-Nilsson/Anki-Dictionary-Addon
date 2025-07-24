"""
Tests for the main dictionary module
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, Mock, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.dictionary import Dictionary, DictionaryConfig, DictionaryResult
from core.database import DictionaryDatabase
from core.image_search import ImageSearcher


class TestDictionaryConfig(unittest.TestCase):
    """Test cases for DictionaryConfig class"""
    
    def setUp(self):
        """Set up test config"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
    
    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_default_config_creation(self):
        """Test creation of default config"""
        config = DictionaryConfig(self.config_path)
        
        # Check that config file was created
        self.assertTrue(os.path.exists(self.config_path))
        
        # Check default values
        self.assertEqual(config.get('max_results'), 50)
        self.assertTrue(config.get('enable_images'))
        self.assertEqual(config.get('default_language'), 'English')
    
    def test_load_existing_config(self):
        """Test loading existing config file"""
        # Create test config file
        test_config = {
            "max_results": 100,
            "enable_images": False,
            "custom_setting": "test_value"
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(test_config, f)
        
        config = DictionaryConfig(self.config_path)
        
        # Check that custom values are loaded
        self.assertEqual(config.get('max_results'), 100)
        self.assertFalse(config.get('enable_images'))
        self.assertEqual(config.get('custom_setting'), 'test_value')
        
        # Check that defaults are still available for missing keys
        self.assertEqual(config.get('default_language'), 'English')
    
    def test_config_get_set(self):
        """Test getting and setting config values"""
        config = DictionaryConfig(self.config_path)
        
        # Test get with default
        self.assertEqual(config.get('nonexistent', 'default'), 'default')
        
        # Test set
        config.set('test_key', 'test_value')
        self.assertEqual(config.get('test_key'), 'test_value')
    
    def test_config_update(self):
        """Test updating multiple config values"""
        config = DictionaryConfig(self.config_path)
        
        updates = {
            'max_results': 200,
            'new_setting': 'new_value'
        }
        
        config.update(updates)
        
        self.assertEqual(config.get('max_results'), 200)
        self.assertEqual(config.get('new_setting'), 'new_value')
    
    def test_save_config(self):
        """Test saving config to file"""
        config = DictionaryConfig(self.config_path)
        config.set('test_setting', 'test_value')
        config.save_config()
        
        # Load config again and verify
        config2 = DictionaryConfig(self.config_path)
        self.assertEqual(config2.get('test_setting'), 'test_value')


class TestDictionaryResult(unittest.TestCase):
    """Test cases for DictionaryResult class"""
    
    def test_basic_result_creation(self):
        """Test creating a basic result"""
        result = DictionaryResult("hello", "a greeting")
        
        self.assertEqual(result.term, "hello")
        self.assertEqual(result.definition, "a greeting")
        self.assertEqual(result.reading, "")
        self.assertEqual(result.frequency, 0)
    
    def test_result_with_kwargs(self):
        """Test creating result with additional fields"""
        result = DictionaryResult(
            "hello", 
            "a greeting",
            reading="heh-loh",
            frequency=100,
            dictionary="Test Dict",
            language="English",
            images=["img1.jpg", "img2.jpg"],
            audio_url="audio.mp3"
        )
        
        self.assertEqual(result.reading, "heh-loh")
        self.assertEqual(result.frequency, 100)
        self.assertEqual(result.dictionary, "Test Dict")
        self.assertEqual(result.language, "English")
        self.assertEqual(result.images, ["img1.jpg", "img2.jpg"])
        self.assertEqual(result.audio_url, "audio.mp3")
    
    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = DictionaryResult(
            "test", 
            "definition",
            reading="test-reading",
            frequency=50
        )
        
        result_dict = result.to_dict()
        
        self.assertEqual(result_dict['term'], "test")
        self.assertEqual(result_dict['definition'], "definition")
        self.assertEqual(result_dict['reading'], "test-reading")
        self.assertEqual(result_dict['frequency'], 50)
    
    def test_result_str_representation(self):
        """Test string representation of result"""
        result = DictionaryResult("hello", "a greeting used when meeting someone")
        result_str = str(result)
        
        self.assertIn("hello", result_str)
        self.assertIn("a greeting", result_str)


class TestDictionary(unittest.TestCase):
    """Test cases for Dictionary class"""
    
    def setUp(self):
        """Set up test dictionary"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_dict.sqlite")
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        
        # Create test dictionary
        self.dictionary = Dictionary(self.db_path, self.config_path)
        
        # Add some test data
        self.dictionary.add_definition("Test Dict", "hello", "a greeting", "heh-loh", 100)
        self.dictionary.add_definition("Test Dict", "world", "the earth", "wurld", 90)
        self.dictionary.add_definition("Test Dict", "goodbye", "farewell", "good-bahy", 80)
    
    def tearDown(self):
        """Clean up"""
        self.dictionary.close()
        
        # Clean up files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dictionary_initialization(self):
        """Test dictionary initialization"""
        self.assertIsInstance(self.dictionary.config, DictionaryConfig)
        self.assertIsInstance(self.dictionary.database, DictionaryDatabase)
        self.assertIsInstance(self.dictionary.image_searcher, ImageSearcher)
    
    def test_dictionary_initialization_no_images(self):
        """Test dictionary initialization with images disabled"""
        # Create config with images disabled
        config_data = {"enable_images": False}
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f)
        
        dict_no_images = Dictionary(self.db_path, self.config_path)
        self.assertIsNone(dict_no_images.image_searcher)
        dict_no_images.close()
    
    def test_search_basic(self):
        """Test basic search functionality"""
        results = self.dictionary.search("hello")
        
        self.assertGreater(len(results), 0)
        self.assertIsInstance(results[0], DictionaryResult)
        self.assertEqual(results[0].term, "hello")
        self.assertEqual(results[0].definition, "a greeting")
    
    def test_search_empty_term(self):
        """Test search with empty term"""
        results = self.dictionary.search("")
        self.assertEqual(len(results), 0)
        
        results = self.dictionary.search("   ")
        self.assertEqual(len(results), 0)
    
    def test_search_no_results(self):
        """Test search with no matching results"""
        results = self.dictionary.search("nonexistent")
        self.assertEqual(len(results), 0)
    
    def test_search_partial_match(self):
        """Test search with partial matches"""
        results = self.dictionary.search("wor")  # Should match "world"
        self.assertGreater(len(results), 0)
        
        # Check that "world" is in the results
        terms = [r.term for r in results]
        self.assertIn("world", terms)
    
    @patch.object(ImageSearcher, 'search_images')
    def test_search_with_images(self, mock_search_images):
        """Test search with image results"""
        # Mock image search results
        mock_images = [
            {"url": "https://example.com/hello1.jpg", "title": "Hello 1"},
            {"url": "https://example.com/hello2.jpg", "title": "Hello 2"}
        ]
        mock_search_images.return_value = mock_images
        
        results = self.dictionary.search("hello", include_images=True)
        
        self.assertGreater(len(results), 0)
        self.assertGreater(len(results[0].images), 0)
        self.assertEqual(results[0].images[0], "https://example.com/hello1.jpg")
        
        mock_search_images.assert_called_once_with("hello", 5)
    
    def test_search_without_images(self):
        """Test search without images"""
        results = self.dictionary.search("hello", include_images=False)
        
        self.assertGreater(len(results), 0)
        self.assertEqual(len(results[0].images), 0)
    
    def test_add_definition(self):
        """Test adding new definitions"""
        success = self.dictionary.add_definition(
            "New Dict", 
            "test", 
            "a test definition", 
            "test-reading", 
            75
        )
        
        self.assertTrue(success)
        
        # Verify definition was added
        results = self.dictionary.search("test")
        self.assertGreater(len(results), 0)
        
        test_result = next((r for r in results if r.term == "test"), None)
        self.assertIsNotNone(test_result)
        self.assertEqual(test_result.definition, "a test definition")
    
    def test_get_search_history(self):
        """Test getting search history"""
        # Perform some searches
        self.dictionary.search("hello")
        self.dictionary.search("world")
        
        history = self.dictionary.get_search_history(10)
        
        self.assertGreaterEqual(len(history), 2)
        
        # Check that searches are in history
        terms = [h['term'] for h in history]
        self.assertIn("hello", terms)
        self.assertIn("world", terms)
    
    def test_get_dictionaries(self):
        """Test getting dictionary information"""
        dictionaries = self.dictionary.get_dictionaries()
        
        self.assertGreater(len(dictionaries), 0)
        
        # Check that our test dictionary is present
        dict_names = [d['name'] for d in dictionaries]
        self.assertIn("Test Dict", dict_names)
    
    @patch.object(ImageSearcher, 'search_images')
    def test_search_images(self, mock_search_images):
        """Test direct image search"""
        mock_results = [
            {"url": "https://example.com/cat1.jpg", "title": "Cat 1"},
            {"url": "https://example.com/cat2.jpg", "title": "Cat 2"}
        ]
        mock_search_images.return_value = mock_results
        
        results = self.dictionary.search_images("cat", 3)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['url'], "https://example.com/cat1.jpg")
        
        mock_search_images.assert_called_once_with("cat", 3)
    
    def test_search_images_disabled(self):
        """Test image search when disabled"""
        # Create dictionary with images disabled
        config_data = {"enable_images": False}
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f)
        
        dict_no_images = Dictionary(self.db_path, self.config_path)
        
        results = dict_no_images.search_images("test")
        self.assertEqual(len(results), 0)
        
        dict_no_images.close()
    
    def test_export_results_json(self):
        """Test exporting results as JSON"""
        results = self.dictionary.search("hello")
        json_export = self.dictionary.export_results(results, 'json')
        
        self.assertIsInstance(json_export, str)
        
        # Verify it's valid JSON
        parsed = json.loads(json_export)
        self.assertIsInstance(parsed, list)
        self.assertGreater(len(parsed), 0)
        self.assertIn('term', parsed[0])
        self.assertIn('definition', parsed[0])
    
    def test_export_results_html(self):
        """Test exporting results as HTML"""
        results = self.dictionary.search("hello")
        html_export = self.dictionary.export_results(results, 'html')
        
        self.assertIsInstance(html_export, str)
        self.assertIn('<html>', html_export)
        self.assertIn('hello', html_export)
        self.assertIn('a greeting', html_export)
    
    def test_export_results_txt(self):
        """Test exporting results as text"""
        results = self.dictionary.search("hello")
        txt_export = self.dictionary.export_results(results, 'txt')
        
        self.assertIsInstance(txt_export, str)
        self.assertIn('Dictionary Search Results', txt_export)
        self.assertIn('hello', txt_export)
        self.assertIn('a greeting', txt_export)
    
    def test_export_results_invalid_format(self):
        """Test exporting with invalid format"""
        results = self.dictionary.search("hello")
        export = self.dictionary.export_results(results, 'invalid')
        
        self.assertEqual(export, "")
    
    def test_callbacks(self):
        """Test callback functionality"""
        search_start_called = []
        search_complete_called = []
        error_called = []
        
        def on_search_start(term):
            search_start_called.append(term)
        
        def on_search_complete(term, results):
            search_complete_called.append((term, len(results)))
        
        def on_error(error):
            error_called.append(error)
        
        # Set callbacks
        self.dictionary.on_search_start = on_search_start
        self.dictionary.on_search_complete = on_search_complete
        self.dictionary.on_error = on_error
        
        # Perform search
        self.dictionary.search("hello")
        
        # Check callbacks were called
        self.assertEqual(len(search_start_called), 1)
        self.assertEqual(search_start_called[0], "hello")
        
        self.assertEqual(len(search_complete_called), 1)
        self.assertEqual(search_complete_called[0][0], "hello")
        self.assertGreater(search_complete_called[0][1], 0)
    
    def test_context_manager(self):
        """Test dictionary as context manager"""
        temp_db = os.path.join(self.temp_dir, "context_test.sqlite")
        temp_config = os.path.join(self.temp_dir, "context_config.json")
        
        with Dictionary(temp_db, temp_config) as dictionary:
            self.assertIsNotNone(dictionary.database)
            dictionary.add_definition("Test", "word", "definition")
        
        # Dictionary should be closed after context
        # We can verify by checking that the database file exists
        self.assertTrue(os.path.exists(temp_db))


class TestDictionaryIntegration(unittest.TestCase):
    """Integration tests for dictionary functionality"""
    
    def setUp(self):
        """Set up integration test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "integration_test.sqlite")
        self.config_path = os.path.join(self.temp_dir, "integration_config.json")
        
        self.dictionary = Dictionary(self.db_path, self.config_path)
    
    def tearDown(self):
        """Clean up"""
        self.dictionary.close()
        
        # Clean up files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_dictionary_workflow(self):
        """Test complete dictionary workflow"""
        # Add multiple definitions
        definitions = [
            ("English Dict", "cat", "a feline animal", "kat", 80),
            ("English Dict", "dog", "a canine animal", "dawg", 90),
            ("Japanese Dict", "ねこ", "cat in Japanese", "neko", 70),
            ("Spanish Dict", "gato", "cat in Spanish", "gah-toh", 60),
        ]
        
        for dict_name, term, definition, reading, frequency in definitions:
            success = self.dictionary.add_definition(dict_name, term, definition, reading, frequency)
            self.assertTrue(success)
        
        # Test search functionality
        cat_results = self.dictionary.search("cat")
        self.assertGreaterEqual(len(cat_results), 2)  # English and Japanese
        
        # Test frequency ordering
        animal_results = self.dictionary.search("animal")
        if len(animal_results) >= 2:
            self.assertGreaterEqual(animal_results[0].frequency, animal_results[1].frequency)
        
        # Test export functionality
        json_export = self.dictionary.export_results(cat_results, 'json')
        self.assertIn('cat', json_export)
        
        html_export = self.dictionary.export_results(cat_results, 'html')
        self.assertIn('<html>', html_export)
        self.assertIn('cat', html_export)
        
        # Test dictionary information
        dictionaries = self.dictionary.get_dictionaries()
        dict_names = [d['name'] for d in dictionaries]
        self.assertIn("English Dict", dict_names)
        self.assertIn("Japanese Dict", dict_names)
        self.assertIn("Spanish Dict", dict_names)
        
        # Test search history
        history = self.dictionary.get_search_history()
        terms = [h['term'] for h in history]
        self.assertIn("cat", terms)
        self.assertIn("animal", terms)


if __name__ == '__main__':
    unittest.main()