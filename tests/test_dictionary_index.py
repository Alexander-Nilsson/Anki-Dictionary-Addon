import unittest
import requests
import json
import urllib.parse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from anki_dictionary.utils.common import prefer_ipv4

class TestDictionaryIndex(unittest.TestCase):
    INDEX_URL = "https://raw.githubusercontent.com/Alexander-Nilsson/dictionaries/main/index.json"
    SERVER_ROOT = "https://raw.githubusercontent.com/Alexander-Nilsson/dictionaries/main"

    def test_index_is_valid_json(self):
        """Test that the dictionary index can be fetched and is valid JSON."""
        with prefer_ipv4():
            resp = requests.get(self.INDEX_URL)
        self.assertEqual(resp.status_code, 200, f"Failed to fetch index from {self.INDEX_URL}")
        
        try:
            data = resp.json()
            self.assertIn("languages", data)
        except json.JSONDecodeError:
            self.fail("Index is not valid JSON")

    def test_all_dictionary_urls(self):
        """Test all dictionary URLs in the index and report which ones are broken."""
        # Use a random param to bust cache just in case
        import time
        cache_buster = f"?t={int(time.time())}"
        with prefer_ipv4():
            resp = requests.get(self.INDEX_URL + cache_buster, headers={"Cache-Control": "no-cache"})
        self.assertEqual(resp.status_code, 200)
        index = resp.json()
        
        broken_urls = []
        checked_count = 0
        
        languages = index.get("languages", [])
        for lang in languages:
            # Check dictionaries in main language
            for d in lang.get("dictionaries", []):
                url = d.get("url")
                if url:
                    full_url = self._construct_url(url)
                    checked_count += 1
                    if not self._check_url(full_url):
                        broken_urls.append(f"{lang['name_en']} -> {d['name']}: {full_url}")
            
            # Check to_languages
            for to_lang in lang.get("to_languages", []):
                for d in to_lang.get("dictionaries", []):
                    url = d.get("url")
                    if url:
                        full_url = self._construct_url(url)
                        checked_count += 1
                        if not self._check_url(full_url):
                            broken_urls.append(f"{lang['name_en']} to {to_lang['name_en']} -> {d['name']}: {full_url}")
        
        if broken_urls:
            report = "\n".join(broken_urls)
            self.fail(f"Found {len(broken_urls)} broken URLs out of {checked_count} checked:\n{report}")
        else:
            print(f"Successfully checked {checked_count} dictionary URLs.")

    def _construct_url(self, url):
        if not url.startswith("http"):
            # Ensure we don't have double slashes if url starts with /
            root = self.SERVER_ROOT.rstrip("/")
            path = url.lstrip("/")
            return f"{root}/{path}"
        return url

    def _check_url(self, url):
        import urllib.parse
        
        # Simple quoting to handle spaces in URLs
        parts = url.split("://")
        if len(parts) > 1:
            quoted_url = parts[0] + "://" + urllib.parse.quote(parts[1], safe="/")
        else:
            quoted_url = urllib.parse.quote(url, safe="/")
        
        try:
            with prefer_ipv4():
                # Using head request to be faster
                resp = requests.head(quoted_url, allow_redirects=True, timeout=10)
                if resp.status_code == 200:
                    return True
                # Some servers might not support HEAD properly
                resp = requests.get(quoted_url, stream=True, timeout=10)
                return resp.status_code == 200
        except Exception as e:
            return False

if __name__ == "__main__":
    unittest.main()
