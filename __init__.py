# -*- coding: utf-8 -*-
"""
Anki Dictionary Addon

This addon provides a comprehensive dictionary interface for Anki,
allowing users to search dictionaries and automatically create cards.
"""

import os
import sys
from typing import Any, Dict, List, Optional
from aqt import mw

# Add the vendor directory to the system path
vendor_path = os.path.join(os.path.dirname(__file__), "vendor")
if vendor_path not in sys.path:
    sys.path.append(vendor_path)

# Add src directory to path for package imports
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.append(src_path)


# Global state container to avoid dynamic attribute access on mw
class AddonState:
    """Container for addon state."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.exporting_definitions: bool = False
        self.settings_open: bool = False
        self.dictionary_instance: Any = (
            None  # Will be properly typed when we fix the dictionary class
        )
        self.editor_loaded_after_dictionary: bool = False
        self.bulk_media_export_cancelled: bool = False
        self.currently_pressed: List[str] = []
        self.dict_db: Any = None  # Will be properly typed when we fix the DictDB class


# Global state instance
_addon_state: Optional[AddonState] = None


def get_addon_state() -> AddonState:
    """Get the global addon state."""
    global _addon_state
    if _addon_state is None:
        _addon_state = AddonState()
    return _addon_state


# Initialize addon configuration and global state
def initialize_addon() -> None:
    """Initialize the addon when Anki starts."""
    if not mw:
        return

    try:
        # Initialize state container
        state = get_addon_state()

        # Get the addon root path for use throughout the addon
        addon_root = os.path.dirname(__file__)
        addon_name = os.path.basename(addon_root)

        # Initialize configuration
        raw_config = mw.addonManager.getConfig(addon_name)
        if raw_config is None:
            # Try to load default config from file
            import json

            config_path = os.path.join(addon_root, "config.json")
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_config = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load default config: {e}")
                raw_config = {}

        state.config = raw_config or {}
        state.config["addon_path"] = addon_root  # Store the actual addon path
        state.config["addon_name"] = addon_name  # Store the addon name
        state.exporting_definitions = False
        state.settings_open = False
        state.dictionary_instance = False
        state.editor_loaded_after_dictionary = False
        state.bulk_media_export_cancelled = False
        state.currently_pressed = []

        # Legacy compatibility - set attributes on mw for backwards compatibility
        if hasattr(mw, "__dict__"):
            mw.__dict__["AnkiDictConfig"] = state.config
            mw.__dict__["DictExportingDefinitions"] = state.exporting_definitions
            mw.__dict__["dictSettings"] = state.settings_open
            mw.__dict__["ankiDictionary"] = state.dictionary_instance
            mw.__dict__["dictEditorLoadedAfterDictionary"] = (
                state.editor_loaded_after_dictionary
            )
            mw.__dict__["DictBulkMediaExportWasCancelled"] = (
                state.bulk_media_export_cancelled
            )
            mw.__dict__["currentlyPressed"] = state.currently_pressed

        # Initialize database
        try:
            from anki_dictionary.core.database import DictDB

            state.dict_db = DictDB()
            if hasattr(mw, "__dict__"):
                mw.__dict__["miDictDB"] = state.dict_db
        except ImportError as e:
            print(f"Warning: Could not import DictDB: {e}")
            return

        # Setup hooks and UI
        try:
            from anki_dictionary.core.hooks import setup_hooks
            from anki_dictionary.ui.main_window import (
                setup_gui_menu,
                refresh_anki_dict_config,
            )

            # Make refresh function globally available (legacy compatibility)
            if hasattr(mw, "__dict__"):
                mw.__dict__["refreshAnkiDictConfig"] = refresh_anki_dict_config

            # Setup the addon
            setup_hooks()
            setup_gui_menu()
            
            # The configuration is already loaded in state.config above,
            # just make sure it's available in the legacy location
            if hasattr(mw, "__dict__"):
                mw.__dict__["AnkiDictConfig"] = state.config
                
            print("Anki Dictionary Addon: Successfully initialized!")
        except ImportError as e:
            print(f"Warning: Could not initialize addon components: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"Error: Failed to initialize Anki Dictionary Addon: {e}")
        import traceback
        traceback.print_exc()


# Initialize when this module is imported by Anki
if mw:
    initialize_addon()
