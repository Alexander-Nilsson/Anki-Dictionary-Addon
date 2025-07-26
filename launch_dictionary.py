#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple launcher for Anki Dictionary Addon

This script provides an easy way to launch the dictionary addon
without having to start the full Anki application.
"""

import sys
import os
from os.path import dirname, join, exists

def check_dependencies():
    """Check if required dependencies are available"""
    missing_deps = []
    
    try:
        import PyQt6
    except ImportError:
        missing_deps.append("PyQt6")
    
    try:
        import anki
    except ImportError:
        missing_deps.append("anki")
    
    if missing_deps:
        print("❌ Missing required dependencies:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n📦 To install dependencies, run:")
        print("   pip install -r requirements_addon.txt")
        print("\n   Or install individually:")
        if "PyQt6" in missing_deps:
            print("   pip install PyQt6 PyQt6-WebEngine")
        if "anki" in missing_deps:
            print("   pip install anki")
        return False
    
    return True

def main():
    """Main launcher function"""
    print("🎯 Anki Dictionary Addon Launcher")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check if we're in the right directory
    addon_path = dirname(__file__)
    if not exists(join(addon_path, "midict.py")):
        print("❌ Error: This script must be run from the addon directory")
        print("   Make sure you're in the Anki-Dictionary-Addon folder")
        return 1
    
    print("✅ Dependencies found")
    print("🚀 Launching dictionary addon...")
    print("   (This may take a moment to initialize)")
    print()
    
    # Import and run the standalone script
    try:
        from external_launcher import main as run_addon
        return run_addon()
    except Exception as e:
        print(f"❌ Error launching addon: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure you have all dependencies installed")
        print("2. Try running: pip install PyQt6 PyQt6-WebEngine anki")
        print("3. Make sure you're in the addon directory")
        print("4. Check that dictionary files are present")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Launcher interrupted by user")
        sys.exit(0)