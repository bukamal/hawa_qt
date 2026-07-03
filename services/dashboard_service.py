# -*- coding: utf-8 -*-
"""Dashboard calculations independent from PyQt widgets.

The dashboard must use amount_base (USD) as the accounting source of truth and
only convert to the selected Display Currency for presentation. Historical
exchange-rate snapshots on individual rows are never recomputed here.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from currency import currency
from database import ExpenseRepository, UserRepository
from money import base_amount, to_decimal
from services.currency_ledger_service import currency_ledger


PERIOD_ALL = 'all'
PERIOD_CURRENT_MONTH = 'current_month'
PERIOD_PREVIOUS_MONTH = 'previous_month'
PERIOD_CURRENT_YEAR = 'current_year'

PERIOD_LABELS = {
    PERIOD_ALL: 'الكل',
    PERIOD_CURRENT_MONTH: 'الشهر الحالي',
    PERIOD_PREVIOUS_MONTH: 'الشهر الماضي',
    PERIOD_CURRENT_YEAR: 'السنة الحالية',
}


class DashboardService:
    def __init__(self, expense_repo: Optional[ExpenseRepository] = None, user_repo: Optional[UserRepository] = None):
        self._expense_repo = expense_repo
        self._user_repo = user_repo

    @property
    def expense_repo(self):
        return self._expense_repo or ExpenseRepository()

    @property
    def user_repo(self):
        return self._user_repo or UserRepository()

    def date_filter(self, period: str, today: Optional[date] = None) -> Tuple[Optional[str], Optional[str]]:
        today = today or date.today()
        if period == PERIOD_CURRENT_MONTH:
            start = today.replace(day=1)
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
            return start.isoformat(), end.isoformat()
        if period == PERIOD_PREVIOUS_MONTH:
            current_start = today.replace(day=1)
            prev_end = current_start - timedelta(days=1)
            prev_start = prev_end.replace(day=1)
            return prev_start.isoformat(), prev_end.isoformat()
        if period == PERIOD_CURRENT_YEAR:
            return date(today.year, 1, 1).isoformat(), date(today.year, 12, 31).isoformat()
        return None, None

    def build(self, period: str = PERIOD_ALL) -> Dict[str, Any]:
        start_date, end_date = self.date_filter(period)
        all_records = [currency_ledger.normalize_record(dict(e)) for e in self.expense_repo.get_all(convert_to_display=False)]
        filtered = [r for r in all_records if self._in_range(r, start_date, end_date)]
        approved = currency_ledger.approved_records(filtered)
        waiting = [r for r in all_records if r.get('status') == 'waiting_payment']
        today_iso = date.today().isoformat()
        overdue = [r for r in waiting if r.get('payment_due_date') and r.get('payment_due_date') < today_iso]

        total_in_base = sum((base_amount(r) for r in approved if r.get('type') == 'incoming'), Decimal('0'))
        total_out_base = sum((base_amount(r) for r in approved if r.get('type') == 'outgoing'), Decimal('0'))
        net_base = total_in_base - total_out_base
        display_currency = currency.get_display_currency()

        companies = {r.get('company_name') for r in approved if r.get('company_name')}
        users_count = self._safe_users_count()
        avg_base = sum((base_amount(r) for r in approved), Decimal('0')) / len(approved) if approved else Decimal('0')
        top_company = self._top_company(approved, display_currency)

        cards = [
            {'key': 'incoming', 'title': 'إجمالي الوارد', 'value': self._fmt(total_in_base), 'raw_base': total_in_base},
            {'key': 'outgoing', 'title': 'إجمالي الصادر', 'value': self._fmt(total_out_base), 'raw_base': total_out_base},
            {'key': 'net', 'title': 'الصافي', 'value': self._fmt(net_base), 'raw_base': net_base, 'kind': 'positive' if net_base >= 0 else 'negative'},
            {'key': 'companies', 'title': 'عدد الشركات', 'value': str(len(companies)), 'raw': len(companies)},
            {'key': 'users', 'title': 'عدد المستخدمين', 'value': str(users_count), 'raw': users_count},
            {'key': 'average', 'title': 'متوسط قيمة القيد', 'value': self._fmt(avg_base), 'raw_base': avg_base},
            {'key': 'top_company', 'title': 'أعلى شركة صافي', 'value': top_company},
            {'key': 'exchange_rate', 'title': 'سعر العرض الحالي', 'value': self._rate_text(display_currency)},
            {'key': 'waiting_payment', 'title': 'عمليات بانتظار الدفع', 'value': str(len(waiting)), 'raw': len(waiting)},
            {'key': 'overdue_payment', 'title': 'دفعات متأخرة', 'value': str(len(overdue)), 'raw': len(overdue)},
        ]

        return {
            'period': period,
            'period_label': PERIOD_LABELS.get(period, PERIOD_LABELS[PERIOD_ALL]),
            'start_date': start_date,
            'end_date': end_date,
            'display_currency': display_currency,
            'base_currency': 'USD',
            'cards': cards,
            'trend': self._monthly_trend(approved, display_currency),
            'recent': self._recent_records(all_records),
            'subtitle': self._subtitle(start_date, end_date, display_currency),
        }

    def _in_range(self, record: Dict[str, Any], start_date: Optional[str], end_date: Optional[str]) -> bool:
        d = record.get('date') or ''
        if start_date and d < start_date:
            return False
        if end_date and d > end_date:
            return False
        return True

    def _fmt(self, amount_base_value) -> str:
        display_currency = currency.get_display_currency()
        display_value = currency_ledger.convert_base_to_display(amount_base_value, display_currency)
        return currency.format_amount(display_value, display_currency)

    def _safe_users_count(self) -> int:
        try:
            return len(self.user_repo.get_all())
        except Exception:
            return 0

    def _top_company(self, records: List[Dict[str, Any]], display_currency: str) -> str:
        totals = defaultdict(lambda: Decimal('0'))
        for r in records:
            company = r.get('company_name') or ''
            if not company:
                continue
            amount = base_amount(r)
            totals[company] += amount if r.get('type') == 'incoming' else -amount
        if not totals:
            return '—'
        company_name, net_base = max(totals.items(), key=lambda item: item[1])
        display_value = currency_ledger.convert_base_to_display(net_base, display_currency)
        return f"{company_name} ({currency.format_amount(display_value, display_currency)})"

    def _rate_text(self, display_currency: str) -> str:
        if display_currency == 'USD':
            return '1 USD = 1.0000 USD'
        rate = currency.get_rate_to_usd(display_currency)
        try:
            return f"1 USD = {float(rate):.4f} {display_currency}"
        except Exception:
            return f"1 USD = {rate} {display_currency}"

    def _monthly_trend(self, records: List[Dict[str, Any]], display_currency: str) -> List[Dict[str, Any]]:
        monthly_in = defaultdict(lambda: Decimal('0'))
        monthly_out = defaultdict(lambda: Decimal('0'))
        for r in records:
            month = (r.get('date') or '')[:7]
            if not month:
                continue
            if r.get('type') == 'incoming':
                monthly_in[month] += base_amount(r)
            else:
                monthly_out[month] += base_amount(r)

        today = datetime.now().date()
        months = []
        cursor = today.replace(day=1)
        for offset in range(5, -1, -1):
            year = cursor.year
            month = cursor.month - offset
            while month <= 0:
                month += 12
                year -= 1
            months.append(f"{year:04d}-{month:02d}")

        rows = []
        for month in months:
            incoming_base = monthly_in[month]
            outgoing_base = monthly_out[month]
            incoming = currency_ledger.convert_base_to_display(incoming_base, display_currency)
            outgoing = currency_ledger.convert_base_to_display(outgoing_base, display_currency)
            rows.append({
                'month': month,
                'incoming': currency.format_amount(incoming, display_currency),
                'outgoing': currency.format_amount(outgoing, display_currency),
                'net': currency.format_amount(incoming - outgoing, display_currency),
                'incoming_raw': to_decimal(incoming),
                'outgoing_raw': to_decimal(outgoing),
            })
        return rows

    def _recent_records(self, records: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        recent = sorted(records, key=lambda r: int(r.get('id') or 0), reverse=True)[:limit]
        rows = []
        for r in recent:
            original_amount = to_decimal(r.get('amount_original', r.get('amount', 0)))
            original_currency = r.get('currency_original') or r.get('currency') or 'USD'
            status = r.get('status') or 'approved'
            if status == 'waiting_payment':
                status_label = f"بانتظار الدفع ({r.get('payment_due_date') or 'غير محدد'})"
            elif r.get('type') == 'incoming':
                status_label = 'لنا'
            else:
                status_label = 'له'
            rows.append({
                'id': r.get('id'),
                'date': r.get('date') or '',
                'company_name': r.get('company_name') or '',
                'amount_original': currency.format_amount(original_amount, original_currency),
                'type': status_label,
                'historical_rate': currency_ledger.historical_rate_label(r),
            })
        return rows

    def _subtitle(self, start_date: Optional[str], end_date: Optional[str], display_currency: str) -> str:
        period_text = 'كل الفترات' if not start_date and not end_date else f"{start_date} → {end_date}"
        return f"الفترة: {period_text} | العملة الأساسية: USD | عملة العرض: {display_currency}"


dashboard_service = DashboardService()
