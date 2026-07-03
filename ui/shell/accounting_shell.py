# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal

from ui.shell.app_shell import AppShell
from ui.documents.accounts_document import AccountsDocument
from ui.documents.company_document import CompanyDocument


class AccountingShell(AppShell):
    """Document shell dedicated to accounting workflows.

    It is used as the Accounts page in the legacy MainWindow, so the project can migrate
    gradually: dashboard/users/settings remain unchanged while accounts already work as
    document navigation + inline editing.
    """
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.accounts_document = AccountsDocument(shell=self)
        self.company_document = CompanyDocument(shell=self)
        self.accounts_document.data_changed.connect(self.data_changed.emit)
        self.company_document.data_changed.connect(self._on_company_data_changed)
        self.register_document('accounts', self.accounts_document, '📋 الحسابات')
        self.register_document('company', self.company_document)
        self.open_document('accounts')

    def _on_company_data_changed(self):
        self.accounts_document.refresh_table()
        self.data_changed.emit()

    def refresh_table(self):
        self.accounts_document.refresh_table()
        if self.workspace.current_route() == 'company':
            self.company_document.refresh()

    def apply_theme_colors(self):
        self.accounts_document.apply_theme_colors()
        if hasattr(self.company_document, 'table'):
            self.company_document.table.refresh_style()

    def open_accounts(self):
        self.open_document('accounts')
