# Base Image Provider Interface
# =============================
#
# This module defines the base interface that all image providers must implement.
# This allows for easy addition of new image search providers while maintaining
# a consistent API.

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

try:
    from PyQt5.QtCore import QObject, pyqtSignal
except ImportError:
    # For testing without Qt
    class QObject:
        pass
    def pyqtSignal(*args, **kwargs):
        return None


class ImageProviderSignals(QObject):
    """Signals for image provider operations."""
    searchFinished = pyqtSignal(list)  # List of image results
    imageDownloaded = pyqtSignal(str, str)  # Image path, base64 data
    finished = pyqtSignal()
    error = pyqtSignal(str)
    resultsFound = pyqtSignal(list)  # [html, idName]
    noResults = pyqtSignal(str)  # Error message


class ImageProvider(ABC):
    """
    Abstract base class for image providers.
    
    This class defines the interface that all image providers must implement
    to be compatible with the dictionary addon's image search functionality.
    """
    
    def __init__(self):
        """Initialize the image provider."""
        super().__init__()
        self.signals = ImageProviderSignals()
        self.cancelled = False
    
    @abstractmethod
    def setTermIdName(self, term: str, idName: str) -> None:
        """
        Set the search term and ID name for this search.
        
        Args:
            term: The search term to look for
            idName: Unique identifier for this search
        """
        pass
    
    @abstractmethod
    def setSearchRegion(self, region_or_code: str) -> None:
        """
        Set the search language/region.
        
        Args:
            region_or_code: Country name or ISO code like 'zh-CN'
        """
        pass
    
    @abstractmethod
    def getCleanedUrls(self, urls: List[str]) -> List[str]:
        """
        Clean and filter image URLs.
        
        Args:
            urls: List of image URLs to clean
            
        Returns:
            List of cleaned URLs
        """
        pass
    
    @abstractmethod
    def search(self, term: str, maximum: int = 15, offset: int = 0) -> List[str]:
        """
        Search for images using the provider's API.
        
        Args:
            term: Search term string
            maximum: Maximum number of images to return
            offset: Pagination offset for getting more results
            
        Returns:
            List of image URLs
        """
        pass
    
    @abstractmethod
    def getHtml(self, term: str, is_load_more: bool = False) -> str:
        """
        Generate HTML using the images from the search results.
        
        Args:
            term: Search term
            is_load_more: Whether this is for loading more images
            
        Returns:
            HTML string containing the image gallery
        """
        pass
    
    @abstractmethod
    def getMoreImages(self, term: str) -> str:
        """
        Get more images for the load more functionality.
        
        Args:
            term: Search term
            
        Returns:
            HTML for additional images without container wrapper
        """
        pass
    
    def getPreparedResults(self, term: str, idName: str) -> List[str]:
        """
        Get prepared results for initial search.
        
        Args:
            term: Search term
            idName: Unique identifier
            
        Returns:
            List containing [html, idName]
        """
        html = self.getHtml(term)
        return [html, idName]
    
    def run(self) -> None:
        """
        Main execution method for QRunnable.
        This method is called when the provider is started in a thread.
        """
        try:
            if self.term:
                is_load_more = self.idName == "load_more"
                if is_load_more:
                    # For load more, just get more images
                    html = self.getMoreImages(self.term)
                    resultList = [html, self.idName]
                else:
                    # For initial search, get normal results
                    resultList = self.getPreparedResults(self.term, self.idName)
                self.signals.resultsFound.emit(resultList)
        except Exception as e:
            print(f"{self.__class__.__name__} run error: {e}")
            self.signals.noResults.emit(
                "No Images Found. This is likely due to a connectivity error."
            )
        finally:
            self.signals.finished.emit()


class ImageProviderConfig:
    """Configuration class for image providers"""
    
    def __init__(self, provider_name: str = 'duckduckgo', region: str = 'United States'):
        self.provider_name = provider_name
        self.region = region
        self.max_images_per_search = 15
        self.timeout = 30
