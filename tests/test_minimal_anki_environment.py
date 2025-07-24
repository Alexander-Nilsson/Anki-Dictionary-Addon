#!/usr/bin/env python3
"""
Tests for MinimalAnkiEnvironment class
"""

import unittest
import tempfile
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from standalone_launcher import MinimalAnkiEnvironment, ConfigManager


class TestMinimalAnkiEnvironment(unittest.TestCase):
    """Test cases for MinimalAnkiEnvironment."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addon_path = Path(self.temp_dir)
        self.environment = MinimalAnkiEnvironment(self.addon_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_setup_paths_creates_temp_dir(self):
        """Test that setup_paths creates temp directory."""
        temp_dir = self.addon_path / 'temp'
        
        # Should be created during __init__
        self.assertTrue(temp_dir.exists())
        self.assertTrue(temp_dir.is_dir())
    
    def test_setup_paths_adds_to_sys_path(self):
        """Test that setup_paths adds addon path to sys.path."""
        # Path should be added during __init__
        self.assertIn(str(self.addon_path), sys.path)
    
    def test_setup_paths_adds_vendor_path(self):
        """Test that setup_paths adds vendor path if it exists."""
        # Create vendor directory
        vendor_path = self.addon_path / 'vendor'
        vendor_path.mkdir()
        
        # Create new environment to trigger path setup
        env = MinimalAnkiEnvironment(self.addon_path)
        
        self.assertIn(str(vendor_path), sys.path)
    
    def test_create_mock_main_window_structure(self):
        """Test that mock main window has required structure."""
        mock_mw = self.environment.create_mock_main_window()
        
        # Check required attributes
        self.assertTrue(hasattr(mock_mw, 'addonManager'))
        self.assertTrue(hasattr(mock_mw, 'AnkiDictConfig'))
        self.assertTrue(hasattr(mock_mw, 'DictExportingDefinitions'))
        self.assertTrue(hasattr(mock_mw, 'dictSettings'))
        self.assertTrue(hasattr(mock_mw, 'miDictDB'))
        self.assertTrue(hasattr(mock_mw, 'refreshAnkiDictConfig'))
        
        # Check initial values
        self.assertFalse(mock_mw.DictExportingDefinitions)
        self.assertFalse(mock_mw.dictSettings)
        self.assertIsNone(mock_mw.miDictDB)
    
    def test_mock_addon_manager_get_config(self):
        """Test that mock addon manager returns config."""
        mock_mw = self.environment.create_mock_main_window()
        
        config = mock_mw.addonManager.getConfig("test_addon")
        
        # Should return the loaded configuration
        self.assertIsInstance(config, dict)
        self.assertIn('maxWidth', config)
    
    def test_mock_main_window_refresh_config(self):
        """Test mock main window config refresh functionality."""
        mock_mw = self.environment.create_mock_main_window()
        
        # Test refresh with new config
        new_config = {"maxWidth": 1500, "theme": "test"}
        mock_mw.refreshAnkiDictConfig(new_config)
        
        self.assertEqual(mock_mw.AnkiDictConfig, new_config)
    
    @patch('standalone_launcher.dictdb')
    def test_initialize_database_success(self, mock_dictdb):
        """Test successful database initialization."""
        mock_db = MagicMock()
        mock_dictdb.DictDB.return_value = mock_db
        
        mock_mw = self.environment.create_mock_main_window()
        result = self.environment.initialize_database(mock_mw)
        
        self.assertTrue(result)
        self.assertEqual(mock_mw.miDictDB, mock_db)
        mock_dictdb.DictDB.assert_called_once()
    
    @patch('standalone_launcher.dictdb')
    def test_initialize_database_failure(self, mock_dictdb):
        """Test database initialization failure."""
        mock_dictdb.DictDB.side_effect = Exception("Database error")
        
        mock_mw = self.environment.create_mock_main_window()
        result = self.environment.initialize_database(mock_mw)
        
        self.assertFalse(result)
        self.assertIsNone(mock_mw.miDictDB)
    
    @patch('standalone_launcher.dictdb')
    @patch('standalone_launcher.aqt')
    def test_setup_environment_success(self, mock_aqt, mock_dictdb):
        """Test successful environment setup."""
        mock_db = MagicMock()
        mock_dictdb.DictDB.return_value = mock_db
        
        result = self.environment.setup_environment()
        
        self.assertIsNotNone(result)
        self.assertEqual(result.miDictDB, mock_db)
        
        # Check that aqt.mw was set
        mock_aqt.mw = result
    
    @patch('builtins.__import__', side_effect=ImportError("No module named 'aqt'"))
    def test_setup_environment_import_failure(self, mock_import):
        """Test environment setup when aqt import fails."""
        result = self.environment.setup_environment()
        
        self.assertIsNone(result)
    
    @patch('standalone_launcher.dictdb')
    @patch('standalone_launcher.aqt')
    def test_setup_environment_database_failure(self, mock_aqt, mock_dictdb):
        """Test environment setup when database initialization fails."""
        mock_dictdb.DictDB.side_effect = Exception("Database error")
        
        result = self.environment.setup_environment()
        
        self.assertIsNone(result)
    
    def test_config_manager_integration(self):
        """Test integration with ConfigManager."""
        # Create a config file
        config_data = {"maxWidth": 1200, "theme": "dark"}
        config_file = self.addon_path / "config.json"
        
        import json
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Create mock main window
        mock_mw = self.environment.create_mock_main_window()
        
        # Should have loaded the config
        self.assertEqual(mock_mw.AnkiDictConfig["maxWidth"], 1200)
        self.assertEqual(mock_mw.AnkiDictConfig["theme"], "dark")
        
        # Should also have defaults
        self.assertIn("jReadingEdit", mock_mw.AnkiDictConfig)


if __name__ == '__main__':
    unittest.main()