"""
utils/logger.py
───────────────
Structured, coloured logging for the Clinical Trial Matcher.

Design decision: We use Python's standard logging module (no third-party
dependency) but wrap it so every module gets a consistent logger that
honours the LOG_LEVEL env var and formats messages with timestamps and the
calling module name — essential for debugging multi-agent pipelines where
you need to know WHICH agent emitted a log line.
"""

import logging
import os
import sys
from typing import Optional


# ── Formatting ────────────────────────────────────────────────────────────────

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Return a named logger configured for the Clinical Trial Matcher.

    Args:
        name:  Typically __name__ of the calling module.
        level: Optional override; falls back to LOG_LEVEL env var → INFO.

    Returns:
        Configured Logger instance.

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Anonymizer started")
    """
    log_level_str: str = level or os.environ.get("LOG_LEVEL", "INFO")
    log_level: int = getattr(logging, log_level_str.upper(), logging.INFO)

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    # Console handler → stderr so it doesn't pollute stdout output (report.md)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)
    formatter = logging.Formatter(fmt=_FORMAT, datefmt=_DATE_FORMAT)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False  # Prevent double-logging from root logger

    return logger
