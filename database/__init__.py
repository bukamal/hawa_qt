# -*- coding: utf-8 -*-
"""Database package exports.

Repositories are loaded lazily to avoid circular imports between currency services and
repository modules during startup/import-time tests.
"""
from database.migrations import ensure_db, init_database
from database.connection import DatabaseConnection

__all__ = [
    'ensure_db', 'init_database', 'DatabaseConnection',
    'UserRepository', 'ExpenseRepository', 'AuditRepository', 'SettingsRepository'
]


def __getattr__(name):
    if name == 'UserRepository':
        from database.repositories.user_repo import UserRepository
        return UserRepository
    if name == 'ExpenseRepository':
        from database.repositories.expense_repo import ExpenseRepository
        return ExpenseRepository
    if name == 'AuditRepository':
        from database.repositories.audit_repo import AuditRepository
        return AuditRepository
    if name == 'SettingsRepository':
        from database.repositories.settings_repo import SettingsRepository
        return SettingsRepository
    raise AttributeError(name)
