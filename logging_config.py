# -*- coding: utf-8 -*-
"""Application logging setup."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from app_config import get_log_path

_CONFIGURED = False


def setup_logging(level=logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = RotatingFileHandler(get_log_path(), maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    _CONFIGURED = True
