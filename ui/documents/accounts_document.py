# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QHeaderView, QMessageBox, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal

from i18n.translator import translate
from views.custom_table_view import CustomTableView
from views.toast import Toast
from models.table_models import CompanySummaryTableModel
from services.accounts_service import accounts_service
from services.permission_service import permission_service
from ui.editors.expense_editor_panel import ExpenseEditorPanel
from ui.components.print_preview_panel import PrintPreviewPanel


class AccountsDocument(QWidget):
    """Accounts summary document inside the Document Shell.

    This phase removes the new shell's dependency on the legacy AccountsWidget.
    Company summaries come from AccountsService, while editing still uses the inline
    ExpenseEditorPanel and CompanyDocument.
    """
    data_changed = pyqtSignal()

    def __init__(self, shell=None, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.current_summary = None
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.header = QLabel('الحسابات')
        self.header.setObjectName('DocumentTitle')
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(translate('search'))
        self.search_edit.textChanged.connect(self.refresh_table)
        header.addWidget(self.header)
        header.addWidget(self.search_edit, 1)
        layout.addLayout(header)

        self.summary_frame = QFrame()
        self.summary_frame.setObjectName('AccountsSummaryStrip')
        self.summary_frame.setStyleSheet('''
            QFrame#AccountsSummaryStrip {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            QLabel#SummaryMetricTitle {
                background: transparent;
                color: #64748b;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#SummaryMetricValue {
                background: transparent;
                color: #1e293b;
                font-size: 13px;
                font-weight: 800;
            }
        ''')
        summary_grid = QGridLayout(self.summary_frame)
        summary_grid.setContentsMargins(14, 10, 14, 10)
        summary_grid.setHorizontalSpacing(16)
        summary_grid.setVerticalSpacing(6)
        self.summary_labels = {}
        for col, key in enumerate(['display', 'companies', 'incoming', 'outgoing', 'net', 'waiting', 'overdue']):
            title = QLabel('')
            title.setObjectName('SummaryMetricTitle')
            title.setAlignment(Qt.AlignCenter)
            value = QLabel('—')
            value.setObjectName('SummaryMetricValue')
            value.setAlignment(Qt.AlignCenter)
            value.setWordWrap(True)
            summary_grid.addWidget(title, 0, col)
            summary_grid.addWidget(value, 1, col)
            self.summary_labels[key] = (title, value)
        layout.addWidget(self.summary_frame)

        self.table = CustomTableView()
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        self.table.doubleClicked.connect(lambda _idx: self.open_selected_company())
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.add_btn = QPushButton('➕ ' + translate('add'))
        self.add_btn.clicked.connect(self.open_global_expense_editor)
        self.add_btn.setVisible(permission_service.can_write_expenses())

        self.open_btn = QPushButton('📂 فتح الشركة')
        self.open_btn.clicked.connect(self.open_selected_company)

        self.preview_btn = QPushButton('🖨️ معاينة إجماليات الشركات')
        self.preview_btn.clicked.connect(self.open_summary_preview)

        actions.addWidget(self.add_btn)
        actions.addWidget(self.open_btn)
        actions.addWidget(self.preview_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

    def activate(self, **_params):
        self.refresh_table()

    def refresh_table(self):
        try:
            self.current_summary = accounts_service.company_summaries(self.search_edit.text())
            rows = self.current_summary['rows']
            self._update_summary_strip(self.current_summary)
            self.model = CompanySummaryTableModel(rows)
            self.table.setModel(self.model)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table.refresh_style()
        except Exception as exc:
            QMessageBox.critical(self, translate('error'), str(exc))

    def _update_summary_strip(self, summary):
        values = {
            'display': ('عملة العرض', summary.get('subtitle', '—')),
            'companies': ('الشركات', str(summary.get('companies_count', 0))),
            'incoming': ('إجمالي الوارد', summary.get('total_incoming', '—')),
            'outgoing': ('إجمالي الصادر', summary.get('total_outgoing', '—')),
            'net': ('الصافي', summary.get('net', '—')),
            'waiting': ('بانتظار الدفع', str(summary.get('waiting_payment_count', 0))),
            'overdue': ('متأخر', str(summary.get('overdue_count', 0))),
        }
        for key, (title, value) in values.items():
            title_label, value_label = self.summary_labels[key]
            title_label.setText(title)
            value_label.setText(value)

    def apply_theme_colors(self):
        if hasattr(self, 'table'):
            self.table.refresh_style()

    def _selected_company_name(self):
        selected = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not selected or not hasattr(self, 'model'):
            return None
        return self.model.get_id(selected[0].row())

    def open_selected_company(self):
        company_name = self._selected_company_name()
        if not company_name:
            QMessageBox.warning(self, translate('warning'), 'اختر شركة لفتح كشفها')
            return
        self.open_company(company_name)

    def open_company(self, company_name):
        if self.shell:
            self.shell.close_inline()
            self.shell.open_document('company', company_name=company_name)

    def open_global_expense_editor(self):
        if not permission_service.can_write_expenses():
            QMessageBox.warning(self, translate('warning'), 'ليس لديك صلاحية لإضافة قيود')
            return
        editor = ExpenseEditorPanel()
        editor.saved.connect(self._on_editor_saved)
        editor.cancelled.connect(lambda: self.shell.close_inline() if self.shell else None)
        if self.shell:
            self.shell.open_inline(editor, 'إضافة قيد مالي')
        else:
            editor.show()

    def open_summary_preview(self):
        try:
            report = accounts_service.build_summary_report(self.search_edit.text())
            panel = PrintPreviewPanel(
                report['html'],
                title='تقرير إجماليات الشركات',
                headers=report.get('headers'),
                rows=report.get('rows'),
                subtitle=report.get('subtitle'),
                default_filename=report.get('default_filename', 'accounts_summary'),
            )
            if self.shell:
                self.shell.open_inline(panel, 'معاينة إجماليات الشركات')
            else:
                panel.show()
        except Exception as exc:
            QMessageBox.critical(self, translate('error'), str(exc))

    def _on_editor_saved(self, payload):
        self.refresh_table()
        self.data_changed.emit()
        if self.shell:
            self.shell.close_inline()
        if payload.get('status') == 'waiting_payment':
            Toast(self, f"📝 تم حفظ العملية بانتظار الدفع\nموعد التنبيه: {payload.get('payment_due_date')}", 'warning')
        else:
            Toast(self, '✅ تم حفظ القيد المالي بنجاح', 'success')
