#!/usr/bin/env python3
"""
Import patcher for Anki Dictionary Addon
This script patches relative imports at runtime to allow standalone execution.
"""

import sys
import os
import importlib.util
from pathlib import Path

class ImportPatcher:
    """Patches relative imports to work in standalone mode"""
    
    def __init__(self, addon_dir):
        self.addon_dir = Path(addon_dir)
        self.modules = {}
        import builtins
        self.original_import = builtins.__import__
        
    def patch_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        """Custom import function that handles relative imports"""
        
        # Handle relative imports
        if level > 0 and globals and '__file__' in globals:
            current_file = Path(globals['__file__'])
            if current_file.parent == self.addon_dir:
                # This is a relative import from within the addon
                if fromlist:
                    # Handle "from . import module" style imports
                    for module_name in fromlist:
                        module_file = self.addon_dir / f"{module_name}.py"
                        if module_file.exists() and module_name not in self.modules:
                            self.load_module(module_name, module_file)
                    
                    # Create a mock module that provides the imported names
                    class MockModule:
                        pass
                    
                    mock = MockModule()
                    for module_name in fromlist:
                        if module_name in self.modules:
                            setattr(mock, module_name, self.modules[module_name])
                    
                    return mock
        
        # Fall back to original import for everything else
        return self.original_import(name, globals, locals, fromlist, level)
    
    def load_module(self, module_name, module_file):
        """Load a module file and store it"""
        if module_name in self.modules:
            return self.modules[module_name]
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules before execution to handle circular imports
            sys.modules[module_name] = module
            self.modules[module_name] = module
            
            # Temporarily patch import for this module
            import builtins
            old_import = builtins.__import__
            builtins.__import__ = self.patch_import
            
            try:
                spec.loader.exec_module(module)
            finally:
                builtins.__import__ = old_import
            
            return module
            
        except Exception as e:
            print(f"Warning: Could not load module {module_name}: {e}")
            return None
    
    def load_all_modules(self):
        """Load all addon modules in dependency order"""
        
        # Define modules in dependency order (modules with fewer dependencies first)
        module_order = [
            'six',           # External dependency, no relative imports
            'Pyperclip',     # External dependency  
            'dictdb',        # Core database module
            'miutils',       # Utility functions
            'themes',        # Theme management
            'history',       # History tracking
            'addonSettings', # Settings management
            'themeEditor',   # Theme editor
            'duckduckgoimages', # Image search
            'forvodl',       # Audio downloads
            'ffmpegInstaller', # FFMPEG installation
            'miJapaneseHandler', # Japanese text handling
            'cardExporter',  # Card export functionality
            'addTemplate',   # Template management
            'dictionaryManager', # Dictionary management
            'freqConjWebWindow', # Frequency/conjugation window
            'webConfig',     # Web configuration
            'midict'         # Main dictionary interface
        ]
        
        for module_name in module_order:
            module_file = self.addon_dir / f"{module_name}.py"
            if module_file.exists():
                print(f"Loading {module_name}...")
                self.load_module(module_name, module_file)
        
        return self.modules

def create_minimal_anki_environment():
    """Create minimal Anki environment required by the addon"""
    
    # Import required Anki modules
    try:
        import aqt
        from aqt.qt import QApplication
        import anki
        import json
    except ImportError as e:
        print(f"Error: Missing required dependency: {e}")
        print("Please install: pip install anki PyQt6 PyQt6-WebEngine")
        sys.exit(1)
    
    # Create minimal main window mock
    class MinimalAnkiMainWindow:
        def __init__(self, dictdb_module):
            # Set up addon manager
            self.addonManager = MinimalAddonManager()
            
            # Load addon configuration
            config_path = Path(__file__).parent / 'config.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.AnkiDictConfig = json.load(f)
            else:
                self.AnkiDictConfig = {}
            
            # Initialize dictionary database
            if dictdb_module and hasattr(dictdb_module, 'DictDB'):
                self.miDictDB = dictdb_module.DictDB()
            else:
                print("Warning: Could not initialize dictionary database")
                self.miDictDB = None
            
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
    
    return MinimalAnkiMainWindow, MinimalAddonManager, MinimalProfileManager

def main():
    """Main entry point for standalone execution"""
    
    print("🎯 Anki Dictionary Addon (Import Patcher)")
    print("=" * 42)
    
    # Get the addon directory
    addon_dir = Path(__file__).parent.absolute()
    
    # Check if we're in the right directory
    if not (addon_dir / 'midict.py').exists():
        print("❌ Error: midict.py not found")
        print("Please run this script from the addon directory")
        sys.exit(1)
    
    try:
        # Create Qt application
        from aqt.qt import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        
        print("✅ Setting up import patcher...")
        
        # Create and configure the import patcher
        patcher = ImportPatcher(addon_dir)
        
        print("✅ Loading addon modules...")
        
        # Load all modules
        modules = patcher.load_all_modules()
        
        if 'dictdb' not in modules:
            print("❌ Error: Could not load required dictdb module")
            sys.exit(1)
        
        print("✅ Setting up minimal Anki environment...")
        
        # Set up the environment
        MinimalAnkiMainWindow, MinimalAddonManager, MinimalProfileManager = create_minimal_anki_environment()
        
        # Create main window with loaded dictdb
        mw = MinimalAnkiMainWindow(modules.get('dictdb'))
        
        # Set global mw
        import aqt
        aqt.mw = mw
        
        print("✅ Loading dictionary interface...")
        
        # Get the main dictionary interface class
        midict_module = modules.get('midict')
        if not midict_module or not hasattr(midict_module, 'DictInterface'):
            print("❌ Error: Could not load DictInterface from midict module")
            sys.exit(1)
        
        DictInterface = midict_module.DictInterface
        
        # Create and show the interface
        welcome_msg = None
        dict_interface = DictInterface(mw.miDictDB, mw, str(addon_dir), welcome_msg)
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
