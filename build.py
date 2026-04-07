#!/usr/bin/env python3
"""
Build script for the Anki Dictionary Addon

This script helps build and package the addon for distribution.
It handles dependency installation and file bundling.
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
        
        return config
    except Exception as e:
        print(f"Warning: Could not read config from pyproject.toml: {e}")
        return {'project': {'version': '0.1.0', 'name': 'Anki Dictionary'}}

def get_version():
    """Get version from pyproject.toml"""
    return get_project_config()['project'].get('version', '0.1.0')

def install_dependencies(addon_dir):
    """Install dependencies into vendor directory"""
    print("📦 Installing dependencies...")
    
    config = get_project_config()
    dependencies = config['project'].get('dependencies', [])
    
    # Filter dependencies to bundle
    # We exclude PyQt (provided by Anki), Pillow (provided by Anki), 
    # and system-specific binary wheels if we can rely on Anki
    # We bundle: pynput
    # We exclude: pyqt6*, requests (Anki has it), pyobjc* (Anki has it)
    
    to_install = []
    for dep in dependencies:
        name = dep.split('>=')[0].split('==')[0].split(';')[0].strip()
        if name.lower() in ['pynput']:
            to_install.append(dep)
        elif name.lower() in ['requests', 'urllib3']:
             # Anki has requests, but bundling specific version might be safer?
             # For now, let's trust Anki's requests to avoid conflicts.
             pass
    
    if not to_install:
        print("   No dependencies to bundle.")
        return

    vendor_dir = addon_dir / 'vendor'
    if vendor_dir.exists():
        shutil.rmtree(vendor_dir)
    vendor_dir.mkdir()
    
    print(f"   Installing: {', '.join(to_install)}")
    
    # Create a requirements file
    req_file = addon_dir / 'requirements-vendor.txt'
    with open(req_file, 'w') as f:
        for dep in to_install:
            f.write(f"{dep}\n")
            
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', 
            '-t', str(vendor_dir), 
            '-r', str(req_file),
            '--no-compile'
        ], check=True, capture_output=True, text=True)
        print("   ✓ Dependencies installed successfully")
        
        # Cleanup requirements file
        req_file.unlink()
        
        # Remove .dist-info directories to save space
        for item in vendor_dir.glob('*.dist-info'):
            shutil.rmtree(item)
            
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error installing dependencies: {e}")
        print(f"   Output: {e.stdout}")
        print(f"   Error: {e.stderr}")
        raise

def create_user_files_structure(addon_dir):
    """Create the user_files directory structure"""
    print("📂 Creating user_files structure...")
    
    user_files = addon_dir / 'user_files'
    user_files.mkdir(exist_ok=True)
    
    # Create subdirectories
    dirs = [
        'db',
        'db/frequency',
        'db/conjugation',
        'dictionaries',
        'fonts',
        'media',
        'themes'
    ]
    
    for d in dirs:
        (user_files / d).mkdir(exist_ok=True)
        
    print("   ✓ Created directory structure")

def generate_manifest():
    """Generate manifest.json from pyproject.toml data"""
    project_config = get_project_config()['project']
    
    # Extract macOS-specific requirements for manifest
    dependencies = project_config.get('dependencies', [])
    macos_requirements = []
    
    for dep in dependencies:
        if 'pyobjc' in dep and 'darwin' in dep:
            # Extract package name before semicolon
            package_name = dep.split(';')[0].strip()
            # macos_requirements.append(package_name) 
            # Actually, manifest 'requirements' are usually not used by Anki for pip install?
            # Anki checks this list to warn users?
            pass
            
    manifest_data = {
        "package": project_config.get('name', 'Anki Dictionary').replace('-', ' ').title(),
        "name": project_config.get('name', 'Anki Dictionary').replace('-', ' ').title(),
        # "requirements": macos_requirements 
    }
    
    manifest_path = Path('build') / 'anki_dictionary_addon' / 'manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f, indent=4)
    
    print(f"   ✓ Generated manifest.json")
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
    
    addon_dir = build_dir / 'anki_dictionary_addon'
    addon_dir.mkdir()
    
    # Copy essential files for Anki addon
    # Note: user_files and vendor are handled separately
    essential_files = [
        '__init__.py',
        'config.json',
        'src/',
        'assets/',
    ]
    
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
    
    # Clean config.json in build directory
    config_path = addon_dir / 'config.json'
    if config_path.exists():
        print("   🧹 Cleaning configuration in build...")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Reset to defaults
        config["DictionaryGroups"] = {}
        config["ExportTemplates"] = {}
        config["ImageFields"] = []
        config["currentGroup"] = "All"
        config["dictSizePos"] = [0, 0, 800, 600]
        config["currentTemplate"] = False
        config["currentDeck"] = False
        
        # Reset LLM settings
        config["llm_enabled"] = False
        config["llm_api_key"] = ""
        config["llm_base_url"] = "https://api.openai.com/v1/chat/completions"
        config["llm_model"] = "gpt-3.5-turbo"
        config["llm_prompt"] = "Provide a concise dictionary definition for the word: {term}"
        config["llm_timeout"] = 15
            
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print("   ✓ Configuration reset to defaults")
    
    # Create user_files structure
    create_user_files_structure(addon_dir)
    
    # Install dependencies
    install_dependencies(addon_dir)
    
    # Generate manifest.json
    generate_manifest()
    
    # Create empty database using separate script
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
        # print(f"   Output: {e.stdout}")
        # print(f"   Error: {e.stderr}")
        # Continue even if DB creation fails (user might create it at runtime)
        pass
    
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
        pass
    
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
            # Write directories (including empty ones)
            for d in dirs:
                dir_path = Path(root) / d
                arc_path = dir_path.relative_to(addon_dir)
                zf.write(dir_path, str(arc_path) + '/')
            # Write files
            for file in files:
                file_path = Path(root) / file
                arc_path = file_path.relative_to(addon_dir)
                zf.write(file_path, arc_path)
    
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
