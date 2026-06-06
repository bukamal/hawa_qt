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
    """حوار بسيط لخيارات طباعة تقرير إجماليات الشركات"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("خيارات الطباعة")
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(450, 550)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # ----- الترويسة -----
        header_group = QGroupBox("الترويسة")
        header_layout = QFormLayout(header_group)
        header_layout.setLabelAlignment(Qt.AlignRight)
        self.show_company_name = QCheckBox("إظهار اسم الشركة")
        self.show_company_name.setChecked(True)
        self.show_address = QCheckBox("إظهار العنوان والهاتف والبريد")
        self.show_address.setChecked(True)
        self.show_logo = QCheckBox("إظهار الشعار (إن وجد)")
        self.show_logo.setChecked(True)
        self.custom_title = QLineEdit()
        self.custom_title.setPlaceholderText("عنوان إضافي للتقرير (اختياري)")
        header_layout.addRow(self.show_company_name)
        header_layout.addRow(self.show_address)
        header_layout.addRow(self.show_logo)
        header_layout.addRow("عنوان إضافي:", self.custom_title)
        layout.addWidget(header_group)

        # ----- الجدول -----
        table_group = QGroupBox("الجدول")
        table_layout = QFormLayout(table_group)
        table_layout.setLabelAlignment(Qt.AlignRight)
        self.colorize_rows = QCheckBox("تلوين الصفوف (أخضر للموجب، أحمر للسالب)")
        self.colorize_rows.setChecked(True)
        self.colorize_numbers = QCheckBox("تلوين الأرقام (أخضر/أحمر)")
        self.colorize_numbers.setChecked(True)
        self.show_row_numbers = QCheckBox("إظهار عمود # (ترقيم الصفوف)")
        self.show_row_numbers.setChecked(True)
        table_layout.addRow(self.colorize_rows)
        table_layout.addRow(self.colorize_numbers)
        table_layout.addRow(self.show_row_numbers)
        layout.addWidget(table_group)

        # ----- التنسيق -----
        style_group = QGroupBox("التنسيق")
        style_layout = QFormLayout(style_group)
        style_layout.setLabelAlignment(Qt.AlignRight)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 20)
        self.font_size.setValue(10)
        style_layout.addRow("حجم الخط (pt):", self.font_size)
        layout.addWidget(style_group)

        # ----- التذييل -----
        footer_group = QGroupBox("التذييل")
        footer_layout = QFormLayout(footer_group)
        footer_layout.setLabelAlignment(Qt.AlignRight)
        self.show_datetime = QCheckBox("إظهار تاريخ ووقت الطباعة")
        self.show_datetime.setChecked(True)
        self.show_printed_by = QCheckBox("إظهار اسم المستخدم الطابع")
        self.show_printed_by.setChecked(True)
        self.footer_note = QLineEdit()
        self.footer_note.setPlaceholderText("ملاحظة ختامية (اختياري)")
        footer_layout.addRow(self.show_datetime)
        footer_layout.addRow(self.show_printed_by)
        footer_layout.addRow("ملاحظة:", self.footer_note)
        layout.addWidget(footer_group)

        # ----- أزرار -----
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        btn_box.button(QDialogButtonBox.Ok).setText("طباعة")
        btn_box.button(QDialogButtonBox.Cancel).setText("إلغاء")
        layout.addWidget(btn_box)

    def get_settings(self):
        return {
            'show_company_name': self.show_company_name.isChecked(),
            'show_address': self.show_address.isChecked(),
            'show_logo': self.show_logo.isChecked(),
            'custom_title': self.custom_title.text(),
            'colorize_rows': self.colorize_rows.isChecked(),
            'colorize_numbers': self.colorize_numbers.isChecked(),
            'show_row_numbers': self.show_row_numbers.isChecked(),
            'font_size': self.font_size.value(),
            'show_datetime': self.show_datetime.isChecked(),
            'show_printed_by': self.show_printed_by.isChecked(),
            'footer_note': self.footer_note.text(),
        }


# ------------------- AccountsWidget -------------------
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

        self.add_btn = QPushButton("➕ " + translate('add'))
        self.add_btn.clicked.connect(self.add_record)
        if not UserSession.is_admin() and UserSession.get_current().get('role') == 'viewer':
            self.add_btn.setVisible(False)
        search_layout.addWidget(self.add_btn)
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
        try:
            expenses = repo.get_all(convert_to_display=False)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل البيانات: {str(e)}")
            return
        search = self.search_edit.text().strip().lower()
        groups = defaultdict(lambda: {'incoming': 0.0, 'outgoing': 0.0})
        for e in expenses:
            if search and search not in e['company_name'].lower():
                continue
            groups[e['company_name']][e['type']] += e['amount']

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
        if UserSession.get_current().get('role') == 'viewer':
            QMessageBox.warning(self, translate('warning'), "ليس لديك صلاحية لإضافة قيود")
            return
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

    def print_report(self):
        """طباعة تقرير إجماليات الشركات مع حوار خيارات"""
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
        """توليد HTML للتقرير مع تطبيق إعدادات الطباعة"""
        # الحصول على البيانات الأصلية
        repo = ExpenseRepository()
        try:
            expenses = repo.get_all(convert_to_display=False)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل البيانات: {str(e)}")
            return ""

        # تجميع البيانات
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
            data_rows.append([company, incoming, outgoing, net, net])
        data_rows.sort(key=lambda x: x[0])

        total_net = total_in_all - total_out_all

        # تطبيق الإعدادات
        show_company_name = settings.get('show_company_name', True)
        show_address = settings.get('show_address', True)
        show_logo = settings.get('show_logo', True)
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
        if show_logo and company_info.get('logo_path') and os.path.exists(company_info['logo_path']):
            # يمكن إضافة الشعار لاحقاً
            pass

        # بناء الجدول - ✅ تصحيح: <table> بدلاً من 一位
        table_rows = ""
        for idx, row in enumerate(data_rows, start=1):
            net_val = row[4]
            row_class = ""
            if colorize_rows:
                row_class = "income-row" if net_val >= 0 else "expense-row"
            # تلوين الأرقام
            net_class = ""
            if colorize_numbers:
                net_class = "income" if net_val >= 0 else "expense"
            incoming_class = "income" if colorize_numbers else ""
            outgoing_class = "expense" if colorize_numbers else ""

            # عمود الترقيم
            num_col = f'<td class="center">{idx}</td>' if show_row_numbers else ''

            # ✅ تصحيح: إغلاق الصف بـ </table> بدلاً من </table>
            table_rows += f"""
            <tr class="{row_class}">
                {num_col}
                <td class="center">{self.clean_text(row[0])}</td>
                <td class="center {incoming_class}">{self.clean_text(format_full(row[1]))}</td>
                <td class="center {outgoing_class}">{self.clean_text(format_full(row[2]))}</td>
                <td class="center {net_class}">{self.clean_text(format_full(row[3]))}</td>
            </tr>"""

        # بناء التذييل
        footer_text = ""
        if show_printed_by:
            user = UserSession.get_current()
            footer_text += f"طبع بواسطة: {user.get('username', '')} | "
        if show_datetime:
            footer_text += f"تاريخ الطباعة: {date_str} {time_str}"
        if footer_note:
            footer_text += f"<br>{self.clean_text(footer_note)}"

        # تحديد رؤوس الأعمدة
        headers = []
        if show_row_numbers:
            headers.append('#')
        headers.extend([translate('company_name'), translate('total_incoming'), translate('total_outgoing'), translate('net')])

        # ✅ تصحيح: إغلاق صف الإجمالي الكلي بـ </tr> بدلاً من </tr>
        # ✅ تصحيح: توسيط عمود اسم الشركة (class="center" بدلاً من class="right")
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
            color: #2c3e50;
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
            text-align: center;
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
        .center {{ text-align: center; }}
        .right {{ text-align: right; }}
        /* ✅ توسيط إجباري لجميع خلايا الجدول */
        table td {{
            text-align: center !important;
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
            <tr>{"".join(f'<th>{h}</th>' for h in headers)}</thead>
        <tbody>
            {table_rows}
            <tr class="total-row">
                {('<td class="center">—</td>' if show_row_numbers else '')}
                <td class="center"><strong>الإجمالي الكلي</strong></td>
                <td class="center income"><strong>{format_full(total_in_all)}</strong></td>
                <td class="center expense"><strong>{format_full(total_out_all)}</strong></td>
                <td class="center"><strong>{format_full(total_net)}</strong></td>
            </tr>
        </tbody>
    </table>
    <div class="footer">{footer_text}</div>
</body>
</html>"""
        return html

    # ------------------- باقي الدوال (التقرير المخصص) -------------------
    def show_custom_report_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("تقرير مخصص لشركة")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(500, 400)
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

        # خيارات التقرير
        self.report_type_group = QButtonGroup()
        self.radio_period = QRadioButton("تقرير فترة (Period)")
        self.radio_cumulative = QRadioButton("تقرير تراكمي (Cumulative)")
        self.radio_period.setChecked(True)
        self.report_type_group.addButton(self.radio_period)
        self.report_type_group.addButton(self.radio_cumulative)
        report_layout = QHBoxLayout()
        report_layout.addWidget(self.radio_period)
        report_layout.addWidget(self.radio_cumulative)
        form.addRow("نوع التقرير:", report_layout)

        self.show_historical_rate_check = QCheckBox("عرض سعر الصرف التاريخي للعملة")
        self.show_historical_rate_check.setChecked(False)
        form.addRow(self.show_historical_rate_check)

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
        is_cumulative = self.radio_cumulative.isChecked()
        show_historical_rate = self.show_historical_rate_check.isChecked()

        repo = ExpenseRepository()
        all_records = repo.get_by_company(company, convert_to_display=False)
        all_records.sort(key=lambda x: x['date'])
        
        period_records = [r for r in all_records if start_date <= r['date'] <= end_date]
        if not period_records:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات لهذه الشركة خلال الفترة المحددة")
            return
        dialog.accept()

        display_currency = currency.get_display_currency()
        decimals = currency.get_currency_decimals()
        symbol = currency.get_currency_symbol(display_currency)
        
        def format_full(amount):
            return f"{amount:,.{decimals}f} {symbol}"
        
        total_in_usd = sum(r['amount'] for r in period_records if r['type'] == 'incoming')
        total_out_usd = sum(r['amount'] for r in period_records if r['type'] == 'outgoing')
        net_usd = total_in_usd - total_out_usd
        total_in_display = currency.convert(total_in_usd, 'USD', display_currency)
        total_out_display = currency.convert(total_out_usd, 'USD', display_currency)
        net_display = currency.convert(net_usd, 'USD', display_currency)
        
        opening_balance_usd = 0.0
        if is_cumulative:
            opening_records = [r for r in all_records if r['date'] < start_date]
            opening_balance_usd = sum(r['amount'] if r['type'] == 'incoming' else -r['amount'] for r in opening_records)
        opening_balance_display = currency.convert(opening_balance_usd, 'USD', display_currency)
        
        table_rows = ""
        running_usd = opening_balance_usd
        for r in period_records:
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
            running_str = format_full(running_display)
            row_class = "income-row" if r['type'] == 'incoming' else "expense-row"
            
            # ✅ تصحيح: استخدام </td> بدلاً من الحرف الصيني "一位"
            historical_rate_col = ""
            if show_historical_rate:
                exchange_rate = r.get('exchange_rate_to_usd', 1.0)
                historical_rate_col = f'<td class="center">{exchange_rate:.4f}</td>'
            
            # ✅ تصحيح: إغلاق كل خلية بـ </tr> وإغلاق الصف بـ </tr>
            table_rows += f"""
            <tr class="{row_class}">
                <td class="center">{date_display}</td>
                <td class="right">{notes}</td>
                <td class="center">{incoming_str}</td>
                <td class="center">{outgoing_str}</td>
                <td class="center">{running_str}</td>
                {historical_rate_col}
            </tr>"""
        
        closing_balance_usd = running_usd
        closing_balance_display = currency.convert(closing_balance_usd, 'USD', display_currency)
        
        # ✅ تصحيح: إغلاق الخلايا بـ <table> بدلاً من "一位"
        opening_row = ""
        if is_cumulative and opening_balance_usd != 0:
            opening_row = f"""
            <tr class="opening-row">
                <td class="center">قبل {start_date}</td>
                <td class="right">الرصيد الافتتاحي</td>
                <td class="center">—</td>
                <td class="center">—</td>
                <td class="center">{format_full(opening_balance_display)}</td>
                {('<td class="center">—</td>' if show_historical_rate else '')}
            </tr>"""
        
        closing_row = ""
        if is_cumulative:
            closing_row = f"""
            <tr class="closing-row">
                <td class="center">بعد {end_date}</td>
                <td class="right">الرصيد الختامي</td>
                <td class="center">—</td>
                <td class="center">—</td>
                <td class="center">{format_full(closing_balance_display)}</td>
                {('<td class="center">—</td>' if show_historical_rate else '')}
            </tr>"""
        
        headers = "<th>التاريخ</th><th>ملاحظات</th><th>لنا</th><th>له</th><th>التراكمي</th>"
        if show_historical_rate:
            headers += "<th>سعر الصرف (USD)</th>"
        
        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><title>تقرير شركة {company}</title>
<style>
    body {{ font-family: 'Tajawal', 'Segoe UI', Tahoma, Arial; margin: 1.5cm; direction: rtl; background: white; }}
    h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; }}
    .period-info {{ text-align: center; margin-bottom: 20px; }}
    .summary {{ text-align: center; margin: 20px 0; font-size: 16px; font-weight: bold; background: #e9ecef; padding: 10px; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; }}
    th {{ background: #2c3e50; color: white; }}
    .income-row td {{ background-color: #d4edda; }}
    .expense-row td {{ background-color: #f8d7da; }}
    .opening-row td, .closing-row td {{ background-color: #fff3cd; font-weight: bold; }}
    .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: gray; }}
    .center {{ text-align: center; }}
    .right {{ text-align: right; }}
    /* ✅ توسيط إجباري لجميع خلايا الجدول */
    table td {{ text-align: center !important; }}
</style>
</head>
<body>
    <h1>📊 تقرير حسابات شركة: {company}</h1>
    <div class="period-info">الفترة: {start_date} إلى {end_date}</div>
    <div class="summary">
        📥 إجمالي وارد: {format_full(total_in_display)} &nbsp;|&nbsp;
        📤 إجمالي صادر: {format_full(total_out_display)} &nbsp;|&nbsp;
        💰 صافي: {format_full(net_display)}
    </div>
    <table class="data-table">
        <thead><tr>{headers} through</thead>
        <tbody>
            {opening_row}
            {table_rows}
            {closing_row}
        </tbody>
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
