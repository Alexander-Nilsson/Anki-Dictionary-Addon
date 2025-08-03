# -*- coding: utf-8 -*-
"""
Configuration utilities for the Anki Dictionary Addon.

This module provides safe access to addon configuration that works
regardless of the module path or Anki version.
"""

from typing import Any, Dict, Optional
from aqt import mw


def get_addon_config() -> Dict[str, Any]:
    """
    Get addon configuration safely.

    Returns:
        dict: The addon configuration, or an empty dict if not available.
    """
    # Try to get config from our state manager first
    try:
        # Import here to avoid circular imports
        import sys
        import os

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

    # Fallback: try to get config from mw.AnkiDictConfig (legacy compatibility)
    if (
        hasattr(mw, "__dict__")
        and "AnkiDictConfig" in mw.__dict__
        and mw.__dict__["AnkiDictConfig"] is not None
    ):
        config_dict = mw.__dict__["AnkiDictConfig"]
        if isinstance(config_dict, dict):
            return config_dict  # type: ignore

    # Fallback: try to get config using correct addon name
    addon_name = "Anki-Dictionary-Addon"
    try:
        config = mw.addonManager.getConfig(addon_name)
        if config is not None:
            return config
    except Exception:
        pass

    # Last resort: Load default config from file
    try:
        import json
        import os

        addon_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        config_path = os.path.join(addon_root, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    # If all else fails, return default dictionary groups to prevent errors
    return {
        "DictionaryGroups": {},
        "maxWidth": 1500,
        "currentGroup": "All",
        "searchMode": "Forward",
        "deinflect": False,
        "onetab": True,
        "dictSizePos": [0, 0, 800, 600],
        "tooltips": True,
        "showTarget": False,
        "day": True,
        "maxSearch": 1000,
        "dictSearch": 50,
    }


def save_addon_config(config: Optional[Dict[str, Any]]) -> None:
    """
    Save addon configuration safely.

    Args:
        config: The configuration to save.
    """
    if config is None:
        return

    # Try to update our state manager first
    try:
        import sys
        import os

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

    # Legacy compatibility: Try to save to mw.AnkiDictConfig
    if hasattr(mw, "__dict__") and "AnkiDictConfig" in mw.__dict__:
        mw.__dict__["AnkiDictConfig"] = config

    # Also save using addon manager
    addon_name = "Anki-Dictionary-Addon"
    try:
        mw.addonManager.writeConfig(addon_name, config)  # type: ignore
    except Exception as e:
        print(f"Warning: Could not save config to addon manager: {e}")


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a specific configuration value safely.

    Args:
        key: The configuration key to retrieve.
        default: The default value to return if key is not found.

    Returns:
        The configuration value or the default.
    """
    config = get_addon_config()
    return config.get(key, default)


def set_config_value(key: str, value: Any) -> None:
    """
    Set a specific configuration value safely.

    Args:
        key: The configuration key to set.
        value: The value to set.
    """
    config = get_addon_config()
    config[key] = value
    save_addon_config(config)
