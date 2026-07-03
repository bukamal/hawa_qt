# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDateEdit, QHeaderView, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QDate

from models.table_models import AuditLogTableModel
from services.audit_service import audit_service
from services.export_service import export_service
from ui.components.print_preview_panel import PrintPreviewPanel
from views.custom_table_view import CustomTableView


class AuditDocument(QWidget):
    """Inline Audit Log document; dialogs are limited to OS save/confirm actions."""
    def __init__(self, shell=None, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.current_logs = []
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel('سجل التدقيق')
        title.setObjectName('DocumentTitle')
        root.addWidget(title)

        filters = QHBoxLayout()
        filters.addWidget(QLabel('المستخدم:'))
        self.user_filter = QComboBox()
        self.user_filter.addItem('الكل', None)
        filters.addWidget(self.user_filter)

        filters.addWidget(QLabel('العملية:'))
        self.action_filter = QComboBox()
        self.action_filter.addItems(['الكل', 'إضافة قيد', 'تعديل قيد', 'حذف قيد', 'إضافة مستخدم', 'تعديل مستخدم', 'حذف مستخدم', 'تغيير كلمة المرور', 'تغيير إعداد'])
        filters.addWidget(self.action_filter)

        filters.addWidget(QLabel('الجدول:'))
        self.table_filter = QComboBox()
        self.table_filter.addItems(['الكل', 'expenses', 'users', 'settings', 'exchange_rates'])
        filters.addWidget(self.table_filter)

        filters.addWidget(QLabel('من:'))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        filters.addWidget(self.start_date)

        filters.addWidget(QLabel('إلى:'))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        filters.addWidget(self.end_date)

        apply_btn = QPushButton('تطبيق')
        apply_btn.clicked.connect(self.refresh_logs)
        filters.addWidget(apply_btn)
        filters.addStretch(1)
        root.addLayout(filters)

        actions = QHBoxLayout()
        preview_btn = QPushButton('🖨️ معاينة')
        preview_btn.clicked.connect(self.open_preview)
        export_btn = QPushButton('📊 تصدير Excel')
        export_btn.clicked.connect(self.export_to_excel)
        stats_btn = QPushButton('📈 الإحصائيات')
        stats_btn.clicked.connect(self.show_stats_inline)
        cleanup_btn = QPushButton('🗑 حذف السجلات الأقدم من 90 يوم')
        cleanup_btn.clicked.connect(self.delete_old_logs)
        actions.addWidget(preview_btn)
        actions.addWidget(export_btn)
        actions.addWidget(stats_btn)
        actions.addWidget(cleanup_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        self.note_label = QLabel('سجل التدقيق للقراءة والمراجعة. الحذف والتنظيف محصور بالمدير، أما المدقق فله القراءة والتصدير فقط.')
        self.note_label.setObjectName('DocumentHint')
        self.note_label.setWordWrap(True)
        root.addWidget(self.note_label)

        self.table = CustomTableView()
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        root.addWidget(self.table, 1)

    def activate(self, **_params):
        self._load_users()
        self.refresh_logs()

    def _load_users(self):
        current = self.user_filter.currentData()
        self.user_filter.blockSignals(True)
        self.user_filter.clear()
        self.user_filter.addItem('الكل', None)
        try:
            for user in audit_service.list_users_for_filter():
                self.user_filter.addItem(user.get('username', ''), user.get('id'))
        except Exception:
            pass
        idx = self.user_filter.findData(current)
        if idx >= 0:
            self.user_filter.setCurrentIndex(idx)
        self.user_filter.blockSignals(False)

    def refresh_logs(self):
        try:
            self.current_logs = audit_service.list_logs(
                limit=2000,
                user_id=self.user_filter.currentData(),
                action=self.action_filter.currentText(),
                table_name=self.table_filter.currentText(),
                start_date=self.start_date.date().toString('yyyy-MM-dd'),
                end_date=self.end_date.date().toString('yyyy-MM-dd'),
            )
            data = []
            for log in self.current_logs:
                data.append({
                    'id': log.get('id'),
                    'username': log.get('username'),
                    'action': log.get('action'),
                    'table_name': log.get('table_name'),
                    'record_id': log.get('record_id'),
                    'details': log.get('details'),
                    'ip_address': log.get('ip_address'),
                    'timestamp': log.get('timestamp'),
                })
            model = AuditLogTableModel(data)
            self.table.setModel(model)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table.refresh_style()
        except Exception as exc:
            QMessageBox.critical(self, 'خطأ', str(exc))

    def open_preview(self):
        try:
            report = audit_service.build_print_payload(self.current_logs)
            panel = PrintPreviewPanel(
                report['html'],
                title=report['title'],
                headers=report['headers'],
                rows=report['rows'],
                subtitle=report.get('subtitle'),
                default_filename=report.get('default_filename', 'audit_log'),
            )
            if self.shell:
                self.shell.open_inline(panel, 'معاينة سجل التدقيق')
            else:
                panel.show()
        except Exception as exc:
            QMessageBox.critical(self, 'خطأ', str(exc))

    def show_stats_inline(self):
        try:
            report = audit_service.build_stats_payload()
            panel = PrintPreviewPanel(
                report['html'],
                title=report['title'],
                headers=report['headers'],
                rows=report['rows'],
                subtitle=report.get('subtitle'),
                default_filename=report.get('default_filename', 'audit_stats'),
            )
            if self.shell:
                self.shell.open_inline(panel, 'إحصائيات التدقيق')
            else:
                panel.show()
        except Exception as exc:
            QMessageBox.critical(self, 'خطأ', str(exc))

    def delete_old_logs(self):
        reply = QMessageBox.question(self, 'تأكيد الحذف', 'حذف السجلات الأقدم من 90 يوم؟ لا يمكن التراجع.', QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            audit_service.delete_old_logs(90)
            self.refresh_logs()
            QMessageBox.information(self, 'نجاح', 'تم حذف السجلات القديمة')
        except Exception as exc:
            QMessageBox.critical(self, 'خطأ', str(exc))

    def export_to_excel(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'حفظ سجل التدقيق', 'audit_log.xlsx', 'Excel (*.xlsx);;CSV (*.csv)')
        if not filename:
            return
        try:
            report = audit_service.build_print_payload(self.current_logs)
            if filename.lower().endswith('.csv'):
                output = export_service.write_csv(filename, report['headers'], report['rows'])
            else:
                output = export_service.write_xlsx(filename, report['title'], report['headers'], report['rows'], report.get('subtitle'))
            QMessageBox.information(self, 'نجاح', f'تم التصدير إلى {output}')
        except Exception as exc:
            QMessageBox.critical(self, 'خطأ', str(exc))
