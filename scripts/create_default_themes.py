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
    
    # Default themes data matching the current structure
    default_themes = {
        "light": {
            "header_background": "#FFFFFF",
            "selector": "#F0F0F0",
            "header_text": "#000000",
            "search_term": "#444444",
            "border": "#000000",
            "anki_button_background": "#F0F0F0",
            "anki_button_text": "#000000",
            "tab_hover": "#E0E0E0",
            "current_tab_gradient_top": "#FFFFFF",
            "current_tab_gradient_bottom": "#C0C0C0",
            "example_highlight": "#ffd3e3",
            "definition_background": "#FFFFFF",
            "definition_text": "#000000",
            "pitch_accent_color": "#FFFFFF"
        },
        "dark": {
            "header_background": "#272828",
            "selector": "#1A1A1A",
            "header_text": "#FFFFFF",
            "search_term": "#CCCCCC",
            "border": "#FFFFFF",
            "anki_button_background": "#272828",
            "anki_button_text": "#FFFFFF",
            "tab_hover": "#333333",
            "current_tab_gradient_top": "#272828",
            "current_tab_gradient_bottom": "#000000",
            "example_highlight": "#CCCCCC",
            "definition_background": "#FFFFFF",
            "definition_text": "#000000",
            "pitch_accent_color": "#FFFFFF"
        },
        "pink": {
            "header_background": "#f4dfdf",
            "selector": "#d0b3f3",
            "header_text": "#000000",
            "search_term": "#ab5283",
            "border": "#ffffff",
            "anki_button_background": "#F0F0F0",
            "anki_button_text": "#000000",
            "tab_hover": "#E0E0E0",
            "current_tab_gradient_top": "#FFFFFF",
            "current_tab_gradient_bottom": "#C0C0C0",
            "example_highlight": "#d2ffff",
            "definition_background": "#FFFFFF",
            "definition_text": "#000000",
            "pitch_accent_color": "#FFFFFF"
        },
        "multi": {
            "header_background": "#f4d3d9",
            "selector": "#d0b3f3",
            "header_text": "#70aab9",
            "search_term": "#ab5283",
            "border": "#ffffff",
            "anki_button_background": "#f3867c",
            "anki_button_text": "#306932",
            "tab_hover": "#48e65d",
            "current_tab_gradient_top": "#c3d4f8",
            "current_tab_gradient_bottom": "#f8d5ed",
            "example_highlight": "#d2ffff",
            "definition_background": "#c8f3f2",
            "definition_text": "#f7b72f",
            "pitch_accent_color": "#ffd582"
        },
        "pastel_dream": {
            "header_background": "#e6f3ff",
            "selector": "#ffebf5",
            "header_text": "#4a5d7e",
            "search_term": "#bf7bd0",
            "border": "#ffffff",
            "anki_button_background": "#bcd9ff",
            "anki_button_text": "#4a5d7e",
            "tab_hover": "#ffd6e6",
            "current_tab_gradient_top": "#e6f3ff",
            "current_tab_gradient_bottom": "#ffebf5",
            "example_highlight": "#e4d7fe",
            "definition_background": "#fff0f7",
            "definition_text": "#4a5d7e",
            "pitch_accent_color": "#bb60fc"
        },
        "catpuccino_frappe": {
            "header_background": "#51576d",
            "selector": "#949cbb",
            "header_text": "#babbf1",
            "search_term": "#f4b8e4",
            "border": "#babbf1",
            "anki_button_background": "#99d1db",
            "anki_button_text": "#c6d0f5",
            "tab_hover": "#f4b8e4",
            "current_tab_gradient_top": "#737994",
            "current_tab_gradient_bottom": "#414559",
            "example_highlight": "#414559",
            "definition_background": "#51576d",
            "definition_text": "#c6d0f5",
            "pitch_accent_color": "#eebebe"
        },
        "kdeWall": {
            "header_background": "#efe1e2",
            "selector": "#F19CB0",
            "header_text": "#0C0F14",
            "search_term": "#018FB3",
            "border": "#2289A5",
            "anki_button_background": "#018FB3",
            "anki_button_text": "#0C0F14",
            "tab_hover": "#C4ABB4",
            "current_tab_gradient_top": "#e6efff",
            "current_tab_gradient_bottom": "#018FB3",
            "example_highlight": "#608EA6",
            "definition_background": "#C4ABB4",
            "definition_text": "#0C0F14",
            "pitch_accent_color": "#F19CB0"
        }
    }
    
    try:
        # Write the themes file
        with open(themes_path, 'w', encoding='utf-8') as f:
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


if __name__ == '__main__':
    main()
