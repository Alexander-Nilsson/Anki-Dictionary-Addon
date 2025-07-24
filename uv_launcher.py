#!/usr/bin/env python3
"""
UV-based launcher for the Anki Dictionary Addon
This uses UV to properly handle the package structure and dependencies.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_uv():
    """Check if UV is available"""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def create_run_script():
    """Create a run script that will be executed by UV"""
    script_content = '''
import sys
import os
from pathlib import Path
import json

def setup_minimal_anki():
    """Setup minimal Anki environment"""
    import aqt
    from aqt.qt import QApplication
    
    # Create QApplication
    app = QApplication.instance() or QApplication([])
    
    # Create minimal main window
    class MinimalAnkiMainWindow:
        def __init__(self):
            self.addonManager = type("AddonManager", (), {
                "getConfig": lambda self, x: {},
                "setConfigAction": lambda self, x, y: None
            })()
            self.pm = type("ProfileManager", (), {"name": "standalone"})()
            self.col = None
            self.miDictDB = None
            
            # Load config
            config_path = Path("config.json")
            if config_path.exists():
                with open(config_path, "r") as f:
                    self.AnkiDictConfig = json.load(f)
            else:
                self.AnkiDictConfig = {}
        
        def checkpoint(self, name): pass
        def reset(self): pass
    
    # Set global mw
    aqt.mw = MinimalAnkiMainWindow()
    
    # Mock addHook
    def addHook(name, func): pass
    import builtins
    builtins.addHook = addHook
    
    return app, aqt.mw

def main():
    print("🎯 Anki Dictionary Addon (UV Mode)")
    print("=" * 40)
    
    try:
        print("✅ Setting up Anki environment...")
        app, mw = setup_minimal_anki()
        
        print("✅ Importing addon modules...")
        
        # Import the addon modules (should work with relative imports now)
        from . import dictdb
        mw.miDictDB = dictdb.DictDB()
        
        from . import midict
        
        print("✅ Creating dictionary interface...")
        dict_interface = midict.DictInterface(
            mw.miDictDB, 
            mw, 
            str(Path.cwd()), 
            None
        )
        
        print("🚀 Launching interface...")
        dict_interface.show()
        
        print("✅ Dictionary ready! Close window to exit.")
        app.exec()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    script_path = Path("__uv_run__.py")
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    return script_path

def main():
    """Main launcher function"""
    print("🎯 Anki Dictionary Addon (UV Launcher)")
    print("=" * 42)
    
    # Check if we're in the right directory
    if not Path('midict.py').exists():
        print("❌ Error: midict.py not found")
        print("Please run this script from the addon directory")
        sys.exit(1)
    
    # Check if UV is available
    if not check_uv():
        print("❌ Error: UV not found")
        print("Please install UV: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)
    
    print("✅ UV found")
    print("✅ Creating run script...")
    
    # Create the run script
    script_path = create_run_script()
    
    try:
        print("🚀 Launching with UV...")
        print("   (This may take a moment to install dependencies)")
        print()
        
        # Run with UV
        result = subprocess.run([
            'uv', 'run', '--module', '__uv_run__'
        ], cwd=Path.cwd())
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\\n👋 Interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Error running with UV: {e}")
        return 1
    finally:
        # Clean up
        if script_path.exists():
            script_path.unlink()

if __name__ == "__main__":
    sys.exit(main())
