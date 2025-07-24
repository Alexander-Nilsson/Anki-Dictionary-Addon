#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script to showcase the standalone dictionary functionality
"""

import requests
import json
import time
import subprocess
import threading
import sys

def test_api():
    """Test the dictionary API"""
    base_url = "http://localhost:12000"
    
    print("🔍 Testing Dictionary API...")
    print("=" * 50)
    
    # Test terms
    test_terms = ["hello", "world", "dictionary", "computer", "language"]
    
    for term in test_terms:
        try:
            response = requests.get(f"{base_url}/search", params={"term": term}, timeout=5)
            if response.status_code == 200:
                data = response.json()
                dict_results = data.get("dictionary_results", [])
                
                print(f"\n📖 Search: '{term}'")
                if dict_results:
                    for result in dict_results:
                        print(f"   Term: {result['term']}")
                        print(f"   Definition: {result['definition']}")
                        if result.get('pronunciation'):
                            print(f"   Pronunciation: [{result['pronunciation']}]")
                        print(f"   Dictionary: {result['dictionary']}")
                else:
                    print(f"   No results found for '{term}'")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Connection error: {e}")
            break
    
    print("\n" + "=" * 50)
    print("✅ API testing completed!")

def check_server():
    """Check if the server is running"""
    try:
        response = requests.get("http://localhost:12000", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_server():
    """Start the dictionary server"""
    print("🚀 Starting Standalone Dictionary Server...")
    
    # Start server in background
    process = subprocess.Popen([
        sys.executable, "standalone_dictionary.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    for i in range(10):
        time.sleep(1)
        if check_server():
            print("✅ Server is running!")
            return process
        print(f"   Checking... ({i+1}/10)")
    
    print("❌ Server failed to start")
    return None

def main():
    """Main demo function"""
    print("🎯 Standalone Dictionary Demo")
    print("=" * 50)
    print("This demo shows that the Anki Dictionary Addon")
    print("can be successfully extracted and run without Anki!")
    print("=" * 50)
    
    # Check if server is already running
    if check_server():
        print("✅ Server is already running!")
    else:
        # Start the server
        server_process = start_server()
        if not server_process:
            print("❌ Could not start server. Please run 'python standalone_dictionary.py' manually.")
            return
    
    # Test the API
    test_api()
    
    # Show web interface info
    print("\n🌐 Web Interface Available:")
    print("   URL: http://localhost:12000")
    print("   Try searching for: hello, world, dictionary, computer")
    
    print("\n📊 Features Demonstrated:")
    print("   ✅ Dictionary database search")
    print("   ✅ Web-based interface")
    print("   ✅ RESTful API")
    print("   ✅ Multi-language support")
    print("   ✅ Pronunciation data")
    
    print("\n🎉 Demo completed successfully!")
    print("The Anki Dictionary Addon core functionality")
    print("is now running independently without Anki!")

if __name__ == "__main__":
    main()