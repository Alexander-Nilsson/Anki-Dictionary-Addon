# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch
from anki_dictionary.integrations.llm import LLMWorker, test_llm_config


class TestLLMWorker(unittest.TestCase):
    def setUp(self):
        self.config = {
            "llm_enabled": True,
            "llm_api_key": "test_key",
            "llm_base_url": "https://api.test.com/v1/chat/completions",
            "llm_model": "test-model",
            "llm_prompt": "Define {term}",
        }
        self.term = "apple"

    @patch("anki_dictionary.integrations.llm.requests.post")
    def test_llm_worker_success(self, mock_post):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "A round red fruit."}}]
        }
        mock_post.return_value = mock_response

        worker = LLMWorker(self.term, self.config)

        # Connect signal to a collector
        results = []
        worker.signals.result_ready.connect(lambda x: results.append(x))

        # Run worker logic
        worker.run()

        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["term"], "apple")
        self.assertEqual(results[0]["definition"], "A round red fruit.")
        self.assertEqual(results[0]["starCount"], "")

        # Verify request details
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], self.config["llm_base_url"])

        # Verify payload contains standard fields and NO non-standard fields like 'think'
        payload = kwargs["json"]
        self.assertEqual(payload["model"], self.config["llm_model"])
        self.assertEqual(payload["messages"][0]["content"], "Define apple")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["temperature"], 0.3)
        self.assertNotIn("think", payload)

    @patch("anki_dictionary.integrations.llm.requests.post")
    def test_llm_config_check(self, mock_post):
        # Mock API response for connection test
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "OK"}}]
        }
        mock_post.return_value = mock_response

        callback_results = []

        def test_callback(success, message):
            callback_results.append((success, message))

        test_llm_config(self.config, test_callback)

        self.assertEqual(len(callback_results), 1)
        self.assertTrue(callback_results[0][0])
        self.assertIn("Successfully connected", callback_results[0][1])

        # Verify payload doesn't have 'think' for OpenAI endpoint
        args, kwargs = mock_post.call_args
        self.assertNotIn("think", kwargs["json"])

    @patch("anki_dictionary.integrations.llm.requests.post")
    def test_ollama_chat_payload(self, mock_post):
        # Setup Ollama chat config
        config = self.config.copy()
        config["llm_base_url"] = "http://localhost:11434/api/chat"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "A fruit."}
        }
        mock_post.return_value = mock_response

        worker = LLMWorker(self.term, config)
        worker.run()

        # Verify Ollama-specific root fields
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["think"], False)
        self.assertEqual(payload["keep_alive"], "30m")
        self.assertEqual(payload["temperature"], 0.3)


if __name__ == "__main__":
    unittest.main()
