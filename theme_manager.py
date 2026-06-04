# -*- coding: utf-8 -*-
"""مدير الثيمات – إصدار نهائي مع توسيط خلايا الجدول"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor

class ThemeManager:
    _current_theme = 'light'
    _app = None

    LIGHT = {
        'bg_window': '#ffffff',
        'bg_panel': '#f8fafc',
        'bg_sidebar': '#f1f5f9',
        'bg_table': '#ffffff',
        'bg_table_alt': '#f8fafc',
        'text_primary': '#1e293b',
        'text_secondary': '#475569',
        'text_muted': '#64748b',
        'border': '#e2e8f0',
        'border_focus': '#4f46e5',
        'primary': '#4f46e5',
        'primary_hover': '#4338ca',
        'success': '#10b981',
        'danger': '#ef4444',
        'warning': '#f59e0b',
        'info': '#3b82f6',
        'header_bg': '#f1f5f9',
        'selection_bg': '#4f46e5',
        'selection_text': '#ffffff',
    }

    DARK = {
        'bg_window': '#0f172a',
        'bg_panel': '#1e293b',
        'bg_sidebar': '#0f172a',
        'bg_table': '#1e293b',
        'bg_table_alt': '#0f172a',
        'text_primary': '#f8fafc',
        'text_secondary': '#cbd5e1',
        'text_muted': '#94a3b8',
        'border': '#334155',
        'border_focus': '#6366f1',
        'primary': '#6366f1',
        'primary_hover': '#4f46e5',
        'success': '#10b981',
        'danger': '#f43f5e',
        'warning': '#f59e0b',
        'info': '#3b82f6',
        'header_bg': '#1e293b',
        'selection_bg': '#4f46e5',
        'selection_text': '#ffffff',
    }

    @classmethod
    def init_app(cls, app):
        cls._app = app
        cls.apply_theme(cls._current_theme)

    @classmethod
    def apply_theme(cls, theme='light'):
        cls._current_theme = theme
        colors = cls.LIGHT if theme == 'light' else cls.DARK
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(colors['bg_window']))
        palette.setColor(QPalette.WindowText, QColor(colors['text_primary']))
        palette.setColor(QPalette.Base, QColor(colors['bg_table']))
        palette.setColor(QPalette.AlternateBase, QColor(colors['bg_table_alt']))
        palette.setColor(QPalette.Text, QColor(colors['text_primary']))
        palette.setColor(QPalette.Button, QColor(colors['bg_panel']))
        palette.setColor(QPalette.ButtonText, QColor(colors['text_primary']))
        palette.setColor(QPalette.Highlight, QColor(colors['selection_bg']))
        palette.setColor(QPalette.HighlightedText, QColor(colors['selection_text']))
        if cls._app:
            cls._app.setPalette(palette)
            cls._app.setStyleSheet(cls._generate_stylesheet(colors))

    @classmethod
    def get_current_theme(cls):
        return cls._current_theme

    @classmethod
    def get(cls, key):
        colors = cls.LIGHT if cls._current_theme == 'light' else cls.DARK
        return colors.get(key, '')

    @classmethod
    def get_stylesheet(cls):
        colors = cls.LIGHT if cls._current_theme == 'light' else cls.DARK
        return cls._generate_stylesheet(colors)

    @classmethod
    def _generate_stylesheet(cls, colors):
        return f"""
            QMainWindow, QDialog, QWidget {{
                background-color: {colors['bg_window']};
                color: {colors['text_primary']};
                font-family: 'Tajawal', 'Segoe UI', sans-serif;
            }}
            QFrame#sidebar, QFrame#MainFrame {{
                background-color: {colors['bg_sidebar']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
            QPushButton {{
                background-color: {colors['bg_panel']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {colors['border']}; }}
            QPushButton:pressed {{ background-color: {colors['primary']}; color: white; }}
            QPushButton#primary {{
                background-color: {colors['primary']};
                color: white;
                border: none;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                min-height: 40px;
            }}
            QPushButton#primary:hover {{ background-color: {colors['primary_hover']}; }}
            QPushButton#danger {{ background-color: {colors['danger']}; color: white; }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
                background-color: {colors['bg_window']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px;
                selection-background-color: {colors['primary']};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 2px solid {colors['border_focus']};
            }}
            QTableView, QTableWidget {{
                background-color: {colors['bg_table']};
                alternate-background-color: {colors['bg_table_alt']};
                gridline-color: {colors['border']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                outline: 0;
            }}
            QTableView::item, QTableWidget::item {{
                background-color: transparent;
                color: {colors['text_primary']};
                padding: 6px;
                text-align: center;
            }}
            QTableView::item:alternate, QTableWidget::item:alternate {{
                background-color: {colors['bg_table_alt']};
                color: {colors['text_primary']};
                text-align: center;
            }}
            QTableView::item:selected, QTableWidget::item:selected {{
                background-color: {colors['selection_bg']};
                color: {colors['selection_text']};
                text-align: center;
            }}
            QHeaderView::section {{
                background-color: {colors['header_bg']};
                color: {colors['text_secondary']};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {colors['border']};
                border-left: 1px solid {colors['border']};
                font-weight: bold;
                text-align: center;
            }}
            QTableCornerButton::section {{
                background-color: {colors['header_bg']};
                border: 1px solid {colors['border']};
            }}
            QTabWidget::pane {{
                border: 1px solid {colors['border']};
                background-color: {colors['bg_window']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {colors['bg_panel']};
                color: {colors['text_secondary']};
                padding: 8px 16px;
                margin-left: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background-color: {colors['primary']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {colors['border']};
            }}
            QProgressBar {{
                border: none;
                background-color: {colors['border']};
                border-radius: 4px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {colors['primary']};
                border-radius: 4px;
            }}
            QLabel {{
                color: {colors['text_primary']};
            }}
            QLabel#error {{ color: {colors['danger']}; }}
            QLabel#success {{ color: {colors['success']}; }}
            QMenuBar {{
                background-color: {colors['bg_panel']};
                color: {colors['text_primary']};
                border-bottom: 1px solid {colors['border']};
            }}
            QMenuBar::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}
            QMenu {{
                background-color: {colors['bg_window']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
            }}
            QMenu::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}
            QScrollBar:vertical {{
                background: {colors['bg_panel']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {colors['border']};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors['primary']};
            }}
            QGroupBox {{
                border: 1px solid {colors['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                color: {colors['text_primary']};
            }}
        """
