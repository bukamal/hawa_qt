# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal

from database import ExpenseRepository
from i18n.translator import translate
from views.custom_table_view import CustomTableView
from models.table_models import CompanyLedgerTableModel
from views.toast import Toast
from currency import currency
from ui.editors.expense_editor_panel import ExpenseEditorPanel
from ui.components.print_preview_panel import PrintPreviewPanel
from services.currency_ledger_service import currency_ledger
from services.expense_service import expense_service
from services.permission_service import permission_service
from services.print_service import print_service


class CompanyDocument(QWidget):
    """Inline company ledger document.

    Replaces CompanyDetailsDialog inside the document workspace. CRUD uses inline
    editors and print preview stays inside the shell, while ledger totals are calculated
    by CurrencyLedgerService so UI and reports always match.
    """
    data_changed = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, shell=None, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.company_name = None
        self.records = []
        self.ledger = None
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        header_layout = QHBoxLayout()
        self.back_btn = QPushButton('← الحسابات')
        self.back_btn.clicked.connect(self._go_back)
        self.title_label = QLabel('تفاصيل الشركة')
        self.title_label.setObjectName('DocumentTitle')
        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(self.title_label, 1)
        layout.addLayout(header_layout)

        self.summary_label = QLabel()
        self.summary_label.setObjectName('CompanySummary')
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.table = CustomTableView()
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        self.table.doubleClicked.connect(lambda _idx: self.edit_record())
        layout.addWidget(self.table, 1)

        btn_layout = QHBoxLayout()
        can_write = permission_service.can_write_expenses()

        self.add_btn = QPushButton('➕ ' + translate('add'))
        self.add_btn.clicked.connect(self.add_record)
        self.add_btn.setVisible(can_write)

        self.edit_btn = QPushButton('✏️ ' + translate('edit'))
        self.edit_btn.clicked.connect(self.edit_record)
        self.edit_btn.setVisible(can_write)

        self.delete_btn = QPushButton('🗑 ' + translate('delete'))
        self.delete_btn.clicked.connect(self.delete_record)
        self.delete_btn.setVisible(can_write)

        self.print_btn = QPushButton('🖨️ معاينة التقرير')
        self.print_btn.clicked.connect(self.print_company_report)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.print_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

    def activate(self, company_name=None, **_params):
        if company_name:
            self.company_name = company_name
        if self.company_name:
            self.title_label.setText(f'تفاصيل حسابات: {self.company_name}')
            self.refresh()
        elif hasattr(self, 'model'):
            self.model.refresh_data([])

    def _go_back(self):
        if self.shell:
            self.shell.close_inline()
            self.shell.open_document('accounts')
        else:
            self.back_requested.emit()

    def refresh(self):
        if not self.company_name:
            return
        repo = ExpenseRepository()
        records = repo.get_by_company(self.company_name, convert_to_display=False)
        self.records = sorted(records, key=lambda x: (x.get('date') or '', x.get('id') or 0))
        self.ledger = currency_ledger.company_ledger_display(self.records)
        display_currency = self.ledger['display_currency']

        self.total_in_display = self.ledger['total_in_display']
        self.total_out_display = self.ledger['total_out_display']
        self.net_display = self.ledger['net_display']
        self.display_currency = display_currency

        self.summary_label.setText(
            f"📥 إجمالي وارد: {currency.format_amount(self.total_in_display, display_currency)}   |   "
            f"📤 إجمالي صادر: {currency.format_amount(self.total_out_display, display_currency)}   |   "
            f"💰 صافي: {currency.format_amount(self.net_display, display_currency)}   |   {self.ledger['mode_note']}"
        )

        data = []
        for row in self.ledger['rows']:
            data.append({
                'id': row['id'],
                'serial': row['serial'],
                'date': row['date'],
                'notes': row['notes'],
                'incoming': row['incoming'],
                'outgoing': row['outgoing'],
                'running': row['running'],
                'historical_rate': row['historical_rate'],
            })

        self.model = CompanyLedgerTableModel(data)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.refresh_style()

    def add_record(self):
        if not permission_service.can_write_expenses():
            QMessageBox.warning(self, translate('warning'), 'ليس لديك صلاحية لإضافة قيود')
            return
        if not self.company_name:
            return
        editor = ExpenseEditorPanel(company_name=self.company_name)
        editor.saved.connect(self._on_editor_saved)
        editor.cancelled.connect(self._close_inline)
        self._open_inline(editor, 'إضافة قيد مالي')

    def edit_record(self):
        if not permission_service.can_write_expenses():
            QMessageBox.warning(self, translate('warning'), 'ليس لديك صلاحية لتعديل القيود')
            return
        exp = self._selected_expense()
        if not exp:
            QMessageBox.warning(self, translate('warning'), 'اختر قيداً للتعديل')
            return
        editor = ExpenseEditorPanel(expense=exp)
        editor.saved.connect(self._on_editor_saved)
        editor.cancelled.connect(self._close_inline)
        self._open_inline(editor, 'تعديل قيد مالي')

    def _selected_expense(self):
        selected = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not selected or not hasattr(self, 'model'):
            return None
        row = selected[0].row()
        exp_id = self.model.get_id(row)
        if not exp_id:
            return None
        return ExpenseRepository().get_by_id(exp_id, convert_to_display=False)

    def _open_inline(self, editor, title):
        if self.shell:
            self.shell.open_inline(editor, title)
        else:
            self._floating_editor = editor
            editor.setWindowTitle(title)
            editor.show()

    def _close_inline(self):
        if self.shell:
            self.shell.close_inline()

    def _on_editor_saved(self, payload):
        self.refresh()
        self.data_changed.emit()
        self._close_inline()
        if payload.get('status') == 'waiting_payment':
            Toast(self, f"📝 تم حفظ العملية بانتظار الدفع\nموعد التنبيه: {payload.get('payment_due_date')}", 'warning', sound_id='payment_due')
        else:
            Toast(self, '✅ تم حفظ القيد المالي بنجاح', 'success')

    def delete_record(self):
        if not permission_service.can_write_expenses():
            QMessageBox.warning(self, translate('warning'), 'ليس لديك صلاحية لحذف القيود')
            return
        exp = self._selected_expense()
        if not exp:
            QMessageBox.warning(self, translate('warning'), 'اختر قيداً للحذف')
            return
        reply = QMessageBox.question(self, translate('confirm_delete'), translate('confirm_delete'), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                expense_service.delete(exp['id'])
            except PermissionError as exc:
                QMessageBox.warning(self, translate('warning'), str(exc))
                return
            self.refresh()
            self.data_changed.emit()
            Toast(self, '🗑 تم حذف القيد المالي', 'warning', sound_id='delete')

    def print_company_report(self):
        if not self.company_name:
            return
        report = print_service.build_company_ledger_payload(self.company_name, self.records)
        panel = PrintPreviewPanel(
            report['html'],
            title=report['title'],
            headers=report['headers'],
            rows=report['rows'],
            subtitle=report.get('subtitle'),
            default_filename=report.get('default_filename', f'company_ledger_{self.company_name}'),
        )
        panel.closed.connect(self._close_inline)
        self._open_inline(panel, 'معاينة كشف الشركة')
