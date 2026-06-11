from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QDateEdit, QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, QDate
from database import ExpenseRepository, UserRepository, AuditRepository
from currency import currency
from i18n.translator import translate
from datetime import datetime
import webbrowser
import tempfile
import os
from money import base_amount

class ReportsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # شريط التحكم بالفترة
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel(translate('period') + ":"))
        self.period_type = QComboBox()
        self.period_type.addItems(["شهر محدد", "سنة محددة", "فترة مخصصة"])
        self.period_type.currentIndexChanged.connect(self.on_period_type_changed)
        period_layout.addWidget(self.period_type)

        self.year_combo = QComboBox()
        current_year = datetime.now().year
        for y in range(current_year - 5, current_year + 2):
            self.year_combo.addItem(str(y))
        period_layout.addWidget(self.year_combo)

        self.month_combo = QComboBox()
        self.month_combo.addItems(["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                                   "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"])
        period_layout.addWidget(self.month_combo)

        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        period_layout.addWidget(self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        period_layout.addWidget(self.end_date)

        self.refresh_btn = QPushButton(translate('refresh_report'))
        self.refresh_btn.clicked.connect(self.refresh_report)
        period_layout.addWidget(self.refresh_btn)

        self.print_btn = QPushButton("🖨️ " + translate('print_report'))
        self.print_btn.clicked.connect(self.print_report)
        period_layout.addWidget(self.print_btn)

        layout.addLayout(period_layout)

        # تبويبات التقارير
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # تبويب قائمة الدخل
        self.income_tab = QWidget()
        self.income_layout = QVBoxLayout(self.income_tab)
        self.income_table = QTableWidget()
        self.income_layout.addWidget(self.income_table)
        self.tabs.addTab(self.income_tab, translate('income_statement'))

        # تبويب الميزانية العمومية
        self.balance_tab = QWidget()
        self.balance_layout = QVBoxLayout(self.balance_tab)
        self.balance_table = QTableWidget()
        self.balance_layout.addWidget(self.balance_table)
        self.tabs.addTab(self.balance_tab, translate('balance_sheet'))

        # تبويب ملخص الحجوزات
        self.bookings_tab = QWidget()
        self.bookings_layout = QVBoxLayout(self.bookings_tab)
        self.bookings_table = QTableWidget()
        self.bookings_layout.addWidget(self.bookings_table)
        self.tabs.addTab(self.bookings_tab, translate('bookings_summary'))

        # تبويب أرصدة العملاء
        self.customers_tab = QWidget()
        self.customers_layout = QVBoxLayout(self.customers_tab)
        self.customers_table = QTableWidget()
        self.customers_layout.addWidget(self.customers_table)
        self.tabs.addTab(self.customers_tab, translate('customer_balances'))

        self.on_period_type_changed()
        self.current_data = None
        self.refresh_report()

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

    def refresh_report(self):
        tab_index = self.tabs.currentIndex()
        start, end = self.get_date_range()
        if tab_index == 0:
            self.load_income_statement(start, end)
        elif tab_index == 1:
            self.load_balance_sheet(start, end)
        elif tab_index == 2:
            self.load_bookings_summary(start, end)
        elif tab_index == 3:
            self.load_customer_balances(start, end)

    def load_income_statement(self, start_date, end_date):
        repo = ExpenseRepository()
        all_expenses = repo.get_all(convert_to_display=True)
        filtered = [e for e in all_expenses if start_date <= e['date'] <= end_date]
        total_income = sum(base_amount(e) for e in filtered if e['type'] == 'incoming')
        total_expense = sum(base_amount(e) for e in filtered if e['type'] == 'outgoing')
        net = total_income - total_expense
        data = [
            [translate('revenues'), currency.format_amount(total_income)],
            [translate('expenses'), currency.format_amount(total_expense)],
            [translate('net'), currency.format_amount(net)]
        ]
        self.display_table(data, [translate('statement'), translate('amount')], self.income_table)

    def load_balance_sheet(self, start_date, end_date):
        repo = ExpenseRepository()
        all_expenses = repo.get_all(convert_to_display=True)
        filtered = [e for e in all_expenses if e['date'] <= end_date]
        total_income = sum(base_amount(e) for e in filtered if e['type'] == 'incoming')
        total_expense = sum(base_amount(e) for e in filtered if e['type'] == 'outgoing')
        equity = total_income - total_expense
        data = [
            [translate('total_assets'), currency.format_amount(equity)],
            [translate('total_liabilities'), currency.format_amount(0)],
            [translate('equity'), currency.format_amount(equity)]
        ]
        self.display_table(data, [translate('statement'), translate('amount')], self.balance_table)

    def load_bookings_summary(self, start_date, end_date):
        repo = ExpenseRepository()
        all_expenses = repo.get_all(convert_to_display=True)
        filtered = [e for e in all_expenses if start_date <= e['date'] <= end_date]
        monthly = {}
        for e in filtered:
            month = e['date'][:7]
            if month not in monthly:
                monthly[month] = {'incoming': 0, 'outgoing': 0}
            if e['type'] == 'incoming':
                monthly[month]['incoming'] += base_amount(e)
            else:
                monthly[month]['outgoing'] += base_amount(e)
        data = []
        for m, val in sorted(monthly.items()):
            data.append([m, currency.format_amount(val['incoming']), currency.format_amount(val['outgoing']), currency.format_amount(val['incoming'] - val['outgoing'])])
        self.display_table(data, [translate('month'), translate('revenues'), translate('expenses'), translate('net')], self.bookings_table)

    def load_customer_balances(self, start_date, end_date):
        repo = ExpenseRepository()
        all_expenses = repo.get_all(convert_to_display=True)
        filtered = [e for e in all_expenses if e['date'] <= end_date]
        company_balances = {}
        for e in filtered:
            company = e['company_name']
            if company not in company_balances:
                company_balances[company] = 0
            if e['type'] == 'incoming':
                company_balances[company] += base_amount(e)
            else:
                company_balances[company] -= base_amount(e)
        data = [[c, currency.format_amount(b)] for c, b in company_balances.items() if b != 0]
        data.sort(key=lambda x: x[0])
        self.display_table(data, [translate('company_name'), translate('amount')], self.customers_table)

    def display_table(self, data, headers, table_widget):
        table_widget.clear()
        table_widget.setRowCount(len(data))
        table_widget.setColumnCount(len(headers))
        table_widget.setHorizontalHeaderLabels(headers)
        for row, row_data in enumerate(data):
            for col, val in enumerate(row_data):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                table_widget.setItem(row, col, item)
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def generate_html_report(self):
        tab_index = self.tabs.currentIndex()
        start, end = self.get_date_range()
        title = self.tabs.tabText(tab_index)
        if tab_index == 0:
            self.load_income_statement(start, end)
            data = []
            for row in range(self.income_table.rowCount()):
                data.append([self.income_table.item(row, 0).text(), self.income_table.item(row, 1).text()])
            headers = [translate('statement'), translate('amount')]
        elif tab_index == 1:
            self.load_balance_sheet(start, end)
            data = []
            for row in range(self.balance_table.rowCount()):
                data.append([self.balance_table.item(row, 0).text(), self.balance_table.item(row, 1).text()])
            headers = [translate('statement'), translate('amount')]
        elif tab_index == 2:
            self.load_bookings_summary(start, end)
            data = []
            for row in range(self.bookings_table.rowCount()):
                data.append([self.bookings_table.item(row, c).text() for c in range(self.bookings_table.columnCount())])
            headers = [translate('month'), translate('revenues'), translate('expenses'), translate('net')]
        else:
            self.load_customer_balances(start, end)
            data = []
            for row in range(self.customers_table.rowCount()):
                data.append([self.customers_table.item(row, 0).text(), self.customers_table.item(row, 1).text()])
            headers = [translate('company_name'), translate('amount')]

        now = datetime.now()
        html = f"""<!DOCTYPE html>
<html dir="rtl">
<head><meta charset="UTF-8"><title>{title}</title>
<style>
    body {{ font-family: 'Tahoma', 'Arial', sans-serif; margin: 2cm; direction: rtl; }}
    h1 {{ text-align: center; color: #2c3e50; }}
    .info {{ text-align: center; margin-bottom: 20px; color: gray; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
    th {{ background: #2c3e50; color: white; }}
    .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: gray; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="info">{translate('period')}: {start} → {end}</div>
<table>
<thead><tr>{"".join(f'<th>{h}</th>' for h in headers)}</tr></thead>
<tbody>
"""
        for row in data:
            html += "<td>" + "".join(f"一位{cell}一位" for cell in row) + "</tr>"
        html += f"""
</tbody>
</table>
<div class="footer">{translate('print_date')}: {now.strftime('%Y-%m-%d %H:%M:%S')}<br>هوى الشام للسياحة والسفر</div>
</body>
</html>"""
        return html

    def print_report(self):
        html = self.generate_html_report()
        fd, temp = tempfile.mkstemp(suffix='.html', prefix='hawaa_report_')
        os.close(fd)
        with open(temp, 'w', encoding='utf-8') as f:
            f.write(html)
        webbrowser.open(f'file://{temp}')
        QMessageBox.information(self, translate('print_report'), translate('report_opened_in_browser'))
