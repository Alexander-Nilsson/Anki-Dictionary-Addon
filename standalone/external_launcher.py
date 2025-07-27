#!/usr/bin/env python3
"""
Ultimate launcher that sets up the environment properly before any imports
"""

import sys
import os
from pathlib import Path

def main():
    print("🎯 Anki Dictionary Addon (Ultimate)")
    print("=" * 40)
    
    # Change to parent directory since we're in standalone/
    parent_dir = Path('..').resolve()
    os.chdir(parent_dir)
    
    # Check directory
    if not Path('src/anki_dictionary').exists():
        print("❌ Error: src/anki_dictionary package not found")
        print("   Make sure you're running from the standalone/ directory")
        print("   and that the reorganized structure exists in the parent directory")
        sys.exit(1)
    
    try:
        # Add src to path for package imports
        src_path = str(Path.cwd() / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Step 1: Import basic Anki/Qt modules
        print("✅ Importing Anki modules...")
        import aqt
        from aqt.qt import QApplication
        import anki
        import json
        
        # Step 2: Create QApplication
        print("✅ Creating Qt application...")
        app = QApplication.instance() or QApplication(["Anki Dictionary"])
        app.setApplicationName("Anki Dictionary")
        app.setApplicationVersion("2.0")
        app.setOrganizationName("Anki Dictionary Addon")
        
        # Step 3: Create minimal mw
        print("✅ Setting up minimal main window...")
        
        from aqt.qt import QWidget
        
        class MinimalAnkiMainWindow(QWidget):
            def __init__(self, app_instance):
                super().__init__()
                self.app = app_instance
                # Load config first
                config_path = Path('config.json')
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        self.AnkiDictConfig = json.load(f)
                else:
                    self.AnkiDictConfig = {}
                
                # Create addon manager that returns our config
                class MinimalAddonManager:
                    def __init__(self, config):
                        self.config = config
                    
                    def getConfig(self, addon_name):
                        return self.config
                    
                    def setConfigAction(self, addon_name, callback):
                        pass
                    
                    def writeConfig(self, addon_name, config):
                        # Save config to file
                        try:
                            config_path = Path('config.json')
                            with open(config_path, 'w') as f:
                                json.dump(config, f, indent=2)
                        except Exception as e:
                            print(f"Warning: Could not save config: {e}")
                
                self.addonManager = MinimalAddonManager(self.AnkiDictConfig)
                
                class ProfileManager:
                    def __init__(self):
                        self.name = 'standalone'
                    
                    def addonFolder(self):
                        return str(Path.cwd())
                
                self.pm = ProfileManager()
                
                # Create a minimal collection with media directory
                class MinimalMediaManager:
                    def dir(self):
                        # Return a directory for media files (create if needed)
                        media_dir = Path.cwd() / 'user_files' / 'media'
                        media_dir.mkdir(parents=True, exist_ok=True)
                        return str(media_dir)
                
                class MinimalCollection:
                    def __init__(self):
                        self.media = MinimalMediaManager()
                        # Create real models manager that provides actual Anki-compatible model data
                        self.models = self._create_models_manager()
                    
                    def _create_models_manager(self):
                        # Real Anki model structures for common note types
                        default_models = [
                            {
                                'name': 'Basic',
                                'flds': [
                                    {'name': 'Front', 'ord': 0},
                                    {'name': 'Back', 'ord': 1}
                                ]
                            },
                            {
                                'name': 'Basic (and reversed card)',
                                'flds': [
                                    {'name': 'Front', 'ord': 0},
                                    {'name': 'Back', 'ord': 1}
                                ]
                            },
                            {
                                'name': 'Japanese',
                                'flds': [
                                    {'name': 'Expression', 'ord': 0},
                                    {'name': 'Reading', 'ord': 1},
                                    {'name': 'Meaning', 'ord': 2},
                                    {'name': 'Audio', 'ord': 3},
                                    {'name': 'Example', 'ord': 4},
                                    {'name': 'Source', 'ord': 5}
                                ]
                            },
                            {
                                'name': 'Japanese Dictionary',
                                'flds': [
                                    {'name': 'Expression', 'ord': 0},
                                    {'name': 'ExpressionAudio', 'ord': 1},
                                    {'name': 'Reading', 'ord': 2},
                                    {'name': 'ReadingAudio', 'ord': 3},
                                    {'name': 'Meaning', 'ord': 4},
                                    {'name': 'MeaningAudio', 'ord': 5},
                                    {'name': 'AdditionalInfo', 'ord': 6},
                                    {'name': 'Sentence', 'ord': 7},
                                    {'name': 'SentenceAudio', 'ord': 8},
                                    {'name': 'Focus', 'ord': 9}
                                ]
                            }
                        ]
                        
                        class ModelsManager:
                            def __init__(self, models_data):
                                self._models = models_data
                            
                            def all(self):
                                return self._models
                            
                            def byName(self, name):
                                for model in self._models:
                                    if model['name'] == name:
                                        return model
                                return None
                        
                        return ModelsManager(default_models)
                
                # Create a minimal media server
                class MinimalMediaServer:
                    def set_page_html(self, webview_id, html, context):
                        # Just ignore this for now
                        pass
                
                self.col = MinimalCollection()
                self.mediaServer = MinimalMediaServer()
                self.miDictDB = None
                
                # Add missing UI elements that the addon expects
                class MinimalMenuItem:
                    def setText(self, text):
                        pass
                
                self.openMiDict = MinimalMenuItem()
                
                # Initialize dictSettings as False (as in main.py)
                self.dictSettings = False
                
                # Add refreshAnkiDictConfig method
                def refreshAnkiDictConfig():
                    """Refresh the addon configuration - used by addon settings"""
                    try:
                        config_path = Path('config.json')
                        if config_path.exists():
                            with open(config_path, 'r') as f:
                                self.AnkiDictConfig = json.load(f)
                        print("✅ Configuration refreshed")
                    except Exception as e:
                        print(f"⚠️  Could not refresh config: {e}")
                
                self.refreshAnkiDictConfig = refreshAnkiDictConfig
            
            def checkpoint(self, name): pass
            def reset(self): pass
            def serverURL(self): 
                return "http://localhost:8080/"
            def dictionaryInit(self):
                # Hotkey callback - just print for now
                print("Dictionary hotkey activated")
        
        # Set global mw
        aqt.mw = MinimalAnkiMainWindow(app)
        
        # Step 4: Mock addHook function
        print("✅ Mocking addon hooks...")
        def addHook(hook_name, callback):
            pass
        
        import builtins
        builtins.addHook = addHook
        
        # Step 5: Import the new package modules
        print("✅ Loading reorganized package modules...")
        
        # Import core modules
        from anki_dictionary.core.database import DictDB
        from anki_dictionary.core.dictionary import DictInterface
        
        # Initialize database
        print("✅ Initializing database...")
        aqt.mw.miDictDB = DictDB()
        
        # Load available dictionaries
        print("✅ Loading dictionaries...")
        try:
            available_dicts = aqt.mw.miDictDB.getAllDicts()
            if available_dicts:
                print(f"   Found {len(available_dicts)} dictionaries:")
                for dict_info in available_dicts:
                    print(f"     - {dict_info[0]}")
            else:
                print("   ⚠️  No dictionaries found in database")
                print("   Note: You may need to install dictionaries through the addon interface")
        except Exception as e:
            print(f"   ⚠️  Could not load dictionaries: {e}")
        
        # Create interface
        print("✅ Creating dictionary interface...")
        print("✅ Attempting to create DictInterface instance...")
        
        try:
            print("   Creating main DictInterface...")
            dict_interface = DictInterface(
                aqt.mw.miDictDB,
                aqt.mw,
                str(Path.cwd()),  # addon path
                None,             # welcome
                None,             # parent
                False             # terms
            )
            
            # Set the ankiDictionary reference on mw
            aqt.mw.ankiDictionary = dict_interface
            
            print("✅ DictInterface created successfully")
        except Exception as e:
            print(f"❌ Error creating DictInterface: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        print("🚀 Showing interface...")
        try:
            dict_interface.show()
            print("✅ Interface shown successfully")
        except Exception as e:
            print(f"❌ Error showing interface: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        print("✅ Dictionary launched! Close window to exit.")
        
        # Run application
        app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
