from dataclasses import dataclass
from typing import Dict, Optional
import json
import os
from ..utils.logger import get_logger

log = get_logger("themes")


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
    def __init__(self, addon_path: str) -> None:
        self.addon_path = addon_path
        self.themes_file = os.path.join(addon_path, "user_files/themes", "themes.json")
        self.active_theme_file = os.path.join(
            addon_path, "user_files/themes", "active.json"
        )
        self.current_theme = "light"
        self.themes = self._load_default_themes()
        self._load_user_themes()
        self._load_active_theme()

    def _load_default_themes(self) -> Dict[str, ThemeColors]:
        return {
            "light": ThemeColors(
                header_background="#FFFFFF",
                selector="#F8F9FA",
                header_text="#212529",
                search_term="#007BFF",
                border="#DEE2E6",
                anki_button_background="#F8F9FA",
                anki_button_text="#212529",
                tab_hover="#E9ECEF",
                current_tab_gradient_top="#FFFFFF",
                current_tab_gradient_bottom="#E9ECEF",
                example_highlight="#FFF3CD",
                definition_background="#FFFFFF",
                definition_text="#212529",
                pitch_accent_color="#DC3545",
            ),
            "dark": ThemeColors(
                header_background="#1A1B1E",
                selector="#25262B",
                header_text="#C1C2C5",
                search_term="#4DABF7",
                border="#373A40",
                anki_button_background="#25262B",
                anki_button_text="#C1C2C5",
                tab_hover="#2C2E33",
                current_tab_gradient_top="#2C2E33",
                current_tab_gradient_bottom="#1A1B1E",
                example_highlight="#2C2E33",
                definition_background="#1A1B1E",
                definition_text="#C1C2C5",
                pitch_accent_color="#FF6B6B",
            ),
            "catppuccin_mocha": ThemeColors(
                header_background="#1e1e2e",
                selector="#181825",
                header_text="#cdd6f4",
                search_term="#89b4fa",
                border="#b4befe",
                anki_button_background="#313244",
                anki_button_text="#cdd6f4",
                tab_hover="#45475a",
                current_tab_gradient_top="#585b70",
                current_tab_gradient_bottom="#1e1e2e",
                example_highlight="#313244",
                definition_background="#1e1e2e",
                definition_text="#cdd6f4",
                pitch_accent_color="#f38ba8",
            ),
            "catppuccin_latte": ThemeColors(
                header_background="#eff1f5",
                selector="#e6e9ef",
                header_text="#4c4f69",
                search_term="#1e66f5",
                border="#7287fd",
                anki_button_background="#ccd0da",
                anki_button_text="#4c4f69",
                tab_hover="#bcc0cc",
                current_tab_gradient_top="#acb0be",
                current_tab_gradient_bottom="#eff1f5",
                example_highlight="#ccd0da",
                definition_background="#eff1f5",
                definition_text="#4c4f69",
                pitch_accent_color="#d20f39",
            ),
            "nord": ThemeColors(
                header_background="#3b4252",
                selector="#434c5e",
                header_text="#eceff4",
                search_term="#88c0d0",
                border="#4c566a",
                anki_button_background="#81a1c1",
                anki_button_text="#2e3440",
                tab_hover="#4c566a",
                current_tab_gradient_top="#434c5e",
                current_tab_gradient_bottom="#3b4252",
                example_highlight="#ebcb8b",
                definition_background="#2e3440",
                definition_text="#d8dee9",
                pitch_accent_color="#bf616a",
            ),
            "solarized_light": ThemeColors(
                header_background="#eee8d5",
                selector="#fdf6e3",
                header_text="#586e75",
                search_term="#268bd2",
                border="#93a1a1",
                anki_button_background="#859900",
                anki_button_text="#fdf6e3",
                tab_hover="#eee8d5",
                current_tab_gradient_top="#fdf6e3",
                current_tab_gradient_bottom="#eee8d5",
                example_highlight="#b58900",
                definition_background="#fdf6e3",
                definition_text="#657b83",
                pitch_accent_color="#dc322f",
            ),
            "tokyo_night": ThemeColors(
                header_background="#1f2335",
                selector="#24283b",
                header_text="#c0caf5",
                search_term="#7aa2f7",
                border="#414868",
                anki_button_background="#bb9af7",
                anki_button_text="#1a1b26",
                tab_hover="#3b4261",
                current_tab_gradient_top="#24283b",
                current_tab_gradient_bottom="#1f2335",
                example_highlight="#e0af68",
                definition_background="#1a1b26",
                definition_text="#a9b1d6",
                pitch_accent_color="#f7768e",
            ),
            "gruvbox": ThemeColors(
                header_background="#3c3836",
                selector="#504945",
                header_text="#ebdbb2",
                search_term="#fabd2f",
                border="#665c54",
                anki_button_background="#b8bb26",
                anki_button_text="#282828",
                tab_hover="#504945",
                current_tab_gradient_top="#504945",
                current_tab_gradient_bottom="#3c3836",
                example_highlight="#d65d0e",
                definition_background="#282828",
                definition_text="#ebdbb2",
                pitch_accent_color="#fb4934",
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
                log.error(f"Error loading user themes: {e}")

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
                log.error(f"Error loading active theme: {e}")
                self.themes["active"] = self.themes[self.current_theme]

        # Validate current theme exists
        self._validate_current_theme()

    def _validate_current_theme(self):
        """Ensure current_theme exists, reset to 'light' if not"""
        if self.current_theme not in self.themes:
            log.warning(
                f"Current theme '{self.current_theme}' not found, resetting to 'light'"
            )
            self.current_theme = "light"

    def get_active_theme(self) -> ThemeColors:
        """Get the currently active theme"""
        return self.themes.get("active", self.themes[self.current_theme])

    @property
    def is_dark(self) -> bool:
        """Check if the current theme is dark"""
        if self.current_theme == "dark":
            return True

        # Check background color brightness as a fallback for user themes
        theme = self.get_active_theme()
        bg = theme.header_background.lstrip("#")
        if len(bg) == 6:
            try:
                r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
                # Standard formula for relative luminance
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return luminance < 0.5
            except ValueError:
                pass

        return False

    def set_active_theme(self, theme_name: str):
        """Set the active theme by name"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.save_active_theme(self.themes[theme_name], theme_name)

    def save_theme(self, name: str, colors: ThemeColors):
        self.themes[name] = colors
        self._save_themes()

    def save_active_theme(self, colors: ThemeColors, theme_name: Optional[str] = None):
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

    def get_css(self, theme_name: Optional[str] = None) -> str:
        """Generate CSS for the current theme"""
        requested_theme = theme_name or self.current_theme

        # Fallback to 'light' theme if the requested theme doesn't exist
        if requested_theme not in self.themes:
            log.warning(
                f"Theme '{requested_theme}' not found, falling back to 'light' theme"
            )
            requested_theme = "light"

        theme = self.themes[requested_theme]

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

    def get_qt_styles(
        self, theme_name: Optional[str] = None, is_mac: bool = False
    ) -> str:
        """Generate Qt styles for the current theme"""
        requested_theme = theme_name or self.current_theme

        # Fallback to 'light' theme if the requested theme doesn't exist
        if requested_theme not in self.themes:
            log.warning(
                f"Theme '{requested_theme}' not found, falling back to 'light' theme"
            )
            requested_theme = "light"

        theme = self.themes[requested_theme]

        if is_mac:
            return f"""
            QLabel {{
                color: {theme.header_text};
            }}
            QLineEdit {{
                color: {theme.header_text}; 
                background: {theme.header_background};
                border: 1.5px solid {theme.border};
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {theme.search_term};
                outline: none;
            }}
            QPushButton {{
                border: 1.5px solid {theme.border};
                border-radius: 6px;
                color: {theme.anki_button_text};
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme.current_tab_gradient_top},
                    stop: 1 {theme.current_tab_gradient_bottom});
                padding: 5px 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme.current_tab_gradient_top},
                    stop: 1 {theme.current_tab_gradient_bottom});
                border: 1.5px solid {theme.search_term};
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme.current_tab_gradient_bottom},
                    stop: 1 {theme.current_tab_gradient_top});
                border: 1.5px solid {theme.border};
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
                border: 1.5px solid {theme.border};
                border-radius: 6px;
                padding: 4px 8px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {theme.search_term};
                outline: none;
            }}
            QPushButton {{
                border: 1.5px solid {theme.border};
                border-radius: 6px;
                color: {theme.anki_button_text};
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme.current_tab_gradient_top},
                    stop: 1 {theme.current_tab_gradient_bottom});
                padding: 5px 12px;
                font-weight: 500;
            }}
            """

    def get_combo_style(
        self, theme_name: Optional[str] = None, is_mac: bool = False
    ) -> str:
        """Generate Qt styles for QComboBox"""
        requested_theme = theme_name or self.current_theme

        # Fallback to 'light' theme if the requested theme doesn't exist
        if requested_theme not in self.themes:
            log.warning(
                f"Theme '{requested_theme}' not found, falling back to 'light' theme"
            )
            requested_theme = "light"

        theme = self.themes[requested_theme]

        return f"""
        QComboBox {{
            color: {theme.header_text};
            border-radius: 6px;
            border: 1.5px solid {theme.border};
            background: {theme.header_background};
            padding: 4px 8px;
            font-weight: 500;
        }}
        QComboBox:hover {{
            border: 1.5px solid {theme.search_term};
            background: {theme.selector};
        }}
        QComboBox:focus {{
            border: 1.5px solid {theme.search_term};
            outline: none;
        }}
        QComboBox::drop-down {{
            border: none;
            background: {theme.selector};
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border: none;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {theme.border};
            background: {theme.header_background};
            color: {theme.header_text};
            selection-background-color: {theme.search_term};
            outline: none;
        }}
        """
