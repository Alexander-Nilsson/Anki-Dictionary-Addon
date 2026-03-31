# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch
from anki_dictionary.integrations.llm import LLMWorker

class TestLLMWorker(unittest.TestCase):
    def setUp(self):
        self.config = {
            "llm_enabled": True,
            "llm_api_key": "test_key",
            "llm_base_url": "https://api.test.com/v1/chat/completions",
            "llm_model": "test-model",
            "llm_prompt": "Define {term}"
        }
        self.term = "apple"

    @patch('anki_dictionary.integrations.llm.requests.post')
    def test_llm_worker_success(self, mock_post):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "A round red fruit."
                }
            }]
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
        self.assertEqual(results[0]["starCount"], "LLM")
        
        # Verify request details
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], self.config["llm_base_url"])
        self.assertEqual(kwargs["json"]["model"], self.config["llm_model"])
        self.assertEqual(kwargs["json"]["messages"][0]["content"], "Define apple")

if __name__ == '__main__':
    unittest.main()
