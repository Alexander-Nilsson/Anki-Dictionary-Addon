import unittest
from unittest.mock import MagicMock, patch
import base64
from anki_dictionary.integrations.forvo import ForvoWorker


class TestForvo(unittest.TestCase):
    def test_forvo_worker_parsing(self):
        """Test that ForvoWorker correctly parses Forvo HTML."""
        # Mock HTML response from Forvo
        # base64.b64encode(b"test.mp3") is b'dGVzdC5tcDM='
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

        # In actual Forvo, the structure might be slightly different but let's match our code.
        # Our code uses item.find(class_="info") and user_info.find("a", class_="user")

        worker = ForvoWorker("test", "ja", {})
        worker.signals = MagicMock()

        with patch.object(worker.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Mock prefer_ipv4
            with patch("anki_dictionary.utils.common.prefer_ipv4"):
                worker.run()

            # Check if result_ready was emitted
            worker.signals.result_ready.emit.assert_called_once()
            result = worker.signals.result_ready.emit.call_args[0][0]

            self.assertEqual(result["term"], "test")
            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(result["items"][0]["user"], "user1")
            self.assertEqual(result["items"][0]["votes"], 5)
            self.assertIn("test.mp3", result["items"][0]["audio_url"])


if __name__ == "__main__":
    unittest.main()
