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

def main():
    """Main launcher function"""
    print("🎯 Anki Dictionary Addon Launcher")
    print("=" * 40)
    
    
    # Check if we're in the right directory
    addon_path = dirname(__file__)
    if not exists(join(addon_path, "midict.py")):
        print("❌ Error: This script must be run from the addon directory")
        print("   Make sure you're in the Anki-Dictionary-Addon folder")
        return 1
    
    print("🚀 Launching dictionary addon...")
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