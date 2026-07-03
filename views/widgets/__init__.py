# -*- coding: utf-8 -*-
"""Legacy widget exports.

The application now routes through ui.shell/* and ui.documents/*.
These widgets are kept only for backward compatibility and are imported lazily
so legacy modules do not load dialogs/services unless explicitly requested.
"""

__all__ = [
    'DashboardWidget',
    'AccountsWidget',
    'UsersWidget',
    'AuditLogWidget',
    'SettingsWidget',
    'ReportsWidget',
]


def __getattr__(name):
    if name == 'DashboardWidget':
        from .dashboard_widget import DashboardWidget
        return DashboardWidget
    if name == 'AccountsWidget':
        from .accounts_widget import AccountsWidget
        return AccountsWidget
    if name == 'UsersWidget':
        from .users_widget import UsersWidget
        return UsersWidget
    if name == 'AuditLogWidget':
        from .audit_log_widget import AuditLogWidget
        return AuditLogWidget
    if name == 'SettingsWidget':
        from .settings_widget import SettingsWidget
        return SettingsWidget
    if name == 'ReportsWidget':
        from .reports_widget import ReportsWidget
        return ReportsWidget
    raise AttributeError(name)
