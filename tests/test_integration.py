#!/usr/bin/env python3
"""
Integration tests for the standalone launcher
"""

import unittest
import tempfile
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from external_launcher import main, DictionaryLauncher


class TestIntegration(unittest.TestCase):
    """Integration test cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addon_path = Path(self.temp_dir)
        
        # Create basic addon structure
        (self.addon_path / "icons").mkdir()
        (self.addon_path / "assets" / "icons" / "dictionary.png").touch()
        
        # Create config file
        config = {
            "maxWidth": 1000,
            "theme": "dark",
            "enableHotkeys": True
        }
        with open(self.addon_path / "config.json", 'w') as f:
            json.dump(config, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('standalone_launcher.Path')
    @patch('standalone_launcher.DictionaryLauncher')
    def test_main_success(self, mock_launcher_class, mock_path):
        """Test successful main function execution."""
        mock_path.return_value.parent = self.addon_path
        
        mock_launcher = MagicMock()
        mock_launcher.launch.return_value = 0
        mock_launcher_class.return_value = mock_launcher
        
        result = main()
        
        self.assertEqual(result, 0)
        mock_launcher_class.assert_called_once_with(self.addon_path)
        mock_launcher.launch.assert_called_once()
    
    @patch('standalone_launcher.Path')
    @patch('standalone_launcher.DictionaryLauncher')
    def test_main_launcher_exception(self, mock_launcher_class, mock_path):
        """Test main function when launcher raises exception."""
        mock_path.return_value.parent = self.addon_path
        
        mock_launcher = MagicMock()
        mock_launcher.launch.side_effect = Exception("Launch error")
        mock_launcher_class.return_value = mock_launcher
        
        result = main()
        
        self.assertEqual(result, 1)
    
    @patch('standalone_launcher.Path')
    @patch('standalone_launcher.DictionaryLauncher')
    def test_main_keyboard_interrupt(self, mock_launcher_class, mock_path):
        """Test main function handling keyboard interrupt."""
        mock_path.return_value.parent = self.addon_path
        
        mock_launcher = MagicMock()
        mock_launcher.launch.side_effect = KeyboardInterrupt()
        mock_launcher_class.return_value = mock_launcher
        
        result = main()
        
        self.assertEqual(result, 0)
    
    @patch('standalone_launcher.DependencyChecker.check_dependencies')
    @patch('standalone_launcher.QApplication')
    @patch('standalone_launcher.aqt')
    @patch('standalone_launcher.dictdb')
    @patch('standalone_launcher.DictInterface')
    def test_full_launch_workflow(self, mock_dict_interface, mock_dictdb, mock_aqt,
                                 mock_qapp, mock_check_deps):
        """Test the complete launch workflow."""
        # Setup mocks
        mock_check_deps.return_value = (True, [])
        
        mock_app = MagicMock()
        mock_app.exec.return_value = 0
        mock_qapp.return_value = mock_app
        
        mock_db = MagicMock()
        mock_dictdb.DictDB.return_value = mock_db
        
        mock_interface = MagicMock()
        mock_dict_interface.return_value = mock_interface
        
        # Create launcher and run
        launcher = DictionaryLauncher(self.addon_path)
        result = launcher.launch()
        
        # Verify workflow
        self.assertEqual(result, 0)
        
        # Check dependencies were checked
        mock_check_deps.assert_called_once()
        
        # Check Qt app was created
        mock_qapp.assert_called_once()
        mock_app.setApplicationName.assert_called_with("Anki Dictionary Addon")
        
        # Check database was initialized
        mock_dictdb.DictDB.assert_called_once()
        
        # Check interface was created and shown
        mock_dict_interface.assert_called_once()
        mock_interface.show.assert_called_once()
        mock_interface.raise_.assert_called_once()
        mock_interface.activateWindow.assert_called_once()
        
        # Check Qt event loop was started
        mock_app.exec.assert_called_once()
    
    def test_config_loading_integration(self):
        """Test configuration loading integration."""
        # Create launcher
        launcher = DictionaryLauncher(self.addon_path)
        
        # Create mock main window
        mock_mw = launcher.environment.create_mock_main_window()
        
        # Verify config was loaded correctly
        self.assertEqual(mock_mw.AnkiDictConfig["maxWidth"], 1000)
        self.assertEqual(mock_mw.AnkiDictConfig["theme"], "dark")
        self.assertTrue(mock_mw.AnkiDictConfig["enableHotkeys"])
        
        # Verify defaults were preserved
        self.assertIn("jReadingEdit", mock_mw.AnkiDictConfig)
        self.assertIn("dictionaryPath", mock_mw.AnkiDictConfig)
    
    def test_path_setup_integration(self):
        """Test path setup integration."""
        # Create vendor directory
        vendor_dir = self.addon_path / "vendor"
        vendor_dir.mkdir()
        
        # Create launcher (triggers path setup)
        launcher = DictionaryLauncher(self.addon_path)
        
        # Verify paths were added
        self.assertIn(str(self.addon_path), sys.path)
        self.assertIn(str(vendor_dir), sys.path)
        
        # Verify temp directory was created
        temp_dir = self.addon_path / "temp"
        self.assertTrue(temp_dir.exists())
        self.assertTrue(temp_dir.is_dir())
    
    @patch('standalone_launcher.DependencyChecker.check_dependencies')
    def test_error_handling_integration(self, mock_check_deps):
        """Test error handling integration."""
        # Test missing dependencies
        mock_check_deps.return_value = (False, ['PyQt6 - GUI framework'])
        
        launcher = DictionaryLauncher(self.addon_path)
        result = launcher.launch()
        
        self.assertEqual(result, 1)
    
    def test_mock_objects_integration(self):
        """Test that mock objects have all required attributes."""
        launcher = DictionaryLauncher(self.addon_path)
        mock_mw = launcher.environment.create_mock_main_window()
        
        # Test MockMainWindow attributes
        required_attrs = [
            'addonManager', 'AnkiDictConfig', 'DictExportingDefinitions',
            'dictSettings', 'miDictDB', 'refreshAnkiDictConfig',
            'dictEditorLoadedAfterDictionary', 'DictBulkMediaExportWasCancelled'
        ]
        
        for attr in required_attrs:
            self.assertTrue(hasattr(mock_mw, attr), f"Missing attribute: {attr}")
        
        # Test MockAddonManager functionality
        config = mock_mw.addonManager.getConfig("test")
        self.assertIsInstance(config, dict)
        
        # Test refresh functionality
        new_config = {"test": "value"}
        mock_mw.refreshAnkiDictConfig(new_config)
        self.assertEqual(mock_mw.AnkiDictConfig, new_config)


if __name__ == '__main__':
    unittest.main()