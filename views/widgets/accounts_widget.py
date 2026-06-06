from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QHeaderView,
    QMessageBox, QComboBox, QDateEdit, QLabel, QDialog, QFormLayout,
    QDialogButtonBox, QRadioButton, QButtonGroup, QCheckBox, QGroupBox,
    QSpinBox
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from database import ExpenseRepository
from i18n.translator import translate
from views.custom_table_view import CustomTableView
from models.table_models import GenericTableModel
from views.dialogs.add_edit_expense_dialog import AddEditExpenseDialog
from views.dialogs.company_details_dialog import CompanyDetailsDialog
from currency import currency
from auth.session import UserSession
from config import get_company_info
from collections import defaultdict
from datetime import datetime
import webbrowser
import tempfile
import os
import re

# ------------------- حوار خيارات الطباعة -------------------
class PrintOptionsDialog(QDialog):
    # ... (نفس الكود السابق، لا تغيير)
    pass

# ------------------- AccountsWidget -------------------
class AccountsWidget(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        # ... (الكود السابق كما هو، لا تغيير)
        pass

    # ... باقي الدوال (refresh_table, add_record, show_details, apply_theme_colors, clean_text) كما هي
    # سأعرض فقط الدوال المعدلة: print_report, generate_html_report

    def print_report(self):
        if self.table.model().rowCount() == 0:
            QMessageBox.warning(self, translate('warning'), translate('no_data_for_print'))
            return
        dialog = PrintOptionsDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        settings = dialog.get_settings()
        html = self.generate_html_report(settings)
        fd, temp = tempfile.mkstemp(suffix='.html', prefix='hawaa_report_')
        os.close(fd)
        with open(temp, 'w', encoding='utf-8') as f:
            f.write(html)
        webbrowser.open(f'file://{temp}')
        QMessageBox.information(self, translate('print_report'), translate('report_opened_in_browser'))

    def generate_html_report(self, settings):
        repo = ExpenseRepository()
        try:
            expenses = repo.get_all(convert_to_display=False)
        except Exception as e:
            return "<html><body>خطأ في تحميل البيانات</body></html>"

        groups = defaultdict(lambda: {'incoming': 0.0, 'outgoing': 0.0})
        for e in expenses:
            groups[e['company_name']][e['type']] += e['amount']

        display_currency = currency.get_display_currency()
        decimals = currency.get_currency_decimals()
        symbol = currency.get_currency_symbol(display_currency)

        def format_full(amount):
            return f"{amount:,.{decimals}f} {symbol}"

        data_rows = []
        total_in_all = 0.0
        total_out_all = 0.0
        for company, vals in groups.items():
            incoming = currency.convert(vals['incoming'], 'USD', display_currency)
            outgoing = currency.convert(vals['outgoing'], 'USD', display_currency)
            net = incoming - outgoing
            total_in_all += incoming
            total_out_all += outgoing
            data_rows.append((company, incoming, outgoing, net, net))
        data_rows.sort(key=lambda x: x[0])

        total_net = total_in_all - total_out_all

        # إعدادات الطباعة
        show_company_name = settings.get('show_company_name', True)
        show_address = settings.get('show_address', True)
        custom_title = settings.get('custom_title', '')
        colorize_rows = settings.get('colorize_rows', True)
        colorize_numbers = settings.get('colorize_numbers', True)
        show_row_numbers = settings.get('show_row_numbers', True)
        font_size = settings.get('font_size', 10)
        show_datetime = settings.get('show_datetime', True)
        show_printed_by = settings.get('show_printed_by', True)
        footer_note = settings.get('footer_note', '')

        company_info = get_company_info()
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # بناء الترويسة
        header_html = ""
        if show_company_name:
            header_html += f"<strong>{self.clean_text(company_info.get('name', 'هوى الشام للسياحة والسفر'))}</strong><br>"
        if show_address:
            header_html += f"{self.clean_text(company_info.get('address', ''))} | 📞 {self.clean_text(company_info.get('phone', ''))} | ✉️ {self.clean_text(company_info.get('email', ''))}<br>"

        # بناء الجدول (طريقة مبسطة وآمنة)
        # سنستخدم قائمة لتجميع الصفوف ثم نربطها بسطر واحد
        table_rows = []
        for idx, (company, inc, out, net, net_val) in enumerate(data_rows, start=1):
            inc_formatted = format_full(inc)
            out_formatted = format_full(out)
            net_formatted = format_full(net)

            row_class = ""
            if colorize_rows:
                row_class = "income-row" if net_val >= 0 else "expense-row"

            # تلوين الأرقام
            net_class = ("income" if net_val >= 0 else "expense") if colorize_numbers else ""
            inc_class = "income" if colorize_numbers else ""
            out_class = "expense" if colorize_numbers else ""

            # بناء الخلايا بشكل بسيط
            cells = []
            if show_row_numbers:
                cells.append(f'<td>{idx}</td>')
            cells.append(f'<td>{self.clean_text(company)}</td>')
            cells.append(f'<td class="{inc_class}">{self.clean_text(inc_formatted)}</td>')
            cells.append(f'<td class="{out_class}">{self.clean_text(out_formatted)}</td>')
            cells.append(f'<td class="{net_class}">{self.clean_text(net_formatted)}</td>')

            # إزالة class إذا كانت فارغة
            row_attrs = f' class="{row_class}"' if row_class else ''
            row_html = f'<tr{row_attrs}>' + "".join(cells) + '</tr>'
            table_rows.append(row_html)

        # صف الإجمالي
        total_cells = []
        if show_row_numbers:
            total_cells.append('<td>—</td>')
        total_cells.append('<td><strong>الإجمالي الكلي</strong></td>')
        total_cells.append(f'<td class="income"><strong>{format_full(total_in_all)}</strong></td>')
        total_cells.append(f'<td class="expense"><strong>{format_full(total_out_all)}</strong></td>')
        total_cells.append(f'<td><strong>{format_full(total_net)}</strong></td>')
        total_row_html = '<tr class="total-row">' + "".join(total_cells) + '</tr>'
        table_rows.append(total_row_html)

        # بناء التذييل
        footer_text = ""
        if show_printed_by:
            user = UserSession.get_current()
            footer_text += f"طبع بواسطة: {user.get('username', '')} | "
        if show_datetime:
            footer_text += f"تاريخ الطباعة: {date_str} {time_str}"
        if footer_note:
            footer_text += f"<br>{self.clean_text(footer_note)}"

        # رؤوس الأعمدة
        headers = []
        if show_row_numbers:
            headers.append('#')
        headers.extend([translate('company_name'), translate('total_incoming'), translate('total_outgoing'), translate('net')])

        # بناء HTML
        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>تقرير حسابات الشركات</title>
    <style>
        body {{
            font-family: 'Tajawal', 'Segoe UI', Tahoma, Arial;
            margin: 1.5cm;
            direction: rtl;
            background: white;
            font-size: {font_size}pt;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
        }}
        .company-info {{
            text-align: center;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            padding: 8px;
            background: #f9f9f9;
        }}
        .summary {{
            text-align: center;
            margin: 20px 0;
            font-size: 16px;
            font-weight: bold;
            background: #e9ecef;
            padding: 10px;
            border-radius: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: right;   /* محاذاة اليمين لجميع الخلايا */
        }}
        th {{
            background-color: #2c3e50;
            color: white;
            font-weight: bold;
        }}
        .income-row td {{
            background-color: #d4edda;
        }}
        .expense-row td {{
            background-color: #f8d7da;
        }}
        .income {{
            color: #28a745;
            font-weight: bold;
        }}
        .expense {{
            color: #dc3545;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            font-size: 11px;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
            padding-top: 10px;
        }}
    </style>
</head>
<body>
    <h1>{' - '.join(filter(None, ['تقرير حسابات الشركات', custom_title]))}</h1>
    <div class="company-info">{header_html}</div>
    <div class="summary">
        📥 إجمالي وارد: {format_full(total_in_all)} &nbsp;|&nbsp;
        📤 إجمالي صادر: {format_full(total_out_all)} &nbsp;|&nbsp;
        💰 صافي الكلي: {format_full(total_net)}
    </div>
    <table>
        <thead>
            <tr>{''.join(f'<th>{h}</th>' for h in headers)}</thead>
        <tbody>
            {''.join(table_rows)}
        </tbody>
    </table>
    <div class="footer">{footer_text}</div>
</body>
</html>"""
        return html

    # ------------------- دوال التقرير المخصص (لا تغيير) -------------------
    def show_custom_report_dialog(self):
        # ... كما هي
        pass

    def generate_company_report(self, dialog):
        # ... كما هي، لم يتم تعديلها
        pass

    def on_period_type_changed(self):
        pass

    def get_date_range(self):
        pass
