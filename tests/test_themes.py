import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anki_dictionary.ui.themes import ThemeColors, ThemeManager


class TestThemes(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.addon_path = self.test_dir.name
        os.makedirs(
            os.path.join(self.addon_path, "user_files", "themes"), exist_ok=True
        )
        self.theme_manager = ThemeManager(self.addon_path)

    def tearDown(self):
        self.test_dir.cleanup()

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
