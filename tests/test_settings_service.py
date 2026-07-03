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


def test_admin_currency_settings_keep_usd_base_and_write_history(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from services.settings_service import SettingsService
    from database import SettingsRepository
    from currency import currency

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})

    service = SettingsService()
    result = service.save_currency_settings(
        display_currency='SYP',
        decimals=2,
        number_format='western',
        abbreviate_numbers=False,
        rates=[('USD', 1), ('SYP', 14500), ('SAR', 3.75)],
    )

    repo = SettingsRepository()
    assert repo.get('base_currency') == 'USD'
    assert repo.get('display_currency') == 'SYP'
    assert result['base_currency'] == 'USD'
    assert float(currency.get_rate_to_usd('SYP')) == 14500.0
    history = service.list_exchange_rate_history(currency_code='SYP', limit=5)
    assert any(float(row['rate_to_usd']) == 14500.0 for row in history)


def test_viewer_cannot_change_currency_settings(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from services.settings_service import SettingsService

    ensure_db()
    UserSession.login({'id': 2, 'username': 'viewer', 'role': 'viewer'})

    try:
        SettingsService().save_currency_settings('EUR', 2, 'western', False, [('EUR', 0.9)])
    except PermissionError:
        return
    raise AssertionError('viewer was allowed to change settings')
