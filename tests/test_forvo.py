import base64
import builtins
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from anki_dictionary.integrations.forvo import (
    NO_HTTP_RESPONSE,
    ForvoWorker,
    _curl_cffi_requests,
    _fetch_url,
)


def _curl(stdout, returncode=0):
    """A completed `curl -w "\n%{http_code}"` run."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


class TestForvo(unittest.TestCase):
    def test_forvo_worker_parsing(self):
        """Test that ForvoWorker correctly parses Forvo HTML."""
        b64_mp3 = base64.b64encode(b"test.mp3").decode("utf-8")

        mock_html = f"""
        <div id="language-container-ja">
            <ul class="pronunciations-list">
                <li>
                    <div id="play_123" class="play" onclick="Play(123,'arg2','arg3',true,'{b64_mp3}','ja',1,'Japan','mp3')"></div>
                    <span class="info">
                        Pronunciation by <a class="ofLink">user1</a>
                        <span class="from">from Japan</span>
                    </span>
                    <span class="num_votes">5 votes</span>
                </li>
            </ul>
        </div>
        """

        worker = ForvoWorker("test", "ja", {})
        worker.signals = MagicMock()

        with patch("anki_dictionary.integrations.forvo._fetch_url") as mock_fetch:
            mock_fetch.return_value = (200, mock_html)
            worker.run()

            worker.signals.result_ready.emit.assert_called_once()
            result = worker.signals.result_ready.emit.call_args[0][0]

            self.assertEqual(result["term"], "test")
            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(result["items"][0]["user"], "user1")
            self.assertEqual(result["items"][0]["votes"], 5)
            self.assertIn("test.mp3", result["items"][0]["audio_url"])


class FakeResponse:
    """Minimal requests-like response for curl_cffi mocks."""

    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class FakeCurlRequests:
    """A curl_cffi-like module yielding `responses` one `.get` call at a time.

    An entry may be an ``(status_code, text)`` tuple or an ``Exception``
    instance (which `.get` raises, standing in for a request-level failure).
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, impersonate=None, timeout=0):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return FakeResponse(*response)


class TestFetchUrl(unittest.TestCase):
    """`_fetch_url` must report Forvo's real HTTP status.

    Fetches go through the bundled curl_cffi (browser TLS impersonation) by
    default, because Cloudflare fingerprint-blocks system curl with HTTP 403.
    The system-curl fallback is covered in TestFetchUrlSubprocessFallback.
    """

    def _fetch(self, responses, url="https://forvo.com/word/cat"):
        fake = FakeCurlRequests(responses)
        with (
            patch(
                "anki_dictionary.integrations.forvo._curl_cffi_requests",
                return_value=fake,
            ),
            patch("time.sleep"),
        ):
            status, html = _fetch_url(url)
        return status, html, fake

    def test_returns_the_real_http_status_and_body(self):
        status, html, fake = self._fetch([(200, "<html>hi</html>")])
        self.assertEqual(status, 200)
        self.assertEqual(html, "<html>hi</html>")
        self.assertEqual(fake.calls, 1)

    def test_404_is_final_and_not_retried(self):
        status, _, fake = self._fetch([(404, "<html>not found</html>")])
        self.assertEqual(status, 404)
        self.assertEqual(fake.calls, 1, "a 404 is a final answer")

    def test_cloudflare_challenge_becomes_403_after_retries(self):
        challenge = (200, "<html>Just a moment...</html>")
        status, html, fake = self._fetch([challenge] * 3)
        self.assertEqual(status, 403)
        self.assertEqual(html, "")
        self.assertEqual(fake.calls, 3)

    def test_retries_then_succeeds(self):
        status, html, fake = self._fetch(
            [RuntimeError("connection refused"), (200, "<html>ok</html>")]
        )
        self.assertEqual(status, 200)
        self.assertEqual(html, "<html>ok</html>")
        self.assertEqual(fake.calls, 2)

    def test_request_failure_reports_no_http_response(self):
        status, _, fake = self._fetch([RuntimeError("reset")] * 3)
        self.assertEqual(status, NO_HTTP_RESPONSE)
        self.assertEqual(fake.calls, 3)

    def test_timeout_is_retried_not_raised(self):
        status, _, fake = self._fetch([TimeoutError("timed out")] * 3)
        self.assertEqual(status, NO_HTTP_RESPONSE)
        self.assertEqual(fake.calls, 3)


class TestFetchUrlSubprocessFallback(unittest.TestCase):
    """Without curl_cffi, `_fetch_url` degrades to the system-curl path."""

    def test_falls_back_to_system_curl_when_curl_cffi_missing(self):
        with (
            patch(
                "anki_dictionary.integrations.forvo._curl_cffi_requests",
                return_value=None,
            ),
            patch("subprocess.run", return_value=_curl("<html>hi</html>\n200")) as run,
        ):
            with patch("time.sleep"):
                status, html = _fetch_url("https://forvo.com/word/cat")
        self.assertEqual(status, 200)
        self.assertEqual(html, "<html>hi</html>")
        self.assertEqual(run.call_count, 1)

    def test_broken_curl_cffi_extension_returns_none_not_raises(self):
        # A mismatched C-extension surfaces as OSError, not ImportError;
        # the import helper must absorb it so _fetch_url still falls back
        # to system curl rather than raising (which would become a popup).
        original_import = builtins.__import__

        def _blocking_import(name, *args, **kwargs):
            if name == "curl_cffi":
                raise OSError("libcurl.so: cannot open shared object file")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_blocking_import):
            result = _curl_cffi_requests()
        self.assertIsNone(result)

    def test_missing_curl_binary_raises_immediately(self):
        with (
            patch(
                "anki_dictionary.integrations.forvo._curl_cffi_requests",
                return_value=None,
            ),
            patch("subprocess.run", side_effect=FileNotFoundError) as run,
        ):
            with self.assertRaises(FileNotFoundError):
                _fetch_url("https://forvo.com/word/cat")
        self.assertEqual(run.call_count, 1, "retrying cannot conjure a curl binary")


class TestForvoWorkerFailures(unittest.TestCase):
    def test_missing_word_emits_empty_results_not_an_error(self):
        worker = ForvoWorker("zzzznotaword", "en", {})
        worker.signals = MagicMock()
        with patch(
            "anki_dictionary.integrations.forvo._fetch_url", return_value=(404, "")
        ):
            worker.run()
        worker.signals.error_occurred.emit.assert_not_called()
        result = worker.signals.result_ready.emit.call_args[0][0]
        self.assertEqual(result["items"], [])

    def test_each_failure_gets_its_own_message(self):
        cases = {
            NO_HTTP_RESPONSE: "Could not reach forvo.com",
            403: "Cloudflare",
            429: "too many requests",
            503: "unavailable",
        }
        for status, expected in cases.items():
            with self.subTest(status=status):
                worker = ForvoWorker("cat", "en", {})
                worker.signals = MagicMock()
                with patch(
                    "anki_dictionary.integrations.forvo._fetch_url",
                    return_value=(status, ""),
                ):
                    worker.run()
                error = worker.signals.error_occurred.emit.call_args[0][0]["error"]
                self.assertIn(expected, error)
