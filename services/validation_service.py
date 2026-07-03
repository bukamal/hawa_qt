# -*- coding: utf-8 -*-
"""Validation and preview rules for financial expense entries.

The UI, desktop services and later the API can share this module. It deliberately
contains no PyQt dependency, so it is testable in isolation.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from money import quantize_money, to_decimal
from services.currency_ledger_service import currency_ledger, BASE_CURRENCY
from currency import currency

VALID_EXPENSE_TYPES = {"incoming", "outgoing"}
SUPPORTED_CURRENCIES = {"USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"}


class ValidationError(ValueError):
    """Raised when submitted business data is invalid."""

    def __init__(self, message: str, field_errors: Optional[Dict[str, str]] = None):
        super().__init__(message)
        self.field_errors = field_errors or {}


@dataclass(frozen=True)
class ExpensePreview:
    amount_original: Decimal
    currency_original: str
    exchange_rate_to_usd: Decimal
    amount_base: Decimal
    status: str
    rate_mode: str
    historical_rate_label: str
    current_rate_label: str
    base_amount_label: str
    display_amount_label: str
    warning: str = ""


@dataclass(frozen=True)
class ExpenseValidationResult:
    cleaned: Dict[str, Any]
    preview: ExpensePreview
    field_errors: Dict[str, str] = field(default_factory=dict)


class ValidationService:
    def normalize_date(self, date_value: Any, field_name: str = "date") -> Tuple[Optional[str], Optional[str]]:
        if isinstance(date_value, _dt.date):
            return date_value.isoformat(), None
        text = str(date_value or "").strip()
        if not text:
            return None, "التاريخ مطلوب"
        try:
            _dt.date.fromisoformat(text)
        except ValueError:
            return None, "صيغة التاريخ يجب أن تكون YYYY-MM-DD"
        return text, None

    def expense_preview(
        self,
        amount: Any,
        currency_code: str,
        existing_record: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> ExpensePreview:
        curr = (currency_code or BASE_CURRENCY).upper().strip()
        amount_dec = quantize_money(amount)
        snapshot = currency_ledger.make_snapshot(amount_dec, curr, existing_record=existing_record)
        existing_currency = None
        if existing_record:
            existing_currency = (existing_record.get("currency_original") or existing_record.get("currency") or "").upper()
        preserves_historical = bool(
            existing_record
            and existing_currency == curr
            and to_decimal(existing_record.get("exchange_rate_to_usd"), Decimal("0")) > 0
        )
        rate_mode = "historical" if preserves_historical else "current_snapshot"
        current_rate = currency.get_rate_to_usd(curr)
        final_status = status or ("waiting_payment" if amount_dec == Decimal("0.00") else "approved")
        display_currency = currency.get_display_currency()
        display_amount = currency_ledger.convert_base_to_display(snapshot.amount_base, display_currency)
        warning = ""
        if existing_record and existing_currency and existing_currency != curr:
            warning = "تم تغيير عملة القيد؛ سيُلتقط سعر صرف تاريخي جديد عند الحفظ."
        elif preserves_historical:
            warning = "يتم الحفاظ على سعر القيد التاريخي؛ السعر الحالي للمرجع فقط."
        elif amount_dec == Decimal("0.00"):
            warning = "مبلغ صفر سيُحفظ كعملية بانتظار الدفع ولا يؤثر على الأرصدة."

        return ExpensePreview(
            amount_original=snapshot.amount_original,
            currency_original=snapshot.currency_original,
            exchange_rate_to_usd=snapshot.exchange_rate_to_usd,
            amount_base=snapshot.amount_base,
            status=final_status,
            rate_mode=rate_mode,
            historical_rate_label=currency_ledger.historical_rate_label(snapshot.exchange_rate_to_usd, curr),
            current_rate_label=f"1 USD = {to_decimal(current_rate):.4f} {curr}",
            base_amount_label=currency.format_amount(snapshot.amount_base, BASE_CURRENCY),
            display_amount_label=currency.format_amount(display_amount, display_currency),
            warning=warning,
        )

    def validate_expense(
        self,
        *,
        company_name: Any,
        amount: Any,
        type_val: Any,
        date: Any,
        notes: Any = "",
        currency_code: Any = BASE_CURRENCY,
        payment_due_date: Any = None,
        payment_reminder_note: Any = None,
        status: Optional[str] = None,
        existing_record: Optional[Dict[str, Any]] = None,
    ) -> ExpenseValidationResult:
        errors: Dict[str, str] = {}

        company = str(company_name or "").strip()
        if not company:
            errors["company_name"] = "اسم الشركة مطلوب"
        elif len(company) > 120:
            errors["company_name"] = "اسم الشركة طويل جدًا"

        curr = str(currency_code or BASE_CURRENCY).upper().strip()
        if curr not in SUPPORTED_CURRENCIES:
            errors["currency_code"] = "عملة غير مدعومة"

        expense_type = str(type_val or "").strip()
        if expense_type not in VALID_EXPENSE_TYPES:
            errors["type_val"] = "نوع العملية غير صحيح"

        amount_dec = quantize_money(amount)
        if amount_dec < Decimal("0.00"):
            errors["amount"] = "لا يمكن حفظ مبلغ سالب"
        elif amount_dec > Decimal("999999999.00"):
            errors["amount"] = "المبلغ يتجاوز الحد المسموح"

        clean_date, date_error = self.normalize_date(date)
        if date_error:
            errors["date"] = date_error

        final_status = status or ("waiting_payment" if amount_dec == Decimal("0.00") else "approved")
        if final_status not in {"approved", "waiting_payment", "cancelled"}:
            errors["status"] = "حالة العملية غير صحيحة"

        due_date_clean = None
        if final_status == "waiting_payment":
            due_date_clean, due_error = self.normalize_date(payment_due_date, "payment_due_date")
            if due_error:
                errors["payment_due_date"] = "تاريخ تنبيه الدفع مطلوب لعملية بانتظار الدفع"
        elif payment_due_date:
            due_date_clean, due_error = self.normalize_date(payment_due_date, "payment_due_date")
            if due_error:
                errors["payment_due_date"] = due_error

        note_text = str(notes or "").strip()
        if len(note_text) > 1000:
            errors["notes"] = "الملاحظات طويلة جدًا"
        payment_note = str(payment_reminder_note or "").strip()
        if len(payment_note) > 300:
            errors["payment_reminder_note"] = "ملاحظة التنبيه طويلة جدًا"

        # Build preview even when other fields fail if currency/amount are usable.
        try:
            preview = self.expense_preview(amount_dec, curr, existing_record=existing_record, status=final_status)
        except Exception:
            preview = self.expense_preview(0, BASE_CURRENCY, existing_record=None, status=final_status)
            errors.setdefault("currency_code", "تعذر حساب سعر الصرف لهذه العملة")

        cleaned = {
            "company_name": company,
            "amount": amount_dec,
            "type_val": expense_type,
            "date": clean_date,
            "notes": note_text,
            "currency_code": curr,
            "payment_due_date": due_date_clean if final_status == "waiting_payment" else None,
            "payment_reminder_note": payment_note if final_status == "waiting_payment" else None,
            "status": final_status,
        }

        if errors:
            raise ValidationError("بيانات القيد غير مكتملة أو غير صحيحة", errors)

        return ExpenseValidationResult(cleaned=cleaned, preview=preview)


validation_service = ValidationService()
