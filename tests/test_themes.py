import unittest
import os
import json
from unittest.mock import MagicMock
import sys

# Mock aqt and mw before importing ThemeManager
sys.modules["aqt"] = MagicMock()
sys.modules["aqt.qt"] = MagicMock()
mw_mock = MagicMock()
mw_mock.pm.addonFolder.return_value = "/tmp/anki_addon_test"
sys.modules["aqt"].mw = mw_mock

from src.anki_dictionary.ui.themes import ThemeManager, ThemeColors


class TestThemes(unittest.TestCase):
    def setUp(self):
        self.addon_path = "anki_dictionary"
        # Ensure the test directory exists
        os.makedirs(
            "/tmp/anki_addon_test/anki_dictionary/user_files/themes", exist_ok=True
        )
        # Mock dictInt for MIDict if needed
        self.dict_int_mock = MagicMock()
        self.dict_int_mock.iconpath = (
            "/tmp/anki_addon_test/anki_dictionary/assets/icons"
        )
        self.theme_manager = ThemeManager(self.addon_path)

    def test_default_themes_loaded(self):
        """Test that all default themes are loaded correctly."""
        expected_themes = [
            "light",
            "dark",
            "catppuccin_mocha",
            "catppuccin_latte",
            "nord",
            "solarized_light",
            "tokyo_night",
            "gruvbox",
        ]
        for theme in expected_themes:
            self.assertIn(theme, self.theme_manager.themes)
            self.assertIsInstance(self.theme_manager.themes[theme], ThemeColors)

    def test_catppuccin_mocha_colors(self):
        """Verify some specific colors of Catppuccin Mocha."""
        mocha = self.theme_manager.themes["catppuccin_mocha"]
        self.assertEqual(mocha.header_background, "#1e1e2e")
        self.assertEqual(mocha.header_text, "#cdd6f4")
        self.assertEqual(mocha.search_term, "#89b4fa")

    def test_get_css(self):
        """Test CSS generation for a theme."""
        css = self.theme_manager.get_css("catppuccin_mocha")
        self.assertIn("#1e1e2e", css)
        self.assertIn("#cdd6f4", css)

    def test_is_dark(self):
        """Test is_dark logic."""
        self.theme_manager.current_theme = "dark"
        self.assertTrue(self.theme_manager.is_dark)

        self.theme_manager.current_theme = "light"
        self.assertFalse(self.theme_manager.is_dark)

        self.theme_manager.current_theme = "catppuccin_mocha"
        self.assertTrue(self.theme_manager.is_dark)

        self.theme_manager.current_theme = "catppuccin_latte"
        self.assertFalse(self.theme_manager.is_dark)


if __name__ == "__main__":
    unittest.main()
