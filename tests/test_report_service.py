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

def test_report_service_uses_base_amount_and_display_currency(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from currency import currency
    from database import SettingsRepository
    from services.expense_service import expense_service
    from services.report_service import ReportService

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})

    SettingsRepository().set('display_currency', 'USD')
    currency.update_rate('SYP', 14000)
    expense_service.add('شركة تقرير', 14000, 'incoming', '2026-07-03', 'دخل تاريخي', 'SYP')
    currency.update_rate('SYP', 15000)

    report = ReportService().build('income_statement', '2026-07-01', '2026-07-31')

    assert any('1.00' in str(cell) and '$' in str(cell) for row in report['rows'] for cell in row)
    assert 'عملة العرض: USD' in report['subtitle']
    assert 'amount_base' not in report['html']
