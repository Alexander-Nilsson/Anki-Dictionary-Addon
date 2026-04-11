#!/usr/bin/env python3
"""
Default themes.json generation script for Anki Dictionary Addon

This script creates the default themes.json file for the addon.
"""

import json
import os
import sys


def create_default_themes_json(themes_path: str) -> None:
    """Create the default themes.json file."""

    # Ensure the directory exists
    themes_dir = os.path.dirname(themes_path)
    if not os.path.exists(themes_dir):
        os.makedirs(themes_dir, exist_ok=True)

    # Default themes data matching the new refined structure
    default_themes = {
        "light": {
            "header_background": "#FFFFFF",
            "selector": "#F8F9FA",
            "header_text": "#212529",
            "search_term": "#007BFF",
            "border": "#DEE2E6",
            "anki_button_background": "#F8F9FA",
            "anki_button_text": "#212529",
            "tab_hover": "#E9ECEF",
            "current_tab_gradient_top": "#FFFFFF",
            "current_tab_gradient_bottom": "#E9ECEF",
            "example_highlight": "#FFF3CD",
            "definition_background": "#FFFFFF",
            "definition_text": "#212529",
            "pitch_accent_color": "#DC3545",
        },
        "dark": {
            "header_background": "#1A1B1E",
            "selector": "#25262B",
            "header_text": "#C1C2C5",
            "search_term": "#4DABF7",
            "border": "#373A40",
            "anki_button_background": "#25262B",
            "anki_button_text": "#C1C2C5",
            "tab_hover": "#2C2E33",
            "current_tab_gradient_top": "#2C2E33",
            "current_tab_gradient_bottom": "#1A1B1E",
            "example_highlight": "#2C2E33",
            "definition_background": "#1A1B1E",
            "definition_text": "#C1C2C5",
            "pitch_accent_color": "#FF6B6B",
        },
        "catppuccin_mocha": {
            "header_background": "#1e1e2e",
            "selector": "#181825",
            "header_text": "#cdd6f4",
            "search_term": "#89b4fa",
            "border": "#b4befe",
            "anki_button_background": "#313244",
            "anki_button_text": "#cdd6f4",
            "tab_hover": "#45475a",
            "current_tab_gradient_top": "#585b70",
            "current_tab_gradient_bottom": "#1e1e2e",
            "example_highlight": "#313244",
            "definition_background": "#1e1e2e",
            "definition_text": "#cdd6f4",
            "pitch_accent_color": "#f38ba8",
        },
        "catppuccin_latte": {
            "header_background": "#eff1f5",
            "selector": "#e6e9ef",
            "header_text": "#4c4f69",
            "search_term": "#1e66f5",
            "border": "#7287fd",
            "anki_button_background": "#ccd0da",
            "anki_button_text": "#4c4f69",
            "tab_hover": "#bcc0cc",
            "current_tab_gradient_top": "#acb0be",
            "current_tab_gradient_bottom": "#eff1f5",
            "example_highlight": "#ccd0da",
            "definition_background": "#eff1f5",
            "definition_text": "#4c4f69",
            "pitch_accent_color": "#d20f39",
        },
        "nord": {
            "header_background": "#3b4252",
            "selector": "#434c5e",
            "header_text": "#eceff4",
            "search_term": "#88c0d0",
            "border": "#4c566a",
            "anki_button_background": "#81a1c1",
            "anki_button_text": "#2e3440",
            "tab_hover": "#4c566a",
            "current_tab_gradient_top": "#434c5e",
            "current_tab_gradient_bottom": "#3b4252",
            "example_highlight": "#ebcb8b",
            "definition_background": "#2e3440",
            "definition_text": "#d8dee9",
            "pitch_accent_color": "#bf616a",
        },
        "solarized_light": {
            "header_background": "#eee8d5",
            "selector": "#fdf6e3",
            "header_text": "#586e75",
            "search_term": "#268bd2",
            "border": "#93a1a1",
            "anki_button_background": "#859900",
            "anki_button_text": "#fdf6e3",
            "tab_hover": "#eee8d5",
            "current_tab_gradient_top": "#fdf6e3",
            "current_tab_gradient_bottom": "#eee8d5",
            "example_highlight": "#b58900",
            "definition_background": "#fdf6e3",
            "definition_text": "#657b83",
            "pitch_accent_color": "#dc322f",
        },
        "tokyo_night": {
            "header_background": "#1f2335",
            "selector": "#24283b",
            "header_text": "#c0caf5",
            "search_term": "#7aa2f7",
            "border": "#414868",
            "anki_button_background": "#bb9af7",
            "anki_button_text": "#1a1b26",
            "tab_hover": "#3b4261",
            "current_tab_gradient_top": "#24283b",
            "current_tab_gradient_bottom": "#1f2335",
            "example_highlight": "#e0af68",
            "definition_background": "#1a1b26",
            "definition_text": "#a9b1d6",
            "pitch_accent_color": "#f7768e",
        },
        "gruvbox": {
            "header_background": "#3c3836",
            "selector": "#504945",
            "header_text": "#ebdbb2",
            "search_term": "#fabd2f",
            "border": "#665c54",
            "anki_button_background": "#b8bb26",
            "anki_button_text": "#282828",
            "tab_hover": "#504945",
            "current_tab_gradient_top": "#504945",
            "current_tab_gradient_bottom": "#3c3836",
            "example_highlight": "#d65d0e",
            "definition_background": "#282828",
            "definition_text": "#ebdbb2",
            "pitch_accent_color": "#fb4934",
        },
    }

    try:
        # Write the themes file
        with open(themes_path, "w", encoding="utf-8") as f:
            json.dump(default_themes, f, indent=2, ensure_ascii=False)

        print(f"   ✓ Created default themes.json: {themes_path}")

    except Exception as e:
        print(f"   ❌ Error creating themes.json: {e}")
        raise


def main():
    """Main function to create the themes file."""
    if len(sys.argv) != 2:
        print("Usage: python create_default_themes.py <themes_path>")
        sys.exit(1)

    themes_path = sys.argv[1]
    print(f"Creating default themes.json: {themes_path}")
    create_default_themes_json(themes_path)
    print("✅ Themes.json creation completed")


if __name__ == "__main__":
    main()
