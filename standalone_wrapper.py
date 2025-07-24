#!/usr/bin/env python3
"""
Standalone wrapper for Anki Dictionary Addon
This script allows running the addon without Anki by creating a minimal environment.
"""

import sys
import os
import importlib.util
from pathlib import Path

# Get the addon directory
ADDON_DIR = Path(__file__).parent.absolute()

def create_module_from_file(module_name, file_path):
    """Create a module from a file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def setup_addon_modules():
    """Set up addon modules with proper imports"""
    
    # Create a namespace for the addon
    addon_namespace = {}
    
    # Load modules in dependency order
    module_files = [
        'dictdb.py',
        'miutils.py', 
        'themes.py',
        'history.py',
        'addonSettings.py',
        'themeEditor.py',
        'duckduckgoimages.py',
        'forvodl.py',
        'ffmpegInstaller.py',
        'miJapaneseHandler.py',
        'cardExporter.py',
        'addTemplate.py',
        'dictionaryManager.py',
        'freqConjWebWindow.py',
        'webConfig.py',
        'midict.py'
    ]
    
    for module_file in module_files:
        module_path = ADDON_DIR / module_file
        if module_path.exists():
            module_name = module_file[:-3]  # Remove .py extension
            
            # Read the file content
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace relative imports with references to our namespace
            modified_content = content
            
            # Handle relative imports by replacing them with absolute references
            import_replacements = {
                'from . import dictdb': 'dictdb = addon_modules["dictdb"]',
                'from . import miutils': 'miutils = addon_modules["miutils"]',
                'from . import themes': 'themes = addon_modules["themes"]',
                'from . import history': 'history = addon_modules["history"]',
                'from . import addonSettings': 'addonSettings = addon_modules["addonSettings"]',
                'from . import themeEditor': 'themeEditor = addon_modules["themeEditor"]',
                'from . import duckduckgoimages': 'duckduckgoimages = addon_modules["duckduckgoimages"]',
                'from . import forvodl': 'forvodl = addon_modules["forvodl"]',
                'from . import ffmpegInstaller': 'ffmpegInstaller = addon_modules["ffmpegInstaller"]',
                'from . import miJapaneseHandler': 'miJapaneseHandler = addon_modules["miJapaneseHandler"]',
                'from . import cardExporter': 'cardExporter = addon_modules["cardExporter"]',
                'from . import addTemplate': 'addTemplate = addon_modules["addTemplate"]',
                'from . import dictionaryManager': 'dictionaryManager = addon_modules["dictionaryManager"]',
                'from . import freqConjWebWindow': 'freqConjWebWindow = addon_modules["freqConjWebWindow"]',
                'from . import webConfig': 'webConfig = addon_modules["webConfig"]'
            }
            
            for old_import, new_import in import_replacements.items():
                modified_content = modified_content.replace(old_import, new_import)
            
            # Create a temporary file with the modified content
            temp_module_path = ADDON_DIR / f"temp_{module_file}"
            try:
                with open(temp_module_path, 'w', encoding='utf-8') as f:
                    # Add the addon_modules reference at the top
                    f.write("# Temporary module for standalone execution\n")
                    f.write("import sys\n")
                    f.write("addon_modules = getattr(sys, '_addon_modules', {})\n\n")
                    f.write(modified_content)
                
                # Load the module
                module = create_module_from_file(module_name, temp_module_path)
                addon_namespace[module_name] = module
                
                # Make it available in sys for other modules
                if not hasattr(sys, '_addon_modules'):
                    sys._addon_modules = {}
                sys._addon_modules[module_name] = module
                
            finally:
                # Clean up temporary file
                if temp_module_path.exists():
                    temp_module_path.unlink()
    
    return addon_namespace

def create_minimal_anki_environment():
    """Create minimal Anki environment required by the addon"""
    
    # Import required Anki modules
    try:
        import aqt
        from aqt.qt import QApplication
        import anki
        from anki.collection import Collection
    except ImportError as e:
        print(f"Error: Missing required dependency: {e}")
        print("Please install: pip install anki PyQt6 PyQt6-WebEngine")
        sys.exit(1)
    
    # Create minimal main window mock
    class MinimalAnkiMainWindow:
        def __init__(self, addon_modules):
            # Set up addon manager
            self.addonManager = MinimalAddonManager()
            
            # Load addon configuration
            config_path = ADDON_DIR / 'config.json'
            if config_path.exists():
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.AnkiDictConfig = json.load(f)
            else:
                self.AnkiDictConfig = {}
            
            # Initialize dictionary database
            self.miDictDB = addon_modules['dictdb'].DictDB()
            
            # Set up other required attributes
            self.pm = MinimalProfileManager()
            self.col = None
            
        def checkpoint(self, name):
            """Mock checkpoint method"""
            pass
        
        def reset(self):
            """Mock reset method"""
            pass
    
    class MinimalAddonManager:
        def getConfig(self, addon_name):
            """Mock addon config getter"""
            return {}
        
        def setConfigAction(self, addon_name, callback):
            """Mock config action setter"""
            pass
    
    class MinimalProfileManager:
        def __init__(self):
            self.name = "standalone"
    
    # Set up the modules
    addon_modules = setup_addon_modules()
    
    # Create and set the main window
    mw = MinimalAnkiMainWindow(addon_modules)
    aqt.mw = mw
    
    return mw, addon_modules

def main():
    """Main entry point for standalone execution"""
    
    print("🎯 Anki Dictionary Addon (Standalone)")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not (ADDON_DIR / 'midict.py').exists():
        print("❌ Error: midict.py not found")
        print("Please run this script from the addon directory")
        sys.exit(1)
    
    try:
        # Create Qt application
        from aqt.qt import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        
        print("✅ Setting up minimal Anki environment...")
        
        # Set up the environment
        mw, addon_modules = create_minimal_anki_environment()
        
        print("✅ Loading dictionary interface...")
        
        # Get the main dictionary interface class
        midict_module = addon_modules['midict']
        DictInterface = midict_module.DictInterface
        
        # Create and show the interface
        welcome_msg = None
        dict_interface = DictInterface(mw.miDictDB, mw, str(ADDON_DIR), welcome_msg)
        dict_interface.show()
        
        print("🚀 Dictionary interface launched!")
        print("   Close the dictionary window to exit.")
        
        # Run the application
        app.exec()
        
    except Exception as e:
        print(f"❌ Error launching dictionary: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
