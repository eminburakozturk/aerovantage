"""Centralized logging for AeroVantage.

Use ``get_logger()`` instead of ``print()`` across the codebase.
Supported levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from core.config import get_settings

_LOG_NAMESPACE = "aerovantage"
_CONFIGURED = False


def configure_logging(force: bool = False) -> logging.Logger:
    """Configure the root AeroVantage logger once and return it."""
    global _CONFIGURED

    logger = logging.getLogger(_LOG_NAMESPACE)

    if _CONFIGURED and not force:
        return logger

    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)

    logger.setLevel(level)
    logger.propagate = False

    if force:
        logger.handlers.clear()

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    _CONFIGURED = True
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a namespaced logger under the AeroVantage root logger."""
    root = configure_logging()
    if not name:
        return root
    return root.getChild(name)
