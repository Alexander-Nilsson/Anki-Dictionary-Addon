import unittest
import requests
import json
import urllib.parse
import sys
import os

import pytest

pytestmark = pytest.mark.network

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from anki_dictionary.utils.common import prefer_ipv4


class TestDictionaryIndex(unittest.TestCase):
    INDEX_URL = "https://github.com/Alexander-Nilsson/dictionaries/raw/main/index.json"
    SERVER_ROOT = "https://github.com/Alexander-Nilsson/dictionaries/raw/main"

    def test_index_is_valid_json(self):
        """Test that the dictionary index can be fetched and is valid JSON."""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            with prefer_ipv4():
                resp = session.get(self.INDEX_URL)
            self.assertEqual(
                resp.status_code, 200, f"Failed to fetch index from {self.INDEX_URL}"
            )

            try:
                data = resp.json()
                self.assertIn("languages", data)
            except json.JSONDecodeError:
                self.fail("Index is not valid JSON")
        finally:
            session.close()

    def _construct_url(self, url):
        if not url.startswith("http"):
            # Ensure we don't have double slashes if url starts with /
            root = self.SERVER_ROOT.rstrip("/")
            path = url.lstrip("/")
            return f"{root}/{path}"
        return url

    def _check_url(self, url):
        import urllib.parse
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        # Simple quoting to handle spaces in URLs
        parts = url.split("://")
        if len(parts) > 1:
            quoted_url = parts[0] + "://" + urllib.parse.quote(parts[1], safe="/")
        else:
            quoted_url = urllib.parse.quote(url, safe="/")

        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            with prefer_ipv4():
                # Use GET with stream=True so we can check the size without downloading everything
                resp = session.get(
                    quoted_url, stream=True, timeout=10, allow_redirects=True
                )
                if resp.status_code != 200:
                    return False, f"HTTP {resp.status_code}"

                # If it's a dictionary (zip), it should definitely be larger than an LFS pointer (approx 130 bytes)
                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) < 500:
                    # Check if it looks like an LFS pointer
                    chunk = next(resp.iter_content(chunk_size=500), b"")
                    if b"git-lfs" in chunk:
                        return False, "LFS pointer detected"

                return True, "OK"
        except Exception as e:
            return False, str(e)
        finally:
            session.close()

    def test_all_dictionary_urls(self):
        """Test all dictionary URLs in the index and report which ones are broken."""
        # Use a random param to bust cache just in case
        import time
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        cache_buster = f"?t={int(time.time())}"

        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            with prefer_ipv4():
                resp = session.get(
                    self.INDEX_URL + cache_buster,
                    headers={"Cache-Control": "no-cache"},
                    timeout=15,
                )
            self.assertEqual(resp.status_code, 200)
            index = resp.json()
        finally:
            session.close()

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
                    success, error = self._check_url(full_url)
                    if not success:
                        broken_urls.append(
                            f"{lang['name_en']} -> {d['name']}: {full_url} ({error})"
                        )

            # Check to_languages
            for to_lang in lang.get("to_languages", []):
                for d in to_lang.get("dictionaries", []):
                    url = d.get("url")
                    if url:
                        full_url = self._construct_url(url)
                        checked_count += 1
                        success, error = self._check_url(full_url)
                        if not success:
                            broken_urls.append(
                                f"{lang['name_en']} to {to_lang['name_en']} -> {d['name']}: {full_url} ({error})"
                            )

        if broken_urls:
            report = "\n".join(broken_urls)
            self.fail(
                f"Found {len(broken_urls)} broken URLs out of {checked_count} checked:\n{report}"
            )
        else:
            print(f"Successfully checked {checked_count} dictionary URLs.")


if __name__ == "__main__":
    unittest.main()
