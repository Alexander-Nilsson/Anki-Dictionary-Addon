"""
Simplified Image Search Module
Uses built-in urllib instead of requests for minimal dependencies
"""

import urllib.request
import urllib.parse
import json
import re
import logging
from typing import List, Dict, Optional
from html import unescape

logger = logging.getLogger(__name__)


class ImageSearchError(Exception):
    """Custom exception for image search operations"""
    pass


class ImageSearcher:
    """Simplified image search using DuckDuckGo"""
    
    def __init__(self, user_agent: str = None):
        """Initialize image searcher
        
        Args:
            user_agent: Custom user agent string
        """
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        self.session_headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    def search_images(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search for images using DuckDuckGo
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of image dictionaries with 'url', 'title', and 'thumbnail' keys
        """
        try:
            # Get search token first
            token = self._get_search_token(query)
            if not token:
                logger.warning("Failed to get search token")
                return []
            
            # Perform image search
            images = self._search_with_token(query, token, max_results)
            return images
            
        except Exception as e:
            logger.error(f"Image search failed: {e}")
            return []
    
    def _get_search_token(self, query: str) -> Optional[str]:
        """Get search token from DuckDuckGo
        
        Args:
            query: Search query
            
        Returns:
            Search token or None if failed
        """
        try:
            # Encode query for URL
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://duckduckgo.com/?q={encoded_query}&t=h_&iax=images&ia=images"
            
            # Create request
            request = urllib.request.Request(url, headers=self.session_headers)
            
            # Get response
            with urllib.request.urlopen(request, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            # Extract token using regex
            token_match = re.search(r'vqd=([\d-]+)', html)
            if token_match:
                return token_match.group(1)
            
            # Alternative token extraction
            token_match = re.search(r'"vqd":"([\d-]+)"', html)
            if token_match:
                return token_match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get search token: {e}")
            return None
    
    def _search_with_token(self, query: str, token: str, max_results: int) -> List[Dict[str, str]]:
        """Search images with token
        
        Args:
            query: Search query
            token: Search token
            max_results: Maximum results
            
        Returns:
            List of image results
        """
        try:
            # Prepare search parameters
            params = {
                'l': 'us-en',
                'o': 'json',
                'q': query,
                'vqd': token,
                'f': ',,,',
                'p': '1',
                's': '0'
            }
            
            # Build URL
            base_url = "https://duckduckgo.com/i.js"
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            
            # Create request
            request = urllib.request.Request(url, headers=self.session_headers)
            
            # Get response
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read().decode('utf-8')
            
            # Parse JSON response
            try:
                json_data = json.loads(data)
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response")
                return []
            
            # Extract image results
            images = []
            results = json_data.get('results', [])
            
            for result in results[:max_results]:
                try:
                    image_info = {
                        'url': result.get('image', ''),
                        'title': unescape(result.get('title', '')),
                        'thumbnail': result.get('thumbnail', ''),
                        'width': result.get('width', 0),
                        'height': result.get('height', 0),
                        'source': result.get('source', '')
                    }
                    
                    # Only add if we have a valid URL
                    if image_info['url']:
                        images.append(image_info)
                        
                except (KeyError, TypeError) as e:
                    logger.warning(f"Skipping malformed result: {e}")
                    continue
            
            logger.info(f"Found {len(images)} images for query: {query}")
            return images
            
        except Exception as e:
            logger.error(f"Failed to search with token: {e}")
            return []
    
    def download_image(self, url: str, output_path: str) -> bool:
        """Download an image from URL
        
        Args:
            url: Image URL
            output_path: Local file path to save image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create request with headers
            request = urllib.request.Request(url, headers=self.session_headers)
            
            # Download image
            with urllib.request.urlopen(request, timeout=30) as response:
                with open(output_path, 'wb') as f:
                    f.write(response.read())
            
            logger.info(f"Downloaded image: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download image {url}: {e}")
            return False
    
    def get_image_info(self, url: str) -> Optional[Dict[str, any]]:
        """Get basic information about an image
        
        Args:
            url: Image URL
            
        Returns:
            Dictionary with image info or None if failed
        """
        try:
            request = urllib.request.Request(url, headers=self.session_headers)
            request.get_method = lambda: 'HEAD'  # Only get headers
            
            with urllib.request.urlopen(request, timeout=10) as response:
                headers = dict(response.headers)
                
                return {
                    'url': url,
                    'content_type': headers.get('Content-Type', ''),
                    'content_length': int(headers.get('Content-Length', 0)),
                    'status_code': response.status
                }
                
        except Exception as e:
            logger.error(f"Failed to get image info for {url}: {e}")
            return None


def search_images_simple(query: str, max_results: int = 5) -> List[str]:
    """Simple function to search for image URLs
    
    Args:
        query: Search term
        max_results: Maximum number of results
        
    Returns:
        List of image URLs
    """
    searcher = ImageSearcher()
    results = searcher.search_images(query, max_results)
    return [result['url'] for result in results if result.get('url')]