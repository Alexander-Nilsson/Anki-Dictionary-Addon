#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to test if the Anki Dictionary Addon is working properly on Windows.
Run this script within Anki's Python environment to check for issues.
"""

import sys
import os
import traceback

def test_imports():
    """Test if all required imports work."""
    print("Testing imports...")
    
    try:
        print("Testing basic Anki imports...")
        from aqt import mw
        print("✓ aqt.mw imported successfully")
        
        from aqt.qt import *
        print("✓ aqt.qt imported successfully")
        
        from anki.hooks import addHook
        print("✓ anki.hooks imported successfully")
        
    except Exception as e:
        print(f"✗ Basic Anki imports failed: {e}")
        return False
    
    try:
        print("Testing PyQt6 imports...")
        from PyQt6.QtCore import QUrl
        print("✓ PyQt6.QtCore imported successfully")
        
        from PyQt6.QtSvgWidgets import QSvgWidget
        print("✓ PyQt6.QtSvgWidgets imported successfully")
        
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        print("✓ PyQt6.QtWebEngineWidgets imported successfully")
        
    except Exception as e:
        print(f"✗ PyQt6 imports failed: {e}")
        return False
    
    try:
        print("Testing pynput import...")
        from pynput import keyboard
        print("✓ pynput imported successfully")
        
    except Exception as e:
        print(f"✗ pynput import failed: {e}")
        print("This will prevent global hotkeys from working")
    
    return True

def test_addon_loading():
    """Test if the addon is properly loaded."""
    print("\nTesting addon loading...")
    
    try:
        # Check if addon state exists
        if hasattr(mw, 'AnkiDictConfig'):
            print("✓ AnkiDictConfig found in mw")
            config = mw.AnkiDictConfig
            print(f"  - Config keys: {list(config.keys()) if isinstance(config, dict) else 'Not a dict'}")
        else:
            print("✗ AnkiDictConfig not found in mw")
        
        # Check if dictionary instance exists
        if hasattr(mw, 'ankiDictionary'):
            print(f"✓ ankiDictionary found: {mw.ankiDictionary}")
        else:
            print("✗ ankiDictionary not found in mw")
        
        # Check if menu exists
        if hasattr(mw, 'DictMainMenu'):
            print("✓ DictMainMenu found")
        else:
            print("✗ DictMainMenu not found")
            
        # Check if hotkeys exist
        if hasattr(mw, 'hotkeyW'):
            print("✓ hotkeyW (Ctrl+W) found")
        else:
            print("✗ hotkeyW not found")
            
    except Exception as e:
        print(f"✗ Error testing addon loading: {e}")
        return False
    
    return True

def test_config_access():
    """Test configuration access."""
    print("\nTesting configuration access...")
    
    try:
        # Test direct config access
        addon_name = "Anki-Dictionary-Addon"
        config = mw.addonManager.getConfig(addon_name)
        if config:
            print("✓ Config loaded via addonManager")
            print(f"  - globalHotkeys: {config.get('globalHotkeys', 'Not set')}")
            print(f"  - enableHotkeys: {config.get('enableHotkeys', 'Not set')}")
        else:
            print("✗ Config not found via addonManager")
            
        # Test our config utility
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        from anki_dictionary.utils.config import get_addon_config
        config2 = get_addon_config()
        if config2:
            print("✓ Config loaded via utility function")
        else:
            print("✗ Config not loaded via utility function")
            
    except Exception as e:
        print(f"✗ Error testing config: {e}")
        traceback.print_exc()
        return False
    
    return True

def main():
    """Main test function."""
    print("Anki Dictionary Addon - Windows Debug Test")
    print("=" * 50)
    
    if not mw:
        print("✗ Anki main window not available. Run this script from within Anki.")
        return
    
    success = True
    success &= test_imports()
    success &= test_addon_loading()
    success &= test_config_access()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! The addon should be working.")
    else:
        print("✗ Some tests failed. Check the output above for issues.")
    
    print("\nIf the menu item isn't showing:")
    print("1. Make sure Anki is completely restarted after installing the addon")
    print("2. Check if the addon is enabled in Tools > Add-ons")
    print("3. Look for any error messages in the Anki console")
    
    print("\nIf shortcuts aren't working:")
    print("1. Make sure globalHotkeys is set to true in config")
    print("2. Check if pynput imported successfully above")
    print("3. Try restarting Anki as administrator (Windows UAC might block hotkeys)")

if __name__ == "__main__":
    main()
