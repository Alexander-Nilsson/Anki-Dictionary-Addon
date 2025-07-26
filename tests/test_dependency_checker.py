#!/usr/bin/env python3
"""
Tests for DependencyChecker class
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from external_launcher import DependencyChecker


class TestDependencyChecker(unittest.TestCase):
    """Test cases for DependencyChecker."""
    
    def test_required_modules_defined(self):
        """Test that required modules are properly defined."""
        self.assertIsInstance(DependencyChecker.REQUIRED_MODULES, dict)
        self.assertIn('PyQt6', DependencyChecker.REQUIRED_MODULES)
        self.assertIn('anki', DependencyChecker.REQUIRED_MODULES)
        self.assertIn('aqt', DependencyChecker.REQUIRED_MODULES)
    
    @patch('builtins.__import__')
    def test_check_dependencies_all_available(self, mock_import):
        """Test dependency checking when all modules are available."""
        mock_import.return_value = MagicMock()
        
        success, missing = DependencyChecker.check_dependencies()
        
        self.assertTrue(success)
        self.assertEqual(len(missing), 0)
        
        # Verify all required modules were checked
        expected_calls = len(DependencyChecker.REQUIRED_MODULES)
        self.assertEqual(mock_import.call_count, expected_calls)
    
    @patch('builtins.__import__')
    def test_check_dependencies_some_missing(self, mock_import):
        """Test dependency checking when some modules are missing."""
        def mock_import_side_effect(module_name):
            if module_name == 'PyQt6':
                raise ImportError(f"No module named '{module_name}'")
            return MagicMock()
        
        mock_import.side_effect = mock_import_side_effect
        
        success, missing = DependencyChecker.check_dependencies()
        
        self.assertFalse(success)
        self.assertEqual(len(missing), 1)
        self.assertIn('PyQt6', missing[0])
    
    @patch('builtins.__import__')
    def test_check_dependencies_all_missing(self, mock_import):
        """Test dependency checking when all modules are missing."""
        mock_import.side_effect = ImportError("No module found")
        
        success, missing = DependencyChecker.check_dependencies()
        
        self.assertFalse(success)
        self.assertEqual(len(missing), len(DependencyChecker.REQUIRED_MODULES))
    
    def test_get_install_command_basic(self):
        """Test install command generation for basic modules."""
        missing = ['anki - Anki core library']
        command = DependencyChecker.get_install_command(missing)
        
        self.assertEqual(command, "pip install anki")
    
    def test_get_install_command_with_pyqt6(self):
        """Test install command generation includes PyQt6-WebEngine for PyQt6."""
        missing = ['PyQt6 - PyQt6 GUI framework']
        command = DependencyChecker.get_install_command(missing)
        
        self.assertIn("PyQt6", command)
        self.assertIn("PyQt6-WebEngine", command)
    
    def test_get_install_command_multiple(self):
        """Test install command generation for multiple modules."""
        missing = [
            'anki - Anki core library',
            'aqt - Anki Qt interface'
        ]
        command = DependencyChecker.get_install_command(missing)
        
        self.assertIn("anki", command)
        self.assertIn("aqt", command)
        self.assertTrue(command.startswith("pip install"))


if __name__ == '__main__':
    unittest.main()