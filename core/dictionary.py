"""
Simplified Dictionary Core Module
Main dictionary functionality with clean interface
"""

import logging
from typing import List, Dict, Optional, Callable
from pathlib import Path
import json
import os

from .database import DictionaryDatabase
from .image_search import ImageSearcher

logger = logging.getLogger(__name__)


class DictionaryConfig:
    """Configuration management for dictionary"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration
        
        Args:
            config_path: Path to config file. If None, uses default.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default config file path"""
        return os.path.join(os.getcwd(), "config.json")
    
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        default_config = {
            "max_results": 50,
            "enable_images": True,
            "enable_audio": False,
            "image_max_results": 5,
            "auto_search_images": True,
            "cache_images": True,
            "search_timeout": 10,
            "ui_theme": "default",
            "languages": ["English", "Japanese"],
            "default_language": "English"
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"Loaded config from {self.config_path}")
            else:
                # Save default config
                self.save_config(default_config)
                logger.info(f"Created default config at {self.config_path}")
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def save_config(self, config: Dict = None):
        """Save configuration to file
        
        Args:
            config: Configuration dictionary. If None, saves current config.
        """
        try:
            config_to_save = config or self.config
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved config to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value"""
        self.config[key] = value
    
    def update(self, updates: Dict):
        """Update multiple configuration values"""
        self.config.update(updates)


class DictionaryResult:
    """Represents a dictionary lookup result"""
    
    def __init__(self, term: str, definition: str, **kwargs):
        """Initialize result
        
        Args:
            term: The searched term
            definition: Definition text
            **kwargs: Additional fields (reading, frequency, etc.)
        """
        self.term = term
        self.definition = definition
        self.reading = kwargs.get('reading', '')
        self.frequency = kwargs.get('frequency', 0)
        self.dictionary = kwargs.get('dictionary', '')
        self.language = kwargs.get('language', '')
        self.images = kwargs.get('images', [])
        self.audio_url = kwargs.get('audio_url', '')
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'term': self.term,
            'definition': self.definition,
            'reading': self.reading,
            'frequency': self.frequency,
            'dictionary': self.dictionary,
            'language': self.language,
            'images': self.images,
            'audio_url': self.audio_url
        }
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.term}: {self.definition[:100]}..."


class Dictionary:
    """Main dictionary class with simplified interface"""
    
    def __init__(self, db_path: Optional[str] = None, config_path: Optional[str] = None):
        """Initialize dictionary
        
        Args:
            db_path: Database file path
            config_path: Configuration file path
        """
        self.config = DictionaryConfig(config_path)
        self.database = DictionaryDatabase(db_path)
        self.image_searcher = ImageSearcher() if self.config.get('enable_images') else None
        
        # Callbacks for events
        self.on_search_start: Optional[Callable] = None
        self.on_search_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        logger.info("Dictionary initialized")
    
    def search(self, term: str, include_images: bool = None) -> List[DictionaryResult]:
        """Search for a term in the dictionary
        
        Args:
            term: Search term
            include_images: Whether to include image search. If None, uses config.
            
        Returns:
            List of DictionaryResult objects
        """
        if not term or not term.strip():
            return []
        
        term = term.strip()
        
        try:
            # Trigger search start callback
            if self.on_search_start:
                self.on_search_start(term)
            
            logger.info(f"Searching for: {term}")
            
            # Search database
            db_results = self.database.search_definitions(
                term, 
                limit=self.config.get('max_results', 50)
            )
            
            # Convert to DictionaryResult objects
            results = []
            for db_result in db_results:
                result = DictionaryResult(**db_result)
                results.append(result)
            
            # Add images if enabled
            if include_images is None:
                include_images = self.config.get('auto_search_images', True)
            
            if include_images and self.image_searcher and results:
                self._add_images_to_results(results, term)
            
            logger.info(f"Found {len(results)} results for: {term}")
            
            # Trigger search complete callback
            if self.on_search_complete:
                self.on_search_complete(term, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            if self.on_error:
                self.on_error(f"Search failed: {e}")
            return []
    
    def _add_images_to_results(self, results: List[DictionaryResult], term: str):
        """Add images to search results
        
        Args:
            results: List of results to enhance with images
            term: Original search term
        """
        try:
            max_images = self.config.get('image_max_results', 5)
            images = self.image_searcher.search_images(term, max_images)
            
            # Add images to first result (most relevant)
            if results and images:
                results[0].images = [img['url'] for img in images]
                logger.info(f"Added {len(images)} images to results")
                
        except Exception as e:
            logger.error(f"Failed to add images: {e}")
    
    def add_definition(self, dictionary_name: str, term: str, definition: str, 
                      reading: str = None, frequency: int = 0) -> bool:
        """Add a new definition to the dictionary
        
        Args:
            dictionary_name: Name of the dictionary
            term: The term/word
            definition: Definition text
            reading: Pronunciation/reading (optional)
            frequency: Frequency score (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.database.add_definition(
                dictionary_name, term, definition, reading, frequency
            )
            
            if success:
                logger.info(f"Added definition for: {term}")
            else:
                logger.error(f"Failed to add definition for: {term}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding definition: {e}")
            if self.on_error:
                self.on_error(f"Failed to add definition: {e}")
            return False
    
    def get_search_history(self, limit: int = 20) -> List[Dict]:
        """Get recent search history
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            List of search history entries
        """
        try:
            return self.database.get_search_history(limit)
        except Exception as e:
            logger.error(f"Error getting search history: {e}")
            return []
    
    def get_dictionaries(self) -> List[Dict]:
        """Get information about available dictionaries
        
        Returns:
            List of dictionary information
        """
        try:
            return self.database.get_dictionaries()
        except Exception as e:
            logger.error(f"Error getting dictionaries: {e}")
            return []
    
    def search_images(self, term: str, max_results: int = None) -> List[Dict]:
        """Search for images related to a term
        
        Args:
            term: Search term
            max_results: Maximum number of results
            
        Returns:
            List of image information dictionaries
        """
        if not self.image_searcher:
            logger.warning("Image search is disabled")
            return []
        
        try:
            max_results = max_results or self.config.get('image_max_results', 5)
            return self.image_searcher.search_images(term, max_results)
            
        except Exception as e:
            logger.error(f"Image search error: {e}")
            if self.on_error:
                self.on_error(f"Image search failed: {e}")
            return []
    
    def export_results(self, results: List[DictionaryResult], format: str = 'json') -> str:
        """Export search results to various formats
        
        Args:
            results: List of results to export
            format: Export format ('json', 'html', 'txt')
            
        Returns:
            Exported data as string
        """
        try:
            if format.lower() == 'json':
                return self._export_json(results)
            elif format.lower() == 'html':
                return self._export_html(results)
            elif format.lower() == 'txt':
                return self._export_txt(results)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Export error: {e}")
            return ""
    
    def _export_json(self, results: List[DictionaryResult]) -> str:
        """Export results as JSON"""
        data = [result.to_dict() for result in results]
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _export_html(self, results: List[DictionaryResult]) -> str:
        """Export results as HTML"""
        html = ["<html><head><title>Dictionary Results</title></head><body>"]
        html.append("<h1>Dictionary Search Results</h1>")
        
        for result in results:
            html.append(f"<div class='result'>")
            html.append(f"<h2>{result.term}</h2>")
            if result.reading:
                html.append(f"<p><strong>Reading:</strong> {result.reading}</p>")
            html.append(f"<p><strong>Definition:</strong> {result.definition}</p>")
            if result.dictionary:
                html.append(f"<p><strong>Dictionary:</strong> {result.dictionary}</p>")
            if result.images:
                html.append("<div class='images'>")
                for img_url in result.images[:3]:  # Show first 3 images
                    html.append(f"<img src='{img_url}' style='max-width:200px;margin:5px;'>")
                html.append("</div>")
            html.append("</div><hr>")
        
        html.append("</body></html>")
        return "\n".join(html)
    
    def _export_txt(self, results: List[DictionaryResult]) -> str:
        """Export results as plain text"""
        lines = ["Dictionary Search Results", "=" * 30, ""]
        
        for i, result in enumerate(results, 1):
            lines.append(f"{i}. {result.term}")
            if result.reading:
                lines.append(f"   Reading: {result.reading}")
            lines.append(f"   Definition: {result.definition}")
            if result.dictionary:
                lines.append(f"   Dictionary: {result.dictionary}")
            lines.append("")
        
        return "\n".join(lines)
    
    def close(self):
        """Close dictionary and cleanup resources"""
        if self.database:
            self.database.close()
        logger.info("Dictionary closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()