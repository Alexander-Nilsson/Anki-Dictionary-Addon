# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch
from anki_dictionary.integrations.llm import (
    LLMWorker,
    split_llm_definitions,
    LLM_DELIMITER,
    test_llm_config as _llm_config_check,
)


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
    def test_llm_worker_single_prompt(self, mock_post):
        """Single prompt via legacy llm_prompt key still works."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "A round red fruit."}}]
        }
        mock_post.return_value = mock_response

        worker = LLMWorker(self.term, self.config)

        results = []
        worker.signals.result_ready.connect(lambda x: results.append(x))

        worker.run()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["term"], "apple")
        self.assertEqual(results[0]["definition"], "A round red fruit.")

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["messages"][0]["content"], "Define apple")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["temperature"], 0.3)
        self.assertNotIn("think", payload)

    @patch("anki_dictionary.integrations.llm.requests.post")
    def test_llm_worker_single_prompt_in_array(self, mock_post):
        """Single prompt in llm_prompts array: no delimiter injection."""
        config = self.config.copy()
        config["llm_prompts"] = ["Define {term} in French"]
        del config["llm_prompt"]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Pomme"}}]
        }
        mock_post.return_value = mock_response

        worker = LLMWorker(self.term, config)
        results = []
        worker.signals.result_ready.connect(lambda x: results.append(x))
        worker.run()

        self.assertEqual(len(results), 1)
        # Single prompt → raw response, no instruction wrapper
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["messages"][0]["content"], "Define apple in French")

    @patch("anki_dictionary.integrations.llm.requests.post")
    def test_llm_worker_multiple_prompts(self, mock_post):
        """Multiple prompts: instruction is injected, prompts are joined."""
        config = self.config.copy()
        config["llm_prompts"] = [
            "Define {term} in simple terms",
            "Define {term} for advanced learners",
        ]
        del config["llm_prompt"]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "A fruit.\n---\nMalus domestica."}}]
        }
        mock_post.return_value = mock_response

        worker = LLMWorker(self.term, config)
        results = []
        worker.signals.result_ready.connect(lambda x: results.append(x))
        worker.run()

        self.assertEqual(len(results), 1)

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        content = payload["messages"][0]["content"]

        # Should contain the delimiter instruction
        self.assertIn("Respond to each request below", content)
        # Should contain the two prompts with {term} replaced
        self.assertIn("Request 1: Define apple in simple terms", content)
        self.assertIn("Request 2: Define apple for advanced learners", content)
        # Should be joined with delimiter
        self.assertIn(LLM_DELIMITER, content)

    @patch("anki_dictionary.integrations.llm.requests.post")
    def test_llm_config_check(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
        mock_post.return_value = mock_response

        callback_results = []

        def test_callback(success, message):
            callback_results.append((success, message))

        _llm_config_check(self.config, test_callback)

        self.assertEqual(len(callback_results), 1)
        self.assertTrue(callback_results[0][0])
        self.assertIn("Successfully connected", callback_results[0][1])

        args, kwargs = mock_post.call_args
        self.assertNotIn("think", kwargs["json"])

    @patch("anki_dictionary.integrations.llm.requests.post")
    def test_ollama_chat_payload(self, mock_post):
        config = self.config.copy()
        config["llm_base_url"] = "http://localhost:11434/api/chat"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "A fruit."}}
        mock_post.return_value = mock_response

        worker = LLMWorker(self.term, config)
        worker.run()

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["think"], False)
        self.assertEqual(payload["keep_alive"], "30m")
        self.assertEqual(payload["temperature"], 0.3)

    def test_split_llm_definitions_single(self):
        """Single definition with no delimiter returns one chunk."""
        text = "A round fruit."
        self.assertEqual(split_llm_definitions(text), ["A round fruit."])

    def test_split_llm_definitions_multiple(self):
        """Multiple definitions separated by delimiter are split."""
        text = "A round fruit.\n---\nMalus domestica is a deciduous tree."
        result = split_llm_definitions(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "A round fruit.")
        self.assertEqual(result[1], "Malus domestica is a deciduous tree.")

    def test_split_llm_definitions_empty_chunks_skipped(self):
        """Empty chunks from extra delimiters are discarded."""
        text = "First def.\n---\n\n---\nThird def."
        result = split_llm_definitions(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "First def.")
        self.assertEqual(result[1], "Third def.")

    def test_split_llm_definitions_no_delimiter(self):
        """No delimiter at all returns the whole text as one chunk."""
        text = "Just a single block of text."
        self.assertEqual(split_llm_definitions(text), [text])


if __name__ == "__main__":
    unittest.main()
