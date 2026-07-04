# -*- coding: utf-8 -*-
"""Shared REST/mobile compatibility contract constants."""
from __future__ import annotations

APP_ID = "hawaa-sham"
SERVER_NAME = "هوى الشام"
API_CONTRACT_VERSION = "2026.07.mobile-v1"
CURRENCY_CONTRACT = "historic-currency-snapshot-v1"
PAIRING_CONTRACT = "hawaa-mobile-pairing-v1"
BASE_CURRENCY = "USD"


def capabilities_payload(server_url: str | None = None) -> dict:
    payload = {
        "app": APP_ID,
        "server_name": SERVER_NAME,
        "api_contract_version": API_CONTRACT_VERSION,
        "currency_contract": CURRENCY_CONTRACT,
        "base_currency": BASE_CURRENCY,
        "supports_historic_currency_snapshot": True,
        "supports_amount_base": True,
        "supports_exchange_rate_history": True,
        "supports_mobile_pairing": True,
        "pairing_contract": PAIRING_CONTRACT,
    }
    if server_url:
        payload["server_url"] = server_url.rstrip("/")
    return payload
