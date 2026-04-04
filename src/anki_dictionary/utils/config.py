# -*- coding: utf-8 -*-
"""
Configuration utilities for the Anki Dictionary Addon.

This module provides safe access to addon configuration that works
regardless of the module path or Anki version.
"""

import os
import sys
import json
from typing import Any, Dict, Optional
from aqt import mw


def get_addon_name() -> str:
    """Get the name of the addon folder."""
    # This file is in src/anki_dictionary/utils/config.py
    # Addon root is 3 levels up
    addon_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    return os.path.basename(addon_root)


def get_addon_config() -> Dict[str, Any]:
    """
    Get addon configuration safely.

    Returns:
        dict: The addon configuration, or an empty dict if not available.
    """
    # Try to get config from our state manager first
    try:
        # Add the addon root to path temporarily
        addon_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        if addon_root not in sys.path:
            sys.path.insert(0, addon_root)

        try:
            from __init__ import get_addon_state

            state = get_addon_state()
            if state.config:
                return state.config
        except ImportError:
            pass
        finally:
            if addon_root in sys.path:
                sys.path.remove(addon_root)
    except Exception:
        pass

    # Fallback 1: try to get config from mw.AnkiDictConfig (legacy compatibility)
    if (
        hasattr(mw, "__dict__")
        and "AnkiDictConfig" in mw.__dict__
        and mw.__dict__["AnkiDictConfig"] is not None
    ):
        config_dict = mw.__dict__["AnkiDictConfig"]
        if isinstance(config_dict, dict):
            return config_dict

    # Fallback 2: try to get config using correct addon name
    addon_name = get_addon_name()
    try:
        config = mw.addonManager.getConfig(addon_name)
        if config is not None:
            return config
    except Exception:
        pass

    # Fallback 3: Load default config from file
    try:
        addon_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        config_path = os.path.join(addon_root, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    # If all else fails, return basic defaults
    return {
        "DictionaryGroups": {},
        "maxWidth": 1500,
        "currentGroup": "All",
        "searchMode": "Forward",
        "deinflect": False,
        "onetab": True,
        "dictSizePos": [0, 0, 800, 600],
        "tooltips": True,
    }


def refresh_anki_dict_config(
    config: Optional[Dict[str, Any]] = None, force: bool = False
) -> None:
    """
    Refresh the addon configuration and update the dictionary window if it exists.

    Args:
        config (dict, optional): Direct config to use. If not provided, it's loaded from disk.
        force (bool): If True, force a reload of the dictionary interface even if config hasn't changed.
    """
    if config is not None:
        # Direct config provided - use it
        if hasattr(mw, "__dict__"):
            mw.__dict__["AnkiDictConfig"] = config
    else:
        # Re-load from disk/state
        config = get_addon_config()
        if hasattr(mw, "__dict__"):
            mw.__dict__["AnkiDictConfig"] = config

    # If dictionary exists and is visible, update its configuration
    if (
        hasattr(mw, "ankiDictionary")
        and mw.ankiDictionary
        and hasattr(mw.ankiDictionary, "resetConfiguration")
    ):
        try:
            # We don't want to pass the config object as terms to resetConfiguration
            # just trigger a reload of settings and groups.
            mw.ankiDictionary.resetConfiguration()
        except Exception as e:
            print(f"Error refreshing dictionary configuration: {e}")


def save_addon_config(config: Dict[str, Any]) -> bool:
    """
    Save addon configuration safely.

    Args:
        config (dict): The configuration to save.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    # 1. Update our state manager
    try:
        addon_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        if addon_root not in sys.path:
            sys.path.insert(0, addon_root)

        try:
            from __init__ import get_addon_state

            state = get_addon_state()
            state.config = config
        except ImportError:
            pass
        finally:
            if addon_root in sys.path:
                sys.path.remove(addon_root)
    except Exception:
        pass

    # 2. Update legacy location
    if hasattr(mw, "__dict__"):
        mw.__dict__["AnkiDictConfig"] = config

    # 3. Save to Anki's config manager
    try:
        addon_name = get_addon_name()
        mw.addonManager.writeConfig(addon_name, config)
    except Exception:
        return False

    return True
