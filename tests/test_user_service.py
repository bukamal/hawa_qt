# -*- coding: utf-8 -*-


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

def test_viewer_cannot_manage_users(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from services.user_service import UserService

    ensure_db()
    UserSession.login({'id': 2, 'username': 'viewer', 'role': 'viewer'})

    try:
        UserService().create_user('blocked', 'secret123', 'Blocked', 'user')
    except PermissionError:
        return
    raise AssertionError('viewer was allowed to create a user')


def test_cannot_delete_primary_admin(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from services.user_service import UserService

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})

    try:
        UserService().delete_user(1)
    except ValueError as exc:
        assert 'المدير الأساسي' in str(exc)
        return
    raise AssertionError('primary admin was deleted')


def test_admin_can_create_extended_role(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from services.user_service import UserService

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})

    service = UserService()
    new_id = service.create_user('auditor1', 'secret123', 'Auditor One', 'auditor')
    created = service.get_user(new_id)

    assert created['username'] == 'auditor1'
    assert created['role'] == 'auditor'
