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


def test_accounts_service_summaries_use_historical_snapshot(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from currency import currency
    from database import SettingsRepository
    from services.expense_service import expense_service
    from services.accounts_service import AccountsService

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})
    SettingsRepository().set('display_currency', 'USD')

    currency.update_rate('SYP', 14000)
    expense_service.add('شركة حسابات', 14000, 'incoming', '2026-07-03', 'دخل تاريخي', 'SYP')
    currency.update_rate('SYP', 15000)

    summary = AccountsService().company_summaries()
    row = next(r for r in summary['rows'] if r['company'] == 'شركة حسابات')

    assert '1.00' in row['incoming']
    assert '$' in row['incoming']
    assert summary['base_currency'] == 'USD'
    assert summary['display_currency'] == 'USD'


def test_accounts_service_waiting_payment_does_not_affect_balances(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from currency import currency
    from database import SettingsRepository
    from services.expense_service import expense_service
    from services.accounts_service import AccountsService

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})
    SettingsRepository().set('display_currency', 'USD')
    currency.update_rate('SYP', 14000)

    expense_service.add('شركة انتظار', 14000, 'incoming', '2026-07-03', 'دخل', 'SYP')
    expense_service.add('شركة انتظار', 0, 'incoming', '2026-07-03', 'انتظار', 'SYP', payment_due_date='2026-07-10')

    summary = AccountsService().company_summaries()
    row = next(r for r in summary['rows'] if r['company'] == 'شركة انتظار')

    assert '1.00' in row['incoming']
    assert row['waiting_payment'] == 1
    assert 'بانتظار الدفع' in row['payment_status']


def test_accounts_service_print_report_is_inline_safe(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from database import SettingsRepository
    from services.expense_service import expense_service
    from services.accounts_service import AccountsService

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})
    SettingsRepository().set('display_currency', 'USD')
    expense_service.add('شركة تقرير إجمالي', 10, 'incoming', '2026-07-03', 'دخل', 'USD')

    report = AccountsService().build_summary_report()

    assert 'تقرير إجماليات الشركات' in report['html']
    assert 'شركة تقرير إجمالي' in report['html']
    assert 'amount_base' not in report['html']
