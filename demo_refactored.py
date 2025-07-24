#!/usr/bin/env python3
"""
Demo script for the refactored Anki Dictionary Addon

This script demonstrates the key features and improvements of the refactored version.
"""

import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from external_launcher import (
    DependencyChecker, ConfigManager, MinimalAnkiEnvironment, 
    DictionaryLauncher
)


def demo_dependency_checker():
    """Demonstrate dependency checking functionality."""
    print("🔍 DEPENDENCY CHECKER DEMO")
    print("=" * 40)
    
    # Check what dependencies are available
    available, missing = DependencyChecker.check_dependencies()
    
    print(f"Dependencies available: {available}")
    if missing:
        print("Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print(f"\nInstall command: {DependencyChecker.get_install_command(missing)}")
    else:
        print("✅ All dependencies are available!")
    
    print()


def demo_config_manager():
    """Demonstrate configuration management."""
    print("⚙️  CONFIG MANAGER DEMO")
    print("=" * 40)
    
    addon_path = Path(__file__).parent
    config_manager = ConfigManager(addon_path)
    
    # Load current config
    config = config_manager.load_config()
    print("Current configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # Demonstrate saving a custom config
    custom_config = {
        **config,
        "maxWidth": 1500,
        "theme": "demo_theme",
        "demo_setting": "This is a demo!"
    }
    
    print("\nSaving custom configuration...")
    success = config_manager.save_config(custom_config)
    print(f"Save successful: {success}")
    
    # Load it back
    reloaded_config = config_manager.load_config()
    print(f"Reloaded maxWidth: {reloaded_config['maxWidth']}")
    print(f"Reloaded theme: {reloaded_config['theme']}")
    
    print()


def demo_minimal_anki_environment():
    """Demonstrate minimal Anki environment setup."""
    print("🏗️  MINIMAL ANKI ENVIRONMENT DEMO")
    print("=" * 40)
    
    addon_path = Path(__file__).parent
    environment = MinimalAnkiEnvironment(addon_path)
    
    # Create mock main window
    print("Creating mock main window...")
    mock_mw = environment.create_mock_main_window()
    
    print("Mock main window attributes:")
    attributes = [
        'addonManager', 'AnkiDictConfig', 'DictExportingDefinitions',
        'dictSettings', 'miDictDB', 'refreshAnkiDictConfig'
    ]
    
    for attr in attributes:
        has_attr = hasattr(mock_mw, attr)
        print(f"  {attr}: {'✅' if has_attr else '❌'}")
    
    # Test addon manager
    print("\nTesting addon manager...")
    config = mock_mw.addonManager.getConfig("test_addon")
    print(f"Got config with {len(config)} keys")
    
    # Test config refresh
    print("Testing config refresh...")
    new_config = {"test": "demo_value"}
    mock_mw.refreshAnkiDictConfig(new_config)
    print(f"Config after refresh: {mock_mw.AnkiDictConfig}")
    
    print()


def demo_dictionary_launcher():
    """Demonstrate dictionary launcher (without actually launching)."""
    print("🚀 DICTIONARY LAUNCHER DEMO")
    print("=" * 40)
    
    addon_path = Path(__file__).parent
    launcher = DictionaryLauncher(addon_path)
    
    print(f"Launcher addon path: {launcher.addon_path}")
    print(f"Environment type: {type(launcher.environment).__name__}")
    
    # Check if temp directory was created
    temp_dir = addon_path / 'temp'
    print(f"Temp directory exists: {'✅' if temp_dir.exists() else '❌'}")
    
    # Check if paths were set up
    print(f"Addon path in sys.path: {'✅' if str(addon_path) in sys.path else '❌'}")
    
    vendor_path = addon_path / 'vendor'
    if vendor_path.exists():
        print(f"Vendor path in sys.path: {'✅' if str(vendor_path) in sys.path else '❌'}")
    else:
        print("Vendor directory not found (this is normal)")
    
    print()


def demo_error_handling():
    """Demonstrate error handling capabilities."""
    print("🛡️  ERROR HANDLING DEMO")
    print("=" * 40)
    
    # Test config manager with bad path
    print("Testing config manager with invalid path...")
    bad_config_manager = ConfigManager(Path("/nonexistent/path"))
    
    # This should not crash, but return defaults
    config = bad_config_manager.load_config()
    print(f"Got default config with {len(config)} keys")
    
    # This should fail gracefully
    save_result = bad_config_manager.save_config({"test": "value"})
    print(f"Save to bad path result: {save_result}")
    
    print()


def demo_testing_framework():
    """Demonstrate the testing framework."""
    print("🧪 TESTING FRAMEWORK DEMO")
    print("=" * 40)
    
    print("Available test files:")
    test_dir = Path(__file__).parent / 'tests'
    if test_dir.exists():
        test_files = list(test_dir.glob('test_*.py'))
        for test_file in test_files:
            print(f"  - {test_file.name}")
        
        print(f"\nTotal test files: {len(test_files)}")
        print("Run tests with: python run_tests.py")
    else:
        print("Tests directory not found")
    
    print()


def main():
    """Run all demos."""
    print("🎯 REFACTORED ANKI DICTIONARY ADDON DEMO")
    print("=" * 50)
    print("This demo shows the key features of the refactored version")
    print()
    
    try:
        demo_dependency_checker()
        demo_config_manager()
        demo_minimal_anki_environment()
        demo_dictionary_launcher()
        demo_error_handling()
        demo_testing_framework()
        
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("Key improvements demonstrated:")
        print("✅ Simplified dependency checking")
        print("✅ Robust configuration management")
        print("✅ Clean minimal Anki environment")
        print("✅ Modular launcher architecture")
        print("✅ Comprehensive error handling")
        print("✅ Full testing framework")
        print()
        print("To run the actual dictionary addon:")
        print("  python standalone_launcher.py")
        print()
        print("To run tests:")
        print("  python run_tests.py")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())