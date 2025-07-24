#!/usr/bin/env python3
"""
Test runner for the simplified Anki Dictionary
"""

import unittest
import sys
import os
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging for tests
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise during tests
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def run_all_tests():
    """Run all tests in the tests directory"""
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return result.wasSuccessful()

def run_specific_test(test_module):
    """Run a specific test module
    
    Args:
        test_module: Name of the test module (e.g., 'test_database')
    """
    try:
        # Import the test module
        module = __import__(f'tests.{test_module}', fromlist=[test_module])
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
        
    except ImportError as e:
        print(f"Error importing test module '{test_module}': {e}")
        return False

def main():
    """Main test runner function"""
    if len(sys.argv) > 1:
        # Run specific test module
        test_module = sys.argv[1]
        if test_module.startswith('test_'):
            test_module = test_module[5:]  # Remove 'test_' prefix
        
        print(f"Running tests for module: {test_module}")
        success = run_specific_test(f'test_{test_module}')
    else:
        # Run all tests
        print("Running all tests...")
        success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()