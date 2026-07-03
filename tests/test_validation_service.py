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


def test_validation_rejects_empty_company_and_bad_type(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from services.validation_service import ValidationError, validation_service

    ensure_db()
    try:
        validation_service.validate_expense(
            company_name='', amount=10, type_val='bad', date='2026-07-03', notes='', currency_code='USD'
        )
    except ValidationError as exc:
        assert 'company_name' in exc.field_errors
        assert 'type_val' in exc.field_errors
        return
    raise AssertionError('invalid expense passed validation')


def test_zero_amount_requires_payment_due_date(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from services.validation_service import ValidationError, validation_service

    ensure_db()
    try:
        validation_service.validate_expense(
            company_name='شركة', amount=0, type_val='incoming', date='2026-07-03', notes='', currency_code='USD'
        )
    except ValidationError as exc:
        assert exc.field_errors['payment_due_date']
        return
    raise AssertionError('zero amount without due date passed validation')


def test_preview_preserves_historical_rate_for_same_currency(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from currency import currency
    from services.validation_service import validation_service

    ensure_db()
    currency.update_rate('SYP', 14000)
    existing = {
        'amount_original': 14000,
        'currency_original': 'SYP',
        'exchange_rate_to_usd': 14000,
        'amount_base': 1,
    }
    currency.update_rate('SYP', 15000)
    preview = validation_service.expense_preview(28000, 'SYP', existing_record=existing)

    assert preview.rate_mode == 'historical'
    assert preview.exchange_rate_to_usd == Decimal('14000')
    assert preview.amount_base == Decimal('2.00')
    assert 'التاريخي' in preview.warning


def test_preview_takes_new_snapshot_when_currency_changes(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()

    from database.migrations import ensure_db
    from currency import currency
    from services.validation_service import validation_service

    ensure_db()
    currency.update_rate('SYP', 14000)
    existing = {
        'amount_original': 14000,
        'currency_original': 'SYP',
        'exchange_rate_to_usd': 14000,
        'amount_base': 1,
    }
    currency.update_rate('EUR', 2)
    preview = validation_service.expense_preview(10, 'EUR', existing_record=existing)

    assert preview.rate_mode == 'current_snapshot'
    assert preview.exchange_rate_to_usd == Decimal('2')
    assert preview.amount_base == Decimal('5.00')
    assert 'تغيير عملة القيد' in preview.warning
