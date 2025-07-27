# -*- coding: utf-8 -*-
"""
Configuration utilities for the Anki Dictionary Addon.

This module provides safe access to addon configuration that works
regardless of the module path or Anki version.
"""

from aqt import mw


def get_addon_config():
    """
    Get addon configuration safely.
    
    Returns:
        dict: The addon configuration, or an empty dict if not available.
    """
    # Try to get config from mw.AnkiDictConfig first (set during addon initialization)
    if hasattr(mw, 'AnkiDictConfig') and mw.AnkiDictConfig is not None:
        return mw.AnkiDictConfig
    
    # Fallback: try to get config using common addon names
    possible_names = ['Anki-Dictionary-Addon', 'anki_dictionary']
    for name in possible_names:
        try:
            config = mw.addonManager.getConfig(name)
            if config is not None:
                return config
        except:
            continue
    
    # If all else fails, return empty dict to prevent None errors
    return {}


def save_addon_config(config):
    """
    Save addon configuration safely.
    
    Args:
        config (dict): The configuration to save.
    """
    if config is None:
        return
    
    # Try to save to mw.AnkiDictConfig first
    if hasattr(mw, 'AnkiDictConfig'):
        mw.AnkiDictConfig = config
    
    # Also save using addon manager
    possible_names = ['Anki-Dictionary-Addon', 'anki_dictionary']
    for name in possible_names:
        try:
            mw.addonManager.writeConfig(name, config)
            break
        except:
            continue


def get_config_value(key, default=None):
    """
    Get a specific configuration value safely.
    
    Args:
        key (str): The configuration key to retrieve.
        default: The default value to return if key is not found.
        
    Returns:
        The configuration value or the default.
    """
    config = get_addon_config()
    return config.get(key, default)


def set_config_value(key, value):
    """
    Set a specific configuration value safely.
    
    Args:
        key (str): The configuration key to set.
        value: The value to set.
    """
    config = get_addon_config()
    config[key] = value
    save_addon_config(config)
