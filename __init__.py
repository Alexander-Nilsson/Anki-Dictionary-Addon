# -*- coding: utf-8 -*-
"""
Anki Dictionary Addon

This addon provides a comprehensive dictionary interface for Anki,
allowing users to search dictionaries and automatically create cards.

Thanks to Damien Elmes, this plugin is loosely based on his original Plugin and borrows slightly from his project
Also thanks to the creators of the Japanese Pronunciation/Pitch Accent, Japanese Pitch Accent Notes, and pitch accent note button  which I also borrowed marginally from
"""

import os
import sys
from anki.utils import is_win, is_mac, is_lin
from aqt import mw

# Add the vendor directory to the system path
vendor_path = os.path.join(os.path.dirname(__file__), "vendor")
if vendor_path not in sys.path:
    sys.path.append(vendor_path)

# Add src directory to path for package imports
src_path = os.path.join(os.path.dirname(__file__), "src")
if src_path not in sys.path:
    sys.path.append(src_path)

# Initialize addon configuration and global state
def initialize_addon():
    """Initialize the addon when Anki starts."""
    # Initialize configuration
    mw.AnkiDictConfig = mw.addonManager.getConfig(__name__)
    mw.DictExportingDefinitions = False
    mw.dictSettings = False
    mw.ankiDictionary = False
    mw.misoEditorLoadedAfterDictionary = False
    mw.DictBulkMediaExportWasCancelled = False
    mw.currentlyPressed = []
    
    # Initialize database
    from anki_dictionary.core.database import DictDB
    mw.miDictDB = DictDB()
    
    # Setup hooks and UI
    from anki_dictionary.core.hooks import setup_hooks
    from anki_dictionary.ui.main_window import setup_gui_menu, refresh_anki_dict_config
    
    # Make refresh function globally available
    mw.refreshAnkiDictConfig = refresh_anki_dict_config
    
    # Setup the addon
    setup_hooks()
    setup_gui_menu()

# Initialize when this module is imported by Anki
initialize_addon()