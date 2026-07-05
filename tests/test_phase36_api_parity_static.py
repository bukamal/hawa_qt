from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_windows_server_exposes_android_required_endpoints():
    source = (ROOT / 'flask_server.py').read_text(encoding='utf-8')
    for endpoint in [
        '/api/health',
        '/api/server_info',
        '/api/expenses/summary',
        '/api/payment_reminders',
        '/api/payment_reminders/count_waiting',
        '/api/audit_log',
        '/api/settings',
    ]:
        assert endpoint in source
    assert "methods=['POST']" in source and "add_audit_log_from_client" in source


def test_capabilities_advertise_full_mobile_contract():
    source = (ROOT / 'services' / 'api_contract.py').read_text(encoding='utf-8')
    for flag in [
        'supports_payment_reminders',
        'supports_audit_post',
        'supports_expense_summary',
        'supports_amount_base',
        'supports_exchange_rate_history',
    ]:
        assert flag in source
    for endpoint in [
        '/api/expenses/summary',
        '/api/payment_reminders',
        '/api/payment_reminders/count_waiting',
        '/api/audit_log',
    ]:
        assert endpoint in source
