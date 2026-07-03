# -*- coding: utf-8 -*-
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QDateEdit, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt, QDate

from i18n.translator import translate
from models.table_models import ReportTableModel
from services.report_service import report_service, REPORT_TYPES
from ui.components.print_preview_panel import PrintPreviewPanel
from views.custom_table_view import CustomTableView


class ReportsDocument(QWidget):
    """Inline reports document using ReportService + PrintService."""
    def __init__(self, shell=None, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.current_report = None
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        title = QLabel('التقارير')
        title.setObjectName('DocumentTitle')
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.addWidget(QLabel('نوع التقرير:'))
        self.report_type_combo = QComboBox()
        for key, label in REPORT_TYPES.items():
            self.report_type_combo.addItem(label, key)
        controls.addWidget(self.report_type_combo)

        controls.addWidget(QLabel(translate('period') + ':'))
        self.period_type = QComboBox()
        self.period_type.addItems(['شهر محدد', 'سنة محددة', 'فترة مخصصة'])
        self.period_type.currentIndexChanged.connect(self._on_period_changed)
        controls.addWidget(self.period_type)

        self.year_combo = QComboBox()
        current_year = datetime.now().year
        for year in range(current_year - 5, current_year + 2):
            self.year_combo.addItem(str(year))
        self.year_combo.setCurrentText(str(current_year))
        controls.addWidget(self.year_combo)

        self.month_combo = QComboBox()
        self.month_combo.addItems(['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'])
        self.month_combo.setCurrentIndex(datetime.now().month - 1)
        controls.addWidget(self.month_combo)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        controls.addWidget(self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        controls.addWidget(self.end_date)

        refresh_btn = QPushButton('🔄 ' + translate('refresh_report'))
        refresh_btn.clicked.connect(self.refresh_report)
        preview_btn = QPushButton('🖨️ معاينة الطباعة')
        preview_btn.clicked.connect(self.open_preview)
        controls.addWidget(refresh_btn)
        controls.addWidget(preview_btn)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.note_label = QLabel('التقارير تعتمد على amount_base بالدولار ثم تُعرض حسب عملة العرض الحالية. لا يتم إعادة تسعير القيود التاريخية.')
        self.note_label.setWordWrap(True)
        self.note_label.setObjectName('DocumentHint')
        layout.addWidget(self.note_label)

        self.subtitle_label = QLabel('')
        self.subtitle_label.setObjectName('ReportSubtitle')
        layout.addWidget(self.subtitle_label)

        self.table = CustomTableView()
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        layout.addWidget(self.table, 1)
        self._on_period_changed()

    def activate(self, **_params):
        self.refresh_report()

    def _on_period_changed(self):
        period = self.period_type.currentIndex()
        self.year_combo.setVisible(period in (0, 1))
        self.month_combo.setVisible(period == 0)
        self.start_date.setVisible(period == 2)
        self.end_date.setVisible(period == 2)

    def _date_range(self):
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
        return start.toString('yyyy-MM-dd'), end.toString('yyyy-MM-dd')

    def refresh_report(self):
        start, end = self._date_range()
        report_type = self.report_type_combo.currentData()
        try:
            self.current_report = report_service.build(report_type, start, end)
            self.subtitle_label.setText(self.current_report['subtitle'])
            self.model = ReportTableModel(self.current_report['headers'], self.current_report['rows'])
            self.table.setModel(self.model)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table.refresh_style()
        except Exception as exc:
            QMessageBox.critical(self, translate('error'), str(exc))

    def open_preview(self):
        if not self.current_report:
            self.refresh_report()
        if not self.current_report:
            return
        panel = PrintPreviewPanel(
            self.current_report['html'],
            title=self.current_report.get('title', 'تقرير'),
            headers=self.current_report.get('headers'),
            rows=self.current_report.get('rows'),
            subtitle=self.current_report.get('subtitle'),
            default_filename=self.current_report.get('default_filename', 'report'),
        )
        if self.shell:
            self.shell.open_inline(panel, 'معاينة التقرير')
        else:
            panel.show()
