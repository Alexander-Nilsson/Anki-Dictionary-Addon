"""
Anki Dictionary Addon

This addon provides a comprehensive dictionary interface for Anki,
allowing users to search dictionaries and automatically create cards.
"""

import os
import ssl
import sys
from typing import Any

try:
    from aqt import mw
except ImportError:
    mw = None

# macOS SSL certificate fix
if sys.platform == "darwin":
    ssl._create_default_https_context = ssl._create_unverified_context

# Add the vendor directory to the system path
vendor_path = os.path.join(os.path.dirname(__file__), "vendor")

# macOS-specific curl_cffi injection
if sys.platform == "darwin":
    try:
        import platform

        machine = platform.machine().lower()
        if machine == "arm64":
            mac_vendor = os.path.join(vendor_path, "mac_arm64")
            if os.path.exists(mac_vendor) and mac_vendor not in sys.path:
                sys.path.insert(0, mac_vendor)
        elif machine in ["x86_64", "amd64", "i386"]:
            mac_vendor = os.path.join(vendor_path, "mac_x86_64")
            if os.path.exists(mac_vendor) and mac_vendor not in sys.path:
                sys.path.insert(0, mac_vendor)
    except Exception as e:
        print(f"Anki Dictionary: Error injecting macOS vendor paths: {e}")

if vendor_path not in sys.path:
    sys.path.append(vendor_path)

# Special check for broken PIL in vendor (often happens if bundled on different OS)
if os.path.exists(os.path.join(vendor_path, "PIL")):
    try:
        __import__("PIL")
    except ImportError:
        # If it's broken, remove vendor from path temporarily or handle it
        pass

# Add src directory to path for package imports
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.append(src_path)


# Global state container to avoid dynamic attribute access on mw
class AddonState:
    """Container for addon state."""

    def __init__(self) -> None:
        self.config: dict[str, Any] = {}
        self.exporting_definitions: bool = False
        self.settings_open: bool = False
        self.dictionary_instance: Any = (
            None  # Will be properly typed when we fix the dictionary class
        )
        self.editor_loaded_after_dictionary: bool = False
        self.bulk_media_export_cancelled: bool = False
        self.currently_pressed: list[str] = []
        self.dict_db: Any = None  # Will be properly typed when we fix the DictDB class


# Global state instance
_addon_state: AddonState | None = None
_initialized = False


def get_addon_state() -> AddonState:
    """Get the global addon state."""
    global _addon_state
    if _addon_state is None:
        _addon_state = AddonState()
    return _addon_state


# Initialize addon configuration and global state
def initialize_addon() -> None:
    """Initialize the addon when Anki starts."""
    global _initialized
    if not mw or _initialized:
        return

    _initialized = True
    print("--- Anki Dictionary: Starting Initialization ---")
    # Initialize state container
    state = get_addon_state()

    # Get the addon root path for use throughout the addon
    addon_root = os.path.dirname(__file__)
    addon_name = os.path.basename(addon_root)

    # Add the addon root to path temporarily to import internal modules
    if addon_root not in sys.path:
        sys.path.insert(0, addon_root)

    # Initialize configuration
    try:
        from anki_dictionary.utils.config import get_addon_config

        state.config = get_addon_config()
    except ImportError:
        # Fallback if config module can't be imported yet
        state.config = {}

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
        from anki_dictionary.core.hooks import setup_gui_menu, setup_hooks
        from anki_dictionary.utils.config import refresh_anki_dict_config

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
    except ImportError as e:
        print(f"Warning: Could not initialize addon components: {e}")


# Initialize when this module is imported by Anki
if mw:
    initialize_addon()
