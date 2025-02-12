import unittest
from duckduckgoimages import DuckDuckGo

class TestDuckDuckGoImages(unittest.TestCase):
    def setUp(self):
        self.ddg = DuckDuckGo()

    def test_image_search_returns_results(self):
        test_term = "cat"
        results = self.ddg.search(test_term)

        print(results)
        
        # Basic validation
        self.assertIsNotNone(results, "Search results should not be None")
        self.assertIsInstance(results, list, "Results should be a list")
        self.assertTrue(len(results) > 0, "Should return at least one image")

        # Verify first result is a URL string
        first_result = results[0]
        self.assertIsInstance(first_result, str, "Result should be a URL string")
        self.assertTrue(first_result.startswith('http'), "URL should start with http")

if __name__ == '__main__':
    unittest.main()