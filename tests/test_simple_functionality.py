#!/usr/bin/env python3
"""
Simple functionality tests that don't require complex mocking
"""

import unittest
import tempfile
import sys
import os
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from external_launcher import (
    DependencyChecker, ConfigManager, MinimalAnkiEnvironment, 
    DictionaryLauncher, main
)


class TestSimpleFunctionality(unittest.TestCase):
    """Test basic functionality without complex dependencies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addon_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_dependency_checker_basic(self):
        """Test basic dependency checker functionality."""
        # Test that required modules are defined
        self.assertIsInstance(DependencyChecker.REQUIRED_MODULES, dict)
        self.assertTrue(len(DependencyChecker.REQUIRED_MODULES) > 0)
        
        # Test install command generation
        missing = ['anki - Anki core library']
        command = DependencyChecker.get_install_command(missing)
        self.assertIn('pip install', command)
        self.assertIn('anki', command)
    
    def test_config_manager_basic(self):
        """Test basic config manager functionality."""
        config_manager = ConfigManager(self.addon_path)
        
        # Test default config loading
        config = config_manager.load_config()
        self.assertIsInstance(config, dict)
        self.assertIn('maxWidth', config)
        self.assertIn('theme', config)
        
        # Test config saving
        test_config = {'test': 'value'}
        result = config_manager.save_config(test_config)
        self.assertTrue(result)
        
        # Verify file was created
        config_file = self.addon_path / 'config.json'
        self.assertTrue(config_file.exists())
    
    def test_minimal_anki_environment_basic(self):
        """Test basic minimal Anki environment functionality."""
        env = MinimalAnkiEnvironment(self.addon_path)
        
        # Test temp directory creation
        temp_dir = self.addon_path / 'temp'
        self.assertTrue(temp_dir.exists())
        
        # Test path setup
        self.assertIn(str(self.addon_path), sys.path)
        
        # Test mock main window creation
        mock_mw = env.create_mock_main_window()
        self.assertTrue(hasattr(mock_mw, 'AnkiDictConfig'))
        self.assertTrue(hasattr(mock_mw, 'addonManager'))
        self.assertTrue(hasattr(mock_mw, 'refreshAnkiDictConfig'))
    
    def test_dictionary_launcher_basic(self):
        """Test basic dictionary launcher functionality."""
        launcher = DictionaryLauncher(self.addon_path)
        
        # Test initialization
        self.assertEqual(launcher.addon_path, self.addon_path)
        self.assertIsInstance(launcher.environment, MinimalAnkiEnvironment)
    
    def test_config_file_handling(self):
        """Test configuration file handling."""
        # Create a config file
        config_data = {
            'maxWidth': 1200,
            'theme': 'dark',
            'customSetting': 'test'
        }
        
        config_file = self.addon_path / 'config.json'
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Test loading
        config_manager = ConfigManager(self.addon_path)
        loaded_config = config_manager.load_config()
        
        # Should have custom values
        self.assertEqual(loaded_config['maxWidth'], 1200)
        self.assertEqual(loaded_config['theme'], 'dark')
        self.assertEqual(loaded_config['customSetting'], 'test')
        
        # Should also have defaults
        self.assertIn('jReadingEdit', loaded_config)
    
    def test_invalid_config_handling(self):
        """Test handling of invalid configuration files."""
        # Create invalid JSON file
        config_file = self.addon_path / 'config.json'
        with open(config_file, 'w') as f:
            f.write('invalid json content')
        
        # Should fall back to defaults
        config_manager = ConfigManager(self.addon_path)
        config = config_manager.load_config()
        
        self.assertEqual(config, ConfigManager.DEFAULT_CONFIG)
    
    def test_vendor_path_handling(self):
        """Test vendor path handling."""
        # Create vendor directory
        vendor_dir = self.addon_path / 'vendor'
        vendor_dir.mkdir()
        
        # Create environment (should add vendor to path)
        env = MinimalAnkiEnvironment(self.addon_path)
        
        self.assertIn(str(vendor_dir), sys.path)
    
    def test_mock_addon_manager(self):
        """Test mock addon manager functionality."""
        env = MinimalAnkiEnvironment(self.addon_path)
        mock_mw = env.create_mock_main_window()
        
        # Test getConfig method
        config = mock_mw.addonManager.getConfig('test_addon')
        self.assertIsInstance(config, dict)
    
    def test_mock_main_window_refresh(self):
        """Test mock main window config refresh."""
        env = MinimalAnkiEnvironment(self.addon_path)
        mock_mw = env.create_mock_main_window()
        
        # Test refresh with new config
        new_config = {'test': 'value'}
        mock_mw.refreshAnkiDictConfig(new_config)
        
        self.assertEqual(mock_mw.AnkiDictConfig, new_config)
    
    def test_path_setup_integration(self):
        """Test complete path setup."""
        # Create addon structure
        (self.addon_path / 'vendor').mkdir()
        (self.addon_path / 'icons').mkdir()
        
        # Create launcher
        launcher = DictionaryLauncher(self.addon_path)
        
        # Verify paths
        self.assertIn(str(self.addon_path), sys.path)
        self.assertIn(str(self.addon_path / 'vendor'), sys.path)
        
        # Verify temp directory
        self.assertTrue((self.addon_path / 'temp').exists())


class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios."""
    
    def test_config_save_error_handling(self):
        """Test config save error handling."""
        # Try to save to non-existent directory
        bad_path = Path('/nonexistent/path')
        config_manager = ConfigManager(bad_path)
        
        result = config_manager.save_config({'test': 'value'})
        self.assertFalse(result)
    
    def test_missing_addon_files(self):
        """Test behavior when addon files are missing."""
        temp_dir = tempfile.mkdtemp()
        addon_path = Path(temp_dir)
        
        try:
            # Should still work without addon files
            launcher = DictionaryLauncher(addon_path)
            self.assertIsNotNone(launcher)
            
            # Should create temp directory
            self.assertTrue((addon_path / 'temp').exists())
            
        finally:
            import shutil
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()