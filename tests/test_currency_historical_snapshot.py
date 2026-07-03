# -*- coding: utf-8 -*-
from decimal import Decimal


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

def test_edit_same_currency_preserves_historical_rate(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from currency import currency
    from services.expense_service import expense_service
    from database import ExpenseRepository

    ensure_db()
    UserSession.login({'id': 1, 'username': 'admin', 'role': 'admin'})

    currency.update_rate('SYP', 14000)
    expense_id = expense_service.add('شركة اختبار', 14000, 'incoming', '2026-07-03', 'قيد أول', 'SYP')

    currency.update_rate('SYP', 15000)
    expense_service.update(expense_id, 'شركة اختبار', 28000, 'incoming', '2026-07-03', 'تعديل بنفس العملة', 'SYP')

    row = ExpenseRepository().get_by_id(expense_id, convert_to_display=False)
    assert Decimal(str(row['exchange_rate_to_usd'])) == Decimal('14000')
    assert Decimal(str(row['amount_base'])) == Decimal('2')


def test_viewer_cannot_write_expenses(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from auth.session import UserSession
    from services.expense_service import expense_service

    ensure_db()
    UserSession.login({'id': 2, 'username': 'viewer', 'role': 'viewer'})

    try:
        expense_service.add('شركة اختبار', 1, 'incoming', '2026-07-03', 'ممنوع', 'USD')
    except PermissionError:
        return
    raise AssertionError('viewer was allowed to add an expense')
