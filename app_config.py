# -*- coding: utf-8 -*-
"""Central application configuration and filesystem helpers.

All runtime data must live outside the installation directory. This is important
for Windows builds installed under Program Files where the application folder is
not writable for normal users.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Hawaa"
ORG_NAME = "Hawaa"
SETTINGS_APP = "Accounting"
DEFAULT_SERVER_URL = "http://localhost:8000"
DEFAULT_CURRENCY = "USD"

# Default development JWT fallback. Server/network mode should override it with
# HAWAA_JWT_SECRET. Readiness checks and ServerService warn when this fallback is
# used in network mode.
_DEFAULT_JWT_SECRET = "hawaa-dev-secret-change-before-network-use"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_frozen() -> bool:
    """Return True when running from a PyInstaller executable."""
    return bool(getattr(__import__("sys"), "frozen", False))


def get_install_dir() -> Path:
    """Best-effort application install/source directory."""
    import sys

    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """Return the writable runtime data directory.

    Precedence:
    1. HAWAA_DATA_DIR environment variable.
    2. Portable marker file next to the executable/source: ``portable.flag``.
    3. Windows %APPDATA%/Hawaa or ~/.hawaa on other systems.
    """
    override = os.environ.get("HAWAA_DATA_DIR")
    if override:
        return _ensure_dir(Path(override).expanduser())

    install_dir = get_install_dir()
    if (install_dir / "portable.flag").exists():
        return _ensure_dir(install_dir / "data")

    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return _ensure_dir(base / APP_NAME)
    return _ensure_dir(Path.home() / ".hawaa")


def get_config_dir() -> Path:
    return _ensure_dir(get_data_dir() / "config")


def get_backup_dir() -> Path:
    return _ensure_dir(get_data_dir() / "backups")


def get_log_dir() -> Path:
    return _ensure_dir(get_data_dir() / "logs")


def get_cache_dir() -> Path:
    return _ensure_dir(get_data_dir() / "cache")


def get_db_path() -> str:
    return str(get_data_dir() / "hawaa_data.db")


def get_log_path(name: str = "app.log") -> str:
    """Return an absolute log path inside the writable logs directory."""
    safe_name = name.replace("/", "_").replace("\\", "_").strip() or "app.log"
    return str(get_log_dir() / safe_name)


def get_error_log_path() -> str:
    return get_log_path("errors.log")


def get_server_log_path() -> str:
    return get_log_path("server.log")


def get_jwt_secret() -> str:
    secret = os.environ.get("HAWAA_JWT_SECRET") or os.environ.get("JWT_SECRET")
    if secret:
        return secret
    return _DEFAULT_JWT_SECRET


def is_default_jwt_secret(secret: str | None) -> bool:
    return secret in {
        "hawaa-secret-key-change-me",
        _DEFAULT_JWT_SECRET,
        "",
        None,
    }


def describe_runtime_paths() -> dict:
    """Small diagnostics payload used by support/readiness tooling."""
    return {
        "install_dir": str(get_install_dir()),
        "data_dir": str(get_data_dir()),
        "config_dir": str(get_config_dir()),
        "backup_dir": str(get_backup_dir()),
        "log_dir": str(get_log_dir()),
        "db_path": get_db_path(),
        "app_log": get_log_path(),
        "error_log": get_error_log_path(),
        "server_log": get_server_log_path(),
        "portable": (get_install_dir() / "portable.flag").exists(),
        "frozen": is_frozen(),
    }
