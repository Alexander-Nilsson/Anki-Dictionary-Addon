# -*- coding: utf-8 -*-
"""
Utility for handling icons and base64 encoding.
"""

import os
import base64
from functools import lru_cache
from os.path import join, dirname


# Cache the base64 icons to avoid redundant file reads
@lru_cache(maxsize=32)
def get_base64_icon(icon_name: str) -> str:
    """
    Convert icon to base64 data URL for embedding in HTML.

    Args:
        icon_name: The name of the icon file in assets/icons/

    Returns:
        str: Base64 data URL string
    """
    try:
        # Calculate the icon path (assuming we are in src/anki_dictionary/web/)
        # assets is 3 levels up from this file
        addon_root = dirname(dirname(dirname(dirname(__file__))))
        icon_path = join(addon_root, "assets", "icons", icon_name)

        if not os.path.exists(icon_path):
            print(f"Warning: Icon not found: {icon_path}")
            return ""

        with open(icon_path, "rb") as icon_file:
            icon_data = icon_file.read()
            icon_base64 = base64.b64encode(icon_data).decode("utf-8")

            # Determine MIME type based on file extension
            if icon_name.endswith(".png"):
                mime_type = "image/png"
            elif icon_name.endswith(".svg"):
                mime_type = "image/svg+xml"
            elif icon_name.endswith(".jpg") or icon_name.endswith(".jpeg"):
                mime_type = "image/jpeg"
            else:
                mime_type = "image/png"  # Default fallback

            return f"data:{mime_type};base64,{icon_base64}"
    except Exception as e:
        print(f"Error loading icon {icon_name}: {e}")
        return ""
