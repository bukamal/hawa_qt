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

def test_company_report_html_has_valid_table_and_historical_rate(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()
    from database.migrations import ensure_db
    ensure_db()
    from services.print_service import print_service

    html = print_service.build_company_ledger_report('شركة اختبار', [{
        'id': 1,
        'company_name': 'شركة اختبار',
        'amount_original': 14000,
        'currency_original': 'SYP',
        'exchange_rate_to_usd': 14000,
        'amount_base': 1,
        'amount': 1,
        'currency': 'SYP',
        'type': 'incoming',
        'date': '2026-07-03',
        'notes': 'قيد أول',
        'status': 'approved',
    }])

    assert '<thead><tr>' in html
    assert '</table>' in html
    assert '1 USD = 14000.0000 SYP' in html
    assert '一位' not in html


def test_company_report_payload_can_be_exported_without_internal_fields(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    _reset_database_singleton()
    from database.migrations import ensure_db
    ensure_db()
    from services.print_service import print_service

    payload = print_service.build_company_ledger_payload('شركة اختبار', [{
        'id': 1,
        'company_name': 'شركة اختبار',
        'amount_original': 14000,
        'currency_original': 'SYP',
        'exchange_rate_to_usd': 14000,
        'amount_base': 1,
        'amount': 1,
        'currency': 'SYP',
        'type': 'incoming',
        'date': '2026-07-03',
        'notes': 'قيد أول',
        'status': 'approved',
    }])

    assert payload['headers'][-1] == 'سعر القيد'
    assert payload['rows'][0][-1] == '1 USD = 14000.0000 SYP'
    assert 'amount_base' not in payload['html']
    assert payload['default_filename'].startswith('company_ledger_')
