#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Anki Dictionary Addon without launching full Anki application

This script initializes the minimal Anki environment needed to run
the dictionary addon directly, without having to start the full Anki application.
"""

import sys
import os
from os.path import dirname, join, exists
import json

# Add the current directory to Python path so we can import the addon modules
addon_path = dirname(__file__)
sys.path.insert(0, addon_path)
sys.path.append(join(addon_path, "vendor"))

# Import required Qt components
try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QIcon
except ImportError:
    print("PyQt6 not found. Please install PyQt6:")
    print("pip install PyQt6 PyQt6-WebEngine")
    sys.exit(1)

# Import Anki components
try:
    import anki
    from anki.collection import Collection
    from anki.utils import is_win, is_mac, is_lin
    import aqt
    from aqt.qt import *
except ImportError:
    print("Anki not found. Please install Anki:")
    print("pip install anki")
    sys.exit(1)

# Import addon modules
try:
    import dictdb
    from midict import DictInterface
except ImportError as e:
    print(f"Error importing addon modules: {e}")
    print("Make sure you're running this script from the addon directory")
    sys.exit(1)


class MinimalAnkiMainWindow:
    """
    Minimal mock of Anki's main window with just the attributes needed by the dictionary addon
    """
    def __init__(self, addon_path):
        self.addon_path = addon_path
        self.addonManager = MinimalAddonManager(addon_path)
        
        # Load addon configuration
        config_path = join(addon_path, "config.json")
        if exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.AnkiDictConfig = json.load(f)
        else:
            # Default configuration
            self.AnkiDictConfig = {
                "maxWidth": 800,
                "jReadingEdit": True,
                "enableHotkeys": True,
                "dictionaryPath": join(addon_path, "dictionaries"),
                "theme": "default"
            }
        
        # Initialize addon-specific attributes
        self.DictExportingDefinitions = False
        self.dictSettings = False
        self.miDictDB = dictdb.DictDB()
        self.misoEditorLoadedAfterDictionary = False
        self.DictBulkMediaExportWasCancelled = False
        
        # Add refresh function
        self.refreshAnkiDictConfig = self.refresh_anki_dict_config
    
    def refresh_anki_dict_config(self, config=False):
        if config:
            self.AnkiDictConfig = config
            return
        # Reload from file
        config_path = join(self.addon_path, "config.json")
        if exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.AnkiDictConfig = json.load(f)


class MinimalAddonManager:
    """
    Minimal mock of Anki's addon manager
    """
    def __init__(self, addon_path):
        self.addon_path = addon_path
    
    def getConfig(self, addon_name):
        config_path = join(self.addon_path, "config.json")
        if exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}


def setup_minimal_anki_environment(addon_path):
    """
    Set up the minimal Anki environment needed for the dictionary addon
    """
    # Create minimal main window mock
    mw = MinimalAnkiMainWindow(addon_path)
    
    # Set global mw variable that the addon expects
    aqt.mw = mw
    
    # Create temp directory if it doesn't exist
    temp_dir = join(addon_path, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    return mw


def main():
    """
    Main function to run the dictionary addon standalone
    """
    print("🚀 Starting Anki Dictionary Addon (Standalone Mode)")
    print("=" * 50)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Anki Dictionary Addon")
    
    # Set application icon if available
    icon_path = join(addon_path, "icons", "icon.png")
    if exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Setup minimal Anki environment
    print("📚 Initializing minimal Anki environment...")
    mw = setup_minimal_anki_environment(addon_path)
    
    # Initialize dictionary database
    print("🗃️  Loading dictionary database...")
    try:
        mw.miDictDB = dictdb.DictDB()
        print("✅ Dictionary database loaded successfully")
    except Exception as e:
        print(f"❌ Error loading dictionary database: {e}")
        print("Make sure dictionary files are available in the addon directory")
        return 1
    
    # Create and show dictionary interface
    print("🖥️  Launching dictionary interface...")
    try:
        # Create welcome message
        welcome_msg = """
        <h2>Anki Dictionary Addon</h2>
        <p>Running in standalone mode (without full Anki application)</p>
        <p>You can now search dictionaries and use all dictionary features!</p>
        """
        
        # Create dictionary interface
        dict_interface = DictInterface(
            dictdb=mw.miDictDB,
            mw=mw,
            path=addon_path,
            welcome=welcome_msg,
            parent=None,
            terms=False
        )
        
        # Show the interface
        dict_interface.show()
        dict_interface.raise_()
        dict_interface.activateWindow()
        
        print("✅ Dictionary interface launched successfully!")
        print("💡 The dictionary addon is now running without Anki!")
        print("=" * 50)
        
        # Run the Qt event loop
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error launching dictionary interface: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Dictionary addon closed by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)