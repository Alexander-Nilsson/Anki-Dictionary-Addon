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
import subprocess
from pathlib import Path

def get_project_config():
    """Get project configuration from pyproject.toml"""
    try:
        # Try tomllib first (Python 3.11+)
        try:
            import tomllib
            with open('pyproject.toml', 'rb') as f:
                config = tomllib.load(f)
        except ImportError:
            # Fallback to toml library
            import toml
            with open('pyproject.toml', 'r') as f:
                config = toml.load(f)
        
        return config['project']
    except Exception as e:
        print(f"Warning: Could not read config from pyproject.toml: {e}")
        return {'version': '0.1.0', 'name': 'Anki Dictionary'}

def get_version():
    """Get version from pyproject.toml"""
    return get_project_config().get('version', '0.1.0')

def generate_manifest():
    """Generate manifest.json from pyproject.toml data"""
    project_config = get_project_config()
    
    # Extract macOS-specific requirements
    dependencies = project_config.get('dependencies', [])
    macos_requirements = []
    
    for dep in dependencies:
        if 'pyobjc' in dep and 'darwin' in dep:
            # Extract package name before semicolon
            package_name = dep.split(';')[0].strip()
            macos_requirements.append(package_name)
    
    manifest_data = {
        "package": project_config.get('name', 'Anki Dictionary').replace('-', ' ').title(),
        "name": project_config.get('name', 'Anki Dictionary').replace('-', ' ').title(),
        "requirements": macos_requirements
    }
    
    manifest_path = Path('build') / 'anki_dictionary_addon' / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f, indent=4)
    
    print(f"   ✓ Generated manifest.json with requirements: {macos_requirements}")
    return manifest_path

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
    
    # Generate manifest.json from pyproject.toml
    generate_manifest()
    
    # Create empty database using separate script instead of copying existing one
    db_path = addon_dir / 'user_files' / 'db' / 'dictionaries.sqlite'
    print("   Creating empty database...")
    try:
        subprocess.run([
            sys.executable, 
            'scripts/create_empty_db.py', 
            str(db_path)
        ], check=True, capture_output=True, text=True)
        print("   ✓ Database creation completed")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error creating database: {e}")
        print(f"   Output: {e.stdout}")
        print(f"   Error: {e.stderr}")
        raise
    
    # Create default themes.json using separate script
    themes_path = addon_dir / 'user_files' / 'themes' / 'themes.json'
    print("   Creating default themes.json...")
    try:
        subprocess.run([
            sys.executable, 
            'scripts/create_default_themes.py', 
            str(themes_path)
        ], check=True, capture_output=True, text=True)
        print("   ✓ Themes.json creation completed")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error creating themes.json: {e}")
        print(f"   Output: {e.stdout}")
        print(f"   Error: {e.stderr}")
        raise
    
    # Remove search history file if it exists (should be created by addon at runtime)
    search_history_path = addon_dir / 'user_files' / 'media' / '_searchHistory.json'
    if search_history_path.exists():
        search_history_path.unlink()
        print(f"   ✓ Removed _searchHistory.json (will be created at runtime)")
    
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
        for root, _, files in os.walk(addon_dir):
            for file in files:
                file_path = Path(root) / file
                arc_path = file_path.relative_to(addon_dir)
                zf.write(file_path, arc_path)
                print(f"   ✓ Added: {arc_path}")
    
    print(f"✅ Package created: {package_path}")
    return package_path



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
        print("  all      - Build addon and package")
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
    elif command == 'all':
        clean()
        build_addon()
        create_ankiaddon_package()
        print("\n🎉 Build completed!")
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == '__main__':
    main()
