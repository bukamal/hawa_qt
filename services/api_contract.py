# -*- coding: utf-8 -*-
"""Shared REST/mobile compatibility contract constants."""
from __future__ import annotations

APP_ID = "hawaa-sham"
SERVER_NAME = "هوى الشام"
API_CONTRACT_VERSION = "2026.07.mobile-v1"
CURRENCY_CONTRACT = "historic-currency-snapshot-v1"
PAIRING_CONTRACT = "hawaa-mobile-pairing-v1"
BASE_CURRENCY = "USD"


REQUIRED_MOBILE_ENDPOINTS = [
    "/api/health",
    "/api/capabilities",
    "/api/login",
    "/api/logout",
    "/api/server_info",
    "/api/expenses",
    "/api/expenses/{id}",
    "/api/expenses/summary",
    "/api/payment_reminders",
    "/api/payment_reminders/count_waiting",
    "/api/users",
    "/api/users/{id}",
    "/api/users/change_password",
    "/api/audit_log",
    "/api/audit_log/old",
    "/api/settings",
    "/api/settings/{key}",
    "/api/exchange_rates",
    "/api/exchange_rate_history",
    "/api/exchange_rates/{currency_code}",
    "/api/mobile/pairing-token",
    "/api/mobile/pair",
]


def capabilities_payload(server_url: str | None = None) -> dict:
    payload = {
        "ok": True,
        "app": APP_ID,
        "service": "hawaa-server",
        "server_name": SERVER_NAME,
        "api_contract_version": API_CONTRACT_VERSION,
        "currency_contract": CURRENCY_CONTRACT,
        "base_currency": BASE_CURRENCY,
        "supports_historic_currency_snapshot": True,
        "supports_amount_base": True,
        "supports_exchange_rate_history": True,
        "supports_mobile_pairing": True,
        "supports_payment_reminders": True,
        "supports_audit_post": True,
        "supports_expense_summary": True,
        "auth_required": True,
        "token_type": "Bearer",
        "pairing_contract": PAIRING_CONTRACT,
        "endpoints": REQUIRED_MOBILE_ENDPOINTS,
    }
    if server_url:
        payload["server_url"] = server_url.rstrip("/")
    return payload
