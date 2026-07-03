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


def test_dashboard_service_uses_historical_snapshot_not_current_rate(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from currency import currency
    from database import SettingsRepository
    from services.expense_service import expense_service
    from services.dashboard_service import DashboardService

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})
    SettingsRepository().set('display_currency', 'USD')
    currency.update_rate('SYP', 14000)

    expense_service.add('شركة لوحة', 14000, 'incoming', '2026-07-03', 'دخل', 'SYP')
    currency.update_rate('SYP', 15000)

    dashboard = DashboardService().build('all')

    incoming_card = next(card for card in dashboard['cards'] if card['key'] == 'incoming')
    assert '1.00' in incoming_card['value']
    assert '$' in incoming_card['value']
    assert dashboard['base_currency'] == 'USD'
    assert dashboard['display_currency'] == 'USD'
    assert dashboard['recent'][0]['historical_rate'].startswith('1 USD = 14000')


def test_dashboard_service_excludes_waiting_payment_from_totals(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from currency import currency
    from database import SettingsRepository
    from services.expense_service import expense_service
    from services.dashboard_service import DashboardService

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})
    SettingsRepository().set('display_currency', 'USD')
    currency.update_rate('SYP', 14000)

    expense_service.add('شركة دفع', 14000, 'incoming', '2026-07-03', 'دخل موافق', 'SYP')
    expense_service.add('شركة دفع', 0, 'incoming', '2026-07-03', 'بانتظار', 'SYP', payment_due_date='2026-07-10')

    dashboard = DashboardService().build('all')

    incoming_card = next(card for card in dashboard['cards'] if card['key'] == 'incoming')
    waiting_card = next(card for card in dashboard['cards'] if card['key'] == 'waiting_payment')
    assert '1.00' in incoming_card['value']
    assert waiting_card['value'] == '1'
