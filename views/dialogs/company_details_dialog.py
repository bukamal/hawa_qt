from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QHeaderView, QFileDialog
from PyQt5.QtCore import Qt
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt5.QtGui import QTextDocument, QFont
from database import ExpenseRepository
from auth.session import UserSession
from i18n.translator import translate
from views.centered_dialog import CenteredDialog
from views.custom_table_view import CustomTableView
from models.table_models import GenericTableModel
from views.dialogs.add_edit_expense_dialog import AddEditExpenseDialog
from currency import currency
from datetime import datetime
from config import get_company_info
import webbrowser
import tempfile
import os
import re

class CompanyDetailsDialog(CenteredDialog):
    def __init__(self, company_name, parent=None):
        super().__init__(parent)
        self.company_name = company_name
        self.setWindowTitle(f"تفاصيل حسابات {company_name}")
        self.resize(900, 550)
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20,20,20,20)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        self.table = CustomTableView()
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ "+translate('add'))
        add_btn.clicked.connect(self.add_record)
        edit_btn = QPushButton("✏️ "+translate('edit'))
        edit_btn.clicked.connect(self.edit_record)
        delete_btn = QPushButton("🗑 "+translate('delete'))
        delete_btn.clicked.connect(self.delete_record)
        print_btn = QPushButton("🖨️ طباعة / PDF")
        print_btn.clicked.connect(self.print_company_report)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(print_btn)
        layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        repo = ExpenseRepository()
        records = repo.get_by_company(self.company_name, convert_to_display=False)
        self.records = list(reversed(records))
        display_curr = currency.get_display_currency()
        total_in_display = 0.0
        total_out_display = 0.0
        for r in self.records:
            amt_display = currency.convert(r['amount'], 'USD', display_curr)
            if r['type'] == 'incoming':
                total_in_display += amt_display
            else:
                total_out_display += amt_display
        net_display = total_in_display - total_out_display
        self.summary_label.setText(
            f"📥 {translate('total_incoming')}: {currency.format_amount(total_in_display)}   |   "
            f"📤 {translate('total_outgoing')}: {currency.format_amount(total_out_display)}   |   "
            f"💰 {translate('net')}: {currency.format_amount(net_display)}"
        )

        data = []
        running_balance = 0.0
        for r in self.records:
            original_amount = currency.convert(r['amount'], 'USD', r['currency'])
            amount_display = currency.format_amount(original_amount, r['currency'])
            if r['currency'] == 'USD' and not amount_display.startswith('$'):
                amount_display = f"$ {amount_display}"
            type_val = r['type']
            amt_display_val = currency.convert(r['amount'], 'USD', display_curr)
            if type_val == 'incoming':
                running_balance += amt_display_val
                incoming_display = amount_display
                outgoing_display = "—"
            else:
                running_balance -= amt_display_val
                incoming_display = "—"
                outgoing_display = amount_display
            running_balance_display = currency.format_amount(running_balance, display_curr)
            data.append({
                'id': r['id'],
                'date': r['date'],
                'notes': r['notes'] or '',
                'incoming': incoming_display,
                'outgoing': outgoing_display,
                'running': running_balance_display
            })
        headers = ['date', 'notes', 'incoming', 'outgoing', 'running']
        display_headers = [translate('date'), translate('notes'), translate('incoming'), translate('outgoing'), translate('cumulative')]
        self.model = GenericTableModel(data, display_headers, key_fields=['id'], data_keys=headers)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.refresh_style()

    def add_record(self):
        dialog = AddEditExpenseDialog(self, company_name=self.company_name)
        if dialog.exec():
            self.refresh()
            if self.parent() and hasattr(self.parent(), 'refresh_table'):
                self.parent().refresh_table()

    def edit_record(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, translate('warning'), "اختر قيداً للتعديل")
            return
        row = selected[0].row()
        exp_id = self.model.get_id(row)
        if not exp_id:
            return
        repo = ExpenseRepository()
        records = repo.get_by_company(self.company_name, convert_to_display=False)
        exp = next((r for r in records if r['id'] == exp_id), None)
        if exp:
            exp['original_amount'] = currency.convert(exp['amount'], 'USD', exp['currency'])
            dialog = AddEditExpenseDialog(self, expense=exp)
            if dialog.exec():
                self.refresh()
                if self.parent() and hasattr(self.parent(), 'refresh_table'):
                    self.parent().refresh_table()

    def delete_record(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, translate('warning'), "اختر قيداً للحذف")
            return
        row = selected[0].row()
        exp_id = self.model.get_id(row)
        if not exp_id:
            return
        reply = QMessageBox.question(self, translate('confirm_delete'), translate('confirm_delete'), QMessageBox.Yes|QMessageBox.No)
        if reply == QMessageBox.Yes:
            user = UserSession.get_current()
            repo = ExpenseRepository()
            repo.delete(exp_id, user['id'] if user else None)
            self.refresh()
            if self.parent() and hasattr(self.parent(), 'refresh_table'):
                self.parent().refresh_table()

    @staticmethod
    def clean_text(text):
        if not text:
            return ''
        text = str(text)
        bad = ['\u200e', '\u200f', '\ufeff', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e', '浏', '�']
        for ch in bad:
            text = text.replace(ch, '')
        text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9\s\-\.\,\:\;\(\)\/\+%]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def generate_html_report(self):
        company_info = get_company_info()
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        display_curr = currency.get_display_currency()
        total_in = 0.0
        total_out = 0.0
        for r in self.records:
            amt = currency.convert(r['amount'], 'USD', display_curr)
            if r['type'] == 'incoming':
                total_in += amt
            else:
                total_out += amt
        net = total_in - total_out

        table_rows = ""
        running = 0.0
        for r in self.records:
            original_amount = currency.convert(r['amount'], 'USD', r['currency'])
            amount_str = currency.format_amount(original_amount, r['currency'])
            if r['currency'] == 'USD' and not amount_str.startswith('$'):
                amount_str = f"$ {amount_str}"
            amt_display_val = currency.convert(r['amount'], 'USD', display_curr)
            if r['type'] == 'incoming':
                running += amt_display_val
                incoming = amount_str
                outgoing = "—"
            else:
                running -= amt_display_val
                incoming = "—"
                outgoing = amount_str
            running_display = currency.format_amount(running, display_curr)
            notes = self.clean_text(r['notes'] or '—')
            date_display = r['date']
            row_class = "income-row" if r['type'] == 'incoming' else "expense-row"
            table_rows += f"""
            <tr class="{row_class}">
                <td class="center">{self.clean_text(running_display)}浏
                <td class="center expense">{self.clean_text(outgoing)}浏
                <td class="center income">{self.clean_text(incoming)}浏
                <td class="right">{notes}浏
                <td class="center">{self.clean_text(date_display)}浏
            </tr>
"""

        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تقرير حسابات {self.clean_text(self.company_name)}</title>
    <style>
        body {{
            font-family: 'Tahoma', 'Arial', sans-serif;
            margin: 1.5cm;
            direction: rtl;
            background: white;
            line-height: 1.4;
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
            margin-bottom: 10px;
        }}
        .company-info {{
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
            font-size: 13px;
            border: 1px solid #ddd;
            padding: 8px;
            background: #f9f9f9;
        }}
        .summary {{
            display: flex;
            justify-content: space-around;
            align-items: center;
            margin: 20px 0;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .summary-item {{
            text-align: center;
            flex: 1;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
        }}
        .summary-label {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .summary-amount {{
            font-size: 22px;
            font-weight: 800;
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .table th {{
            background: #2c3e50;
            color: white;
            padding: 10px;
            border: 1px solid #1a252f;
            text-align: center;
        }}
        .table td {{
            border: 1px solid #bdc3c7;
            padding: 8px;
        }}
        .income-row {{ background-color: #d4edda; }}
        .expense-row {{ background-color: #f8d7da; }}
        .income {{ color: #28a745; font-weight: bold; }}
        .expense {{ color: #dc3545; font-weight: bold; }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            font-size: 11px;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
            padding-top: 10px;
        }}
        .center {{ text-align: center; }}
        .right {{ text-align: right; }}
    </style>
</head>
<body>
    <h1>تفاصيل حسابات شركة: {self.clean_text(self.company_name)}</h1>
    <div class="company-info">
        <strong>{self.clean_text(company_info.get('name', 'هوى الشام للسياحة والسفر'))}</strong><br>
        {self.clean_text(company_info.get('address', ''))} | 📞 {self.clean_text(company_info.get('phone', ''))} | ✉️ {self.clean_text(company_info.get('email', ''))}
    </div>

    <div class="summary">
        <div class="summary-item">
            <div class="summary-label">صادر (له)</div>
            <div class="summary-amount" style="color:#dc3545;">{self.clean_text(currency.format_amount(total_out, display_curr))}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">وارد (لنا)</div>
            <div class="summary-amount" style="color:#28a745;">{self.clean_text(currency.format_amount(total_in, display_curr))}</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">صافي الرصيد</div>
            <div class="summary-amount" style="color:#007bff;">{self.clean_text(currency.format_amount(net, display_curr))}</div>
        </div>
    </div>

    <table class="table">
        <thead>
            <tr>
                <th>{translate('cumulative')}</th>
                <th>له (صادر)</th>
                <th>لنا (وارد)</th>
                <th>{translate('notes')}</th>
                <th>{translate('date')}</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>

    <div class="footer">
        نظام هوى الشام للسياحة والسفر<br>
        {self.clean_text(date_str)} - {self.clean_text(time_str)}
    </div>
</body>
</html>"""
        return html

    def print_company_report(self):
        if not hasattr(self, 'records') or not self.records:
            QMessageBox.warning(self, translate('warning'), translate('no_data_for_print'))
            return

        html = self.generate_html_report()
        fd, temp_html = tempfile.mkstemp(suffix='.html', prefix='hawaa_report_')
        os.close(fd)
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html)

        # فتح في المتصفح (أبسط وأضمن طريقة للعربية والتنسيق)
        webbrowser.open(f'file://{temp_html}')
        QMessageBox.information(self, translate('print_report'), translate('report_opened_in_browser'))
