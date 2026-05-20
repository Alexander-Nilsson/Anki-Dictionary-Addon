# -*- coding: utf-8 -*-
"""
Path utilities for the Anki Dictionary Addon.
"""

import os
from typing import Optional
from aqt import mw


def get_addon_root() -> str:
    """
    Get the absolute path to the addon root directory.

    This works whether the addon is running from the source tree
    or as a bundled Anki addon.
    """
    # This file is in src/anki_dictionary/utils/paths.py
    # Addon root is 4 levels up from this file
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


def get_user_files_dir() -> str:
    """Get the path to the user_files directory."""
    return os.path.join(get_addon_root(), "user_files")


def get_assets_dir() -> str:
    """Get the path to the assets directory."""
    return os.path.join(get_addon_root(), "assets")


def get_icons_dir() -> str:
    """Get the path to the icons directory."""
    return os.path.join(get_assets_dir(), "icons")


def get_templates_dir() -> str:
    """Get the path to the templates directory."""
    return os.path.join(get_assets_dir(), "templates")


def get_db_dir() -> str:
    """Get the path to the database directory."""
    return os.path.join(get_user_files_dir(), "db")


def get_frequency_dir() -> str:
    """Get the path to the frequency data directory."""
    return os.path.join(get_db_dir(), "frequency")


def get_hsk_dir() -> str:
    """Get the path to the HSK data directory."""
    return os.path.join(get_db_dir(), "hsk")


def get_conjugation_dir() -> str:
    """Get the path to the conjugation data directory."""
    return os.path.join(get_db_dir(), "conjugation")


def get_themes_dir() -> str:
    """Get the path to the themes directory."""
    return os.path.join(get_user_files_dir(), "themes")


def get_vendor_dir() -> str:
    """Get the path to the vendor directory."""
    return os.path.join(get_addon_root(), "vendor")


def get_addon_name() -> str:
    """Get the name of the addon folder."""
    return os.path.basename(get_addon_root())
