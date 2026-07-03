import datetime

from auth.activation import _expiration_error, _parse_expiration


def test_lifetime_expiration_values_are_valid():
    for value in [None, '', 'lifetime', 'unlimited', 'never', 'permanent', 'غير محدود', 'مدى الحياة', 0, '0']:
        assert _expiration_error({'expiration': value}) is None


def test_expiration_accepts_common_date_formats():
    for value in ['2999-12-31', '31/12/2999', '31.12.2999', '2999-12-31T12:00:00Z']:
        kind, parsed = _parse_expiration(value)
        assert kind == 'date'
        assert isinstance(parsed, datetime.datetime)
        assert _expiration_error({'expiration': value}) is None


def test_expiration_accepts_unix_timestamps_seconds_and_millis():
    future_seconds = 32503680000  # 3000-01-01
    future_millis = future_seconds * 1000
    assert _expiration_error({'expiration': future_seconds}) is None
    assert _expiration_error({'expiration': str(future_millis)}) is None


def test_invalid_expiration_message_includes_value():
    msg = _expiration_error({'expiration': 'not-a-real-date-value'})
    assert msg is not None
    assert 'غير مفهوم' in msg
