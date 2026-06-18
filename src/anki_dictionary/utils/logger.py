# -*- coding: utf-8 -*-
"""
Logging utility for the Anki Dictionary Addon.
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from aqt import mw

from .paths import get_addon_root

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
    logger.propagate = False

    # Set base level to DEBUG so handlers can decide what to show
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Console handler - Keep at WARNING to avoid triggering Anki's error dialog
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)

        # File handler (if Anki is running and we have a path)
        try:
            if mw and mw.pm:
                addon_root = get_addon_root()
                log_dir = os.path.join(addon_root, "logs")
                os.makedirs(log_dir, exist_ok=True)

                log_file = os.path.join(log_dir, "addon.log")

                # TimedRotatingFileHandler:
                # when='midnight' (daily rotation)
                # interval=1 (every 1 day)
                # backupCount=3 (keep last 3 days of logs)
                file_handler = TimedRotatingFileHandler(
                    log_file,
                    when="midnight",
                    interval=1,
                    backupCount=3,
                    encoding="utf-8",
                )

                # Enable DEBUG level for the file
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
                logger.addHandler(file_handler)
        except Exception:
            # Fallback if mw is not available yet
            pass

    return logger
