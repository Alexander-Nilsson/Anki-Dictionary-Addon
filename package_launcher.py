#!/usr/bin/env python3
"""
Package-based launcher for Anki Dictionary Addon
This approach uses Python's package system to handle relative imports properly.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Launch the addon using Python's module system"""
    
    print("🎯 Anki Dictionary Addon (Package Mode)")
    print("=" * 40)
    
    # Get the addon directory
    addon_dir = Path(__file__).parent.absolute()
    
    # Check if we're in the right directory
    if not (addon_dir / 'midict.py').exists():
        print("❌ Error: midict.py not found")
        print("Please run this script from the addon directory")
        sys.exit(1)
    
    # Go up one directory to run the addon as a package
    parent_dir = addon_dir.parent
    addon_name = addon_dir.name
    
    print("✅ Setting up package environment...")
    print(f"   Addon directory: {addon_dir}")
    print(f"   Parent directory: {parent_dir}")
    print(f"   Package name: {addon_name}")
    
    # Create a temporary launcher script that will run the addon as a package
    launcher_script = f'''
import sys
import os
from pathlib import Path

# Add the parent directory to Python path so we can import the addon as a package
addon_parent = r"{parent_dir}"
if addon_parent not in sys.path:
    sys.path.insert(0, addon_parent)

# Now import and run the standalone launcher from the package
try:
    from {addon_name}.run_addon_standalone import main
    main()
except ImportError as e:
    print(f"Import error: {{e}}")
    print("Falling back to direct execution...")
    
    # Fallback: try to run directly
    os.chdir(r"{addon_dir}")
    exec(open("run_addon_standalone.py").read())
'''
    
    # Write the launcher script to a temporary file
    temp_launcher = addon_dir / "temp_package_launcher.py"
    try:
        with open(temp_launcher, 'w', encoding='utf-8') as f:
            f.write(launcher_script)
        
        print("🚀 Launching via package system...")
        
        # Run the temporary launcher
        result = subprocess.run([
            sys.executable, str(temp_launcher)
        ], cwd=str(parent_dir))
        
        return result.returncode
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        # Clean up temporary file
        if temp_launcher.exists():
            temp_launcher.unlink()

if __name__ == "__main__":
    sys.exit(main())
