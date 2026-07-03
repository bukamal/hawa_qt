# -*- coding: utf-8 -*-
"""Reusable branded header/panel for auth and startup screens."""
from __future__ import annotations

from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from branding import APP_DISPLAY_NAME_AR, APP_TAGLINE_AR, branding_path
from theme_manager import ThemeManager


class BrandHeader(QWidget):
    """Compact brand block used by login, activation and startup screens."""

    def __init__(self, subtitle: str | None = None, logo_size: int = 84, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet('background: transparent;')
        logo = QPixmap(branding_path("app_symbol_512.png"))
        if logo.isNull():
            logo = QPixmap(branding_path("app_logo.png"))
        if not logo.isNull():
            self.logo_label.setPixmap(logo.scaled(logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_label.setText("▣")
            self.logo_label.setStyleSheet(f"font-size: {logo_size // 2}px; color: {ThemeManager.get('primary')};")
        layout.addWidget(self.logo_label)

        self.title_label = QLabel(APP_DISPLAY_NAME_AR)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"background: transparent; font-size: 25px; font-weight: 800; color: {ThemeManager.get('primary')};")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle or APP_TAGLINE_AR)
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet(f"background: transparent; font-size: 12px; color: {ThemeManager.get('text_secondary')};")
        layout.addWidget(self.subtitle_label)


class BrandCard(QFrame):
    """Soft card container matching the project identity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BrandCard")
        self.setStyleSheet(f"""
            QFrame#BrandCard {{
                background-color: {ThemeManager.get('bg_panel')};
                border: 1px solid {ThemeManager.get('border')};
                border-radius: 18px;
            }}
        """)
        self.setLayoutDirection(Qt.RightToLeft)


class StatusPill(QFrame):
    """Small status badge used in auth screens."""

    def __init__(self, text: str, tone: str = "info", parent=None):
        super().__init__(parent)
        self.setObjectName("StatusPill")
        colors = {
            "success": ThemeManager.get("success"),
            "danger": ThemeManager.get("danger"),
            "warning": ThemeManager.get("warning"),
            "info": ThemeManager.get("primary"),
        }
        color = colors.get(tone, ThemeManager.get("primary"))
        self.setStyleSheet(f"""
            QFrame#StatusPill {{
                background-color: rgba(15, 118, 110, 0.08);
                border: 1px solid {color};
                border-radius: 13px;
            }}
            QLabel {{ background: transparent; color: {color}; font-size: 11px; font-weight: 700; }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
