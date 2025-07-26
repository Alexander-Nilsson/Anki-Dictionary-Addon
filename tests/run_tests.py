#!/usr/bin/env python3
"""
Test runner for Anki Dictionary Addon standalone functionality

This script runs all tests and provides a comprehensive test report.
"""

import unittest
import sys
import os
from pathlib import Path
import time

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def discover_and_run_tests():
    """Discover and run all tests."""
    print("🧪 Anki Dictionary Addon - Test Suite")
    print("=" * 50)
    
    # Discover tests
    test_dir = Path(__file__).parent / 'tests'
    loader = unittest.TestLoader()
    
    try:
        suite = loader.discover(str(test_dir), pattern='test_*.py')
        
        # Count tests
        test_count = suite.countTestCases()
        print(f"📊 Found {test_count} test cases")
        print()
        
        # Run tests
        runner = unittest.TextTestRunner(
            verbosity=2,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        start_time = time.time()
        result = runner.run(suite)
        end_time = time.time()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📈 TEST SUMMARY")
        print("=" * 50)
        print(f"⏱️  Total time: {end_time - start_time:.2f} seconds")
        print(f"🧪 Tests run: {result.testsRun}")
        print(f"✅ Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"💥 Errors: {len(result.errors)}")
        print(f"⏭️  Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
        
        if result.failures:
            print("\n🔴 FAILURES:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\n💥 ERRORS:")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        # Return success/failure
        success = len(result.failures) == 0 and len(result.errors) == 0
        
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n❌ {len(result.failures) + len(result.errors)} TEST(S) FAILED")
            return 1
            
    except Exception as e:
        print(f"💥 Error running tests: {e}")
        return 1

def check_test_dependencies():
    """Check if test dependencies are available."""
    print("🔍 Checking test dependencies...")
    
    missing = []
    
    # Check if tests directory exists
    test_dir = Path(__file__).parent / 'tests'
    if not test_dir.exists():
        print("❌ Tests directory not found")
        return False
    
    # Check for test files
    test_files = list(test_dir.glob('test_*.py'))
    if not test_files:
        print("❌ No test files found")
        return False
    
    print(f"✅ Found {len(test_files)} test files")
    
    # Check if main module can be imported
    try:
        import external_launcher
        print("✅ Main module can be imported")
    except ImportError as e:
        print(f"❌ Cannot import main module: {e}")
        missing.append("standalone_launcher module")
    
    if missing:
        print("❌ Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        return False
    
    print("✅ All test dependencies available")
    return True

def main():
    """Main test runner function."""
    if not check_test_dependencies():
        return 1
    
    print()
    return discover_and_run_tests()

if __name__ == "__main__":
    sys.exit(main())