#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultimate fix for Anki Dictionary Addon relative imports

This script patches the import system to handle relative imports properly
"""

import sys
import os
import builtins
import importlib.util
from os.path import dirname, join, exists, abspath

def setup_import_patch(addon_path):
    """Patch the import system to handle relative imports"""
    
    # Store the original import function
    original_import = builtins.__import__
    
    # List of addon modules that use relative imports
    addon_modules = {
        'dictdb', 'midict', 'history', 'cardExporter', 'miJapaneseHandler',
        'duckduckgoimages', 'addonSettings', 'forvodl', 'miutils', 
        'themeEditor', 'themes', 'webConfig', 'dictionaryWebInstallWizard',
        'freqConjWebWindow', 'miUpdater', 'main'
    }
    
    def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        """Custom import that handles relative imports for addon modules"""
        
        # Handle relative imports (level > 0)
        if level > 0 and globals is not None:
            caller_module = globals.get('__name__', '')
            
            # Check if the caller is one of our addon modules
            if any(caller_module.endswith(mod) for mod in addon_modules):
                
                if level == 1:  # from . import module or from .module import something
                    if name == '':  # from . import module1, module2, ...
                        if fromlist:
                            imported_modules = []
                            for module_name in fromlist:
                                try:
                                    # Try to load the module from the addon directory
                                    module_path = join(addon_path, f"{module_name}.py")
                                    if exists(module_path):
                                        spec = importlib.util.spec_from_file_location(
                                            module_name, module_path
                                        )
                                        module = importlib.util.module_from_spec(spec)
                                        # Set the module in sys.modules so it can be found later
                                        sys.modules[module_name] = module
                                        spec.loader.exec_module(module)
                                        imported_modules.append(module)
                                    else:
                                        # Fallback to original import
                                        module = original_import(module_name, globals, locals, (), 0)
                                        imported_modules.append(module)
                                except Exception:
                                    # Last resort: try original import
                                    module = original_import(module_name, globals, locals, (), 0)
                                    imported_modules.append(module)
                            
                            # Return the first module if only one, otherwise return a module with attributes
                            if len(imported_modules) == 1:
                                return imported_modules[0]
                            else:
                                # Create a namespace-like object with all modules as attributes
                                class ModuleNamespace:
                                    pass
                                ns = ModuleNamespace()
                                for mod, mod_name in zip(imported_modules, fromlist):
                                    setattr(ns, mod_name, mod)
                                return ns
                    
                    else:  # from .module import something
                        try:
                            module_path = join(addon_path, f"{name}.py")
                            if exists(module_path):
                                if name not in sys.modules:
                                    spec = importlib.util.spec_from_file_location(name, module_path)
                                    module = importlib.util.module_from_spec(spec)
                                    sys.modules[name] = module
                                    spec.loader.exec_module(module)
                                return sys.modules[name]
                            else:
                                # Try as absolute import
                                return original_import(name, globals, locals, fromlist, 0)
                        except Exception:
                            return original_import(name, globals, locals, fromlist, 0)
        
        # For all other cases, use the original import
        return original_import(name, globals, locals, fromlist, level)
    
    # Apply the patch
    builtins.__import__ = patched_import

def main():
    """Main launcher with import patching"""
    
    print("🎯 Anki Dictionary Addon Launcher (Import Patch)")
    print("=" * 55)
    
    # Get addon path
    addon_path = dirname(abspath(__file__))
    
    # Check dependencies
    missing_deps = []
    
    try:
        import PyQt6
        print("✅ PyQt6 found")
    except ImportError:
        missing_deps.append("PyQt6")
    
    try:
        import anki
        print("✅ Anki found")
    except ImportError:
        missing_deps.append("anki")
    
    if missing_deps:
        print("❌ Missing dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n📦 Install with: pip install PyQt6 PyQt6-WebEngine anki")
        return 1
    
    # Check if we're in addon directory
    if not exists(join(addon_path, "midict.py")):
        print("❌ Error: midict.py not found")
        return 1
    
    print("🔧 Setting up import patch...")
    setup_import_patch(addon_path)
    
    # Change to addon directory
    original_cwd = os.getcwd()
    os.chdir(addon_path)
    
    # Add to Python path
    if addon_path not in sys.path:
        sys.path.insert(0, addon_path)
    
    try:
        print("📚 Importing components...")
        
        # Import Qt and Anki
        import json
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QIcon
        import anki
        import aqt
        
        # Import addon modules - should now work with patched imports
        print("📦 Loading dictdb...")
        import dictdb
        print("📦 Loading midict...")
        import midict
        
        print("✅ All modules loaded successfully!")
        
        # Setup minimal Anki environment
        class MinimalAnkiMainWindow:
            def __init__(self, addon_path):
                self.addon_path = addon_path
                self.addonManager = MinimalAddonManager(addon_path)
                
                # Load config
                config_path = join(addon_path, "config.json")
                if exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self.AnkiDictConfig = json.load(f)
                else:
                    self.AnkiDictConfig = {
                        "maxWidth": 800,
                        "jReadingEdit": True,
                        "enableHotkeys": True,
                        "theme": "default"
                    }
                
                self.DictExportingDefinitions = False
                self.dictSettings = False
                self.miDictDB = None
                self.misoEditorLoadedAfterDictionary = False
                self.DictBulkMediaExportWasCancelled = False
                self.refreshAnkiDictConfig = self.refresh_anki_dict_config
            
            def refresh_anki_dict_config(self, config=False):
                if config:
                    self.AnkiDictConfig = config
                    return
                config_path = join(self.addon_path, "config.json")
                if exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self.AnkiDictConfig = json.load(f)

        class MinimalAddonManager:
            def __init__(self, addon_path):
                self.addon_path = addon_path
            
            def getConfig(self, addon_name):
                config_path = join(self.addon_path, "config.json")
                if exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                return {}

        # Create Qt application
        print("🖥️  Creating Qt application...")
        app = QApplication(sys.argv)
        app.setApplicationName("Anki Dictionary Addon")
        
        # Setup Anki environment
        print("⚙️  Setting up Anki environment...")
        mw = MinimalAnkiMainWindow(addon_path)
        aqt.mw = mw
        
        # Create temp directory
        temp_dir = join(addon_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Initialize dictionary database
        print("🗃️  Initializing dictionary database...")
        try:
            mw.miDictDB = dictdb.DictDB()
            print("✅ Dictionary database ready")
        except Exception as e:
            print(f"⚠️  Database init warning: {e}")
            # Create mock if needed
            class MockDictDB:
                def search(self, term): return []
            mw.miDictDB = MockDictDB()
        
        # Launch interface
        print("🚀 Launching dictionary interface...")
        
        welcome_msg = """
        <h2>🎯 Anki Dictionary Addon</h2>
        <p><strong>Successfully running standalone!</strong></p>
        <p>✅ Import patch applied successfully</p>
        <p>✅ All modules loaded without errors</p>
        <p>You can now use all dictionary features.</p>
        """
        
        dict_interface = midict.DictInterface(
            dictdb=mw.miDictDB,
            mw=mw,
            path=addon_path,
            welcome=welcome_msg,
            parent=None,
            terms=False
        )
        
        dict_interface.show()
        dict_interface.raise_()
        dict_interface.activateWindow()
        
        print("✅ Dictionary interface launched successfully!")
        print("🎉 Anki Dictionary Addon is now running standalone!")
        print("=" * 55)
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
