# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal

from ui.shell.document_workspace import DocumentWorkspace
from ui.shell.inline_panel import InlinePanel
from branding import APP_DISPLAY_NAME_AR, branding_path


ROUTE_TITLES = {
    'dashboard': 'لوحة التحكم',
    'accounts': 'الحسابات',
    'company': 'كشف الشركة',
    'reports': 'التقارير',
    'users': 'المستخدمون',
    'audit': 'سجل التدقيق',
    'settings': 'الإعدادات',
    'settings.currency': 'الإعدادات / العملات',
    'settings.backup': 'الإعدادات / النسخ الاحتياطي',
    'settings.network': 'الإعدادات / الشبكة',
    'settings.company': 'الإعدادات / الشركة',
    'settings.theme': 'الإعدادات / المظهر واللغة',
    'settings.audio': 'الإعدادات / الصوت',
    'settings.license': 'الإعدادات / الترخيص',
}


class AppShell(QWidget):
    """Document Shell: navigation + command bar + workspace + inline panel.

    This class is intentionally independent from the legacy MainWindow so the migration can
    happen one document at a time without breaking the existing executable.
    """
    route_requested = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('AppShell')
        self.setLayoutDirection(Qt.RightToLeft)
        self.workspace = DocumentWorkspace(self)
        self.inline_panel = InlinePanel(self)
        self.nav_buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.command_bar = QFrame()
        self.command_bar.setObjectName('CommandBar')
        bar = QHBoxLayout(self.command_bar)
        bar.setContentsMargins(12, 8, 12, 8)
        self.title_icon = QLabel()
        self.title_icon.setFixedSize(28, 28)
        pm = QPixmap(branding_path('app_icon_64.png'))
        if not pm.isNull():
            self.title_icon.setPixmap(pm.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.title_icon.setText('◆')
        self.title_label = QLabel(APP_DISPLAY_NAME_AR)
        self.title_label.setObjectName('TitleBrandText')
        self.breadcrumb_label = QLabel('')
        self.breadcrumb_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.breadcrumb_label.setObjectName('BreadcrumbLabel')
        self.breadcrumb_label.setStyleSheet('background: transparent; color: #64748b; font-size: 12px;')
        bar.addWidget(self.title_icon)
        bar.addWidget(self.title_label)
        bar.addWidget(self.breadcrumb_label, 1)
        root.addWidget(self.command_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.nav = QFrame()
        self.nav.setObjectName('NavigationRail')
        self.nav.setFixedWidth(220)
        self.nav_layout = QVBoxLayout(self.nav)
        self.nav_layout.setContentsMargins(8, 12, 8, 12)
        self.nav_layout.setSpacing(6)
        self.nav_layout.addStretch(1)

        body.addWidget(self.nav)
        body.addWidget(self.workspace, 1)
        body.addWidget(self.inline_panel)
        root.addLayout(body, 1)

        self.workspace.document_changed.connect(self._on_document_changed)

    def add_nav_item(self, route: str, text: str):
        btn = QPushButton(text)
        btn.setObjectName('NavigationButton')
        btn.clicked.connect(lambda: self.open_document(route))
        self.nav_layout.insertWidget(max(0, self.nav_layout.count() - 1), btn)
        self.nav_buttons[route] = btn
        return btn

    def register_document(self, route: str, widget, nav_text: str = None):
        self.workspace.register_document(route, widget)
        if nav_text:
            self.add_nav_item(route, nav_text)

    def open_document(self, route: str, **params):
        self.workspace.open_document(route, **params)
        self.route_requested.emit(route, dict(params))

    def open_inline(self, widget, title: str = None):
        self.inline_panel.set_content(widget, title)

    def close_inline(self):
        return self.inline_panel.close_panel()

    def _route_title(self, route: str, params: dict) -> str:
        if route == 'company' and params.get('company_name'):
            return f"الحسابات / {params.get('company_name')}"
        return ROUTE_TITLES.get(route, route.replace('.', ' / '))

    def _on_document_changed(self, route, params):
        self.breadcrumb_label.setText(self._route_title(route, params or {}))
        for key, btn in self.nav_buttons.items():
            btn.setProperty('active', key == route)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
