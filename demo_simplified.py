#!/usr/bin/env python3
"""
Demo script for the simplified Anki Dictionary
Shows how to use the refactored codebase with minimal dependencies
"""

import os
import sys
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

from core.dictionary import Dictionary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def setup_demo_data(dictionary):
    """Set up some demo dictionary data"""
    print("Setting up demo data...")
    
    # English definitions
    english_definitions = [
        ("hello", "a greeting used when meeting someone", "heh-loh", 100),
        ("world", "the earth and all its inhabitants", "wurld", 95),
        ("dictionary", "a book or electronic resource that lists words", "dik-shuh-ner-ee", 80),
        ("computer", "an electronic device for processing data", "kuhm-pyoo-ter", 90),
        ("language", "a system of communication used by people", "lang-gwij", 85),
    ]
    
    for term, definition, reading, frequency in english_definitions:
        dictionary.add_definition("English Dictionary", term, definition, reading, frequency)
    
    # Japanese definitions
    japanese_definitions = [
        ("こんにちは", "hello in Japanese", "konnichiwa", 100),
        ("世界", "world in Japanese", "sekai", 95),
        ("辞書", "dictionary in Japanese", "jisho", 80),
        ("コンピューター", "computer in Japanese", "konpyuutaa", 90),
        ("言語", "language in Japanese", "gengo", 85),
    ]
    
    for term, definition, reading, frequency in japanese_definitions:
        dictionary.add_definition("Japanese Dictionary", term, definition, reading, frequency)
    
    print("Demo data setup complete!")

def demo_search(dictionary, term):
    """Demonstrate search functionality"""
    print(f"\n--- Searching for: '{term}' ---")
    
    results = dictionary.search(term)
    
    if results:
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.term}")
            if result.reading:
                print(f"   Reading: {result.reading}")
            print(f"   Definition: {result.definition}")
            print(f"   Dictionary: {result.dictionary}")
            print(f"   Language: {result.language}")
            print(f"   Frequency: {result.frequency}")
            
            if result.images:
                print(f"   Images: {len(result.images)} found")
                for img_url in result.images[:2]:  # Show first 2 images
                    print(f"     - {img_url}")
    else:
        print("No results found.")

def demo_export(dictionary, term, format_type):
    """Demonstrate export functionality"""
    print(f"\n--- Exporting results for '{term}' as {format_type.upper()} ---")
    
    results = dictionary.search(term)
    if results:
        exported = dictionary.export_results(results, format_type)
        
        # Save to file
        filename = f"export_{term}_{format_type}.{format_type}"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(exported)
        
        print(f"Exported to: {filename}")
        
        # Show preview
        if format_type == 'txt':
            print("\nPreview:")
            print(exported[:300] + "..." if len(exported) > 300 else exported)
    else:
        print("No results to export.")

def demo_history(dictionary):
    """Demonstrate search history"""
    print("\n--- Search History ---")
    
    history = dictionary.get_search_history(5)
    if history:
        print("Recent searches:")
        for entry in history:
            print(f"  - '{entry['term']}' ({entry['results_count']} results) at {entry['timestamp']}")
    else:
        print("No search history found.")

def demo_dictionaries(dictionary):
    """Demonstrate dictionary information"""
    print("\n--- Available Dictionaries ---")
    
    dictionaries = dictionary.get_dictionaries()
    if dictionaries:
        for dict_info in dictionaries:
            print(f"  - {dict_info['name']} ({dict_info['language']})")
            print(f"    Definitions: {dict_info['definition_count']}")
            print(f"    Created: {dict_info['created_at']}")
            print(f"    Enabled: {'Yes' if dict_info['enabled'] else 'No'}")
            print()
    else:
        print("No dictionaries found.")

def demo_image_search(dictionary, term):
    """Demonstrate image search functionality"""
    print(f"\n--- Image Search for: '{term}' ---")
    
    try:
        images = dictionary.search_images(term, max_results=3)
        if images:
            print(f"Found {len(images)} images:")
            for i, img in enumerate(images, 1):
                print(f"  {i}. {img.get('title', 'No title')}")
                print(f"     URL: {img['url']}")
                if img.get('thumbnail'):
                    print(f"     Thumbnail: {img['thumbnail']}")
                print()
        else:
            print("No images found.")
    except Exception as e:
        print(f"Image search failed: {e}")

def main():
    """Main demo function"""
    print("=== Simplified Anki Dictionary Demo ===")
    print("This demo shows the refactored codebase with minimal dependencies.\n")
    
    # Initialize dictionary
    print("Initializing dictionary...")
    with Dictionary() as dictionary:
        
        # Set up demo data
        setup_demo_data(dictionary)
        
        # Demo searches
        demo_search(dictionary, "hello")
        demo_search(dictionary, "computer")
        demo_search(dictionary, "こんにちは")  # Japanese
        demo_search(dictionary, "dict")  # Partial match
        
        # Demo export
        demo_export(dictionary, "hello", "json")
        demo_export(dictionary, "computer", "html")
        demo_export(dictionary, "language", "txt")
        
        # Demo history
        demo_history(dictionary)
        
        # Demo dictionaries
        demo_dictionaries(dictionary)
        
        # Demo image search (requires network)
        if len(sys.argv) > 1 and sys.argv[1] == "--with-images":
            demo_image_search(dictionary, "cat")
        else:
            print("\n--- Image Search ---")
            print("Image search skipped. Use --with-images flag to enable.")
            print("(Requires network connection)")
    
    print("\n=== Demo Complete ===")
    print("\nFiles created:")
    for filename in os.listdir('.'):
        if filename.startswith('export_'):
            print(f"  - {filename}")
    
    print("\nThe simplified codebase features:")
    print("  ✓ No external dependencies (uses Python standard library)")
    print("  ✓ Clean, modular architecture")
    print("  ✓ Comprehensive test coverage")
    print("  ✓ Simple configuration management")
    print("  ✓ Built-in export functionality")
    print("  ✓ Search history tracking")
    print("  ✓ Image search with DuckDuckGo")
    print("  ✓ Context manager support")
    print("  ✓ Proper error handling and logging")

if __name__ == '__main__':
    main()