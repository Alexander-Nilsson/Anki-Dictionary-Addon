#!/usr/bin/env python3
"""
Tests for DictionaryLauncher class
"""

import unittest
import tempfile
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from external_launcher import DictionaryLauncher, MinimalAnkiEnvironment


class TestDictionaryLauncher(unittest.TestCase):
    """Test cases for DictionaryLauncher."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.addon_path = Path(self.temp_dir)
        self.launcher = DictionaryLauncher(self.addon_path)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test launcher initialization."""
        self.assertEqual(self.launcher.addon_path, self.addon_path)
        self.assertIsInstance(self.launcher.environment, MinimalAnkiEnvironment)

    @patch("PyQt6.QtWidgets.QApplication")
    @patch("PyQt6.QtGui.QIcon")
    def test_create_qt_application_success(self, mock_qicon, mock_qapp):
        """Test successful Qt application creation."""
        mock_app = MagicMock()
        mock_qapp.return_value = mock_app

        app = self.launcher.create_qt_application()

        self.assertEqual(app, mock_app)
        mock_qapp.assert_called_once()
        mock_app.setApplicationName.assert_called_with("Anki Dictionary Addon")

    @patch("standalone_launcher.QApplication")
    @patch("standalone_launcher.QIcon")
    def test_create_qt_application_with_icon(self, mock_qicon, mock_qapp):
        """Test Qt application creation with icon."""
        # Create icon file
        icons_dir = self.addon_path / "icons"
        icons_dir.mkdir()
        icon_file = icons_dir / "dictionary.png"
        icon_file.touch()

        mock_app = MagicMock()
        mock_qapp.return_value = mock_app
        mock_icon = MagicMock()
        mock_qicon.return_value = mock_icon

        app = self.launcher.create_qt_application()

        mock_qicon.assert_called_with(str(icon_file))
        mock_app.setWindowIcon.assert_called_with(mock_icon)

    @patch("builtins.__import__", side_effect=ImportError("No PyQt6"))
    def test_create_qt_application_import_error(self, mock_import):
        """Test Qt application creation when PyQt6 is not available."""
        app = self.launcher.create_qt_application()

        self.assertIsNone(app)

    @patch("standalone_launcher.DictInterface")
    def test_create_dictionary_interface_success(self, mock_dict_interface):
        """Test successful dictionary interface creation."""
        mock_mw = MagicMock()
        mock_mw.miDictDB = MagicMock()

        mock_interface = MagicMock()
        mock_dict_interface.return_value = mock_interface

        interface = self.launcher.create_dictionary_interface(mock_mw)

        self.assertEqual(interface, mock_interface)
        mock_dict_interface.assert_called_once()

        # Check call arguments
        call_args = mock_dict_interface.call_args
        self.assertEqual(call_args[1]["dictdb"], mock_mw.miDictDB)
        self.assertEqual(call_args[1]["mw"], mock_mw)
        self.assertEqual(call_args[1]["path"], str(self.addon_path))
        self.assertIn("Standalone Mode", call_args[1]["welcome"])

    @patch(
        "standalone_launcher.DictInterface", side_effect=Exception("Interface error")
    )
    def test_create_dictionary_interface_failure(self, mock_dict_interface):
        """Test dictionary interface creation failure."""
        mock_mw = MagicMock()

        interface = self.launcher.create_dictionary_interface(mock_mw)

        self.assertIsNone(interface)

    @patch("standalone_launcher.DependencyChecker.check_dependencies")
    def test_launch_missing_dependencies(self, mock_check_deps):
        """Test launch when dependencies are missing."""
        mock_check_deps.return_value = (False, ["PyQt6 - GUI framework"])

        result = self.launcher.launch()

        self.assertEqual(result, 1)

    @patch("standalone_launcher.DependencyChecker.check_dependencies")
    @patch.object(DictionaryLauncher, "create_qt_application")
    def test_launch_qt_app_creation_failure(self, mock_create_app, mock_check_deps):
        """Test launch when Qt application creation fails."""
        mock_check_deps.return_value = (True, [])
        mock_create_app.return_value = None

        result = self.launcher.launch()

        self.assertEqual(result, 1)

    @patch("standalone_launcher.DependencyChecker.check_dependencies")
    @patch.object(DictionaryLauncher, "create_qt_application")
    @patch.object(MinimalAnkiEnvironment, "setup_environment")
    def test_launch_environment_setup_failure(
        self, mock_setup_env, mock_create_app, mock_check_deps
    ):
        """Test launch when environment setup fails."""
        mock_check_deps.return_value = (True, [])
        mock_create_app.return_value = MagicMock()
        mock_setup_env.return_value = None

        result = self.launcher.launch()

        self.assertEqual(result, 1)

    @patch("standalone_launcher.DependencyChecker.check_dependencies")
    @patch.object(DictionaryLauncher, "create_qt_application")
    @patch.object(MinimalAnkiEnvironment, "setup_environment")
    @patch.object(DictionaryLauncher, "create_dictionary_interface")
    def test_launch_interface_creation_failure(
        self, mock_create_interface, mock_setup_env, mock_create_app, mock_check_deps
    ):
        """Test launch when dictionary interface creation fails."""
        mock_check_deps.return_value = (True, [])
        mock_create_app.return_value = MagicMock()
        mock_setup_env.return_value = MagicMock()
        mock_create_interface.return_value = None

        result = self.launcher.launch()

        self.assertEqual(result, 1)

    @patch("standalone_launcher.DependencyChecker.check_dependencies")
    @patch.object(DictionaryLauncher, "create_qt_application")
    @patch.object(MinimalAnkiEnvironment, "setup_environment")
    @patch.object(DictionaryLauncher, "create_dictionary_interface")
    def test_launch_success(
        self, mock_create_interface, mock_setup_env, mock_create_app, mock_check_deps
    ):
        """Test successful launch."""
        mock_check_deps.return_value = (True, [])

        mock_app = MagicMock()
        mock_app.exec.return_value = 0
        mock_create_app.return_value = mock_app

        mock_mw = MagicMock()
        mock_setup_env.return_value = mock_mw

        mock_interface = MagicMock()
        mock_create_interface.return_value = mock_interface

        result = self.launcher.launch()

        self.assertEqual(result, 0)

        # Verify interface was shown
        mock_interface.show.assert_called_once()
        mock_interface.raise_.assert_called_once()
        mock_interface.activateWindow.assert_called_once()

        # Verify Qt event loop was started
        mock_app.exec.assert_called_once()


if __name__ == "__main__":
    unittest.main()
