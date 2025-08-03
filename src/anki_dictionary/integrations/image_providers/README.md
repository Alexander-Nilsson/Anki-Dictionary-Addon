# Image Providers

This directory contains the extensible image provider system for the Anki Dictionary Addon. The system is designed to make it easy to add new image search providers without modifying the core dictionary functionality.

## Current Providers

### DuckDuckGo (Default)
- **File**: `duckduckgo.py`
- **Status**: Active
- **Features**: Full implementation with async image downloading, pagination, and regional search support

### Google Images (Example)
- **File**: `google.py`
- **Status**: Placeholder/Example
- **Purpose**: Demonstrates how to implement a new provider

## Adding a New Provider

To add a new image provider (e.g., Baidu, Bing, etc.), follow these steps:

### 1. Create Provider File

Create a new file in this directory (e.g., `baidu.py`) that implements the `ImageProvider` interface:

```python
from typing import List
from .base import ImageProvider

class BaiduImagesProvider(ImageProvider):
    def __init__(self):
        super().__init__()
        # Initialize your provider
        
    def setTermIdName(self, term: str, idName: str) -> None:
        # Set search term and ID
        pass
        
    def setSearchRegion(self, region_or_code: str) -> None:
        # Set search region/language
        pass
        
    def getCleanedUrls(self, urls: List[str]) -> List[str]:
        # Clean and filter URLs
        pass
        
    def search(self, term: str, maximum: int = 15, offset: int = 0) -> List[str]:
        # Implement the actual search API calls
        pass
        
    def getHtml(self, term: str, is_load_more: bool = False) -> str:
        # Generate HTML for initial search
        pass
        
    def getMoreImages(self, term: str) -> str:
        # Generate HTML for load more functionality
        pass
```

### 2. Register Provider

Add your provider to the `__init__.py` file:

```python
from .baidu import BaiduImagesProvider

AVAILABLE_PROVIDERS = {
    'duckduckgo': DuckDuckGoProvider,
    'baidu': BaiduImagesProvider,  # Add your provider here
    # ... other providers
}
```

### 3. Update Configuration

Users can then select your provider by setting the `imageProvider` configuration:

```json
{
    "imageProvider": "baidu"
}
```

## Provider Interface

All providers must implement the `ImageProvider` abstract base class defined in `base.py`. This ensures a consistent API and makes providers interchangeable.

### Required Methods

- `setTermIdName()`: Set the search term and unique identifier
- `setSearchRegion()`: Set the search language/region
- `getCleanedUrls()`: Clean and filter image URLs
- `search()`: Perform the actual image search
- `getHtml()`: Generate HTML for the initial search results
- `getMoreImages()`: Generate HTML for additional images (load more)

### Inherited Properties

- `signals`: Qt signals for communication (resultsFound, noResults, finished)
- `term`: Current search term
- `idName`: Unique identifier for the search
- `language`: Current language/region setting
- `search_offset`: Pagination offset for load more functionality

## HTML Structure

Providers should generate HTML that follows this structure:

```html
<div class="imageCont horizontal-layout">
    <div class="imgBox">
        <div onclick="toggleImageSelect(this)" data-url="..." class="imageHighlight"></div>
        <img class="imageImg" src="..." ankiDict="...">
    </div>
    <!-- More image boxes -->
</div>
<button class="imageLoader" onclick="loadMoreImages(this, 'search-term')">Load More</button>
```

## CSS Classes

The following CSS classes should be used:

- `.imageCont.horizontal-layout`: Main container for images
- `.imgBox`: Individual image container
- `.imageImg`: The actual image element
- `.imageHighlight`: Overlay for selection highlighting
- `.imageLoader`: Load more button

## Best Practices

1. **Async Operations**: Use async/await for image downloading to avoid blocking the UI
2. **Error Handling**: Gracefully handle network errors and API failures
3. **Rate Limiting**: Respect the search provider's rate limits
4. **Image Processing**: Resize images to reasonable dimensions to save space
5. **Clean URLs**: Remove unnecessary parameters from image URLs
6. **Base64 Embedding**: Consider embedding small images as base64 data URLs
7. **Pagination**: Support load more functionality for better user experience

## Testing Your Provider

1. Set your provider in the configuration
2. Test basic search functionality
3. Test load more functionality
4. Test with different languages/regions if supported
5. Test error conditions (no internet, API errors, etc.)

## Future Extensions

The provider system could be extended to support:

- Video search providers
- Audio/sound effect providers
- Document/PDF search providers
- Custom search engines
