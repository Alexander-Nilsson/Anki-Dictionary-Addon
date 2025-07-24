#!/usr/bin/env python3
"""
Tests for ConfigManager class
"""

import unittest
import tempfile
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from external_launcher import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addon_path = Path(self.temp_dir)
        self.config_manager = ConfigManager(self.addon_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_default_config_structure(self):
        """Test that default configuration has expected structure."""
        expected_keys = {
            "maxWidth", "jReadingEdit", "enableHotkeys", 
            "dictionaryPath", "theme"
        }
        
        self.assertEqual(set(ConfigManager.DEFAULT_CONFIG.keys()), expected_keys)
        self.assertIsInstance(ConfigManager.DEFAULT_CONFIG["maxWidth"], int)
        self.assertIsInstance(ConfigManager.DEFAULT_CONFIG["jReadingEdit"], bool)
    
    def test_load_config_no_file(self):
        """Test loading config when no config file exists."""
        config = self.config_manager.load_config()
        
        self.assertEqual(config, ConfigManager.DEFAULT_CONFIG)
    
    def test_load_config_valid_file(self):
        """Test loading config from valid JSON file."""
        test_config = {
            "maxWidth": 1000,
            "theme": "dark",
            "customSetting": "test"
        }
        
        config_file = self.addon_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        config = self.config_manager.load_config()
        
        # Should merge with defaults
        self.assertEqual(config["maxWidth"], 1000)  # From file
        self.assertEqual(config["theme"], "dark")   # From file
        self.assertEqual(config["jReadingEdit"], True)  # From defaults
        self.assertEqual(config["customSetting"], "test")  # From file
    
    def test_load_config_invalid_json(self):
        """Test loading config when JSON file is invalid."""
        config_file = self.addon_path / "config.json"
        with open(config_file, 'w') as f:
            f.write("invalid json content")
        
        config = self.config_manager.load_config()
        
        # Should fall back to defaults
        self.assertEqual(config, ConfigManager.DEFAULT_CONFIG)
    
    def test_save_config_success(self):
        """Test successful config saving."""
        test_config = {"maxWidth": 1200, "theme": "custom"}
        
        result = self.config_manager.save_config(test_config)
        
        self.assertTrue(result)
        
        # Verify file was created and contains correct data
        config_file = self.addon_path / "config.json"
        self.assertTrue(config_file.exists())
        
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config, test_config)
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_save_config_failure(self, mock_file):
        """Test config saving when file operation fails."""
        test_config = {"maxWidth": 1200}
        
        result = self.config_manager.save_config(test_config)
        
        self.assertFalse(result)
    
    def test_config_file_path(self):
        """Test that config file path is correctly set."""
        expected_path = self.addon_path / "config.json"
        self.assertEqual(self.config_manager.config_file, expected_path)
    
    def test_load_config_preserves_defaults(self):
        """Test that loading config preserves all default values."""
        # Create config file with only one setting
        test_config = {"maxWidth": 1500}
        
        config_file = self.addon_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        config = self.config_manager.load_config()
        
        # All default keys should be present
        for key in ConfigManager.DEFAULT_CONFIG:
            self.assertIn(key, config)
        
        # Custom value should override default
        self.assertEqual(config["maxWidth"], 1500)
        
        # Other defaults should remain
        self.assertEqual(config["jReadingEdit"], ConfigManager.DEFAULT_CONFIG["jReadingEdit"])


if __name__ == '__main__':
    unittest.main()