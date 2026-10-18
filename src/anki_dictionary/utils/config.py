"""
Configuration utilities for the Anki Dictionary Addon.

This module provides safe access to addon configuration that works
regardless of the module path or Anki version.
"""

import json
import os
import sys
from typing import Any

import aqt

from .logger import get_logger
from .paths import get_addon_name, get_addon_root

logger = get_logger(__name__.split(".")[-1])

# Bump when a new key needs a one-off migration. ``get_addon_config`` fills in
# missing keys from the packaged defaults on every load, so most versions only
# need the merge; this stamp is for changes that cannot be expressed as a
# default.
CONFIG_VERSION = 2

# Keys injected into the live config for convenience, never persisted.
_TRANSIENT_KEYS = frozenset(
    {
        "addon_path",
        "addon_name",
        "addon_root",
        "dict_path",
        "home_dir",
    }
)

_DEFAULT_CONFIG: dict[str, Any] = {
    "config_version": CONFIG_VERSION,
    "DictionaryGroups": {},
    "ExportTemplates": {},
    "ImageFields": [],
    "ImageAddType": "add",
    "maxWidth": 1500,
    "maxHeight": 400,
    "dictSearch": 50,
    "maxSearch": 1000,
    "frontBracket": "【",
    "backBracket": "】",
    "highlightTarget": True,
    "showTarget": False,
    "exportHeaderHtml": False,
    "tooltips": True,
    "currentGroup": "All",
    "searchMode": "Forward",
    "currentTemplate": False,
    "currentDeck": False,
    "exporterSizePos": None,
    "exporterLastTags": "",
    "autoDefinitionSettings": False,
    "autoAddDefinitions": False,
    "unknownsToSearch": 3,
    "deinflect": False,
    "onetab": True,
    "dictSizePos": [0, 0, 800, 600],
    "dictAlwaysOnTop": False,
    "dictOnStart": False,
    "day": True,
    "theme": "light",
    "imageAutoConvert": True,
    "imageSearchRegion": "United States",
    "forvo_enabled": True,
    "forvo_language": "en",
    "forvo_limit": 3,
    "ForvoFields": [],
    "ForvoAddType": "add",
    "star_char": "★",
    "star_thresholds": [1501, 5001, 15001, 30001, 60001],
    "show_stars": True,
    "show_rank": False,
    "show_level_labels": True,
    "word_list_visibility": {},
    "auto_select_dict_group": True,
    "language_defaults": {},
    "last_seen_version": "",
    "hide_release_notes": False,
    "clipboard_monitor_enabled": True,
    "restore_session": False,
    "session_terms": [],
    "llm_enabled": False,
    "llm_api_key": "",
    "llm_base_url": "https://api.openai.com/v1/chat/completions",
    "llm_model": "gpt-4o-mini",
    "llm_prompt": "Provide a concise dictionary definition for the word: {term}",
    "llm_timeout": 20,
    "llm_temperature": 0.3,
    "llm_keep_alive": "30m",
    "llm_think": False,
    "llm_stream": False,
    "llm_get_pronunciation": False,
}


def _packaged_defaults() -> dict[str, Any]:
    """Return the defaults shipped in ``config.json``, if readable."""
    defaults = dict(_DEFAULT_CONFIG)
    try:
        config_path = os.path.join(get_addon_root(), "config.json")
        with open(config_path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            # Packaged defaults win over the built-in fallback for every key
            # they define, but never contribute user data (groups/templates).
            for key, value in data.items():
                if key not in ("DictionaryGroups", "ExportTemplates", "ImageFields"):
                    defaults[key] = value
    except Exception:
        logger.debug("Could not read packaged config.json defaults", exc_info=True)
    defaults["config_version"] = CONFIG_VERSION
    return defaults


def _normalise_config(config: dict[str, Any] | None) -> dict[str, Any]:
    """Merge stored config over packaged defaults and stamp the version."""
    merged = _packaged_defaults()
    if isinstance(config, dict):
        merged.update({k: v for k, v in config.items() if k not in _TRANSIENT_KEYS})
    merged["config_version"] = CONFIG_VERSION
    return merged


def get_addon_config() -> dict[str, Any]:
    """
    Get addon configuration safely, with missing keys filled from defaults.

    Returns:
        dict: The addon configuration, or defaults if not available.
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
                return _normalise_config(state.config)
        except ImportError:
            logger.debug("get_addon_state not available, using fallback")
        finally:
            if addon_root in sys.path:
                sys.path.remove(addon_root)
    except Exception:
        logger.debug("Could not load config from addon state")

    # Fallback 1: try to get config from mw.AnkiDictConfig (legacy compatibility)
    if (
        hasattr(aqt.mw, "__dict__")
        and "AnkiDictConfig" in aqt.mw.__dict__
        and aqt.mw.__dict__["AnkiDictConfig"] is not None
    ):
        config_dict = aqt.mw.__dict__["AnkiDictConfig"]
        if isinstance(config_dict, dict):
            return _normalise_config(config_dict)

    # Fallback 2: try to get config using correct addon name
    addon_name = get_addon_name()
    try:
        config = aqt.mw.addonManager.getConfig(addon_name)
        if config:
            return _normalise_config(config)
    except Exception:
        logger.debug("Could not load config from addonManager")

    # Fallback 3: Load default config from file
    try:
        addon_root = get_addon_root()
        config_path = os.path.join(addon_root, "config.json")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                return _normalise_config(json.load(f))
    except Exception:
        logger.debug("Could not load config from config.json")

    # If all else fails, return basic defaults
    return _packaged_defaults()


def get_session_terms(config: dict[str, Any] | None) -> list[str]:
    """
    Return the persisted open-tab terms when session restore is enabled (A5).
    """
    if not config or not config.get("restore_session"):
        return []
    terms = config.get("session_terms", [])
    if not isinstance(terms, list):
        return []
    # Drop stale empty/whitespace entries and duplicates in display order so a
    # saved session can't reopen blank or repeated tabs.
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        if isinstance(term, str) and term.strip() and term not in seen:
            seen.add(term)
            out.append(term)
    return out


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
        config = _normalise_config(config)
        if hasattr(aqt.mw, "__dict__"):
            aqt.mw.__dict__["AnkiDictConfig"] = config
    else:
        # Re-load from disk/state
        config = get_addon_config()
        if hasattr(aqt.mw, "__dict__"):
            aqt.mw.__dict__["AnkiDictConfig"] = config

    # If dictionary exists and is visible, update its configuration
    if (
        hasattr(aqt.mw, "ankiDictionary")
        and aqt.mw.ankiDictionary
        and hasattr(aqt.mw.ankiDictionary, "resetConfiguration")
    ):
        try:
            # We don't want to pass the config object as terms to resetConfiguration
            # just trigger a reload of settings and groups.
            aqt.mw.ankiDictionary.resetConfiguration()  # ty:ignore[call-non-callable]
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
    config = _normalise_config(config)

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
    if hasattr(aqt.mw, "__dict__"):
        aqt.mw.__dict__["AnkiDictConfig"] = config

    # 3. Save to Anki's config manager
    try:
        addon_name = get_addon_name()
        aqt.mw.addonManager.writeConfig(addon_name, config)
    except Exception:
        return False

    return True
