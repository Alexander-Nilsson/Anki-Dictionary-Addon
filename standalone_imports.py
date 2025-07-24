#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import handler for standalone addon execution

This module handles the complex import requirements when running the Anki addon
as a standalone application without the full Anki environment.
"""

import sys
import os
from os.path import dirname, join, exists, abspath

def setup_addon_imports():
    """
    Set up the import environment for the addon to work standalone
    """
    # Get current directory (addon directory)
    addon_path = dirname(abspath(__file__))
    addon_name = os.path.basename(addon_path)
    
    # Add vendor directory to path
    vendor_path = join(addon_path, "vendor")
    if exists(vendor_path):
        sys.path.insert(0, vendor_path)
    
    # Patch relative imports to work as absolute imports
    original_import = __builtins__.__import__
    
    def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        """
        Custom import function that converts relative imports to absolute ones
        """
        if level > 0 and globals is not None:
            # This is a relative import
            current_module = globals.get('__name__', '')
            
            # If we're in the addon directory, convert relative imports
            if current_module in ['dictdb', 'midict', 'main', 'duckduckgoimages', 
                                'webConfig', 'dictionaryWebInstallWizard', 
                                'freqConjWebWindow', 'miUpdater']:
                if name == '':
                    # from . import module
                    if fromlist:
                        results = []
                        for module_name in fromlist:
                            try:
                                # Try importing as absolute
                                module = original_import(module_name, globals, locals, (), 0)
                                results.append(module)
                            except ImportError:
                                # If that fails, try finding the file
                                module_path = join(addon_path, f"{module_name}.py")
                                if exists(module_path):
                                    import importlib.util
                                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                                    module = importlib.util.module_from_spec(spec)
                                    sys.modules[module_name] = module
                                    spec.loader.exec_module(module)
                                    results.append(module)
                                else:
                                    raise ImportError(f"No module named '{module_name}'")
                        return results[0] if len(results) == 1 else results
                else:
                    # from .module import something
                    try:
                        return original_import(name, globals, locals, fromlist, 0)
                    except ImportError:
                        module_path = join(addon_path, f"{name}.py")
                        if exists(module_path):
                            import importlib.util
                            spec = importlib.util.spec_from_file_location(name, module_path)
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[name] = module
                            spec.loader.exec_module(module)
                            return module
                        raise
        
        # For all other imports, use the original function
        return original_import(name, globals, locals, fromlist, level)
    
    # Apply the patch
    __builtins__.__import__ = patched_import
    
    return addon_path

def import_addon_modules():
    """
    Import the required addon modules after setting up the environment
    """
    addon_path = setup_addon_imports()
    
    # Now we can import the modules normally
    try:
        import dictdb
        import midict
        return dictdb, midict, addon_path
    except ImportError as e:
        print(f"Error importing addon modules: {e}")
        raise
