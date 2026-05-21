import unittest
import os
import json
from unittest.mock import MagicMock
import sys

# Mock aqt and mw before importing ThemeManager
sys.modules["aqt"] = MagicMock()
sys.modules["aqt.qt"] = MagicMock()
sys.modules["aqt.utils"] = MagicMock()
mw_mock = MagicMock()
mw_mock.pm.addonFolder.return_value = "/tmp/anki_addon_test"
sys.modules["aqt"].mw = mw_mock
sys.modules["anki"] = MagicMock()

from src.anki_dictionary.ui.themes import ThemeManager, ThemeColors


class TestThemes(unittest.TestCase):
    def setUp(self):
        self.addon_path = "anki_dictionary"
        os.makedirs(
            "/tmp/anki_addon_test/anki_dictionary/user_files/themes", exist_ok=True
        )
        self.dict_int_mock = MagicMock()
        self.dict_int_mock.iconpath = (
            "/tmp/anki_addon_test/anki_dictionary/assets/icons"
        )
        self.theme_manager = ThemeManager(self.addon_path)

    def test_default_themes_loaded(self):
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
        mocha = self.theme_manager.themes["catppuccin_mocha"]
        self.assertEqual(mocha.header_background, "#1e1e2e")
        self.assertEqual(mocha.header_text, "#cdd6f4")
        self.assertEqual(mocha.search_term, "#89b4fa")

    def test_get_css(self):
        css = self.theme_manager.get_css("catppuccin_mocha")
        self.assertIn("#1e1e2e", css)
        self.assertIn("#cdd6f4", css)

    def test_is_dark(self):
        self.theme_manager.current_theme = "dark"
        self.assertTrue(self.theme_manager.is_dark)
        self.theme_manager.current_theme = "light"
        self.assertFalse(self.theme_manager.is_dark)
        self.theme_manager.current_theme = "catppuccin_mocha"
        self.assertTrue(self.theme_manager.is_dark)
        self.theme_manager.current_theme = "catppuccin_latte"
        self.assertFalse(self.theme_manager.is_dark)

    def test_get_qt_styles(self):
        css = self.theme_manager.get_qt_styles("light")
        self.assertIn("QLabel", css)
        self.assertIn("QLineEdit", css)

    def test_get_combo_style(self):
        css = self.theme_manager.get_combo_style("light")
        self.assertIn("QComboBox", css)

    def test_validate_current_theme_resets_missing(self):
        self.theme_manager.current_theme = "nonexistent"
        self.theme_manager._validate_current_theme()
        self.assertEqual(self.theme_manager.current_theme, "light")


if __name__ == "__main__":
    unittest.main()
