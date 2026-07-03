# -*- coding: utf-8 -*-
"""Accounts summary service used by the Document Shell.

The accounts page should not calculate balances inside PyQt widgets. This service
returns one canonical company-summary view built from amount_base (USD) and the
selected Display Currency. Historical exchange-rate snapshots stay untouched.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from currency import currency
from database import ExpenseRepository
from money import base_amount
from services.currency_ledger_service import currency_ledger
from services.print_service import print_service


class AccountsService:
    def __init__(self, repo: Optional[ExpenseRepository] = None):
        self._repo = repo

    @property
    def repo(self):
        return self._repo or ExpenseRepository()

    def records(self) -> List[Dict[str, Any]]:
        return [currency_ledger.normalize_record(dict(r)) for r in self.repo.get_all(convert_to_display=False)]

    def company_summaries(self, search: str = "") -> Dict[str, Any]:
        query = (search or "").strip().lower()
        display_currency = currency.get_display_currency()
        groups = defaultdict(lambda: {
            "incoming_base": Decimal("0"),
            "outgoing_base": Decimal("0"),
            "approved_records": [],
            "waiting_payment": 0,
            "overdue": 0,
        })
        today = date.today().isoformat()

        for record in self.records():
            company_name = record.get("company_name") or ""
            if not company_name:
                continue
            if query and query not in company_name.lower():
                continue

            status = record.get("status", "approved")
            if status == "waiting_payment":
                groups[company_name]["waiting_payment"] += 1
                due = record.get("payment_due_date")
                if due and due < today:
                    groups[company_name]["overdue"] += 1
                continue
            if status != "approved":
                continue

            if record.get("type") == "incoming":
                groups[company_name]["incoming_base"] += base_amount(record)
            else:
                groups[company_name]["outgoing_base"] += base_amount(record)
            groups[company_name]["approved_records"].append(record)

        rows = []
        total_in_base = Decimal("0")
        total_out_base = Decimal("0")
        for company_name, values in groups.items():
            incoming, outgoing, net, row_currency = currency_ledger.company_summary_display_values(
                values["approved_records"],
                values["incoming_base"],
                values["outgoing_base"],
                display_currency,
            )
            total_in_base += values["incoming_base"]
            total_out_base += values["outgoing_base"]
            rows.append({
                "company": company_name,
                "incoming": currency.format_amount(incoming, row_currency),
                "outgoing": currency.format_amount(outgoing, row_currency),
                "net": currency.format_amount(net, row_currency),
                "payment_status": self._payment_status(values),
                "row_currency": row_currency,
                "incoming_base": values["incoming_base"],
                "outgoing_base": values["outgoing_base"],
                "net_base": values["incoming_base"] - values["outgoing_base"],
                "waiting_payment": values["waiting_payment"],
                "overdue": values["overdue"],
            })

        rows.sort(key=lambda item: item["company"])
        total_in_display = currency_ledger.convert_base_to_display(total_in_base, display_currency)
        total_out_display = currency_ledger.convert_base_to_display(total_out_base, display_currency)
        return {
            "display_currency": display_currency,
            "base_currency": "USD",
            "rows": rows,
            "total_incoming": currency.format_amount(total_in_display, display_currency),
            "total_outgoing": currency.format_amount(total_out_display, display_currency),
            "net": currency.format_amount(total_in_display - total_out_display, display_currency),
            "companies_count": len(rows),
            "waiting_payment_count": sum(r["waiting_payment"] for r in rows),
            "overdue_count": sum(r["overdue"] for r in rows),
            "subtitle": f"الأساس: USD | العرض: {display_currency}",
            "historical_note": "لا يتم إعادة تسعير القيود التاريخية",
        }

    def build_summary_report(self, search: str = "") -> Dict[str, Any]:
        summary = self.company_summaries(search)
        headers = ["الشركة", "إجمالي الوارد", "إجمالي الصادر", "الصافي", "تنبيهات الدفع"]
        rows = [[
            row["company"], row["incoming"], row["outgoing"], row["net"], row["payment_status"]
        ] for row in summary["rows"]]
        rows.append(["الإجمالي", summary["total_incoming"], summary["total_outgoing"], summary["net"], "—"])
        html = print_service.build_table_report("تقرير إجماليات الشركات", headers, rows, subtitle=summary["subtitle"])
        return {"headers": headers, "rows": rows, "html": html, "default_filename": "accounts_summary", **summary}

    @staticmethod
    def _payment_status(values: Dict[str, Any]) -> str:
        waiting = int(values.get("waiting_payment", 0) or 0)
        overdue = int(values.get("overdue", 0) or 0)
        if overdue:
            return f"⚠️ {overdue} متأخر / ⏳ {waiting} بانتظار الدفع"
        if waiting:
            return f"⏳ {waiting} بانتظار الدفع"
        return "—"


accounts_service = AccountsService()
