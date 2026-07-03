# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal

from ui.shell.app_shell import AppShell
from ui.documents.dashboard_document import DashboardDocument


class DashboardShell(AppShell):
    """Document shell wrapper for the dashboard."""
    refresh_needed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dashboard_document = DashboardDocument(shell=self)
        self.register_document('dashboard', self.dashboard_document, '📊 لوحة التحكم')
        self.refresh_needed.connect(self.dashboard_document.refresh_dashboard)
        self.open_document('dashboard')

    def refresh(self):
        self.dashboard_document.refresh_dashboard()

    def apply_theme_colors(self):
        for table_name in ('recent_table', 'trend_table'):
            table = getattr(self.dashboard_document, table_name, None)
            if table:
                table.refresh_style()
