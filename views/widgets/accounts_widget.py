from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QHeaderView, QMessageBox, QComboBox, QDateEdit, QLabel, QDialog, QFormLayout, QDialogButtonBox
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from database import ExpenseRepository
from i18n.translator import translate
from views.custom_table_view import CustomTableView
from models.table_models import GenericTableModel
from views.dialogs.add_edit_expense_dialog import AddEditExpenseDialog
from views.dialogs.company_details_dialog import CompanyDetailsDialog
from currency import currency
from collections import defaultdict
from datetime import datetime
import webbrowser
import tempfile
import os

class AccountsWidget(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(translate('search'))
        self.search_edit.textChanged.connect(self.refresh_table)
        search_layout.addWidget(self.search_edit)
        add_btn = QPushButton("➕ " + translate('add'))
        add_btn.clicked.connect(self.add_record)
        search_layout.addWidget(add_btn)
        layout.addLayout(search_layout)

        btn_layout = QHBoxLayout()
        self.print_btn = QPushButton("🖨️ " + translate('print_report'))
        self.print_btn.clicked.connect(self.print_report)
        self.custom_report_btn = QPushButton("📊 تقرير مخصص لشركة")
        self.custom_report_btn.clicked.connect(self.show_custom_report_dialog)
        btn_layout.addWidget(self.print_btn)
        btn_layout.addWidget(self.custom_report_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = CustomTableView()
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        self.table.doubleClicked.connect(self.show_details)
        layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        repo = ExpenseRepository()
        expenses = repo.get_all(convert_to_display=False)  # amount بالدولار الثابت
        search = self.search_edit.text().strip().lower()
        groups = defaultdict(lambda: {'incoming': 0.0, 'outgoing': 0.0})
        for e in expenses:
            if search and search not in e['company_name'].lower():
                continue
            groups[e['company_name']][e['type']] += e['amount']  # بالدولار
        
        display_currency = currency.get_display_currency()
        data = []
        for company, vals in groups.items():
            incoming_display = currency.convert(vals['incoming'], 'USD', display_currency)
            outgoing_display = currency.convert(vals['outgoing'], 'USD', display_currency)
            net_display = incoming_display - outgoing_display
            data.append({
                'company': company,
                'incoming': currency.format_amount(incoming_display, display_currency),
                'outgoing': currency.format_amount(outgoing_display, display_currency),
                'net': currency.format_amount(net_display, display_currency),
                'net_raw': net_display
            })
        data.sort(key=lambda x: x['company'])
        headers = ['company', 'incoming', 'outgoing', 'net']
        display_headers = [translate('company_name'), translate('total_incoming'), translate('total_outgoing'), translate('net')]
        data_keys = ['company', 'incoming', 'outgoing', 'net']
        self.model = GenericTableModel(data, display_headers, key_fields=['company'], data_keys=data_keys)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.refresh_style()

    def add_record(self):
        dialog = AddEditExpenseDialog(self)
        if dialog.exec():
            self.refresh_table()
            self.data_changed.emit()

    def show_details(self, index):
        row = index.row()
        company = self.model.get_row(row).get('company')
        if company:
            dialog = CompanyDetailsDialog(company, self)
            dialog.exec()
            self.refresh_table()
            self.data_changed.emit()

    def apply_theme_colors(self):
        if hasattr(self, 'table'):
            self.table.refresh_style()

    def print_report(self):
        from printing.print_manager import PrintManager
        model = self.table.model()
        if not model or model.rowCount() == 0:
            QMessageBox.warning(self, translate('warning'), translate('no_data_for_print'))
            return
        headers = [model.headerData(i, Qt.Horizontal, Qt.DisplayRole) for i in range(model.columnCount())]
        data = []
        for row in range(model.rowCount()):
            row_data = []
            for col in range(model.columnCount()):
                idx = model.index(row, col)
                value = model.data(idx, Qt.DisplayRole)
                row_data.append(str(value) if value else '')
            data.append(row_data)
        html = self.generate_html_general_report("تقرير حسابات الشركات", headers, data)
        fd, temp = tempfile.mkstemp(suffix='.html', prefix='hawaa_report_')
        os.close(fd)
        with open(temp, 'w', encoding='utf-8') as f:
            f.write(html)
        webbrowser.open(f'file://{temp}')
        QMessageBox.information(self, translate('print_report'), translate('report_opened_in_browser'))

    def generate_html_general_report(self, title, headers, data):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        html = f"""<!DOCTYPE html>
<html dir="rtl">
<head><meta charset="UTF-8"><title>{title}</title>
<style>
    body {{ font-family: 'Tahoma', 'Arial', sans-serif; margin: 2cm; direction: rtl; }}
    h1 {{ text-align: center; color: #2c3e50; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
    th {{ background: #2c3e50; color: white; }}
    .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: gray; }}
</style>
</head>
<body>
<h1>{title}</h1>
<table>
<thead><tr>{"".join(f'<th>{h}</th>' for h in headers)}</thead>
<tbody>
"""
        for row in data:
            html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        html += f"""
</tbody>
</table>
<div class="footer">تاريخ الطباعة: {date_str}<br>هوى الشام للسياحة والسفر</div>
</body>
</html>"""
        return html

    def show_custom_report_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("تقرير مخصص لشركة")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(450, 300)
        layout = QVBoxLayout(dialog)

        form = QFormLayout()

        repo = ExpenseRepository()
        expenses = repo.get_all(convert_to_display=False)
        companies = sorted(set(e['company_name'] for e in expenses))
        self.company_combo = QComboBox()
        self.company_combo.addItems(companies)
        form.addRow("الشركة:", self.company_combo)

        self.period_type = QComboBox()
        self.period_type.addItems(["شهر محدد", "سنة محددة", "فترة مخصصة"])
        self.period_type.currentIndexChanged.connect(self.on_period_type_changed)
        form.addRow("الفترة:", self.period_type)

        self.year_combo = QComboBox()
        current_year = datetime.now().year
        for y in range(current_year - 5, current_year + 2):
            self.year_combo.addItem(str(y))
        form.addRow("السنة:", self.year_combo)

        self.month_combo = QComboBox()
        self.month_combo.addItems(["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                                   "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"])
        form.addRow("الشهر:", self.month_combo)

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        form.addRow("من تاريخ:", self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        form.addRow("إلى تاريخ:", self.end_date)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self.generate_company_report(dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        self.on_period_type_changed()
        dialog.exec()

    def on_period_type_changed(self):
        period = self.period_type.currentIndex()
        self.year_combo.setVisible(period in (0, 1))
        self.month_combo.setVisible(period == 0)
        self.start_date.setVisible(period == 2)
        self.end_date.setVisible(period == 2)

    def get_date_range(self):
        period = self.period_type.currentIndex()
        if period == 0:
            year = int(self.year_combo.currentText())
            month = self.month_combo.currentIndex() + 1
            start = QDate(year, month, 1)
            end = QDate(year, month, start.daysInMonth())
        elif period == 1:
            year = int(self.year_combo.currentText())
            start = QDate(year, 1, 1)
            end = QDate(year, 12, 31)
        else:
            start = self.start_date.date()
            end = self.end_date.date()
        return start.toString("yyyy-MM-dd"), end.toString("yyyy-MM-dd")

    def generate_company_report(self, dialog):
        company = self.company_combo.currentText()
        start_date, end_date = self.get_date_range()

        repo = ExpenseRepository()
        records = repo.get_by_company(company, convert_to_display=False)
        filtered = [r for r in records if start_date <= r['date'] <= end_date]
        if not filtered:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات لهذه الشركة خلال الفترة المحددة")
            return
        dialog.accept()

        display_currency = currency.get_display_currency()
        table_rows = ""
        running_usd = 0.0
        for r in filtered:
            amount_original = r['amount_original']
            currency_original = r['currency_original']
            amount_str = f"{amount_original:,.2f} {currency_original}"
            notes = r['notes'] or '—'
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
                <td class="center">{date_display}</td>
                <td class="right">{notes}</td>
                <td class="center">{incoming_str}</td>
                <td class="center">{outgoing_str}</td>
                <td class="center">{running_str}</td>
            </tr>
"""
        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><title>تقرير شركة {company}</title>
<style>
    body {{ font-family: 'Tahoma', 'Arial', sans-serif; margin: 1.5cm; direction: rtl; background: white; }}
    h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; }}
    .period-info {{ text-align: center; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; }}
    th {{ background: #2c3e50; color: white; }}
    .income-row td {{ background-color: #d4edda; }}
    .expense-row td {{ background-color: #f8d7da; }}
    .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: gray; }}
    .center {{ text-align: center; }}
    .right {{ text-align: right; }}
</style>
</head>
<body>
    <h1>📊 تقرير حسابات شركة: {company}</h1>
    <div class="period-info">الفترة: {start_date} إلى {end_date}</div>
    <table>
        <thead><tr><th>التاريخ</th><th>ملاحظات</th><th>لنا</th><th>له</th><th>التراكمي</th></tr></thead>
        <tbody>{table_rows}</tbody>
    </table>
    <div class="footer">نظام هوى الشام للسياحة والسفر<br>تاريخ الطباعة: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
</body>
</html>"""
        fd, temp = tempfile.mkstemp(suffix='.html', prefix='hawaa_report_')
        os.close(fd)
        with open(temp, 'w', encoding='utf-8') as f:
            f.write(html)
        webbrowser.open(f'file://{temp}')
        QMessageBox.information(self, "طباعة التقرير", "تم فتح التقرير في المتصفح للطباعة.")
