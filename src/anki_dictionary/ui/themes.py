from dataclasses import dataclass
from typing import Dict
import json
import os
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from aqt import mw


@dataclass
class ThemeColors:
    # Base colors
    header_background: str  # Previously "background"
    selector: str  # Previously "background_secondary"
    header_text: str  # Previously "text"
    search_term: str  # Previously "text_secondary"
    border: str

    # UI Element colors
    anki_button_background: str  # Previously "button_bg"
    anki_button_text: str  # Previously "button_text"
    tab_hover: str  # Previously "tab_hover_bg"

    # Gradient definitions
    current_tab_gradient_top: str  # Previously "button_gradient_start"
    current_tab_gradient_bottom: str  # Previously "button_gradient_end"

    # Accent colors
    example_highlight: str  # Previously "accent_secondary"

    # Definition and term colors
    definition_background: str  # Previously "definitionBlock_bg"
    definition_text: str  # Previously "definitionBlock_color"
    pitch_accent_color: str  # Previously "altterm_color"


class ThemeManager:
    def __init__(self, addon_path):
        self.addon_path = addon_path
        self.themes_file = os.path.join(
            mw.pm.addonFolder(), addon_path, "user_files/themes", "themes.json"
        )
        self.active_theme_file = os.path.join(
            mw.pm.addonFolder(), addon_path, "user_files/themes", "active.json"
        )
        self.current_theme = "light"
        self.themes = self._load_default_themes()
        self._load_user_themes()
        self._load_active_theme()

    def _load_default_themes(self) -> Dict[str, ThemeColors]:
        return {
            "light": ThemeColors(
                header_background="#FFFFFF",
                selector="#F0F0F0",
                header_text="#000000",
                search_term="#444444",
                border="#000000",
                anki_button_background="#F0F0F0",
                anki_button_text="#000000",
                tab_hover="#E0E0E0",
                current_tab_gradient_top="#FFFFFF",
                current_tab_gradient_bottom="#C0C0C0",
                example_highlight="#444444",
                definition_background="#FFFFFF",
                definition_text="#000000",
                pitch_accent_color="#FFFFFF",
            ),
            "dark": ThemeColors(
                header_background="#272828",
                selector="#1A1A1A",
                header_text="#FFFFFF",
                search_term="#CCCCCC",
                border="#FFFFFF",
                anki_button_background="#272828",
                anki_button_text="#FFFFFF",
                tab_hover="#333333",
                current_tab_gradient_top="#272828",
                current_tab_gradient_bottom="#000000",
                example_highlight="#CCCCCC",
                definition_background="#FFFFFF",
                definition_text="#000000",
                pitch_accent_color="#FFFFFF",
            ),
            "pink": ThemeColors(
                header_background="#f4dfdf",
                selector="#d0b3f3",
                header_text="#000000",
                search_term="#ab5283",
                border="#ffffff",
                anki_button_background="#F0F0F0",
                anki_button_text="#000000",
                tab_hover="#E0E0E0",
                current_tab_gradient_top="#FFFFFF",
                current_tab_gradient_bottom="#C0C0C0",
                example_highlight="#d2ffff",
                definition_background="#FFFFFF",
                definition_text="#000000",
                pitch_accent_color="#FFFFFF",
            ),
            "multi": ThemeColors(
                header_background="#f4d3d9",
                selector="#d0b3f3",
                header_text="#70aab9",
                search_term="#ab5283",
                border="#ffffff",
                anki_button_background="#f3867c",
                anki_button_text="#306932",
                tab_hover="#48e65d",
                current_tab_gradient_top="#c3d4f8",
                current_tab_gradient_bottom="#f8d5ed",
                example_highlight="#d2ffff",
                definition_background="#FFFFFF",
                definition_text="#000000",
                pitch_accent_color="#FFFFFF",
            ),
        }

    def _load_user_themes(self):
        """Load user-defined themes from themes.json"""
        if os.path.exists(self.themes_file):
            try:
                with open(self.themes_file, "r") as f:
                    user_themes = json.load(f)
                for name, colors in user_themes.items():
                    self.themes[name] = ThemeColors(**colors)
            except Exception as e:
                print(f"Error loading user themes: {e}")

    def _load_active_theme(self):
        """Load the active theme from active.json"""
        if os.path.exists(self.active_theme_file):
            try:
                with open(self.active_theme_file, "r") as f:
                    active_theme_data = json.load(f)

                # Remove any extra fields that aren't part of ThemeColors
                valid_fields = {
                    "header_background",
                    "selector",
                    "header_text",
                    "search_term",
                    "border",
                    "anki_button_background",
                    "anki_button_text",
                    "tab_hover",
                    "current_tab_gradient_top",
                    "current_tab_gradient_bottom",
                    "example_highlight",
                    "definition_background",
                    "definition_text",
                    "pitch_accent_color",
                }
                filtered_data = {
                    k: v for k, v in active_theme_data.items() if k in valid_fields
                }

                # Store the theme name if it exists
                if "active_theme_name" in active_theme_data:
                    self.current_theme = active_theme_data["active_theme_name"]

                self.themes["active"] = ThemeColors(**filtered_data)
            except Exception as e:
                print(f"Error loading active theme: {e}")
                # If loading fails, create a default active theme
                self.themes["active"] = self.themes[self.current_theme]

    def get_active_theme(self) -> ThemeColors:
        """Get the currently active theme"""
        return self.themes.get("active", self.themes[self.current_theme])

    def set_active_theme(self, theme_name: str):
        """Set the active theme by name"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.save_active_theme(self.themes[theme_name], theme_name)

    def save_theme(self, name: str, colors: ThemeColors):
        self.themes[name] = colors
        self._save_themes()

    def save_active_theme(self, colors: ThemeColors, theme_name: str = None):
        self.themes["active"] = colors
        self._save_themes()
        os.makedirs(os.path.dirname(self.active_theme_file), exist_ok=True)
        with open(self.active_theme_file, "w") as f:
            # Save only the active theme colors, not all themes
            active_theme_dict = vars(colors).copy()
            if theme_name:
                active_theme_dict["active_theme_name"] = theme_name
            json.dump(active_theme_dict, f, indent=2)

    def _save_themes(self):
        os.makedirs(os.path.dirname(self.themes_file), exist_ok=True)
        with open(self.themes_file, "w") as f:
            themes_dict = {name: vars(colors) for name, colors in self.themes.items()}
            json.dump(themes_dict, f, indent=2)

    def get_css(self, theme_name: str = None) -> str:
        """Generate CSS for the current theme"""
        theme = self.themes[theme_name or self.current_theme]

        return f"""
        /* Base styles */
        body {{
            color: {theme.header_text};
            background: {theme.header_background};
        }}

        .definitionSideBar {{
            background-color: {theme.selector};
            border: 2px solid {theme.border};
            color: {theme.header_text};
        }}

        .fieldSelectCont, .overwriteSelectCont {{
            background-color: {theme.selector};
        }}

        .fieldCheckboxes, .overwriteCheckboxes {{
            background-color: {theme.selector};
            border: 1px solid {theme.border};
        }}

        /* Tabs */
        #tabs {{
            background: {theme.header_background};
            color: {theme.header_text};
        }}

        .tablinks {{
            color: {theme.header_text};
        }}

        .tablinks:hover {{
            background: {theme.tab_hover};
        }}

        .active {{
            background-image: linear-gradient({theme.current_tab_gradient_top}, {theme.current_tab_gradient_bottom});
            border-left: 1px solid {theme.border};
            border-right: 1px solid {theme.border};
        }}

        /* New CSS rules */
        .definitionBlock {{
            color: {theme.definition_text};
            background-color: {theme.definition_background};
        }}

        .altterm {{
            color: {theme.pitch_accent_color};
        }}

        .exampleSentence {{
            background-color: {theme.example_highlight};
        }}
        """

    def get_qt_styles(self, theme_name: str = None, is_mac: bool = False) -> str:
        """Generate Qt styles for the current theme"""
        theme = self.themes[theme_name or self.current_theme]

        if is_mac:
            return f"""
            QLabel {{
                color: {theme.header_text};
            }}
            QLineEdit {{
                color: {theme.header_text}; 
                background: {theme.header_background};
            }}
            QPushButton {{
                border: 1px solid {theme.border};
                border-radius: 5px;
                color: {theme.anki_button_text};
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme.current_tab_gradient_top},
                    stop: 1 {theme.current_tab_gradient_bottom});
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme.current_tab_gradient_top},
                    stop: 1 {theme.current_tab_gradient_bottom});
                border: 1px solid {theme.border};
            }}
            """
        else:
            return f"""
            QLabel {{
                color: {theme.header_text};
            }}
            QLineEdit {{
                color: {theme.header_text};
                background: {theme.header_background};
            }}
            QPushButton {{
                border: 1px solid {theme.border};
                border-radius: 5px;
                color: {theme.anki_button_text};
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme.current_tab_gradient_top},
                    stop: 1 {theme.current_tab_gradient_bottom});
            }}
            """

    def get_combo_style(self, theme_name: str = None, is_mac: bool = False) -> str:
        """Generate Qt styles for QComboBox"""
        theme = self.themes[theme_name or self.current_theme]

        return f"""
        QComboBox {{
            color: {theme.header_text};
            border-radius: 3px;
            border: 1px solid {theme.border};
            background: {theme.header_background};
        }}
        QComboBox:hover {{
            border: 1px solid {theme.border};
        }}
        QComboBox::drop-down {{
            border: none;
            background: {theme.selector};
        }}
        """
