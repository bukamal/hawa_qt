# -*- coding: utf-8 -*-
from ui.shell.app_shell import AppShell
from ui.documents.users_document import UsersDocument


class UsersShell(AppShell):
    """Document shell wrapper for user-management workflows."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.users_document = UsersDocument(shell=self)
        self.register_document('users', self.users_document, '👥 المستخدمون')
        self.open_document('users')

    def refresh_table(self):
        self.users_document.refresh_table()

    def apply_theme_colors(self):
        if hasattr(self.users_document, 'table'):
            self.users_document.table.refresh_style()
