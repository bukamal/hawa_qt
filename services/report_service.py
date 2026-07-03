# -*- coding: utf-8 -*-
"""Canonical financial report calculations.

Reports must use amount_base (USD) as the accounting source of truth. The selected
Display Currency is presentation only and must not rewrite historical entries.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Iterable, Any

from currency import currency
from database import ExpenseRepository
from i18n.translator import translate
from money import base_amount
from services.currency_ledger_service import currency_ledger
from services.print_service import print_service


REPORT_TYPES = {
    'income_statement': 'قائمة الدخل',
    'balance_sheet': 'الميزانية العمومية',
    'bookings_summary': 'ملخص شهري',
    'customer_balances': 'أرصدة العملاء/الشركات',
}


class ReportService:
    def __init__(self, repo=None):
        self._repo = repo

    @property
    def repo(self):
        return self._repo or ExpenseRepository()

    def build(self, report_type: str, start_date: str, end_date: str) -> Dict[str, Any]:
        if report_type == 'income_statement':
            return self.income_statement(start_date, end_date)
        if report_type == 'balance_sheet':
            return self.balance_sheet(start_date, end_date)
        if report_type == 'bookings_summary':
            return self.bookings_summary(start_date, end_date)
        if report_type == 'customer_balances':
            return self.customer_balances(start_date, end_date)
        raise ValueError(f'نوع تقرير غير معروف: {report_type}')

    def _records(self) -> List[Dict[str, Any]]:
        rows = self.repo.get_all(convert_to_display=False)
        return [currency_ledger.normalize_record(dict(r)) for r in rows]

    def _approved(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return currency_ledger.approved_records(records)

    def _fmt(self, amount_base_value) -> str:
        display_currency = currency.get_display_currency()
        display_value = currency_ledger.convert_base_to_display(amount_base_value, display_currency)
        return currency.format_amount(display_value, display_currency)

    def _subtitle(self, start_date: str, end_date: str) -> str:
        return f"الفترة: {start_date} → {end_date} | العملة الأساسية: USD | عملة العرض: {currency.get_display_currency()}"

    def _package(self, title: str, headers: List[str], rows: List[List[Any]], start_date: str, end_date: str) -> Dict[str, Any]:
        subtitle = self._subtitle(start_date, end_date)
        html = print_service.build_table_report(title, headers, rows, subtitle=subtitle)
        safe_key = title.replace(' ', '_')
        return {
            'title': title,
            'headers': headers,
            'rows': rows,
            'subtitle': subtitle,
            'html': html,
            'default_filename': f'report_{safe_key}_{start_date}_{end_date}',
        }

    def income_statement(self, start_date: str, end_date: str) -> Dict[str, Any]:
        records = [r for r in self._approved(self._records()) if start_date <= (r.get('date') or '') <= end_date]
        total_income = sum((base_amount(r) for r in records if r.get('type') == 'incoming'), Decimal('0'))
        total_expense = sum((base_amount(r) for r in records if r.get('type') == 'outgoing'), Decimal('0'))
        net = total_income - total_expense
        rows = [
            [translate('revenues'), self._fmt(total_income)],
            [translate('expenses'), self._fmt(total_expense)],
            [translate('net'), self._fmt(net)],
        ]
        return self._package(REPORT_TYPES['income_statement'], [translate('statement'), translate('amount')], rows, start_date, end_date)

    def balance_sheet(self, start_date: str, end_date: str) -> Dict[str, Any]:
        records = [r for r in self._approved(self._records()) if (r.get('date') or '') <= end_date]
        total_income = sum((base_amount(r) for r in records if r.get('type') == 'incoming'), Decimal('0'))
        total_expense = sum((base_amount(r) for r in records if r.get('type') == 'outgoing'), Decimal('0'))
        equity = total_income - total_expense
        rows = [
            [translate('total_assets'), self._fmt(equity)],
            [translate('total_liabilities'), self._fmt(0)],
            [translate('equity'), self._fmt(equity)],
        ]
        return self._package(REPORT_TYPES['balance_sheet'], [translate('statement'), translate('amount')], rows, start_date, end_date)

    def bookings_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        records = [r for r in self._approved(self._records()) if start_date <= (r.get('date') or '') <= end_date]
        monthly = defaultdict(lambda: {'incoming': Decimal('0'), 'outgoing': Decimal('0')})
        for r in records:
            month = (r.get('date') or '')[:7]
            if not month:
                continue
            if r.get('type') == 'incoming':
                monthly[month]['incoming'] += base_amount(r)
            else:
                monthly[month]['outgoing'] += base_amount(r)
        rows = []
        for month, values in sorted(monthly.items()):
            incoming = values['incoming']
            outgoing = values['outgoing']
            rows.append([month, self._fmt(incoming), self._fmt(outgoing), self._fmt(incoming - outgoing)])
        return self._package(REPORT_TYPES['bookings_summary'], [translate('month'), translate('revenues'), translate('expenses'), translate('net')], rows, start_date, end_date)

    def customer_balances(self, start_date: str, end_date: str) -> Dict[str, Any]:
        records = [r for r in self._approved(self._records()) if (r.get('date') or '') <= end_date]
        balances = defaultdict(lambda: Decimal('0'))
        for r in records:
            company = r.get('company_name') or ''
            if not company:
                continue
            if r.get('type') == 'incoming':
                balances[company] += base_amount(r)
            else:
                balances[company] -= base_amount(r)
        rows = [[company, self._fmt(balance)] for company, balance in sorted(balances.items()) if balance != 0]
        return self._package(REPORT_TYPES['customer_balances'], [translate('company_name'), translate('amount')], rows, start_date, end_date)


report_service = ReportService()
