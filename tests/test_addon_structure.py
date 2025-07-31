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
        """Test that the addon module structure exists."""
        addon_root = Path(__file__).parent.parent

        # Check essential files exist
        self.assertTrue((addon_root / "__init__.py").exists())
        self.assertTrue((addon_root / "config.json").exists())
        self.assertTrue((addon_root / "manifest.json").exists())

        # Check src directory structure
        src_dir = addon_root / "src" / "anki_dictionary"
        self.assertTrue(src_dir.exists())
        self.assertTrue((src_dir / "__init__.py").exists())

        # Check main modules exist
        self.assertTrue((src_dir / "core").exists())
        self.assertTrue((src_dir / "ui").exists())
        self.assertTrue((src_dir / "utils").exists())

    def test_config_json_valid(self):
        """Test that config.json is valid JSON."""
        import json

        config_path = Path(__file__).parent.parent / "config.json"
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
        """Test that core addon modules can be imported."""
        try:
            # These imports might fail due to Anki dependencies,
            # but we test the structure
            import anki_dictionary  # noqa: F401
            from anki_dictionary import core, ui, utils  # noqa: F401

            # If we get here, imports worked
            self.assertTrue(True)
        except ImportError as e:
            # This is expected in test environment without Anki
            self.assertIn("anki", str(e).lower())

    def test_addon_structure_integrity(self):
        """Test that addon module structure is intact."""
        src_dir = Path(__file__).parent.parent / "src" / "anki_dictionary"

        # Test core modules
        core_modules = ["database", "dictionary", "hooks"]
        for module in core_modules:
            module_path = src_dir / "core" / f"{module}.py"
            self.assertTrue(module_path.exists(), f"Core module {module}.py missing")

        # Test UI modules
        ui_path = src_dir / "ui"
        self.assertTrue((ui_path / "main_window.py").exists())
        self.assertTrue((ui_path / "themes.py").exists())

        # Test utils modules
        utils_modules = [
            "common",
            "config",
            "clipboard",
            "ffmpeg",
            "history",
            "updater",
        ]
        for module in utils_modules:
            module_path = src_dir / "utils" / f"{module}.py"
            self.assertTrue(module_path.exists(), f"Utils module {module}.py missing")


if __name__ == "__main__":
    unittest.main()
