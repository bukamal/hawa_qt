# -*- coding: utf-8 -*-
"""Branding and resource helpers for Hawaa.

The paths are PyInstaller-safe: when the app is bundled, resources can be
resolved through ``sys._MEIPASS``; during development they resolve relative to
this source directory.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_SLUG = "hawaa"
APP_DISPLAY_NAME_AR = "هوى الشام"
APP_DISPLAY_NAME_EN = "Hawaa Al-Sham"
APP_TAGLINE_AR = "نظام الحسابات الداخلية"
APP_TAGLINE_EN = "Internal Accounting System"
APP_FILE_EXTENSION = ".hawa"

BRAND_COLORS = {
    "primary": "#0f766e",
    "primary_dark": "#134e4a",
    "primary_hover": "#115e59",
    "accent": "#d97706",
    "success": "#059669",
    "warning": "#d97706",
    "danger": "#dc2626",
    "info": "#2563eb",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "sidebar": "#f1f5f9",
    "text": "#0f172a",
    "muted": "#64748b",
    "border": "#dbe4e8",
}


def project_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> str:
    return str(project_root().joinpath("resources", *parts))


def branding_path(filename: str) -> str:
    return resource_path("branding", filename)


def app_icon_path() -> str:
    ico = branding_path("app.ico")
    png = branding_path("app_icon_256.png")
    return ico if os.path.exists(ico) else png


def installer_icon_path() -> str:
    return branding_path("installer.ico")


def project_file_icon_path() -> str:
    return branding_path("project_file.ico")


def backup_file_icon_path() -> str:
    return branding_path("backup_file.ico")


def safe_qicon(path: str = None):
    """Return QIcon when PyQt is available; otherwise return None.

    This keeps non-GUI tests and scripts independent from PyQt runtime.
    """
    try:
        from PyQt5.QtGui import QIcon
        chosen = path or app_icon_path()
        if chosen and os.path.exists(chosen):
            return QIcon(chosen)
        return QIcon()
    except Exception:
        return None
