# -*- coding: utf-8 -*-
"""Currency ledger rules used by UI, repositories and reports.

Business invariant:
- amount_original/currency_original are the exact user-entered values.
- exchange_rate_to_usd is a historical snapshot captured when the financial
  value of the entry is created.
- amount_base is the canonical USD value computed from that snapshot.
- display_currency is only a presentation preference and must never rewrite old
  financial rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional, Tuple, List

from currency import currency
from money import (
    base_amount,
    decimal_to_storage,
    quantize_money,
    rate_to_storage,
    to_decimal,
    convert_to_usd,
)

BASE_CURRENCY = "USD"


@dataclass(frozen=True)
class CurrencySnapshot:
    amount_original: Decimal
    currency_original: str
    exchange_rate_to_usd: Decimal
    amount_base: Decimal

    def as_storage(self) -> Dict[str, Any]:
        return {
            "amount": decimal_to_storage(self.amount_base),
            "amount_base": decimal_to_storage(self.amount_base),
            "amount_original": decimal_to_storage(self.amount_original),
            "currency_original": self.currency_original,
            "currency": self.currency_original,
            "exchange_rate_to_usd": rate_to_storage(self.exchange_rate_to_usd),
        }


class CurrencyLedgerService:
    """Single source of truth for accounting currency calculations."""

    def current_rate_to_usd(self, currency_code: str) -> Decimal:
        return to_decimal(currency.get_rate_to_usd(currency_code), Decimal("1"))

    def make_snapshot(
        self,
        amount: Any,
        currency_code: str,
        existing_record: Optional[Dict[str, Any]] = None,
        preserve_rate_if_same_currency: bool = True,
    ) -> CurrencySnapshot:
        amount_dec = quantize_money(amount)
        code = (currency_code or BASE_CURRENCY).upper()
        rate = self.current_rate_to_usd(code)

        if (
            preserve_rate_if_same_currency
            and existing_record
            and (existing_record.get("currency_original") or existing_record.get("currency") or "").upper() == code
            and to_decimal(existing_record.get("exchange_rate_to_usd"), Decimal("0")) > 0
        ):
            # Editing notes/date/amount of the same original currency must not silently reprice the old row.
            rate = to_decimal(existing_record.get("exchange_rate_to_usd"), Decimal("1"))

        amount_base = convert_to_usd(amount_dec, code, rate)
        return CurrencySnapshot(amount_dec, code, rate, amount_base)

    def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Return a record with canonical currency fields populated consistently."""
        if record is None:
            return record
        amount_original = to_decimal(record.get("amount_original", record.get("amount", 0)))
        currency_original = record.get("currency_original") or record.get("currency") or BASE_CURRENCY
        rate = to_decimal(record.get("exchange_rate_to_usd"), Decimal("1"))
        amount_base = to_decimal(record.get("amount_base"), Decimal("0"))
        if amount_base == 0 and amount_original != 0:
            amount_base = convert_to_usd(amount_original, currency_original, rate)
        record["amount_original"] = decimal_to_storage(amount_original)
        record["currency_original"] = currency_original
        record["exchange_rate_to_usd"] = rate_to_storage(rate)
        record["amount_base"] = decimal_to_storage(amount_base)
        record["amount"] = record["amount_base"]
        return record

    def convert_base_to_display(self, amount_base_value: Any, display_currency: Optional[str] = None) -> Decimal:
        display = display_currency or currency.get_display_currency()
        return currency.convert(to_decimal(amount_base_value), BASE_CURRENCY, display)

    def original_amount(self, record: Dict[str, Any]) -> Decimal:
        return to_decimal(record.get("amount_original", record.get("amount", 0)))

    def original_currency(self, record: Dict[str, Any]) -> str:
        return record.get("currency_original") or record.get("currency") or BASE_CURRENCY

    def format_original_amount(self, record: Dict[str, Any]) -> str:
        return currency.format_amount(self.original_amount(record), self.original_currency(record))

    def single_original_currency(self, records: Iterable[Dict[str, Any]]) -> Optional[str]:
        currencies = {self.original_currency(r) for r in records if r}
        return next(iter(currencies)) if len(currencies) == 1 else None

    def company_summary_display_values(
        self,
        records: Iterable[Dict[str, Any]],
        incoming_base: Any,
        outgoing_base: Any,
        display_currency: Optional[str] = None,
    ) -> Tuple[Decimal, Decimal, Decimal, str]:
        """Return incoming/outgoing/net in the user-facing display currency.

        If all rows are in one original currency and the selected display currency is that same
        currency, totals are summed from original amounts. Otherwise totals are summed from the
        canonical USD base and converted only for presentation.
        """
        display = display_currency or currency.get_display_currency()
        records = list(records)
        original = self.single_original_currency(records)
        if original and original == display:
            incoming = sum((self.original_amount(r) for r in records if r.get("type") == "incoming"), Decimal("0"))
            outgoing = sum((self.original_amount(r) for r in records if r.get("type") == "outgoing"), Decimal("0"))
            return incoming, outgoing, incoming - outgoing, original
        incoming = self.convert_base_to_display(incoming_base, display)
        outgoing = self.convert_base_to_display(outgoing_base, display)
        return incoming, outgoing, incoming - outgoing, display



    def approved_records(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rows that affect balances and financial reports."""
        return [r for r in records if r and r.get("status", "approved") == "approved"]

    def company_ledger_display(
        self,
        records: Iterable[Dict[str, Any]],
        display_currency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build one canonical company-ledger view used by UI and printing.

        Waiting-payment rows are displayed but do not affect balances. If all approved
        rows share one original currency and that currency equals the requested display
        currency, running totals are summed directly from original amounts. Otherwise
        running totals are summed in USD base and converted only for presentation.
        """
        display = display_currency or currency.get_display_currency()
        normalized_records = [self.normalize_record(dict(r)) for r in records]
        approved = self.approved_records(normalized_records)
        original_currency = self.single_original_currency(approved)
        use_original_running = bool(original_currency and original_currency == display)

        if use_original_running:
            total_in = sum((self.original_amount(r) for r in approved if r.get("type") == "incoming"), Decimal("0"))
            total_out = sum((self.original_amount(r) for r in approved if r.get("type") == "outgoing"), Decimal("0"))
            net = total_in - total_out
            running_currency = original_currency
            mode_note = "عرض أصلي"
        else:
            total_in_base = sum((base_amount(r) for r in approved if r.get("type") == "incoming"), Decimal("0"))
            total_out_base = sum((base_amount(r) for r in approved if r.get("type") == "outgoing"), Decimal("0"))
            net_base = total_in_base - total_out_base
            total_in = self.convert_base_to_display(total_in_base, display)
            total_out = self.convert_base_to_display(total_out_base, display)
            net = self.convert_base_to_display(net_base, display)
            running_currency = display
            mode_note = "عرض محوّل من USD حسب عملة العرض الحالية"

        rows = []
        running_balance = Decimal("0")
        for idx, r in enumerate(normalized_records, start=1):
            amount_str = self.format_original_amount(r)
            historical_rate_str = self.historical_rate_label(r)
            is_waiting = r.get("status") == "waiting_payment"

            if is_waiting:
                incoming_str = "⏳ بانتظار الدفع"
                outgoing_str = "—"
                running_str = "موعد التنبيه: " + (r.get("payment_due_date") or "غير محدد")
            elif r.get("type") == "incoming":
                incoming_str = amount_str
                outgoing_str = "—"
                running_balance += self.original_amount(r) if use_original_running else base_amount(r)
                running_display = running_balance if use_original_running else currency.convert(running_balance, BASE_CURRENCY, display)
                running_str = currency.format_amount(running_display, running_currency)
            else:
                incoming_str = "—"
                outgoing_str = amount_str
                running_balance -= self.original_amount(r) if use_original_running else base_amount(r)
                running_display = running_balance if use_original_running else currency.convert(running_balance, BASE_CURRENCY, display)
                running_str = currency.format_amount(running_display, running_currency)

            rows.append({
                "id": r.get("id"),
                "serial": idx,
                "date": r.get("date") or "",
                "notes": r.get("notes") or "",
                "incoming": incoming_str,
                "outgoing": outgoing_str,
                "running": running_str,
                "historical_rate": historical_rate_str,
                "status": r.get("status", "approved"),
                "type": r.get("type"),
                "amount_original": self.original_amount(r),
                "currency_original": self.original_currency(r),
                "amount_base": base_amount(r),
            })

        return {
            "display_currency": display,
            "use_original_running": use_original_running,
            "mode_note": mode_note,
            "total_in_display": total_in,
            "total_out_display": total_out,
            "net_display": net,
            "rows": rows,
        }

    def historical_rate_label(self, record_or_rate: Any, currency_code: Optional[str] = None) -> str:
        if isinstance(record_or_rate, dict):
            rate = to_decimal(record_or_rate.get("exchange_rate_to_usd", 1))
            code = self.original_currency(record_or_rate)
        else:
            rate = to_decimal(record_or_rate, Decimal("1"))
            code = currency_code or BASE_CURRENCY
        return f"1 USD = {rate:.4f} {code}"


currency_ledger = CurrencyLedgerService()
