# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSignal

from ui.shell.app_shell import AppShell
from ui.documents.settings_documents import (
    CurrencySettingsDocument,
    BackupSettingsDocument,
    NetworkSettingsDocument,
    CompanySettingsDocument,
    AppearanceSettingsDocument,
    AudioSettingsDocument,
    LicenseSettingsDocument,
)


class SettingsShell(AppShell):
    """Document Shell wrapper for settings workflows.

    Settings are split by risk area instead of being a single tabbed widget:
    currency, backup, network, company data, appearance, and license.
    """
    rates_changed = pyqtSignal()
    backup_settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currency_document = CurrencySettingsDocument(shell=self)
        self.backup_document = BackupSettingsDocument(shell=self)
        self.network_document = NetworkSettingsDocument(shell=self)
        self.company_document = CompanySettingsDocument(shell=self)
        self.appearance_document = AppearanceSettingsDocument(shell=self)
        self.audio_document = AudioSettingsDocument(shell=self)
        self.license_document = LicenseSettingsDocument(shell=self)

        self.currency_document.rates_changed.connect(self.rates_changed.emit)
        self.backup_document.backup_settings_changed.connect(self.backup_settings_changed.emit)

        self.register_document('settings.currency', self.currency_document, '💱 العملات')
        self.register_document('settings.backup', self.backup_document, '🔄 النسخ')
        self.register_document('settings.network', self.network_document, '🌐 الشبكة')
        self.register_document('settings.company', self.company_document, '🏢 الشركة')
        self.register_document('settings.appearance', self.appearance_document, '🎨 المظهر')
        self.register_document('settings.audio', self.audio_document, '🔊 الصوت')
        self.register_document('settings.license', self.license_document, '🔐 الترخيص')
        self.open_document('settings.currency')

    def apply_theme_colors(self):
        pass
