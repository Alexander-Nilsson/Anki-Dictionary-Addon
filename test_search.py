import unittest
from duckduckgoimages import DuckDuckGo, Google    

########################################
# Test Code to Validate Different Parts
########################################

if __name__ == '__main__':
    # Test Google Search Engine
    print("=== Testing Google Search Engine ===")
    google_engine = Google()
    google_engine.setTermIdName("dogs", "google_test")
    google_engine.setSearchRegion("US")
    google_engine.setSafeSearch(True)
    google_results = google_engine.search("dogs", maximum=10)
    print("\nGoogle image URLs for 'dogs':")
    for url in google_results:
        print(url)
    google_html = google_engine.getHtml("dogs")
    print("\nGenerated Google HTML:")
    print(google_html)
    
    # Test DuckDuckGo Search Engine
    print("\n=== Testing DuckDuckGo Search Engine ===")
    duck_engine = DuckDuckGo()
    duck_engine.setTermIdName("cats", "duckduckgo_test")
    duck_engine.setSearchRegion("US")  # Even though not used, for compatibility
    duck_engine.setSafeSearch(True)
    duck_results = duck_engine.search("cats")
    print("\nDuckDuckGo image URLs for 'cats':")
    for url in duck_results:
        print(url)
    duck_html = duck_engine.getHtml("cats")
    print("\nGenerated DuckDuckGo HTML:")
    print(duck_html)
    
    # Test prepared results (HTML + idName) for DuckDuckGo
    duck_prepared = duck_engine.getPreparedResults("cats", "duckduckgo_test")
    print("\nDuckDuckGo Prepared Results:")
    print(duck_prepared)