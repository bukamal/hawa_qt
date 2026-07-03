# -*- coding: utf-8 -*-
"""Central HTML report builder for inline previews, printing and exports.

Reports are rendered from small HTML templates. The service never recalculates
financial values independently from CurrencyLedgerService/ReportService; it only
formats canonical rows for preview, print and export flows.
"""
from __future__ import annotations

import datetime
from html import escape
from pathlib import Path
from typing import Iterable, List, Sequence, Any, Optional, Dict

from currency import currency
from services.currency_ledger_service import currency_ledger


class PrintService:
    TEMPLATE_DIR = Path(__file__).resolve().parents[1] / 'printing' / 'templates'

    def _html(self, value: Any) -> str:
        return escape("" if value is None else str(value))

    def _load_template(self, name: str) -> str:
        path = self.TEMPLATE_DIR / name
        try:
            return path.read_text(encoding='utf-8')
        except FileNotFoundError:
            # Keep a safe fallback so packaging mistakes do not break every report.
            if name == 'base.html':
                return '<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="UTF-8"><title>{{title}}</title><style>{{style}}</style></head><body>{{body_html}}</body></html>'
            if name == 'table_report.html':
                return '<table><thead><tr>{{header_html}}</tr></thead><tbody>{{rows_html}}</tbody></table>'
            return '{{body_html}}'

    def _render(self, template_name: str, **context: Any) -> str:
        html = self._load_template(template_name)
        for key, value in context.items():
            html = html.replace('{{' + key + '}}', "" if value is None else str(value))
        return html

    def _style(self) -> str:
        return """
        :root {
            --primary: #0f766e;
            --primary-dark: #115e59;
            --accent: #f59e0b;
            --text: #111827;
            --muted: #6b7280;
            --line: #d1d5db;
            --surface: #ffffff;
            --surface-soft: #f9fafb;
            --success: #047857;
            --danger: #b91c1c;
            --warning-bg: #fffbeb;
            --warning-line: #fbbf24;
            --warning-text: #92400e;
        }
        body {
            font-family: 'Tajawal', 'Segoe UI', Tahoma, Arial, sans-serif;
            direction: rtl;
            text-align: right;
            background: var(--surface);
            color: var(--text);
            margin: 24px;
            font-size: 13px;
        }
        .report-shell { max-width: 1120px; margin: 0 auto; }
        .report-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 14px;
            margin-bottom: 16px;
            gap: 16px;
        }
        .brand-line { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
        .brand-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 38px;
            min-height: 28px;
            border-radius: 9px;
            background: var(--primary);
            color: #fff;
            font-weight: 800;
            letter-spacing: .5px;
        }
        .brand-subtitle { color: var(--muted); font-size: 12px; }
        h1 { margin: 0 0 8px 0; font-size: 24px; color: var(--text); }
        .muted { color: var(--muted); font-size: 12px; }
        .generated-box {
            color: var(--muted);
            font-size: 11px;
            border: 1px solid #e5e7eb;
            background: var(--surface-soft);
            border-radius: 10px;
            padding: 8px 10px;
            min-width: 120px;
            text-align: center;
        }
        .generated-box strong { display: block; color: var(--text); margin-top: 3px; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin: 16px 0;
        }
        .summary-card {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 12px;
            background: var(--surface-soft);
        }
        .summary-card .label { color: var(--muted); font-size: 12px; }
        .summary-card .value { font-weight: 800; font-size: 16px; margin-top: 4px; }
        .success { color: var(--success); }
        .danger { color: var(--danger); }
        .mode-note {
            background: var(--warning-bg);
            border: 1px solid var(--warning-line);
            color: var(--warning-text);
            padding: 10px 12px;
            border-radius: 10px;
            margin-bottom: 14px;
        }
        .report-meta {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            margin: 12px 0 16px;
        }
        .meta-item {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 8px 10px;
            background: var(--surface-soft);
        }
        .meta-item .label { color: var(--muted); font-size: 11px; }
        .meta-item .value { font-weight: 700; margin-top: 2px; }
        table { width: 100%; border-collapse: collapse; direction: rtl; }
        th, td { border: 1px solid var(--line); padding: 7px 8px; vertical-align: top; }
        th { background: #f3f4f6; font-weight: 800; color: #1f2937; }
        td.numeric, th.numeric { text-align: center; white-space: nowrap; }
        tr.waiting td { background: var(--warning-bg); }
        tr.total-row td { background: #ecfdf5; font-weight: 800; }
        .footer { margin-top: 18px; color: var(--muted); font-size: 11px; border-top: 1px solid #e5e7eb; padding-top: 10px; }
        @page { size: A4; margin: 1.2cm; }
        @media print {
            body { margin: 0; }
            .report-shell { max-width: none; }
            .generated-box, .summary-card, .mode-note, .meta-item { break-inside: avoid; }
            tr { break-inside: avoid; }
        }
        """

    def document(self, title: str, body_html: str, subtitle: Optional[str] = None) -> str:
        generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        subtitle_html = f'<div class="muted">{self._html(subtitle)}</div>' if subtitle else ''
        return self._render(
            'base.html',
            title=self._html(title),
            style=self._style(),
            subtitle_html=subtitle_html,
            generated_at=self._html(generated_at),
            body_html=body_html,
        )

    def build_table_report(
        self,
        title: str,
        headers: Sequence[str],
        rows: Iterable[Sequence[Any]],
        subtitle: Optional[str] = None,
        summary_html: str = '',
    ) -> str:
        head = ''.join(f'<th>{self._html(h)}</th>' for h in headers)
        body_rows: List[str] = []
        for row in rows:
            cells = ''.join(f'<td>{self._html(cell)}</td>' for cell in row)
            klass = ' class="total-row"' if row and str(row[0]) in ('الإجمالي', 'المجموع') else ''
            body_rows.append(f'<tr{klass}>{cells}</tr>')
        body = self._render('table_report.html', summary_html=summary_html, header_html=head, rows_html=''.join(body_rows))
        return self.document(title, body, subtitle=subtitle)

    def build_company_ledger_payload(self, company_name: str, records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        ledger = currency_ledger.company_ledger_display(records)
        display_currency = ledger['display_currency']
        headers = ['#', 'التاريخ', 'ملاحظات', 'لنا', 'له', 'الرصيد التراكمي', 'سعر القيد']
        rows: List[List[Any]] = []
        rows_html: List[str] = []
        for row in ledger['rows']:
            row_values = [
                row['serial'],
                row['date'],
                row['notes'],
                row['incoming'],
                row['outgoing'],
                row['running'],
                row['historical_rate'],
            ]
            rows.append(row_values)
            klass = ' class="waiting"' if row.get('status') == 'waiting_payment' else ''
            rows_html.append(
                f"<tr{klass}>"
                f"<td class='numeric'>{self._html(row['serial'])}</td>"
                f"<td class='numeric'>{self._html(row['date'])}</td>"
                f"<td>{self._html(row['notes'])}</td>"
                f"<td class='numeric'>{self._html(row['incoming'])}</td>"
                f"<td class='numeric'>{self._html(row['outgoing'])}</td>"
                f"<td class='numeric'>{self._html(row['running'])}</td>"
                f"<td class='numeric'>{self._html(row['historical_rate'])}</td>"
                f"</tr>"
            )
        header_html = ''.join(f'<th>{self._html(h)}</th>' for h in headers)
        body = self._render(
            'company_ledger.html',
            total_in=self._html(currency.format_amount(ledger['total_in_display'], display_currency)),
            total_out=self._html(currency.format_amount(ledger['total_out_display'], display_currency)),
            net=self._html(currency.format_amount(ledger['net_display'], display_currency)),
            mode_note=self._html(ledger['mode_note']),
            display_currency=self._html(display_currency),
            header_html=header_html,
            rows_html=''.join(rows_html),
        )
        title = f"كشف حساب: {company_name}"
        subtitle = "كشف شركة مع أسعار الصرف التاريخية"
        html = self.document(title, body, subtitle=subtitle)
        return {
            'title': title,
            'subtitle': subtitle,
            'headers': headers,
            'rows': rows,
            'html': html,
            'display_currency': display_currency,
            'default_filename': f"company_ledger_{company_name}",
        }

    def build_company_ledger_report(self, company_name: str, records: Iterable[Dict[str, Any]]) -> str:
        return self.build_company_ledger_payload(company_name, records)['html']


print_service = PrintService()
