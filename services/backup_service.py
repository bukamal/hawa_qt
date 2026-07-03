# -*- coding: utf-8 -*-
"""SQLite backup/restore service safe for WAL databases."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path


class BackupService:
    def create_backup(self, source_db: str, backup_path: str) -> str:
        source = Path(source_db)
        target = Path(backup_path)
        if not source.exists():
            raise FileNotFoundError(f"Database not found: {source_db}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(source)) as src, sqlite3.connect(str(target)) as dst:
            src.execute('PRAGMA wal_checkpoint(FULL)')
            src.backup(dst)
            dst.execute('PRAGMA integrity_check')
        self.verify_backup(str(target))
        return str(target)

    def restore_backup(self, backup_path: str, target_db: str) -> str:
        backup = Path(backup_path)
        target = Path(target_db)
        if not backup.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")
        self.verify_backup(str(backup))
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(backup)) as src, sqlite3.connect(str(target)) as dst:
            src.backup(dst)
        return str(target)

    def verify_backup(self, db_path: str) -> bool:
        if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
            raise ValueError('ملف النسخة الاحتياطية فارغ أو غير موجود')
        with sqlite3.connect(db_path) as conn:
            result = conn.execute('PRAGMA integrity_check').fetchone()[0]
            if result != 'ok':
                raise ValueError(f'فشل فحص سلامة قاعدة البيانات: {result}')
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {'users', 'expenses', 'settings', 'exchange_rates'}
            missing = required - tables
            if missing:
                raise ValueError('النسخة الاحتياطية ناقصة الجداول: ' + ', '.join(sorted(missing)))
        return True


backup_service = BackupService()
