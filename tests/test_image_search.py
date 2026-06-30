from __future__ import annotations

import hashlib
import os
import ssl
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests
from requests.adapters import HTTPAdapter

from anki_dictionary.integrations.image_search import (
    DuckDuckGo,
    DuckDuckGoSignals,
    TLSAdapter,
    _make_session,
    log_debug,
)


class TestDuckDuckGoSetTermIdName(unittest.TestCase):
    def test_sets_term_and_id_name_and_resets_offset(self):
        ddg = DuckDuckGo()
        ddg.search_offset = 10
        ddg.setTermIdName("apple", "search")
        self.assertEqual(ddg.term, "apple")
        self.assertEqual(ddg.idName, "search")
        self.assertEqual(ddg.search_offset, 0)

    def test_load_more_preserves_offset(self):
        ddg = DuckDuckGo()
        ddg.search_offset = 10
        ddg.setTermIdName("apple", "load_more")
        self.assertEqual(ddg.term, "apple")
        self.assertEqual(ddg.idName, "load_more")
        self.assertEqual(ddg.search_offset, 10)


class TestDuckDuckGoSetSearchRegion(unittest.TestCase):
    def test_valid_country_sets_language(self):
        ddg = DuckDuckGo()
        ddg.setSearchRegion("France")
        self.assertEqual(ddg.language, "fr-fr")

    def test_invalid_country_defaults_to_us_en(self):
        ddg = DuckDuckGo()
        ddg.setSearchRegion("NonExistentCountry")
        self.assertEqual(ddg.language, "us-en")


class TestDuckDuckGoFetchVQD(unittest.TestCase):
    def test_returns_vqd_from_header(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.headers = {"x-vqd-4": "abc123vqd"}
        mock_resp.text = ""
        ddg.session.post.return_value = mock_resp

        result = ddg._fetch_vqd("test")
        self.assertEqual(result, "abc123vqd")

    def test_returns_vqd_from_html_pattern(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.headers = {}
        mock_resp.text = 'some text vqd="myvqdvalue" more text'
        ddg.session.post.return_value = mock_resp

        result = ddg._fetch_vqd("test")
        self.assertEqual(result, "myvqdvalue")

    def test_returns_none_when_vqd_not_found(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.headers = {}
        mock_resp.text = "<html>no vqd token here</html>"
        ddg.session.post.return_value = mock_resp

        result = ddg._fetch_vqd("test")
        self.assertIsNone(result)

    def test_handles_request_exception(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        ddg.session.post.side_effect = requests.RequestException("connection error")

        result = ddg._fetch_vqd("test")
        self.assertIsNone(result)


class TestDuckDuckGoSearch(unittest.TestCase):
    def test_returns_empty_list_when_no_vqd(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        with patch.object(ddg, "_fetch_vqd", return_value=None):
            with patch("anki_dictionary.integrations.image_search.prefer_ipv4"):
                result = ddg.search("test")
                self.assertEqual(result, [])

    def test_returns_image_urls_on_success(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {"image": "http://example.com/img1.jpg"},
                {"image": "http://example.com/img2.jpg"},
            ]
        }
        ddg.session.get.return_value = mock_resp

        with patch.object(ddg, "_fetch_vqd", return_value="testvqd"):
            with patch("anki_dictionary.integrations.image_search.prefer_ipv4"):
                result = ddg.search("test", maximum=15)
                self.assertEqual(len(result), 2)
                self.assertIn("http://example.com/img1.jpg", result)
                self.assertIn("http://example.com/img2.jpg", result)

    def test_respects_maximum_param(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [{"image": f"http://example.com/img{i}.jpg"} for i in range(20)]
        }
        ddg.session.get.return_value = mock_resp

        with patch.object(ddg, "_fetch_vqd", return_value="testvqd"):
            with patch("anki_dictionary.integrations.image_search.prefer_ipv4"):
                result = ddg.search("test", maximum=5)
                self.assertEqual(len(result), 5)

    def test_handles_non_200_status(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {}
        ddg.session.get.return_value = mock_resp

        with patch.object(ddg, "_fetch_vqd", return_value="testvqd"):
            with patch("anki_dictionary.integrations.image_search.prefer_ipv4"):
                result = ddg.search("test")
                self.assertEqual(result, [])

    def test_handles_exception_in_search(self):
        ddg = DuckDuckGo()
        ddg.session = MagicMock()
        ddg.session.get.side_effect = requests.RequestException("timeout")

        with patch.object(ddg, "_fetch_vqd", return_value="testvqd"):
            with patch("anki_dictionary.integrations.image_search.prefer_ipv4"):
                result = ddg.search("test")
                self.assertEqual(result, [])


class TestDuckDuckGoProcessImage(unittest.TestCase):
    def test_returns_empty_string_for_empty_content(self):
        ddg = DuckDuckGo()
        result = ddg.process_image("http://example.com/img.jpg", b"")
        self.assertEqual(result, "")

    def test_returns_empty_when_load_from_data_fails(self):
        ddg = DuckDuckGo()
        with patch("anki_dictionary.integrations.image_search.QImage") as mock_qc:
            mock_img = mock_qc.return_value
            mock_img.loadFromData.return_value = False

            result = ddg.process_image("http://example.com/img.jpg", b"bad_data")
            self.assertEqual(result, "")

    def test_returns_filename_on_success(self):
        url = "http://example.com/img.jpg"
        expected_hash = hashlib.md5(url.encode()).hexdigest()
        expected_name = f"dict_img_{expected_hash}.avif"

        ddg = DuckDuckGo()
        with patch("anki_dictionary.integrations.image_search.QImage") as mock_qc:
            mock_img = mock_qc.return_value
            mock_img.loadFromData.return_value = True
            mock_img.scaled.return_value = mock_img
            mock_img.save.return_value = True

            with patch("anki_dictionary.integrations.image_search.temp_dir", "/tmp"):
                result = ddg.process_image(url, b"valid_content")
                self.assertEqual(result, expected_name)

    def test_returns_empty_when_save_fails(self):
        ddg = DuckDuckGo()
        with patch("anki_dictionary.integrations.image_search.QImage") as mock_qc:
            mock_img = mock_qc.return_value
            mock_img.loadFromData.return_value = True
            mock_img.scaled.return_value = mock_img
            mock_img.save.return_value = False

            with patch("anki_dictionary.integrations.image_search.temp_dir", "/tmp"):
                result = ddg.process_image("http://example.com/img.jpg", b"valid")
                self.assertEqual(result, "")

    def test_scales_image_to_200x200(self):
        ddg = DuckDuckGo()
        with patch("anki_dictionary.integrations.image_search.QImage") as mock_qc:
            mock_img = mock_qc.return_value
            mock_img.loadFromData.return_value = True
            mock_scaled_mock = MagicMock()
            mock_img.scaled = mock_scaled_mock
            mock_img.save.return_value = True

            with patch("anki_dictionary.integrations.image_search.temp_dir", "/tmp"):
                ddg.process_image("http://example.com/img.jpg", b"valid")
                mock_scaled_mock.assert_called_once()
                args, kwargs = mock_scaled_mock.call_args
                self.assertEqual(len(args), 3)
                self.assertEqual(kwargs, {})
                # First arg should be QSize-like with width=200, height=200
                size_arg = args[0]
                self.assertTrue(
                    hasattr(size_arg, "width") and hasattr(size_arg, "height")
                )
                self.assertEqual(size_arg.width(), 200)
                self.assertEqual(size_arg.height(), 200)
                # Second and third args should be the enum values (we can't easily check exact values
                # due to potential mocking, but we can verify they're not None)
                self.assertIsNotNone(args[1])
                self.assertIsNotNone(args[2])


class TestDuckDuckGoImageToHtml(unittest.TestCase):
    def test_returns_error_html_for_missing_file(self):
        ddg = DuckDuckGo()
        result = ddg._image_to_html("nonexistent.avif")
        self.assertIn("Error loading image", result)

    def test_returns_image_html_for_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("anki_dictionary.integrations.image_search.temp_dir", tmpdir):
                filename = "test_img.avif"
                with open(os.path.join(tmpdir, filename), "wb") as f:
                    f.write(b"fake_image_data")

                ddg = DuckDuckGo()
                result = ddg._image_to_html(filename)
                self.assertIn("data:image/avif;base64,", result)
                self.assertIn('class="imgBox"', result)
                self.assertIn('class="searchImage"', result)
                self.assertIn(f'ankiDict="{os.path.join(tmpdir, filename)}"', result)


class TestDuckDuckGoDownloadAndProcessImageSync(unittest.TestCase):
    def test_returns_empty_string_on_failure(self):
        ddg = DuckDuckGo()
        dl_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        dl_session.get.return_value = mock_resp

        with patch("anki_dictionary.integrations.image_search.prefer_ipv4"):
            result = ddg.download_and_process_image_sync(
                "http://example.com/img.jpg", dl_session
            )
            self.assertEqual(result, "")

    def test_returns_filename_on_success(self):
        ddg = DuckDuckGo()
        dl_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake_image"
        dl_session.get.return_value = mock_resp

        with patch.object(ddg, "process_image", return_value="dict_img_abc.avif"):
            with patch("anki_dictionary.integrations.image_search.prefer_ipv4"):
                result = ddg.download_and_process_image_sync(
                    "http://example.com/img.jpg", dl_session
                )
                self.assertEqual(result, "dict_img_abc.avif")
                dl_session.get.assert_called_once_with(
                    "http://example.com/img.jpg", timeout=10
                )

    def test_handles_request_exception(self):
        ddg = DuckDuckGo()
        dl_session = MagicMock()
        dl_session.get.side_effect = requests.RequestException("timeout")

        with patch("anki_dictionary.integrations.image_search.prefer_ipv4"):
            result = ddg.download_and_process_image_sync(
                "http://example.com/img.jpg", dl_session
            )
            self.assertEqual(result, "")


class TestDuckDuckGoSignals(unittest.TestCase):
    def test_signals_exist(self):
        signals = DuckDuckGoSignals()
        self.assertTrue(hasattr(signals, "resultsFound"))
        self.assertTrue(hasattr(signals, "noResults"))
        self.assertTrue(hasattr(signals, "finished"))


class TestTLSAdapter(unittest.TestCase):
    def test_init_poolmanager_sets_ssl_context(self):
        adapter = TLSAdapter()
        with patch.object(HTTPAdapter, "init_poolmanager") as mock_super:
            adapter.init_poolmanager()
            mock_super.assert_called_once()
            _, kwargs = mock_super.call_args
            ctx = kwargs["ssl_context"]
            self.assertIsNotNone(ctx)
            self.assertFalse(ctx.check_hostname)
            self.assertEqual(ctx.verify_mode, ssl.CERT_NONE)

    def test_init_poolmanager_sets_minimum_tls_version(self):
        adapter = TLSAdapter()
        with patch.object(HTTPAdapter, "init_poolmanager") as mock_super:
            adapter.init_poolmanager()
            _, kwargs = mock_super.call_args
            ctx = kwargs["ssl_context"]
            self.assertEqual(ctx.minimum_version, ssl.TLSVersion.TLSv1_2)


class TestMakeSession(unittest.TestCase):
    def test_returns_requests_session_on_linux(self):
        with patch("anki_dictionary.integrations.image_search._ON_MAC", False):
            session = _make_session()
            self.assertIsInstance(session, requests.Session)
            self.assertFalse(session.verify)

    def test_mounts_tls_adapter_on_https(self):
        with patch("anki_dictionary.integrations.image_search._ON_MAC", False):
            session = _make_session()
            adapter = session.get_adapter("https://duckduckgo.com")
            self.assertIsInstance(adapter, TLSAdapter)


class TestLogDebug(unittest.TestCase):
    def test_writes_to_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("anki_dictionary.integrations.image_search.temp_dir", tmpdir):
                log_debug("test message")
                log_path = os.path.join(tmpdir, "image_search_debug.log")
                self.assertTrue(os.path.exists(log_path))
                with open(log_path, encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("test message", content)

    def test_handles_write_error_gracefully(self):
        with patch("builtins.open", side_effect=OSError("permission denied")):
            try:
                log_debug("should not crash")
            except Exception:
                self.fail("log_debug raised an exception on write error")


if __name__ == "__main__":
    unittest.main()
