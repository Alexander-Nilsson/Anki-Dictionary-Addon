import base64
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from anki_dictionary.integrations.forvo import (
    NO_HTTP_RESPONSE,
    ForvoWorker,
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


class TestFetchUrl(unittest.TestCase):
    """`_fetch_url` must report Forvo's real HTTP status.

    It used to return curl's *exit code* as the status, so every distinct
    failure — a missing word, a Cloudflare challenge, a dead network — was
    reported as "HTTP 403", and the 404 branch in `ForvoWorker.run` could never
    fire.
    """

    def test_returns_the_real_http_status_and_body(self):
        with patch("subprocess.run", return_value=_curl("<html>hi</html>\n200")):
            status, html = _fetch_url("https://forvo.com/word/cat")
        self.assertEqual(status, 200)
        self.assertEqual(html, "<html>hi</html>")

    def test_404_is_final_and_not_retried(self):
        with patch(
            "subprocess.run", return_value=_curl("<html>not found</html>\n404")
        ) as run:
            with patch("time.sleep") as sleep:
                status, _ = _fetch_url("https://forvo.com/word/nope")
        self.assertEqual(status, 404)
        self.assertEqual(run.call_count, 1, "a 404 is a final answer")
        sleep.assert_not_called()

    def test_cloudflare_challenge_becomes_403_after_retries(self):
        challenge = _curl("<html>Just a moment...</html>\n200")
        with patch("subprocess.run", return_value=challenge) as run:
            with patch("time.sleep"):
                status, html = _fetch_url("https://forvo.com/word/cat")
        self.assertEqual(status, 403)
        self.assertEqual(html, "")
        self.assertEqual(run.call_count, 3)

    def test_retries_then_succeeds(self):
        responses = [
            _curl("", 6),  # curl: could not resolve host
            _curl("<html>ok</html>\n200"),
        ]
        with patch("subprocess.run", side_effect=responses) as run:
            with patch("time.sleep"):
                status, html = _fetch_url("https://forvo.com/word/cat")
        self.assertEqual(status, 200)
        self.assertEqual(html, "<html>ok</html>")
        self.assertEqual(run.call_count, 2)

    def test_curl_failure_reports_no_http_response(self):
        with patch("subprocess.run", return_value=_curl("", 7)):
            with patch("time.sleep"):
                status, _ = _fetch_url("https://forvo.com/word/cat")
        self.assertEqual(status, NO_HTTP_RESPONSE)

    def test_timeout_is_retried_not_raised(self):
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("curl", 20)
        ) as run:
            with patch("time.sleep"):
                status, _ = _fetch_url("https://forvo.com/word/cat")
        self.assertEqual(status, NO_HTTP_RESPONSE)
        self.assertEqual(run.call_count, 3)

    def test_missing_curl_binary_raises_immediately(self):
        with patch("subprocess.run", side_effect=FileNotFoundError) as run:
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
