"""
Tests for the image search module
"""

import unittest
import tempfile
import os
from unittest.mock import patch, Mock, MagicMock
import json

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.image_search import ImageSearcher, ImageSearchError, search_images_simple


class TestImageSearcher(unittest.TestCase):
    """Test cases for ImageSearcher class"""
    
    def setUp(self):
        """Set up test image searcher"""
        self.searcher = ImageSearcher()
    
    def test_initialization(self):
        """Test ImageSearcher initialization"""
        self.assertIsNotNone(self.searcher.user_agent)
        self.assertIn('Mozilla', self.searcher.user_agent)
        self.assertIsInstance(self.searcher.session_headers, dict)
    
    def test_custom_user_agent(self):
        """Test custom user agent"""
        custom_agent = "Custom Test Agent"
        searcher = ImageSearcher(user_agent=custom_agent)
        self.assertEqual(searcher.user_agent, custom_agent)
        self.assertEqual(searcher.session_headers['User-Agent'], custom_agent)
    
    @patch('urllib.request.urlopen')
    def test_get_search_token_success(self, mock_urlopen):
        """Test successful token extraction"""
        # Mock HTML response with token in the format that the regex expects
        mock_html = '''
        <html>
        <body>
        <script>
        vqd=12345-67890&other=value
        </script>
        </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.read.return_value = mock_html.encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        token = self.searcher._get_search_token("test")
        self.assertEqual(token, "12345-67890")
    
    @patch('urllib.request.urlopen')
    def test_get_search_token_alternative_format(self, mock_urlopen):
        """Test token extraction with alternative format"""
        # Mock HTML response with JSON-style token
        mock_html = '''
        <html>
        <script>
        {"vqd":"98765-43210"}
        </script>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.read.return_value = mock_html.encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        token = self.searcher._get_search_token("test")
        self.assertEqual(token, "98765-43210")
    
    @patch('urllib.request.urlopen')
    def test_get_search_token_failure(self, mock_urlopen):
        """Test token extraction failure"""
        # Mock HTML response without token
        mock_html = '<html><body>No token here</body></html>'
        
        mock_response = Mock()
        mock_response.read.return_value = mock_html.encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        token = self.searcher._get_search_token("test")
        self.assertIsNone(token)
    
    @patch('urllib.request.urlopen')
    def test_search_with_token_success(self, mock_urlopen):
        """Test successful image search with token"""
        # Mock JSON response
        mock_json_data = {
            "results": [
                {
                    "image": "https://example.com/image1.jpg",
                    "title": "Test Image 1",
                    "thumbnail": "https://example.com/thumb1.jpg",
                    "width": 800,
                    "height": 600,
                    "source": "example.com"
                },
                {
                    "image": "https://example.com/image2.jpg",
                    "title": "Test Image 2",
                    "thumbnail": "https://example.com/thumb2.jpg",
                    "width": 1024,
                    "height": 768,
                    "source": "example.com"
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_json_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        results = self.searcher._search_with_token("test", "12345-67890", 5)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['url'], "https://example.com/image1.jpg")
        self.assertEqual(results[0]['title'], "Test Image 1")
        self.assertEqual(results[1]['url'], "https://example.com/image2.jpg")
    
    @patch('urllib.request.urlopen')
    def test_search_with_token_malformed_json(self, mock_urlopen):
        """Test handling of malformed JSON response"""
        mock_response = Mock()
        mock_response.read.return_value = b"Invalid JSON"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        results = self.searcher._search_with_token("test", "12345-67890", 5)
        self.assertEqual(results, [])
    
    @patch('urllib.request.urlopen')
    def test_search_with_token_empty_results(self, mock_urlopen):
        """Test handling of empty results"""
        mock_json_data = {"results": []}
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_json_data).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        results = self.searcher._search_with_token("test", "12345-67890", 5)
        self.assertEqual(results, [])
    
    @patch.object(ImageSearcher, '_search_with_token')
    @patch.object(ImageSearcher, '_get_search_token')
    def test_search_images_success(self, mock_get_token, mock_search_with_token):
        """Test complete image search workflow"""
        # Mock token retrieval
        mock_get_token.return_value = "test-token"
        
        # Mock search results
        mock_results = [
            {"url": "https://example.com/image1.jpg", "title": "Image 1"},
            {"url": "https://example.com/image2.jpg", "title": "Image 2"}
        ]
        mock_search_with_token.return_value = mock_results
        
        results = self.searcher.search_images("test query", 5)
        
        self.assertEqual(len(results), 2)
        mock_get_token.assert_called_once_with("test query")
        mock_search_with_token.assert_called_once_with("test query", "test-token", 5)
    
    @patch.object(ImageSearcher, '_get_search_token')
    def test_search_images_no_token(self, mock_get_token):
        """Test image search when token retrieval fails"""
        mock_get_token.return_value = None
        
        results = self.searcher.search_images("test query", 5)
        self.assertEqual(results, [])
    
    @patch('urllib.request.urlopen')
    def test_download_image_success(self, mock_urlopen):
        """Test successful image download"""
        # Mock image data
        mock_image_data = b"fake image data"
        mock_response = Mock()
        mock_response.read.return_value = mock_image_data
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            success = self.searcher.download_image("https://example.com/image.jpg", temp_path)
            self.assertTrue(success)
            
            # Verify file was written
            with open(temp_path, 'rb') as f:
                self.assertEqual(f.read(), mock_image_data)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    @patch('urllib.request.urlopen')
    def test_download_image_failure(self, mock_urlopen):
        """Test image download failure"""
        mock_urlopen.side_effect = Exception("Network error")
        
        success = self.searcher.download_image("https://example.com/image.jpg", "/tmp/test.jpg")
        self.assertFalse(success)
    
    @patch('urllib.request.urlopen')
    def test_get_image_info_success(self, mock_urlopen):
        """Test getting image information"""
        mock_response = Mock()
        mock_response.headers = {
            'Content-Type': 'image/jpeg',
            'Content-Length': '12345'
        }
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        info = self.searcher.get_image_info("https://example.com/image.jpg")
        
        self.assertIsNotNone(info)
        self.assertEqual(info['content_type'], 'image/jpeg')
        self.assertEqual(info['content_length'], 12345)
        self.assertEqual(info['status_code'], 200)
    
    @patch('urllib.request.urlopen')
    def test_get_image_info_failure(self, mock_urlopen):
        """Test image info retrieval failure"""
        mock_urlopen.side_effect = Exception("Network error")
        
        info = self.searcher.get_image_info("https://example.com/image.jpg")
        self.assertIsNone(info)


class TestImageSearchHelpers(unittest.TestCase):
    """Test helper functions"""
    
    @patch.object(ImageSearcher, 'search_images')
    def test_search_images_simple(self, mock_search_images):
        """Test simple image search function"""
        mock_results = [
            {"url": "https://example.com/image1.jpg", "title": "Image 1"},
            {"url": "https://example.com/image2.jpg", "title": "Image 2"},
            {"url": "", "title": "Invalid Image"}  # Should be filtered out
        ]
        mock_search_images.return_value = mock_results
        
        urls = search_images_simple("test", 5)
        
        self.assertEqual(len(urls), 2)  # Empty URL should be filtered out
        self.assertEqual(urls[0], "https://example.com/image1.jpg")
        self.assertEqual(urls[1], "https://example.com/image2.jpg")


class TestImageSearchIntegration(unittest.TestCase):
    """Integration tests for image search (requires network)"""
    
    def setUp(self):
        """Set up for integration tests"""
        self.searcher = ImageSearcher()
    
    @unittest.skip("Requires network connection - enable for manual testing")
    def test_real_image_search(self):
        """Test real image search (requires network)"""
        results = self.searcher.search_images("cat", 3)
        
        self.assertIsInstance(results, list)
        if results:  # Only test if we got results
            self.assertGreater(len(results), 0)
            self.assertIn('url', results[0])
            self.assertIn('title', results[0])
    
    @unittest.skip("Requires network connection - enable for manual testing")
    def test_real_token_extraction(self):
        """Test real token extraction (requires network)"""
        token = self.searcher._get_search_token("test")
        
        if token:  # Only test if we got a token
            self.assertIsInstance(token, str)
            self.assertGreater(len(token), 0)


if __name__ == '__main__':
    unittest.main()