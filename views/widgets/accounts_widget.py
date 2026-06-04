from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal
from database import ExpenseRepository
from i18n.translator import translate
from views.custom_table_view import CustomTableView
from models.table_models import GenericTableModel
from views.dialogs.add_edit_expense_dialog import AddEditExpenseDialog
from views.dialogs.company_details_dialog import CompanyDetailsDialog
from currency import currency
from collections import defaultdict

class AccountsWidget(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
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
        self.print_btn = QPushButton("🖨️ طباعة التقرير")
        self.print_btn.clicked.connect(self.print_report)
        self.pdf_btn = QPushButton("📄 حفظ PDF")
        self.pdf_btn.clicked.connect(self.export_pdf)
        btn_layout.addWidget(self.print_btn)
        btn_layout.addWidget(self.pdf_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = CustomTableView()
        self.table.setLayoutDirection(Qt.RightToLeft)
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        self.table.doubleClicked.connect(self.show_details)
        layout.addWidget(self.table)

        self.refresh_table()

    def refresh_table(self):
        repo = ExpenseRepository()
        expenses = repo.get_all(convert_to_display=True)
        search = self.search_edit.text().strip().lower()
        groups = defaultdict(lambda: {'incoming':0.0, 'outgoing':0.0})
        for e in expenses:
            if search and search not in e['company_name'].lower():
                continue
            groups[e['company_name']][e['type']] += e['amount']
        data = []
        for company, vals in groups.items():
            net = vals['incoming'] - vals['outgoing']
            data.append({
                'company': company,
                'incoming': currency.format_amount(vals['incoming']),
                'outgoing': currency.format_amount(vals['outgoing']),
                'net': currency.format_amount(net),
                'net_raw': net
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
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات للطباعة")
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
        PrintManager.print_report("تقرير حسابات الشركات", headers, data, self)

    def export_pdf(self):
        from printing.print_manager import PrintManager
        model = self.table.model()
        if not model or model.rowCount() == 0:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "تنبيه", "لا توجد بيانات للطباعة")
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
        PrintManager.save_as_pdf("تقرير حسابات الشركات", headers, data, self)
