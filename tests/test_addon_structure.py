#!/usr/bin/env python3
"""
Tests for the main Anki Dictionary Addon functionality
"""

import unittest
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestAddonBasics(unittest.TestCase):
    """Test basic addon functionality."""

    def test_addon_module_structure(self):
        """Test that the built addon module structure exists."""
        build_dir = Path(__file__).parent.parent / "build" / "anki_dictionary_addon"

        # Check if build directory exists
        self.assertTrue(build_dir.exists(), "Build directory does not exist - run build first")

        # Check essential files exist in build directory
        self.assertTrue((build_dir / "__init__.py").exists())
        self.assertTrue((build_dir / "config.json").exists())
        self.assertTrue((build_dir / "manifest.json").exists())

        # Check main directories exist in build
        self.assertTrue((build_dir / "src").exists(), "src directory missing from build")
        self.assertTrue((build_dir / "assets").exists(), "assets directory missing from build")

    def test_config_json_valid(self):
        """Test that config.json is valid JSON."""
        import json

        config_path = Path(__file__).parent.parent / "build" / "anki_dictionary_addon" / "config.json"
        with open(config_path, "r") as f:
            config = json.load(f)

        # Should be a dictionary
        self.assertIsInstance(config, dict)

    def test_pyproject_toml_valid(self):
        """Test that pyproject.toml is valid TOML and has version."""
        try:
            import tomllib

            pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)

            # Should be a dictionary with required fields
            self.assertIsInstance(config, dict)
            self.assertIn("project", config)
            self.assertIn("version", config["project"])
        except ImportError:
            # Skip test if tomllib not available (Python < 3.11)
            self.skipTest("tomllib not available")


class TestAddonImports(unittest.TestCase):
    """Test addon module imports."""

    def test_can_import_addon_modules(self):
        """Test that core addon modules can be imported from build."""
        build_dir = Path(__file__).parent.parent / "build" / "anki_dictionary_addon"
        if not build_dir.exists():
            self.skipTest("Build directory does not exist - run build first")
            
        # Add src directory from build to path for import test
        import sys
        src_path = str(build_dir / "src")
        sys.path.insert(0, src_path)
        
        try:
            # Test if anki_dictionary module can be imported from build
            import anki_dictionary  # noqa: F401
            self.assertTrue(True, "anki_dictionary module imported successfully from build")
        except ImportError as e:
            # This might be expected if dependencies are missing
            if "anki" in str(e).lower():
                self.skipTest(f"Anki dependencies not available: {e}")
            else:
                self.fail(f"Unexpected import error: {e}")
        finally:
            # Clean up sys.path
            if src_path in sys.path:
                sys.path.remove(src_path)

    def test_addon_structure_integrity(self):
        """Test that addon module structure is intact in build."""
        build_dir = Path(__file__).parent.parent / "build" / "anki_dictionary_addon"
        
        if not build_dir.exists():
            self.skipTest("Build directory does not exist - run build first")

        # Test essential files exist in build
        essential_files = ["__init__.py", "config.json", "manifest.json"]
        for file_name in essential_files:
            file_path = build_dir / file_name
            self.assertTrue(file_path.exists(), f"Essential file {file_name} missing from build")

        # Test that build directory contains expected directories
        expected_dirs = ["src", "assets", "user_files", "vendor"]
        for dir_name in expected_dirs:
            dir_path = build_dir / dir_name
            self.assertTrue(dir_path.exists(), f"Expected directory {dir_name} missing from build")

        # Test that build directory contains expected structure
        self.assertTrue(len(list(build_dir.iterdir())) > 0, "Build directory is empty")


if __name__ == "__main__":
    unittest.main()
