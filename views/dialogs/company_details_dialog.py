from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QHeaderView
from PyQt5.QtCore import Qt
from database import ExpenseRepository
from auth.session import UserSession
from i18n.translator import translate
from views.centered_dialog import CenteredDialog
from views.custom_table_view import CustomTableView
from models.table_models import GenericTableModel
from views.dialogs.add_edit_expense_dialog import AddEditExpenseDialog
from currency import currency
from printing.print_manager import PrintManager

class CompanyDetailsDialog(CenteredDialog):
    def __init__(self, company_name, parent=None):
        super().__init__(parent)
        # إزالة RTL (الاتجاه الافتراضي LTR)
        self.company_name = company_name
        self.setWindowTitle(f"تفاصيل حسابات {company_name}")
        self.resize(900, 550)
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20,20,20,20)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        self.table = CustomTableView()
        self.table.setLayoutDirection(Qt.LeftToRight)  # LTR للجدول
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ "+translate('add'))
        add_btn.clicked.connect(self.add_record)
        edit_btn = QPushButton("✏️ "+translate('edit'))
        edit_btn.clicked.connect(self.edit_record)
        delete_btn = QPushButton("🗑 "+translate('delete'))
        delete_btn.clicked.connect(self.delete_record)
        print_btn = QPushButton("🖨️ طباعة / معاينة")
        print_btn.clicked.connect(self.print_company_report)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(print_btn)
        layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        repo = ExpenseRepository()
        self.records = repo.get_by_company(self.company_name, convert_to_display=False)
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
        self.summary_label.setText(f"📥 {translate('total_incoming')}: {currency.format_amount(total_in_display)}   |   "
                                   f"📤 {translate('total_outgoing')}: {currency.format_amount(total_out_display)}   |   "
                                   f"💰 {translate('net')}: {currency.format_amount(net_display)}")

        data = []
        for r in self.records:
            original_amount = currency.convert(r['amount'], 'USD', r['currency'])
            data.append({
                'id': r['id'],
                'date': r['date'],
                'type': translate('incoming') if r['type'] == 'incoming' else translate('outgoing'),
                'amount': currency.format_amount(original_amount, r['currency']),
                'currency': r['currency'],
                'notes': r['notes'] or ''
            })
        headers = ['id', 'date', 'type', 'amount', 'currency', 'notes']
        display_headers = ['#', translate('date'), translate('type'), translate('amount'), translate('currency'), translate('notes')]
        data_keys = ['id', 'date', 'type', 'amount', 'currency', 'notes']
        self.model = GenericTableModel(data, display_headers, key_fields=['id'], data_keys=data_keys)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnHidden(0, True)
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

    def print_company_report(self):
        if not hasattr(self, 'records') or not self.records:
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات للطباعة")
            return

        headers = [translate('date'), translate('type'), translate('amount'), translate('currency'), translate('notes')]
        data = []
        for r in self.records:
            original_amount = currency.convert(r['amount'], 'USD', r['currency'])
            amount_str = currency.format_amount(original_amount, r['currency'])
            row = [
                r['date'],
                translate('incoming') if r['type'] == 'incoming' else translate('outgoing'),
                amount_str,
                r['currency'],
                r['notes'] or '-'
            ]
            data.append(row)

        PrintManager.print_report(f"تفاصيل حسابات {self.company_name}", headers, data, self)
