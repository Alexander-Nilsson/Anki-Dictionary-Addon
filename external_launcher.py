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
    
    # Check directory
    if not Path('midict.py').exists():
        print("❌ Error: midict.py not found")
        sys.exit(1)
    
    try:
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
        
        class MinimalAnkiMainWindow:
            def __init__(self):
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
                
                self.pm = type('ProfileManager', (), {
                    'name': 'standalone',
                    'addonFolder': lambda self: str(Path.cwd().parent)  # Return parent directory for addon folder
                })()
                
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
                                'name': 'Migaku Japanese',
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
            
            def checkpoint(self, name): pass
            def reset(self): pass
            def serverURL(self): 
                return "http://localhost:8080/"
            def dictionaryInit(self):
                # Hotkey callback - just print for now
                print("Dictionary hotkey activated")
        
        # Set global mw
        aqt.mw = MinimalAnkiMainWindow()
        
        # Important: Set mw.app to the QApplication instance  
        aqt.mw.app = app
        
        # Step 4: Mock addHook function
        print("✅ Mocking addon hooks...")
        def addHook(hook_name, callback):
            pass
        
        import builtins
        builtins.addHook = addHook
        
        # Step 5: Load addon modules in proper dependency order
        print("✅ Loading addon modules in dependency order...")
        
        import importlib.util
        loaded_modules = {}
        
        def load_module_with_deps(name, file_path, required_deps=None):
            """Load a module and ensure its dependencies are available"""
            if name in loaded_modules:
                return loaded_modules[name]
            
            print(f"   Loading {name}...")
            
            spec = importlib.util.spec_from_file_location(name, file_path)
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules before execution to handle circular imports
            sys.modules[name] = module
            loaded_modules[name] = module
            
            # Patch import system to handle relative imports
            original_import = __builtins__['__import__'] if isinstance(__builtins__, dict) else __builtins__.__import__
            
            def patched_import(import_name, globals=None, locals=None, fromlist=(), level=0):
                # Handle relative imports
                if level > 0 and fromlist:  # from . import something
                    # Create a namespace object to hold the imported items
                    result_module = type('RelativeImport', (), {})()
                    
                    for item in fromlist:
                        if item == '*':
                            # Handle "from .module import *" by copying all public attributes
                            # Try to find which module this star import is from
                            if globals and '__file__' in globals:
                                current_file = Path(globals['__file__'])
                                # This is a hacky way but look at the bytecode context to determine the module
                                # For now, let's handle common cases
                                if 'themes' in str(current_file) or 'themeEditor' in str(current_file):
                                    # Import from themes module
                                    if 'themes' in loaded_modules:
                                        themes_mod = loaded_modules['themes']
                                        for attr_name in dir(themes_mod):
                                            if not attr_name.startswith('_'):
                                                setattr(result_module, attr_name, getattr(themes_mod, attr_name))
                                elif 'midict' in str(current_file):
                                    # midict.py imports from multiple modules with *
                                    for mod_name in ['themes', 'themeEditor']:
                                        if mod_name in loaded_modules:
                                            mod = loaded_modules[mod_name]
                                            for attr_name in dir(mod):
                                                if not attr_name.startswith('_') and not hasattr(result_module, attr_name):
                                                    setattr(result_module, attr_name, getattr(mod, attr_name))
                        else:
                            # Try to find the item in our loaded modules
                            if item in loaded_modules:
                                setattr(result_module, item, loaded_modules[item])
                            else:
                                # Look for the attribute in any loaded module
                                found = False
                                for mod_name, mod in loaded_modules.items():
                                    if hasattr(mod, item):
                                        setattr(result_module, item, getattr(mod, item))
                                        found = True
                                        break
                                
                                if not found:
                                    # Create a placeholder - will be filled when the module loads
                                    if item == '_version' or item == '__version__':
                                        # Common version attributes - return a dummy version
                                        setattr(result_module, item, '1.0.0')
                                    elif item.endswith('__version__'):
                                        # Handle module-specific version attributes
                                        setattr(result_module, item, '1.0.0')
                                    else:
                                        print(f"     Note: {item} not yet available, will resolve later")
                                        setattr(result_module, item, None)
                    
                    return result_module
                
                # Fall back to original import for absolute imports
                return original_import(import_name, globals, locals, fromlist, level)
            
            # Apply the patch
            if isinstance(__builtins__, dict):
                __builtins__['__import__'] = patched_import
            else:
                __builtins__.__import__ = patched_import
            
            try:
                spec.loader.exec_module(module)
            except ImportError as e:
                print(f"     Import error in {name}: {e}")
                # Don't fail completely, just mark as partially loaded
            except AttributeError as e:
                print(f"     Attribute error in {name}: {e}")
                # Don't fail completely, just mark as partially loaded
            except Exception as e:
                print(f"     Warning: Error loading {name}: {e}")
                # Don't fail completely, just mark as partially loaded
            finally:
                # Restore original import
                if isinstance(__builtins__, dict):
                    __builtins__['__import__'] = original_import
                else:
                    __builtins__.__import__ = original_import
            
            return module
        
        # Load modules in dependency order (least dependent first)
        module_order = [
            ('miutils', 'miutils.py'),          # Base utilities, no dependencies
            ('dictdb', 'dictdb.py'),            # Database, depends on miutils
            ('themes', 'themes.py'),            # Theme system
            ('themeEditor', 'themeEditor.py'),  # Theme editor
            ('addDictGroup', 'addDictGroup.py'), # Dictionary group editor
            ('addTemplate', 'addTemplate.py'),  # Template editor
            ('dictionaryManager', 'dictionaryManager.py'), # Dictionary manager
            ('ffmpegInstaller', 'ffmpegInstaller.py'), # FFMPEG installer
            ('duckduckgoimages', 'duckduckgoimages.py'),  # Image search
            ('forvodl', 'forvodl.py'),          # Audio downloads
            ('miJapaneseHandler', 'miJapaneseHandler.py'),  # Japanese handling
            ('history', 'history.py'),          # History system, depends on miutils
            ('cardExporter', 'cardExporter.py'), # Card export, depends on miutils
            ('addonSettings', 'addonSettings.py'), # Settings, may depend on others
            ('midict', 'midict.py')             # Main interface, depends on everything
        ]
        
        # Load each module
        for module_name, module_file in module_order:
            if Path(module_file).exists():
                try:
                    loaded_modules[module_name] = load_module_with_deps(module_name, module_file)
                except Exception as e:
                    print(f"     Failed to load {module_name}: {e}")
                    # Continue loading other modules
        
        # Post-process: Inject real classes into modules that need them
        print("✅ Resolving cross-module dependencies...")
        
        # Inject real classes from their source modules into target modules
        cross_injections = [
            # (source_module, target_module, class_name)
            ('themes', 'midict', 'ThemeManager'),
            ('themes', 'midict', 'ThemeColors'),
            ('themeEditor', 'midict', 'ThemeEditorDialog'),
            ('history', 'midict', 'HistoryBrowser'),
            ('history', 'midict', 'HistoryModel'),
            ('cardExporter', 'midict', 'CardExporter'),
            ('miJapaneseHandler', 'midict', 'miJHandler'),
            ('addonSettings', 'midict', 'SettingsGui'),
            ('forvodl', 'midict', 'Forvo'),
            ('addDictGroup', 'midict', 'DictGroupEditor'),
            ('addTemplate', 'midict', 'TemplateEditor'),
            ('dictionaryManager', 'midict', 'DictionaryManagerWidget'),
            ('ffmpegInstaller', 'midict', 'FFMPEGInstaller'),
            ('duckduckgoimages', 'midict', 'DuckDuckGo'),
        ]
        
        for source_mod, target_mod, class_name in cross_injections:
            if source_mod in loaded_modules and target_mod in loaded_modules:
                source = loaded_modules[source_mod]
                target = loaded_modules[target_mod]
                if hasattr(source, class_name):
                    setattr(target, class_name, getattr(source, class_name))
                    print(f"   ✅ {class_name} injected from {source_mod} to {target_mod}")
                else:
                    print(f"   ⚠️  {class_name} not found in {source_mod}")
                    # Special handling for DuckDuckGo - try to reload the module and find the class
                    if class_name == 'DuckDuckGo' and source_mod == 'duckduckgoimages':
                        print(f"   🔧 Attempting to reload {source_mod} and find {class_name}")
                        try:
                            # Try to reload the module more carefully
                            import importlib
                            importlib.reload(source)
                            
                            # Check again if the class exists now
                            if hasattr(source, class_name):
                                real_class = getattr(source, class_name)
                                setattr(target, class_name, real_class)
                                print(f"   ✅ Real {class_name} found and injected after reload")
                            else:
                                # Try to manually execute the class definition
                                print(f"   🔧 Manually loading {class_name} from source file")
                                with open('duckduckgoimages.py', 'r') as f:
                                    source_code = f.read()
                                
                                # Extract just the DuckDuckGo class definition
                                import re
                                class_pattern = r'class DuckDuckGo.*?(?=\nclass|\nif __name__|\Z)'
                                match = re.search(class_pattern, source_code, re.DOTALL)
                                
                                if match:
                                    class_code = match.group(0)
                                    # Execute the class definition in the module's namespace
                                    exec(class_code, source.__dict__)
                                    
                                    if hasattr(source, class_name):
                                        real_class = getattr(source, class_name)
                                        setattr(target, class_name, real_class)
                                        print(f"   ✅ Real {class_name} manually loaded and injected")
                                    else:
                                        print(f"   ❌ Could not manually load {class_name}")
                                else:
                                    print(f"   ❌ Could not find {class_name} class definition in source")
                        except Exception as reload_error:
                            print(f"   ❌ Failed to reload and find {class_name}: {reload_error}")
            else:
                print(f"   ⚠️  Could not inject {class_name}: {source_mod} or {target_mod} not loaded")
        
        # Verify we have the essential modules
        if 'dictdb' not in loaded_modules:
            print("❌ Critical error: Could not load dictdb module")
            sys.exit(1)
        
        if 'midict' not in loaded_modules:
            print("❌ Critical error: Could not load midict module")
            sys.exit(1)
        
        # Initialize database
        print("✅ Initializing database...")
        dictdb = loaded_modules['dictdb']
        aqt.mw.miDictDB = dictdb.DictDB()
        
        # Load available dictionaries
        print("✅ Loading dictionaries...")
        try:
            available_dicts = aqt.mw.miDictDB.getAllDicts()
            if available_dicts:
                print(f"   Found {len(available_dicts)} dictionaries:")
                for dict_info in available_dicts:
                    print(f"     - {dict_info}")
            else:
                print("   ⚠️  No dictionaries found in database")
                print("   Note: You may need to install dictionaries through the addon interface")
        except Exception as e:
            print(f"   ⚠️  Could not load dictionaries: {e}")
        
        # Get midict module
        midict = loaded_modules['midict']
        
        # Create interface
        print("✅ Creating dictionary interface...")
        
        # Verify DictInterface exists
        if not hasattr(midict, 'DictInterface'):
            print("❌ Error: DictInterface not found in midict module")
            print(f"Available attributes: {[attr for attr in dir(midict) if not attr.startswith('_')]}")
            sys.exit(1)
        
        print("✅ Attempting to create DictInterface instance...")
        try:
            print("   Creating miJHandler...")
            # Use the loaded modules instead of importing directly
            miJHandler = loaded_modules['miJapaneseHandler'].miJHandler
            jhandler_test = miJHandler(aqt.mw)
            print("   ✅ miJHandler created successfully")
            
            print("   Creating ThemeManager...")
            ThemeManager = loaded_modules['themes'].ThemeManager
            theme_manager_test = ThemeManager(str(Path.cwd()))
            print("   ✅ ThemeManager created successfully")
            
            print("   Creating main DictInterface...")
            dict_interface = midict.DictInterface(
                aqt.mw.miDictDB, 
                aqt.mw, 
                str(Path.cwd()), 
                None
            )
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
