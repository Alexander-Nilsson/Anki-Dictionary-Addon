# Image Providers Package
# =======================
# 
# This package contains different image search providers that can be used
# by the dictionary addon. Each provider implements the ImageProvider interface
# and can be easily swapped or extended.

from typing import List
from .base import ImageProvider
from .duckduckgo import DuckDuckGoProvider

# Registry of available image providers
AVAILABLE_PROVIDERS = {
    'duckduckgo': DuckDuckGoProvider,
    # Future providers can be added here:
    # 'google': GoogleImagesProvider,
    # 'baidu': BaiduImagesProvider,
    # 'bing': BingImagesProvider,
}

def get_provider(provider_name: str = 'duckduckgo') -> ImageProvider:
    """
    Get an image provider by name.
    
    Args:
        provider_name: Name of the provider to get (default: 'duckduckgo')
        
    Returns:
        ImageProvider instance
        
    Raises:
        ValueError: If the provider is not available
    """
    if provider_name not in AVAILABLE_PROVIDERS:
        raise ValueError(f"Provider '{provider_name}' not available. Available providers: {list(AVAILABLE_PROVIDERS.keys())}")
    
    return AVAILABLE_PROVIDERS[provider_name]()

def list_providers() -> List[str]:
    """
    Get a list of available provider names.
    
    Returns:
        List of provider names
    """
    return list(AVAILABLE_PROVIDERS.keys())
