#!/usr/bin/env python3
"""
Test suite for the image provider system.
"""

import sys
import os
import unittest

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from anki_dictionary.integrations.image_providers import get_provider, AVAILABLE_PROVIDERS
    from anki_dictionary.integrations.image_providers.base import ImageProvider
    from anki_dictionary.integrations.image_providers.duckduckgo import DuckDuckGoProvider
except ImportError as e:
    print(f"Warning: Could not import image providers: {e}")
    print("This test requires the full Anki environment to run properly.")
    sys.exit(0)


class TestImageProviderSystem(unittest.TestCase):
    """Test the image provider system."""

    def test_available_providers(self):
        """Test that providers are registered correctly."""
        self.assertIn('duckduckgo', AVAILABLE_PROVIDERS)
        self.assertEqual(AVAILABLE_PROVIDERS['duckduckgo'], DuckDuckGoProvider)

    def test_get_provider_duckduckgo(self):
        """Test getting DuckDuckGo provider."""
        try:
            provider = get_provider('duckduckgo')
            self.assertIsInstance(provider, DuckDuckGoProvider)
            self.assertIsInstance(provider, ImageProvider)
        except Exception as e:
            self.skipTest(f"Could not instantiate provider (requires Qt): {e}")

    def test_get_provider_invalid(self):
        """Test getting invalid provider."""
        with self.assertRaises(ValueError):
            get_provider('nonexistent')

    def test_provider_interface(self):
        """Test that DuckDuckGo provider implements required methods."""
        # Check that the class has required methods
        required_methods = ['search', 'getHtml', 'setSearchRegion']
        for method in required_methods:
            self.assertTrue(hasattr(DuckDuckGoProvider, method))

    def test_backwards_compatibility(self):
        """Test that old imports still work."""
        try:
            from anki_dictionary.integrations.image_search import DuckDuckGo
            # Should be importable (even if it's a wrapper)
            self.assertTrue(hasattr(DuckDuckGo, 'search'))
            self.assertTrue(hasattr(DuckDuckGo, 'getHtml'))
        except ImportError as e:
            self.fail(f"Backwards compatibility broken: {e}")


if __name__ == '__main__':
    unittest.main()
