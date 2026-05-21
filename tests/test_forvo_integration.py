import unittest
import os
import time

import pytest

from anki_dictionary.integrations.forvo import ForvoWorker

pytestmark = pytest.mark.network


class TestForvoIntegration(unittest.TestCase):
    @unittest.skipIf(
        os.environ.get("GITHUB_ACTIONS") == "true",
        "Skipping real Forvo search in GitHub Actions due to 403 Forbidden errors.",
    )
    def test_real_forvo_search(self):
        """Perform a real search on Forvo to verify functionality without mocks."""
        # We'll search for a very common word to ensure results exist
        term = "house"
        language = "en"

        # We need to mock QRunnable/QObject dependencies if they aren't available,
        # but here we are in a dev environment where they should be or mocked by the import.
        # The ForvoWorker itself uses requests, which we want to test for real.

        worker = ForvoWorker(term, language, {})

        # Container for results from the signal
        self.received_result = None
        self.error_received = None

        # Connect signals to local handlers
        worker.signals.result_ready.connect(
            lambda res: setattr(self, "received_result", res)
        )
        worker.signals.error_occurred.connect(
            lambda err: setattr(self, "error_received", err)
        )

        # Run the worker directly in this thread for testing
        worker.run()

        # Check if we got an error
        if self.error_received:
            self.fail(f"Forvo search failed with error: {self.error_received}")

        # Verify results
        self.assertIsNotNone(
            self.received_result, "No result received from ForvoWorker"
        )
        self.assertEqual(self.received_result["term"], term)
        self.assertIn("items", self.received_result)

        # We expect at least one pronunciation for "house"
        items = self.received_result["items"]
        self.assertGreater(
            len(items), 0, f"No pronunciations found for common word '{term}'"
        )

        # Verify structure of the first result
        first_item = items[0]
        self.assertTrue(first_item["user"], "User should not be empty")
        self.assertTrue(
            first_item["audio_url"].startswith("https://"),
            f"Invalid audio URL: {first_item['audio_url']}",
        )
        self.assertEqual(first_item["word"], term)
        self.assertIn("origin", first_item)

        print(
            f"\n✅ Successfully fetched {len(items)} pronunciations for '{term}' from Forvo."
        )


if __name__ == "__main__":
    unittest.main()
