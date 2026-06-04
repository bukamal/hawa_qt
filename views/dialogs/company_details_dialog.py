from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QHeaderView, QFileDialog
from PyQt5.QtCore import Qt
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
        super().__init__(parent=parent)
        self.company_name = company_name
        self.setWindowTitle(f"تفاصيل حسابات {company_name}")
        self.resize(1000, 600)
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20,20,20,20)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        self.table = CustomTableView()
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        
        is_viewer = UserSession.get_current().get('role') == 'viewer'
        
        self.add_btn = QPushButton("➕ "+translate('add'))
        self.add_btn.clicked.connect(self.add_record)
        self.add_btn.setVisible(not is_viewer)
        
        self.edit_btn = QPushButton("✏️ "+translate('edit'))
        self.edit_btn.clicked.connect(self.edit_record)
        self.edit_btn.setVisible(not is_viewer)
        
        self.delete_btn = QPushButton("🗑 "+translate('delete'))
        self.delete_btn.clicked.connect(self.delete_record)
        self.delete_btn.setVisible(not is_viewer)
        
        self.print_btn = QPushButton("🖨️ طباعة / معاينة")
        self.print_btn.clicked.connect(self.print_company_report)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.print_btn)
        layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        repo = ExpenseRepository()
        records = repo.get_by_company(self.company_name, convert_to_display=False)
        self.records = sorted(records, key=lambda x: x['date'])
        display_currency = currency.get_display_currency()

        total_in_usd = sum(r['amount'] for r in self.records if r['type'] == 'incoming')
        total_out_usd = sum(r['amount'] for r in self.records if r['type'] == 'outgoing')
        net_usd = total_in_usd - total_out_usd
        
        total_in_display = currency.convert(total_in_usd, 'USD', display_currency)
        total_out_display = currency.convert(total_out_usd, 'USD', display_currency)
        net_display = currency.convert(net_usd, 'USD', display_currency)
        
        self.summary_label.setText(
            f"📥 إجمالي وارد: {currency.format_amount(total_in_display, display_currency)}   |   "
            f"📤 إجمالي صادر: {currency.format_amount(total_out_display, display_currency)}   |   "
            f"💰 صافي: {currency.format_amount(net_display, display_currency)}"
        )

        data = []
        running_usd = 0.0
        for idx, r in enumerate(self.records, start=1):
            amount_original = r['amount_original']
            currency_original = r['currency_original']
            amount_str = f"{amount_original:,.2f} {currency_original}"
            
            if r['type'] == 'incoming':
                incoming_str = amount_str
                outgoing_str = "—"
                running_usd += r['amount']
            else:
                incoming_str = "—"
                outgoing_str = amount_str
                running_usd -= r['amount']
            
            running_display = currency.convert(running_usd, 'USD', display_currency)
            running_str = currency.format_amount(running_display, display_currency)
            
            data.append({
                'id': r['id'],
                'serial': idx,
                'date': r['date'],
                'notes': r['notes'] or '',
                'incoming': incoming_str,
                'outgoing': outgoing_str,
                'running': running_str
            })
        
        headers = ['serial', 'date', 'notes', 'incoming', 'outgoing', 'running']
        display_headers = ['#', translate('date'), translate('notes'), 'لنا', 'له', translate('cumulative')]
        data_keys = ['serial', 'date', 'notes', 'incoming', 'outgoing', 'running']
        
        self.model = GenericTableModel(data, display_headers, key_fields=['id'], data_keys=data_keys)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnHidden(0, True)
        self.table.refresh_style()

    def add_record(self):
        if UserSession.get_current().get('role') == 'viewer':
            QMessageBox.warning(self, translate('warning'), "ليس لديك صلاحية لإضافة قيود")
            return
        dialog = AddEditExpenseDialog(self, company_name=self.company_name)
        if dialog.exec():
            self.refresh()
            if self.parent() and hasattr(self.parent(), 'refresh_table'):
                self.parent().refresh_table()

    def edit_record(self):
        if UserSession.get_current().get('role') == 'viewer':
            QMessageBox.warning(self, translate('warning'), "ليس لديك صلاحية لتعديل القيود")
            return
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
            dialog = AddEditExpenseDialog(self, expense=exp)
            if dialog.exec():
                self.refresh()
                if self.parent() and hasattr(self.parent(), 'refresh_table'):
                    self.parent().refresh_table()

    def delete_record(self):
        if UserSession.get_current().get('role') == 'viewer':
            QMessageBox.warning(self, translate('warning'), "ليس لديك صلاحية لحذف القيود")
            return
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
        bad = ['\u200e', '\u200f', '\ufeff', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e', '浏', '']
        for ch in bad:
            text = text.replace(ch, '')
        text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9\s\-\.\,\:\;\(\)\/\+%\$]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def generate_html_report(self):
        company_info = get_company_info()
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        display_currency = currency.get_display_currency()
        
        running_usd = 0.0
        table_rows = ""
        for idx, r in enumerate(self.records, start=1):
            amount_original = r['amount_original']
            currency_original = r['currency_original']
            amount_str = f"{amount_original:,.2f} {currency_original}"
            notes = self.clean_text(r['notes'] or '—')
            date_display = r['date']
            
            if r['type'] == 'incoming':
                incoming_str = amount_str
                outgoing_str = "—"
                running_usd += r['amount']
            else:
                incoming_str = "—"
                outgoing_str = amount_str
                running_usd -= r['amount']
            
            running_display = currency.convert(running_usd, 'USD', display_currency)
            running_str = currency.format_amount(running_display, display_currency)
            row_class = "income-row" if r['type'] == 'incoming' else "expense-row"
            
            table_rows += f"""
            <tr class="{row_class}">
                <td class="center">{idx}</td>
                <td class="center">{self.clean_text(date_display)}</td>
                <td class="right">{notes}</td>
                <td class="center income">{self.clean_text(incoming_str)}</td>
                <td class="center expense">{self.clean_text(outgoing_str)}</td>
                <td class="center">{self.clean_text(running_str)}</td>
             </tr>
"""
        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><title>تقرير حسابات {self.clean_text(self.company_name)}</title>
<style>
    body {{ font-family: 'Tahoma', 'Arial', sans-serif; margin: 1.5cm; direction: rtl; background: white; }}
    h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 8px; }}
    .company-info {{ text-align: center; margin-bottom: 20px; color: #2c3e50; border: 1px solid #ddd; padding: 8px; background: #f9f9f9; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th {{ background: #2c3e50; color: white; padding: 10px; border: 1px solid #1a252f; text-align: center; }}
    td {{ border: 1px solid #bdc3c7; padding: 8px; }}
    .income-row td {{ background-color: #d4edda; }}
    .expense-row td {{ background-color: #f8d7da; }}
    .income {{ color: #28a745; font-weight: bold; }}
    .expense {{ color: #dc3545; font-weight: bold; }}
    .footer {{ text-align: center; margin-top: 30px; font-size: 11px; color: #6c757d; border-top: 1px solid #dee2e6; padding-top: 10px; }}
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
    <table class="data-table">
        <thead><tr><th>#</th><th>{translate('date')}</th><th>{translate('notes')}</th><th>لنا</th><th>له</th><th>{translate('cumulative')}</th></tr></thead>
        <tbody>{table_rows}</tbody>
    </table>
    <div class="footer">نظام هوى الشام للسياحة والسفر<br>{self.clean_text(date_str)} - {self.clean_text(time_str)}</div>
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
        webbrowser.open(f'file://{temp_html}')
        QMessageBox.information(self, translate('print_report'), translate('report_opened_in_browser'))
