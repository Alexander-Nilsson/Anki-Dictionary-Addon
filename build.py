#!/usr/bin/env python3
"""
Build script for the Anki Dictionary Addon

This script helps build and package the addon for distribution.
"""

import os
import sys
import shutil
import zipfile
import json
from pathlib import Path

def get_version():
    """Get version from meta.json"""
    try:
        with open('meta.json', 'r') as f:
            meta = json.load(f)
            return meta.get('human_version', '2.0.0')
    except:
        return '2.0.0'

def build_addon():
    """Build the addon for Anki installation"""
    print("🔨 Building Anki Dictionary Addon...")
    
    version = get_version()
    print(f"   Version: {version}")
    
    # Create build directory
    build_dir = Path('build')
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    
    # Copy essential files for Anki addon
    essential_files = [
        '__init__.py',
        'manifest.json', 
        'meta.json',
        'config.json',
        'src/',
        'assets/',
        'vendor/',
        'user_files/'
    ]
    
    addon_dir = build_dir / 'anki_dictionary_addon'
    addon_dir.mkdir()
    
    for item in essential_files:
        src = Path(item)
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, addon_dir / src.name)
                print(f"   ✓ Copied directory: {item}")
            else:
                shutil.copy2(src, addon_dir / src.name)
                print(f"   ✓ Copied file: {item}")
        else:
            print(f"   ⚠️  Skipped missing: {item}")
    
    print(f"✅ Addon built in: {addon_dir}")
    return addon_dir

def create_ankiaddon_package():
    """Create .ankiaddon package file"""
    print("📦 Creating .ankiaddon package...")
    
    build_dir = Path('build')
    addon_dir = build_dir / 'anki_dictionary_addon'
    
    if not addon_dir.exists():
        print("❌ Build directory not found. Run build first.")
        return None
    
    version = get_version()
    package_name = f"anki_dictionary_addon_v{version}.ankiaddon"
    package_path = build_dir / package_name
    
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(addon_dir):
            for file in files:
                file_path = Path(root) / file
                arc_path = file_path.relative_to(addon_dir)
                zf.write(file_path, arc_path)
                print(f"   ✓ Added: {arc_path}")
    
    print(f"✅ Package created: {package_path}")
    return package_path

def build_standalone():
    """Build standalone version"""
    print("🔧 Building standalone version...")
    
    build_dir = Path('build')
    standalone_dir = build_dir / 'standalone'
    
    if standalone_dir.exists():
        shutil.rmtree(standalone_dir)
    standalone_dir.mkdir(parents=True)
    
    # Copy standalone files
    standalone_files = [
        'src/',
        'assets/',
        'vendor/',
        'user_files/',
        'launch_dictionary.py',
        'standalone/',
        'config.json',
        'pyproject.toml',
        'README.md',
        'docs/'
    ]
    
    for item in standalone_files:
        src = Path(item)
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, standalone_dir / src.name)
                print(f"   ✓ Copied directory: {item}")
            else:
                shutil.copy2(src, standalone_dir / src.name)
                print(f"   ✓ Copied file: {item}")
        else:
            print(f"   ⚠️  Skipped missing: {item}")
    
    print(f"✅ Standalone version built in: {standalone_dir}")
    return standalone_dir

def clean():
    """Clean build artifacts"""
    print("🧹 Cleaning build artifacts...")
    
    build_dir = Path('build')
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("   ✓ Removed build directory")
    
    # Clean Python cache
    for cache_dir in Path('.').rglob('__pycache__'):
        shutil.rmtree(cache_dir)
        print(f"   ✓ Removed: {cache_dir}")
    
    print("✅ Clean completed")

def main():
    """Main build script"""
    if len(sys.argv) < 2:
        print("Usage: python build.py [command]")
        print("Commands:")
        print("  build    - Build addon for Anki")
        print("  package  - Create .ankiaddon package")
        print("  standalone - Build standalone version")
        print("  all      - Build addon, package, and standalone")
        print("  clean    - Clean build artifacts")
        return
    
    command = sys.argv[1]
    
    if command == 'clean':
        clean()
    elif command == 'build':
        build_addon()
    elif command == 'package':
        build_addon()
        create_ankiaddon_package()
    elif command == 'standalone':
        build_standalone()
    elif command == 'all':
        clean()
        build_addon()
        create_ankiaddon_package()
        build_standalone()
        print("\n🎉 All builds completed!")
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == '__main__':
    main()
