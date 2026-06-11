from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QHeaderView,
    QMessageBox, QComboBox, QDateEdit, QLabel, QDialog, QFormLayout,
    QDialogButtonBox, QRadioButton, QButtonGroup, QCheckBox, QGroupBox,
    QSpinBox, QListWidget, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices
from database import ExpenseRepository
from i18n.translator import translate
from views.custom_table_view import CustomTableView
from models.table_models import GenericTableModel
from views.dialogs.add_edit_expense_dialog import AddEditExpenseDialog
from views.toast import Toast
from views.dialogs.company_details_dialog import CompanyDetailsDialog
from currency import currency
from auth.session import UserSession
from config import get_company_info
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import webbrowser
import tempfile
import os
import re
from money import base_amount, to_decimal

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
        groups = defaultdict(lambda: {
            'incoming': Decimal('0'),
            'outgoing': Decimal('0'),
            'waiting_payment': 0,
            'overdue': 0,
            'approved_records': []
        })
        today = datetime.now().date().isoformat()
        for e in expenses:
            if search and search not in e['company_name'].lower():
                continue
            status = e.get('status', 'approved')
            if status == 'waiting_payment':
                groups[e['company_name']]['waiting_payment'] += 1
                due = e.get('payment_due_date')
                if due and due < today:
                    groups[e['company_name']]['overdue'] += 1
                continue
            if status == 'approved':
                groups[e['company_name']][e['type']] += base_amount(e)
                groups[e['company_name']]['approved_records'].append(e)

        default_display_currency = currency.get_display_currency()
        data = []
        for company, vals in groups.items():
            incoming_display, outgoing_display, net_display, row_currency = self._company_summary_display_values(
                vals.get('approved_records', []),
                vals['incoming'],
                vals['outgoing'],
                default_display_currency
            )
            data.append({
                'company': company,
                'incoming': currency.format_amount(incoming_display, row_currency),
                'outgoing': currency.format_amount(outgoing_display, row_currency),
                'net': currency.format_amount(net_display, row_currency),
                'payment_status': self._format_payment_status(vals),
                'net_raw': net_display
            })
        data.sort(key=lambda x: x['company'])
        headers = ['company', 'incoming', 'outgoing', 'net', 'payment_status']
        display_headers = [translate('company_name'), translate('total_incoming'), translate('total_outgoing'), translate('net'), 'تنبيهات الدفع']
        data_keys = ['company', 'incoming', 'outgoing', 'net', 'payment_status']
        self.model = GenericTableModel(data, display_headers, key_fields=['company'], data_keys=data_keys)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.refresh_style()

    @staticmethod
    def _company_summary_display_values(records, incoming_base, outgoing_base, fallback_currency):
        """
        يحترم عملة العرض المختارة.
        يستخدم المبلغ الأصلي فقط عندما تكون كل قيود الشركة بنفس العملة وهذه العملة هي نفسها عملة العرض.
        خلاف ذلك تُعرض المجاميع محولة من القيمة الأساسية USD حتى لا تبقى SYP ظاهرة عند اختيار USD.
        """
        original_currency = AccountsWidget._single_original_currency(records)
        if original_currency and original_currency == fallback_currency:
            incoming = sum((AccountsWidget._original_amount(r) for r in records if r.get('type') == 'incoming'), Decimal('0'))
            outgoing = sum((AccountsWidget._original_amount(r) for r in records if r.get('type') == 'outgoing'), Decimal('0'))
            return incoming, outgoing, incoming - outgoing, original_currency
        incoming = currency.convert(incoming_base, 'USD', fallback_currency)
        outgoing = currency.convert(outgoing_base, 'USD', fallback_currency)
        return incoming, outgoing, incoming - outgoing, fallback_currency

    def _format_payment_status(self, vals):
        waiting = vals.get('waiting_payment', 0)
        overdue = vals.get('overdue', 0)
        if overdue:
            return f"⚠️ {overdue} متأخر / ⏳ {waiting} بانتظار الدفع"
        if waiting:
            return f"⏳ {waiting} بانتظار الدفع"
        return "—"

    def add_record(self):
        if UserSession.get_current().get('role') == 'viewer':
            QMessageBox.warning(self, translate('warning'), "ليس لديك صلاحية لإضافة قيود")
            return
        dialog = AddEditExpenseDialog(self)
        if dialog.exec():
            self.refresh_table()
            self.data_changed.emit()
            if getattr(dialog, 'saved_status', None) == 'waiting_payment':
                Toast(self, f"📝 تم حفظ العملية بانتظار الدفع\nموعد التنبيه: {dialog.saved_payment_due_date}\nلن تؤثر على الأرصدة حتى إدخال مبلغ فعلي.", 'warning')
            else:
                Toast(self, "✅ تم حفظ القيد المالي بنجاح", 'success')

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
        bad = ['\u200e', '\u200f', '\ufeff', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e', '浏']
        for ch in bad:
            text = text.replace(ch, '')
        text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9\s\-\.\,\:\;\(\)\/\+%\$]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _open_html_report(self, html, title=None):
        """حفظ تقرير HTML مؤقت وفتحه بطريقة متوافقة مع PyQt/النظام."""
        if not html:
            QMessageBox.warning(self, translate('warning'), 'تعذر توليد التقرير للطباعة')
            return False
        try:
            fd, temp = tempfile.mkstemp(suffix='.html', prefix='hawaa_report_')
            os.close(fd)
            with open(temp, 'w', encoding='utf-8') as f:
                f.write(html)

            file_url = QUrl.fromLocalFile(os.path.abspath(temp))
            opened = QDesktopServices.openUrl(file_url)
            if not opened:
                opened = webbrowser.open(file_url.toString())
            if opened:
                QMessageBox.information(self, title or translate('print_report'), translate('report_opened_in_browser'))
                return True
            QMessageBox.warning(self, translate('warning'), f'تم إنشاء التقرير لكن تعذر فتح المتصفح تلقائياً:\n{temp}')
            return False
        except Exception as e:
            QMessageBox.critical(self, 'خطأ', f'فشل فتح تقرير الطباعة:\n{str(e)}')
            return False

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
        self._open_html_report(html, translate('print_report'))

    def generate_html_report(self, settings):
        """توليد HTML للتقرير مع تطبيق إعدادات الطباعة"""
        # الحصول على البيانات الأصلية
        repo = ExpenseRepository()
        try:
            expenses = repo.get_all(convert_to_display=False)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تحميل البيانات: {str(e)}")
            return ""

        # تجميع البيانات: نحافظ على إجمالي كل شركة بعملتها الأصلية إذا كانت موحدة،
        # مع إبقاء الإجمالي العام محسوبًا من القيمة الأساسية حتى لا تختلط العملات.
        groups = defaultdict(lambda: {'incoming': Decimal('0'), 'outgoing': Decimal('0'), 'approved_records': []})
        for e in expenses:
            if e.get('status', 'approved') != 'approved':
                continue
            groups[e['company_name']][e['type']] += base_amount(e)
            groups[e['company_name']]['approved_records'].append(e)

        display_currency = currency.get_display_currency()
        total_decimals = currency.get_currency_decimals()
        total_symbol = currency.get_currency_symbol(display_currency)

        def format_amount_for(amount, curr):
            return currency.format_amount(to_decimal(amount), curr)

        def format_total(amount):
            return f"{to_decimal(amount):,.{total_decimals}f} {total_symbol}"

        data_rows = []
        total_in_all_base = Decimal('0')
        total_out_all_base = Decimal('0')
        for company, vals in groups.items():
            incoming, outgoing, net, row_currency = self._company_summary_display_values(
                vals.get('approved_records', []),
                vals['incoming'],
                vals['outgoing'],
                display_currency
            )
            total_in_all_base += vals['incoming']
            total_out_all_base += vals['outgoing']
            data_rows.append([company, incoming, outgoing, net, net, row_currency])
        data_rows.sort(key=lambda x: x[0])

        total_in_all = currency.convert(total_in_all_base, 'USD', display_currency)
        total_out_all = currency.convert(total_out_all_base, 'USD', display_currency)
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
                <td class="center {incoming_class}">{self.clean_text(format_amount_for(row[1], row[5]))}</td>
                <td class="center {outgoing_class}">{self.clean_text(format_amount_for(row[2], row[5]))}</td>
                <td class="center {net_class}">{self.clean_text(format_amount_for(row[3], row[5]))}</td>
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
        📥 إجمالي وارد: {format_total(total_in_all)} &nbsp;|&nbsp;
        📤 إجمالي صادر: {format_total(total_out_all)} &nbsp;|&nbsp;
        💰 صافي الكلي: {format_total(total_net)}
    </div>
    <table>
        <thead>
            <tr>{"".join(f'<th>{h}</th>' for h in headers)}</tr>
        </thead>
        <tbody>
            {table_rows}
            <tr class="total-row">
                {('<td class="center">—</td>' if show_row_numbers else '')}
                <td class="center"><strong>الإجمالي الكلي</strong></td>
                <td class="center income"><strong>{format_total(total_in_all)}</strong></td>
                <td class="center expense"><strong>{format_total(total_out_all)}</strong></td>
                <td class="center"><strong>{format_total(total_net)}</strong></td>
            </tr>
        </tbody>
    </table>
    <div class="footer">{footer_text}</div>
</body>
</html>"""
        return html

    # ------------------- باقي الدوال (التقرير المخصص) -------------------
    def show_custom_report_dialog(self):
        """نافذة موحدة لتقرير مخصص: شركة واحدة أو عدة شركات مع نفس خيارات الطباعة."""
        dialog = QDialog(self)
        dialog.setWindowTitle("تقرير مخصص للشركات")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(560, 560)
        layout = QVBoxLayout(dialog)

        form = QFormLayout()

        repo = ExpenseRepository()
        expenses = repo.get_all(convert_to_display=False)
        companies = sorted(set(e['company_name'] for e in expenses))
        if not companies:
            QMessageBox.warning(self, translate('warning'), translate('no_data_for_print'))
            return

        self.all_companies_check = QCheckBox("طباعة لكل الشركات")
        self.company_list = QListWidget()
        self.company_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.company_list.setMinimumHeight(120)
        for company in companies:
            self.company_list.addItem(company)
        if self.company_list.count() > 0:
            self.company_list.item(0).setSelected(True)

        def toggle_all_companies(state):
            select_all = state == Qt.Checked
            self.company_list.setEnabled(not select_all)
            for i in range(self.company_list.count()):
                self.company_list.item(i).setSelected(select_all)

        self.all_companies_check.stateChanged.connect(toggle_all_companies)
        form.addRow(self.all_companies_check)
        form.addRow("الشركات:", self.company_list)

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
        self.radio_period = QRadioButton("تقرير فترة")
        self.radio_cumulative = QRadioButton("تقرير تراكمي")
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
        buttons.button(QDialogButtonBox.Ok).setText("التالي: خيارات الطباعة")
        buttons.button(QDialogButtonBox.Cancel).setText("إلغاء")
        layout.addWidget(buttons)

        self.on_period_type_changed()
        dialog.exec()

    def _selected_custom_report_companies(self):
        if getattr(self, 'all_companies_check', None) and self.all_companies_check.isChecked():
            return [self.company_list.item(i).text() for i in range(self.company_list.count())]
        return [item.text() for item in self.company_list.selectedItems()]

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

    @staticmethod
    def _approved_non_waiting(records):
        return [r for r in records if r.get('status', 'approved') == 'approved']

    @staticmethod
    def _single_original_currency(records):
        currencies = {r.get('currency_original') for r in records if r.get('currency_original')}
        return next(iter(currencies)) if len(currencies) == 1 else None

    @staticmethod
    def _original_amount(record):
        return to_decimal(record.get('amount_original', record.get('amount', 0)))

    @staticmethod
    def _format_original_entry_amount(record):
        original_currency = record.get('currency_original') or currency.get_display_currency()
        return currency.format_amount(
            to_decimal(record.get('amount_original', record.get('amount', 0))),
            original_currency
        )

    def _company_report_math(self, active_records, opening_records, display_currency, is_cumulative):
        """حساب ملخص شركة واحدة مع احترام قاعدة العملة الأصلية/عملة العرض."""
        scope_records = active_records + (opening_records if is_cumulative else [])
        original_currency = self._single_original_currency(scope_records)
        use_original_running = bool(original_currency and original_currency == display_currency)

        if use_original_running:
            total_in = sum((self._original_amount(r) for r in active_records if r['type'] == 'incoming'), Decimal('0'))
            total_out = sum((self._original_amount(r) for r in active_records if r['type'] == 'outgoing'), Decimal('0'))
            opening = Decimal('0')
            if is_cumulative:
                opening = sum((self._original_amount(r) if r['type'] == 'incoming' else -self._original_amount(r)
                               for r in opening_records), Decimal('0'))
            row_balance_currency = display_currency
        else:
            total_in_usd = sum((base_amount(r) for r in active_records if r['type'] == 'incoming'), Decimal('0'))
            total_out_usd = sum((base_amount(r) for r in active_records if r['type'] == 'outgoing'), Decimal('0'))
            total_in = currency.convert(total_in_usd, 'USD', display_currency)
            total_out = currency.convert(total_out_usd, 'USD', display_currency)
            opening_usd = Decimal('0')
            if is_cumulative:
                opening_usd = sum((base_amount(r) if r['type'] == 'incoming' else -base_amount(r)
                                   for r in opening_records), Decimal('0'))
            opening = currency.convert(opening_usd, 'USD', display_currency)
            row_balance_currency = 'USD'

        return {
            'use_original_running': use_original_running,
            'total_in': total_in,
            'total_out': total_out,
            'net': total_in - total_out,
            'opening': opening,
            'row_balance_currency': row_balance_currency,
        }

    def generate_company_report(self, dialog):
        selected_companies = self._selected_custom_report_companies()
        if not selected_companies:
            QMessageBox.warning(self, "تنبيه", "اختر شركة واحدة على الأقل للطباعة")
            return

        start_date, end_date = self.get_date_range()
        is_cumulative = self.radio_cumulative.isChecked()
        show_historical_rate = self.show_historical_rate_check.isChecked()

        repo = ExpenseRepository()
        report_data = []
        for company in selected_companies:
            all_records = repo.get_by_company(company, convert_to_display=False)
            all_records.sort(key=lambda x: (x['date'], x.get('id', 0)))
            period_records = [r for r in all_records if start_date <= r['date'] <= end_date]
            active_period_records = self._approved_non_waiting(period_records)
            opening_records = [r for r in all_records if r['date'] < start_date and r.get('status', 'approved') == 'approved']
            if active_period_records or (is_cumulative and opening_records):
                report_data.append({
                    'company': company,
                    'period_records': period_records,
                    'active_period_records': active_period_records,
                    'opening_records': opening_records,
                })

        if not report_data:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات للشركات المحددة خلال الفترة المحددة")
            return

        print_dialog = PrintOptionsDialog(self)
        print_dialog.setWindowTitle("خيارات طباعة التقرير المخصص")
        if print_dialog.exec() != QDialog.Accepted:
            return
        settings = print_dialog.get_settings()
        dialog.accept()

        display_currency = currency.get_display_currency()
        decimals = currency.get_currency_decimals()
        symbol = currency.get_currency_symbol(display_currency)

        def format_full(amount):
            return f"{to_decimal(amount):,.{decimals}f} {symbol}"

        show_row_numbers = settings.get('show_row_numbers', True)
        colorize_rows = settings.get('colorize_rows', True)
        colorize_numbers = settings.get('colorize_numbers', True)
        font_size = settings.get('font_size', 10)
        show_datetime = settings.get('show_datetime', True)
        show_printed_by = settings.get('show_printed_by', True)
        footer_note = settings.get('footer_note', '')
        custom_title = settings.get('custom_title', '')
        show_company_name = settings.get('show_company_name', True)
        show_address = settings.get('show_address', True)
        show_logo = settings.get('show_logo', True)

        total_in_all_usd = Decimal('0')
        total_out_all_usd = Decimal('0')
        sections_html = ""

        for company_index, block in enumerate(report_data, start=1):
            company = block['company']
            active_records = block['active_period_records']
            opening_records = block['opening_records']
            period_records = block['period_records']
            math = self._company_report_math(active_records, opening_records, display_currency, is_cumulative)

            total_in_all_usd += sum((base_amount(r) for r in active_records if r['type'] == 'incoming'), Decimal('0'))
            total_out_all_usd += sum((base_amount(r) for r in active_records if r['type'] == 'outgoing'), Decimal('0'))

            running_balance = math['opening']
            row_number = 1
            table_rows = ""

            opening_row = ""
            if is_cumulative and math['opening'] != 0:
                num_col = '<td class="center">—</td>' if show_row_numbers else ''
                opening_row = f"""
                <tr class="opening-row">
                    {num_col}
                    <td class="center">قبل {start_date}</td>
                    <td class="right">الرصيد الافتتاحي</td>
                    <td class="center">—</td>
                    <td class="center">—</td>
                    <td class="center">{format_full(math['opening'])}</td>
                    {('<td class="center">—</td>' if show_historical_rate else '')}
                </tr>"""

            for r in period_records:
                # حقلا لنا/له: المبلغ الأصلي بعملة القيد، لا يتأثر بعملة العرض.
                amount_str = self._format_original_entry_amount(r)
                notes = self.clean_text(r.get('notes') or '—')
                date_display = self.clean_text(r['date'])
                is_approved = r.get('status', 'approved') == 'approved'
                row_class = "income-row" if r['type'] == 'incoming' else "expense-row"
                if not is_approved:
                    row_class = "waiting-row"

                if r['type'] == 'incoming':
                    incoming_str = amount_str
                    outgoing_str = "—"
                    if is_approved:
                        running_balance += self._original_amount(r) if math['use_original_running'] else currency.convert(base_amount(r), 'USD', display_currency)
                else:
                    incoming_str = "—"
                    outgoing_str = amount_str
                    if is_approved:
                        running_balance -= self._original_amount(r) if math['use_original_running'] else currency.convert(base_amount(r), 'USD', display_currency)

                running_str = format_full(running_balance)
                num_col = f'<td class="center">{row_number}</td>' if show_row_numbers else ''
                row_number += 1
                historical_rate_col = ""
                if show_historical_rate:
                    exchange_rate = to_decimal(r.get('exchange_rate_to_usd', 1))
                    historical_rate_col = f'<td class="center">{exchange_rate}</td>'

                table_rows += f"""
                <tr class="{row_class if colorize_rows else ''}">
                    {num_col}
                    <td class="center">{date_display}</td>
                    <td class="right">{notes}</td>
                    <td class="center income">{self.clean_text(incoming_str)}</td>
                    <td class="center expense">{self.clean_text(outgoing_str)}</td>
                    <td class="center">{self.clean_text(running_str)}</td>
                    {historical_rate_col}
                </tr>"""

            closing_row = ""
            if is_cumulative:
                num_col = '<td class="center">—</td>' if show_row_numbers else ''
                closing_row = f"""
                <tr class="closing-row">
                    {num_col}
                    <td class="center">بعد {end_date}</td>
                    <td class="right">الرصيد الختامي</td>
                    <td class="center">—</td>
                    <td class="center">—</td>
                    <td class="center">{format_full(running_balance)}</td>
                    {('<td class="center">—</td>' if show_historical_rate else '')}
                </tr>"""

            headers = []
            if show_row_numbers:
                headers.append('#')
            headers.extend(['التاريخ', 'ملاحظات', 'لنا', 'له', 'التراكمي'])
            if show_historical_rate:
                headers.append('سعر الصرف (USD)')

            page_break = ' page-break-before: always;' if company_index > 1 else ''
            sections_html += f"""
            <section class="company-section" style="{page_break}">
                <h2>شركة: {self.clean_text(company)}</h2>
                <div class="company-summary">
                    📥 إجمالي وارد: {self.clean_text(format_full(math['total_in']))} &nbsp;|&nbsp;
                    📤 إجمالي صادر: {self.clean_text(format_full(math['total_out']))} &nbsp;|&nbsp;
                    💰 صافي: {self.clean_text(format_full(math['net']))}
                </div>
                <table class="data-table">
                    <thead><tr>{''.join(f'<th>{h}</th>' for h in headers)}</tr></thead>
                    <tbody>
                        {opening_row}
                        {table_rows}
                        {closing_row}
                    </tbody>
                </table>
            </section>"""

        total_in_display = currency.convert(total_in_all_usd, 'USD', display_currency)
        total_out_display = currency.convert(total_out_all_usd, 'USD', display_currency)
        total_net_display = total_in_display - total_out_display

        company_info = get_company_info()
        header_html = ""
        if show_company_name:
            header_html += f"<strong>{self.clean_text(company_info.get('name', 'هوى الشام للسياحة والسفر'))}</strong><br>"
        if show_address:
            header_html += f"{self.clean_text(company_info.get('address', ''))} | 📞 {self.clean_text(company_info.get('phone', ''))} | ✉️ {self.clean_text(company_info.get('email', ''))}<br>"
        if show_logo and company_info.get('logo_path') and os.path.exists(company_info['logo_path']):
            # يمكن إضافة تضمين الشعار لاحقًا عند توحيد أصول الطباعة.
            pass

        footer_text = ""
        if show_printed_by:
            user = UserSession.get_current()
            footer_text += f"طبع بواسطة: {self.clean_text(user.get('username', ''))} | "
        if show_datetime:
            footer_text += f"تاريخ الطباعة: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if footer_note:
            footer_text += f"<br>{self.clean_text(footer_note)}"

        report_title = "تقرير مخصص للشركات" if len(selected_companies) > 1 else f"تقرير حسابات شركة: {selected_companies[0]}"
        if custom_title:
            report_title += f" - {self.clean_text(custom_title)}"

        html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>{self.clean_text(report_title)}</title>
<style>
    body {{ font-family: 'Tajawal', 'Segoe UI', Tahoma, Arial; margin: 1.5cm; direction: rtl; background: white; font-size: {font_size}pt; }}
    h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 8px; }}
    h2 {{ color: #2c3e50; margin-top: 24px; border-right: 4px solid #3498db; padding-right: 8px; }}
    .company-info {{ text-align: center; margin-bottom: 18px; color: #2c3e50; border: 1px solid #ddd; padding: 8px; background: #f9f9f9; }}
    .period-info {{ text-align: center; margin-bottom: 12px; }}
    .summary, .company-summary {{ text-align: center; margin: 16px 0; font-size: 15px; font-weight: bold; background: #e9ecef; padding: 10px; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
    th, td {{ border: 1px solid #ccc; padding: 7px; text-align: center; }}
    th {{ background: #2c3e50; color: white; font-weight: bold; }}
    .income-row td {{ background-color: #d4edda; }}
    .expense-row td {{ background-color: #f8d7da; }}
    .waiting-row td {{ background-color: #fff3cd; }}
    .opening-row td, .closing-row td {{ background-color: #fff3cd; font-weight: bold; }}
    .income {{ color: #28a745; font-weight: bold; }}
    .expense {{ color: #dc3545; font-weight: bold; }}
    .footer {{ text-align: center; margin-top: 30px; font-size: 11px; color: #6c757d; border-top: 1px solid #dee2e6; padding-top: 10px; }}
    .center {{ text-align: center; }}
    .right {{ text-align: right; }}
    @media print {{ .company-section {{ break-inside: avoid; }} }}
</style>
</head>
<body>
    <h1>{self.clean_text(report_title)}</h1>
    <div class="company-info">{header_html}</div>
    <div class="period-info">الفترة: {start_date} إلى {end_date}</div>
    <div class="summary">
        📥 الإجمالي العام الوارد: {self.clean_text(format_full(total_in_display))} &nbsp;|&nbsp;
        📤 الإجمالي العام الصادر: {self.clean_text(format_full(total_out_display))} &nbsp;|&nbsp;
        💰 الصافي العام: {self.clean_text(format_full(total_net_display))}
    </div>
    {sections_html}
    <div class="footer">{footer_text}</div>
</body>
</html>"""
        self._open_html_report(html, "طباعة التقرير المخصص")
