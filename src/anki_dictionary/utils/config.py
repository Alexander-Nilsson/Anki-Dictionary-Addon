"""
Configuration utilities for the Anki Dictionary Addon.

This module provides safe access to addon configuration that works
regardless of the module path or Anki version.
"""

import json
import os
import sys
from typing import Any

from aqt import mw

from .logger import get_logger
from .paths import get_addon_name, get_addon_root

logger = get_logger(__name__.split(".")[-1])


def get_addon_config() -> dict[str, Any]:
    """
    Get addon configuration safely.

    Returns:
        dict: The addon configuration, or an empty dict if not available.
    """
    # Try to get config from our state manager first
    try:
        # Add the addon root to path temporarily
        addon_root = get_addon_root()
        if addon_root not in sys.path:
            sys.path.insert(0, addon_root)

        try:
            from __init__ import get_addon_state

            state = get_addon_state()
            if state.config:
                return state.config
        except ImportError:
            logger.debug("get_addon_state not available, using fallback")
        finally:
            if addon_root in sys.path:
                sys.path.remove(addon_root)
    except Exception:
        logger.debug("Could not load config from addon state")

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
        if config:
            return config
    except Exception:
        logger.debug("Could not load config from addonManager")

    # Fallback 3: Load default config from file
    try:
        addon_root = get_addon_root()
        config_path = os.path.join(addon_root, "config.json")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        logger.debug("Could not load config from config.json")

    # If all else fails, return basic defaults
    return {
        "DictionaryGroups": {},
        "maxWidth": 1500,
        "maxHeight": 400,
        "dictSearch": 50,
        "maxSearch": 1000,
        "frontBracket": "【",
        "backBracket": "】",
        "highlightTarget": True,
        "showTarget": False,
        "tooltips": True,
        "currentGroup": "All",
        "searchMode": "Forward",
        "deinflect": False,
        "onetab": True,
        "dictSizePos": [0, 0, 800, 600],
        "dictAlwaysOnTop": False,
        "day": True,
        "theme": "light",
        "imageAutoConvert": True,
        "forvo_enabled": True,
        "forvo_language": "ja",
        "forvo_limit": 3,
        "ForvoFields": [],
        "ForvoAddType": "add",
        "star_char": "★",
        "star_thresholds": [1501, 5001, 15001, 30001, 60001],
        "show_stars": True,
        "show_rank": False,
        "show_level_labels": True,
        "word_list_visibility": {},
    }


def refresh_anki_dict_config(
    config: dict[str, Any] | None = None, force: bool = False
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
            mw.ankiDictionary.resetConfiguration()  # ty:ignore[call-non-callable]
        except Exception as e:
            logger.error(f"Error refreshing dictionary configuration: {e}")


def save_addon_config(config: dict[str, Any]) -> bool:
    """
    Save addon configuration safely.

    Args:
        config (dict): The configuration to save.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    # 1. Update our state manager
    try:
        addon_root = get_addon_root()
        if addon_root not in sys.path:
            sys.path.insert(0, addon_root)

        try:
            from __init__ import get_addon_state

            state = get_addon_state()
            state.config = config
        except ImportError:
            logger.debug("get_addon_state not available, skipping state save")
        finally:
            if addon_root in sys.path:
                sys.path.remove(addon_root)
    except Exception:
        logger.debug("Could not save config to addon state")

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
