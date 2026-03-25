# -*- coding: utf-8 -*-
"""
Logging utility for the Anki Dictionary Addon.
"""

import logging
import os
from aqt import mw

# Define the log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: The name for the logger.

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(f"AnkiDict.{name}")

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)

        # File handler (if Anki is running and we have a path)
        try:
            if mw and mw.pm:
                # Addon root is 3 levels up from this file's directory (src/anki_dictionary/utils)
                addon_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                )
                log_dir = os.path.join(addon_root, "logs")
                os.makedirs(log_dir, exist_ok=True)

                log_file = os.path.join(log_dir, "addon.log")
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
                logger.addHandler(file_handler)
        except Exception:
            # Fallback if mw is not available yet
            pass

    return logger
