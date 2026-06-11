# -*- coding: utf-8 -*-
"""Safe money conversion helpers.

SQLite stores numeric columns as REAL in the existing schema. These helpers keep
all calculations in Decimal, then convert at storage/API boundaries to avoid
binary float arithmetic errors inside business logic.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext
from typing import Any

getcontext().prec = 28
MONEY_QUANT = Decimal("0.01")
RATE_QUANT = Decimal("0.00000001")


def to_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, AttributeError):
        return default


def quantize_money(value: Any) -> Decimal:
    return to_decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def quantize_rate(value: Any) -> Decimal:
    return to_decimal(value, Decimal("1")).quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


def decimal_to_storage(value: Any) -> float:
    return float(quantize_money(value))


def rate_to_storage(value: Any) -> float:
    return float(quantize_rate(value))


def convert_to_usd(amount: Any, currency_code: str, rate_to_usd: Any) -> Decimal:
    amount_dec = quantize_money(amount)
    rate_dec = to_decimal(rate_to_usd, Decimal("1"))
    if currency_code == "USD" or rate_dec == 0:
        return amount_dec
    return (amount_dec / rate_dec).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
