#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fixed launcher for Anki Dictionary Addon

This script resolves the relative import issues by properly setting up
the Python environment and working directory.
"""

import sys
import os
from os.path import dirname, join, exists, abspath

def main():
    """Launch the addon with proper import handling"""
    
    print("🎯 Anki Dictionary Addon Launcher (Import Fix)")
    print("=" * 50)
    
    # Get current directory (should be addon directory)
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
    
    # Check if we're in the right directory
    if not exists(join(addon_path, "midict.py")):
        print("❌ Error: midict.py not found")
        print("   Make sure you're running from the addon directory")
        return 1
    
    print("🚀 Launching dictionary addon...")
    
    # Change to addon directory to make relative imports work
    original_cwd = os.getcwd()
    os.chdir(addon_path)
    
    # Add addon directory to Python path
    if addon_path not in sys.path:
        sys.path.insert(0, addon_path)
    
    try:
        # Import required components
        import json
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QIcon
        import anki
        import aqt
        
        # Now import addon modules - should work with relative imports
        print("📚 Loading addon modules...")
        import dictdb
        import midict
        
        print("✅ Modules loaded successfully")
        
        # Create minimal Anki environment
        class MinimalAnkiMainWindow:
            def __init__(self, addon_path):
                self.addon_path = addon_path
                self.addonManager = MinimalAddonManager(addon_path)
                
                # Load configuration
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
                
                # Required attributes
                self.DictExportingDefinitions = False
                self.dictSettings = False
                self.miDictDB = None  # Will be set later
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
        app = QApplication(sys.argv)
        app.setApplicationName("Anki Dictionary Addon")
        
        # Setup minimal Anki environment
        print("📚 Setting up Anki environment...")
        mw = MinimalAnkiMainWindow(addon_path)
        aqt.mw = mw
        
        # Create temp directory
        temp_dir = join(addon_path, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Initialize dictionary database
        print("🗃️  Initializing dictionary database...")
        try:
            mw.miDictDB = dictdb.DictDB()
            print("✅ Dictionary database initialized")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize full database: {e}")
            print("   Some features may be limited")
            # Create a minimal database mock if needed
            class MockDictDB:
                def __init__(self):
                    pass
                def search(self, term):
                    return []
            mw.miDictDB = MockDictDB()
        
        # Launch dictionary interface
        print("🖥️  Launching dictionary interface...")
        
        welcome_msg = """
        <h2>🎯 Anki Dictionary Addon</h2>
        <p><strong>Running in standalone mode</strong></p>
        <p>✅ Successfully loaded without full Anki application!</p>
        <p>You can now use the dictionary features.</p>
        """
        
        try:
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
            print("💡 The dictionary addon is now running!")
            print("=" * 50)
            
            # Run the application
            exit_code = app.exec()
            return exit_code
            
        except Exception as e:
            print(f"❌ Error launching interface: {e}")
            print("\n🔧 This might be due to missing dictionary files or")
            print("   other addon-specific dependencies.")
            import traceback
            traceback.print_exc()
            return 1
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   This indicates a problem with the addon's internal imports.")
        print("   The addon may need modification to run standalone.")
        return 1
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Restore original working directory
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
