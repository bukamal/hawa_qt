# -*- coding: utf-8 -*-
from ui.shell.app_shell import AppShell
from ui.documents.audit_document import AuditDocument


class AuditShell(AppShell):
    """Document shell wrapper for Audit Log."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audit_document = AuditDocument(shell=self)
        self.register_document('audit_log', self.audit_document, '📜 سجل التدقيق')
        self.open_document('audit_log')

    def refresh(self):
        self.audit_document.refresh_logs()

    def apply_theme_colors(self):
        if hasattr(self.audit_document, 'table'):
            self.audit_document.table.refresh_style()
