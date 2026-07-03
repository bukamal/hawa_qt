# -*- coding: utf-8 -*-
from ui.shell.app_shell import AppShell
from ui.documents.reports_document import ReportsDocument


class ReportsShell(AppShell):
    """Document shell wrapper for reports/print-preview workflows."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.reports_document = ReportsDocument(shell=self)
        self.register_document('reports', self.reports_document, '📊 التقارير')
        self.open_document('reports')

    def refresh_table(self):
        self.reports_document.refresh_report()

    def apply_theme_colors(self):
        if hasattr(self.reports_document, 'table'):
            self.reports_document.table.refresh_style()
