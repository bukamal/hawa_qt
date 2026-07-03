# -*- coding: utf-8 -*-
"""Lazy repository exports to keep import order safe."""
__all__ = ['UserRepository', 'ExpenseRepository', 'AuditRepository', 'SettingsRepository']


def __getattr__(name):
    if name == 'UserRepository':
        from .user_repo import UserRepository
        return UserRepository
    if name == 'ExpenseRepository':
        from .expense_repo import ExpenseRepository
        return ExpenseRepository
    if name == 'AuditRepository':
        from .audit_repo import AuditRepository
        return AuditRepository
    if name == 'SettingsRepository':
        from .settings_repo import SettingsRepository
        return SettingsRepository
    raise AttributeError(name)
