# -*- coding: utf-8 -*-
import pytest


def _reset_database_singleton():
    from app_config import get_db_path
    import database.connection as dc
    dc.LOCAL_DB_PATH = get_db_path()
    dc.DB_PATH = dc.LOCAL_DB_PATH
    try:
        import database.migrations as mig
        mig.DB_PATH = dc.DB_PATH
    except Exception:
        pass
    if getattr(dc.DatabaseConnection, '_local_conn', None):
        dc.DatabaseConnection._local_conn.close()
    dc.DatabaseConnection._instance = None
    dc.DatabaseConnection._local_conn = None


def test_audit_service_allows_auditor_read_only(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from database import AuditRepository
    from services.audit_service import AuditService

    ensure_db()
    AuditRepository().log(1, 'admin', 'إضافة قيد', 'expenses', 10, 'اختبار')
    UserSession.login({'id': 2, 'username': 'auditor', 'role': 'auditor'})

    logs = AuditService().list_logs()

    assert logs
    assert logs[0]['action'] == 'إضافة قيد'
    with pytest.raises(PermissionError):
        AuditService().delete_old_logs(90)


def test_audit_service_denies_viewer(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from services.audit_service import AuditService

    ensure_db()
    UserSession.login({'id': 3, 'username': 'viewer', 'role': 'viewer'})

    with pytest.raises(PermissionError):
        AuditService().list_logs()
