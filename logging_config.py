# -*- coding: utf-8 -*-
"""Application logging setup.

Phase 11 moves logging from one flat file to a production-style layout:
``logs/app.log``, ``logs/errors.log`` and ``logs/server.log``. The function is
idempotent so tests and command-line scripts can call it safely.
"""
from __future__ import annotations

import logging
import sys
import warnings
from logging.handlers import RotatingFileHandler
from typing import Optional

from app_config import get_error_log_path, get_log_path, get_server_log_path

_CONFIGURED = False


def _make_file_handler(path: str, level: int) -> RotatingFileHandler:
    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=7, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(process)d | %(threadName)s | %(name)s | %(message)s"
    ))
    return handler


def setup_logging(level: int = logging.INFO, *, context: str = "app", force: bool = False) -> None:
    """Configure root logging.

    Args:
        level: minimum level for the root logger and app log.
        context: ``app`` for desktop mode or ``server`` for bundled Flask mode.
        force: remove existing handlers and configure again. Useful in tests.
    """
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED and not force:
        return
    if force:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
        _CONFIGURED = False

    root.setLevel(level)
    root.addHandler(_make_file_handler(get_log_path("app.log"), level))
    root.addHandler(_make_file_handler(get_error_log_path(), logging.ERROR))
    if context == "server":
        root.addHandler(_make_file_handler(get_server_log_path(), level))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    root.addHandler(console_handler)

    logging.captureWarnings(True)
    warnings.simplefilter("default")
    _CONFIGURED = True
    logging.getLogger(__name__).info("Logging initialized", extra={})


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "hawaa")
