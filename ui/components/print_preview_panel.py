# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

from services.export_service import export_service
from services.audio_service import audio_service


class PrintPreviewPanel(QWidget):
    """Inline HTML preview panel.

    The preview remains inline. Print/PDF/Save actions may use native OS dialogs.
    When headers/rows are supplied, the panel can also export the exact same report
    data as Excel or CSV without recalculating financial values.
    """
    closed = pyqtSignal()

    def __init__(
        self,
        html: str,
        title: str = 'معاينة الطباعة',
        headers=None,
        rows=None,
        subtitle: str = None,
        default_filename: str = 'report',
        parent=None,
    ):
        super().__init__(parent)
        self.html = html
        self.title = title
        self.headers = list(headers or [])
        self.rows = list(rows or [])
        self.subtitle = subtitle
        self.default_filename = default_filename or 'report'
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        btns = QHBoxLayout()
        self.print_btn = QPushButton('🖨️ طباعة')
        self.print_btn.clicked.connect(self.print_now)
        self.pdf_btn = QPushButton('📄 حفظ PDF')
        self.pdf_btn.clicked.connect(self.save_pdf)
        self.xlsx_btn = QPushButton('📊 حفظ Excel')
        self.xlsx_btn.clicked.connect(self.save_xlsx)
        self.csv_btn = QPushButton('🧾 حفظ CSV')
        self.csv_btn.clicked.connect(self.save_csv)
        self.html_btn = QPushButton('🌐 حفظ HTML')
        self.html_btn.clicked.connect(self.save_html)
        self.close_btn = QPushButton('✖ إغلاق')
        self.close_btn.clicked.connect(self.request_close)

        can_export_rows = bool(self.headers)
        self.xlsx_btn.setEnabled(can_export_rows)
        self.csv_btn.setEnabled(can_export_rows)
        if not can_export_rows:
            self.xlsx_btn.setToolTip('يتطلب التقرير بيانات جدولية للتصدير')
            self.csv_btn.setToolTip('يتطلب التقرير بيانات جدولية للتصدير')

        btns.addWidget(self.print_btn)
        btns.addWidget(self.pdf_btn)
        btns.addWidget(self.xlsx_btn)
        btns.addWidget(self.csv_btn)
        btns.addWidget(self.html_btn)
        btns.addStretch(1)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        self.preview.setHtml(self.html)
        layout.addWidget(self.preview, 1)


    def request_close(self):
        """Request the host InlinePanel to close, with a standalone fallback."""
        self.closed.emit()
        # If the panel is shown standalone during debugging, `closed` may have no
        # receiver.  In that case, close the widget itself so the button still
        # behaves as users expect.
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, 'close_panel'):
                return
            parent = parent.parentWidget()
        self.close()

    def _document(self):
        doc = QTextDocument()
        doc.setHtml(self.html)
        return doc

    def _suggested(self, extension: str) -> str:
        return export_service.safe_filename(self.default_filename or self.title or 'report', extension)

    def print_now(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setLayoutDirection(Qt.RightToLeft)
        if dialog.exec_() == QPrintDialog.Accepted:
            self._document().print_(printer)

    def save_pdf(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'حفظ التقرير كـ PDF', self._suggested('pdf'), 'PDF (*.pdf)')
        if not filename:
            return
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(filename)
        self._document().print_(printer)
        audio_service.play_export_done()
        QMessageBox.information(self, 'نجاح', f'تم حفظ التقرير: {filename}')

    def save_xlsx(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'حفظ التقرير كـ Excel', self._suggested('xlsx'), 'Excel (*.xlsx)')
        if not filename:
            return
        try:
            output = export_service.write_xlsx(filename, self.title, self.headers, self.rows, subtitle=self.subtitle)
            audio_service.play_export_done()
            QMessageBox.information(self, 'نجاح', f'تم حفظ التقرير: {output}')
        except Exception as exc:
            audio_service.play_error()
            QMessageBox.critical(self, 'خطأ', str(exc))

    def save_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'حفظ التقرير كـ CSV', self._suggested('csv'), 'CSV (*.csv)')
        if not filename:
            return
        try:
            output = export_service.write_csv(filename, self.headers, self.rows)
            audio_service.play_export_done()
            QMessageBox.information(self, 'نجاح', f'تم حفظ التقرير: {output}')
        except Exception as exc:
            audio_service.play_error()
            QMessageBox.critical(self, 'خطأ', str(exc))

    def save_html(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'حفظ التقرير كـ HTML', self._suggested('html'), 'HTML (*.html)')
        if not filename:
            return
        try:
            output = export_service.write_html(filename, self.html)
            audio_service.play_export_done()
            QMessageBox.information(self, 'نجاح', f'تم حفظ التقرير: {output}')
        except Exception as exc:
            audio_service.play_error()
            QMessageBox.critical(self, 'خطأ', str(exc))
