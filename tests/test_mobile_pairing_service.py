# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as dt
import json

from services.mobile_pairing_service import MobilePairingService, iso_utc, utc_now
from services.api_contract import APP_ID, PAIRING_CONTRACT, CURRENCY_CONTRACT


def test_mobile_pairing_payload_contains_safe_qr_contract(tmp_path):
    service = MobilePairingService(db_path=str(tmp_path / "hawaa.db"))
    result = service.create_pairing_payload(server_url="http://192.168.1.50:8000", ttl_minutes=5)
    payload = json.loads(result["qr_text"])

    assert payload["app"] == APP_ID
    assert payload["kind"] == "mobile_pairing"
    assert payload["pairing_contract"] == PAIRING_CONTRACT
    assert payload["currency_contract"] == CURRENCY_CONTRACT
    assert payload["server_url"] == "http://192.168.1.50:8000"
    assert "password" not in result["qr_text"].lower()
    assert "jwt" not in result["qr_text"].lower()


def test_mobile_pairing_token_is_one_time_use(tmp_path):
    service = MobilePairingService(db_path=str(tmp_path / "hawaa.db"))
    result = service.create_pairing_payload(server_url="http://192.168.1.50:8000")
    token = result["pairing_token"]

    first = service.validate_pairing_token(token, consume=True)
    second = service.validate_pairing_token(token, consume=True)

    assert first["ok"] is True
    assert first["supports_historic_currency_snapshot"] is True
    assert second["ok"] is False
    assert "used" in second["error"].lower()


def test_mobile_pairing_rejects_expired_token(tmp_path):
    service = MobilePairingService(db_path=str(tmp_path / "hawaa.db"))
    result = service.create_pairing_payload(server_url="http://192.168.1.50:8000")
    expired_at = iso_utc(utc_now() - dt.timedelta(minutes=1))
    with service._connect() as conn:
        conn.execute("UPDATE mobile_pairing_tokens SET expires_at=? WHERE token=?", (expired_at, result["pairing_token"]))
        conn.commit()

    validation = service.validate_pairing_token(result["pairing_token"], consume=True)
    assert validation["ok"] is False
    assert "expired" in validation["error"].lower()


def test_server_url_options_prefers_configured_lan_address(tmp_path):
    service = MobilePairingService(db_path=str(tmp_path / "hawaa.db"))
    options = service.server_url_options(
        port=8000,
        preferred_url="http://192.168.43.132:8000",
    )
    assert options[0]["url"] == "http://192.168.43.132:8000"
    assert options[0]["recommended"] is True


def test_server_url_options_rejects_localhost_and_public_vpn_like_preferred_url(tmp_path):
    service = MobilePairingService(db_path=str(tmp_path / "hawaa.db"))
    options = service.server_url_options(
        port=8000,
        preferred_url="http://26.26.26.1:8000",
    )
    assert all(item["url"] != "http://26.26.26.1:8000" for item in options)
    assert all("localhost" not in item["url"] for item in options)


def test_normalized_pairing_payload_uses_selected_server_url(tmp_path):
    service = MobilePairingService(db_path=str(tmp_path / "hawaa.db"))
    result = service.create_pairing_payload(server_url="192.168.43.132:8000")
    payload = json.loads(result["qr_text"])
    assert result["server_url"] == "http://192.168.43.132:8000"
    assert payload["server_url"] == "http://192.168.43.132:8000"


def test_pairing_validation_returns_paired_flag_for_android(tmp_path):
    service = MobilePairingService(db_path=str(tmp_path / "hawaa.db"))
    result = service.create_pairing_payload(server_url="http://127.0.0.1:8000")
    validation = service.validate_pairing_token(result["pairing_token"], consume=True)
    assert validation["ok"] is True
    assert validation["paired"] is True
    assert validation["server_url"] == "http://127.0.0.1:8000"


def test_localhost_and_zero_dot_zero_are_allowed_for_same_device_testing(tmp_path):
    service = MobilePairingService(db_path=str(tmp_path / "hawaa.db"))
    result = service.create_pairing_payload(server_url="http://0.0.0.0:8000")
    payload = json.loads(result["qr_text"])
    assert payload["server_url"] == "http://127.0.0.1:8000"
    options = service.server_url_options(port=8000, preferred_url="http://127.0.0.1:8000")
    assert any(item["url"] == "http://127.0.0.1:8000" for item in options)
