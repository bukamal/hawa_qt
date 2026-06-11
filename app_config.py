# -*- coding: utf-8 -*-
"""Central application configuration helpers."""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Hawaa"
ORG_NAME = "Hawaa"
SETTINGS_APP = "Accounting"
DEFAULT_SERVER_URL = "http://localhost:8000"
DEFAULT_CURRENCY = "USD"


def get_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        data_dir = base / APP_NAME
    else:
        data_dir = Path.home() / ".hawaa"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> str:
    return str(get_data_dir() / "hawaa_data.db")


def get_log_path() -> str:
    return str(get_data_dir() / "hawaa.log")


def get_jwt_secret() -> str:
    secret = os.environ.get("HAWAA_JWT_SECRET") or os.environ.get("JWT_SECRET")
    if secret:
        return secret
    # Development fallback only. Production/server mode must set HAWAA_JWT_SECRET.
    return "hawaa-dev-secret-change-before-network-use"


def is_default_jwt_secret(secret: str) -> bool:
    return secret in {
        "hawaa-secret-key-change-me",
        "hawaa-dev-secret-change-before-network-use",
        "",
        None,
    }
