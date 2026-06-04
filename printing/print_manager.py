# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QComboBox, QSpinBox, QCheckBox, QLabel, QGroupBox,
                             QFormLayout, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (QTextDocument, QFont, QTextCursor, QTextBlockFormat,
                         QTextCharFormat, QTextTableFormat, QTextLength, QPixmap)
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintDialog
from config import get_company_info
from utils import clean_text

class PrintManager:
    @staticmethod
    def get_printer_settings(parent=None):
        dialog = QDialog(parent)
        dialog.setWindowTitle("إعدادات الطباعة")
        dialog.setLayoutDirection(Qt.LeftToRight)  # LTR
        dialog.resize(450, 400)
        layout = QVBoxLayout(dialog)

        printer_group = QGroupBox("إعدادات الطابعة")
        printer_layout = QFormLayout(printer_group)
        from printer_manager import PrinterManager
        pm = PrinterManager()
        pm.load_default_printer()
        printer_combo = QComboBox()
        for p in pm.printers:
            printer_combo.addItem(p.name, p.id)
        printer_layout.addRow("الطابعة:", printer_combo)
        copies_spin = QSpinBox()
        copies_spin.setRange(1, 99)
        copies_spin.setValue(1)
        printer_layout.addRow("عدد النسخ:", copies_spin)
        color_check = QCheckBox("طباعة بالألوان")
        color_check.setChecked(True)
        printer_layout.addRow(color_check)
        layout.addWidget(printer_group)

        paper_group = QGroupBox("إعدادات الورق")
        paper_layout = QFormLayout(paper_group)
        paper_size_combo = QComboBox()
        paper_size_combo.addItems(["A4", "A5", "Letter", "Legal", "B5"])
        paper_size_combo.setCurrentText("A4")
        paper_layout.addRow("حجم الورق:", paper_size_combo)
        orientation_combo = QComboBox()
        orientation_combo.addItems(["عمودي", "أفقي"])
        paper_layout.addRow("الاتجاه:", orientation_combo)
        layout.addWidget(paper_group)

        options_group = QGroupBox("خيارات إضافية")
        options_layout = QFormLayout(options_group)
        show_logo_check = QCheckBox("إظهار شعار الشركة")
        show_logo_check.setChecked(True)
        options_layout.addRow(show_logo_check)
        show_footer_check = QCheckBox("إظهار التذييل")
        show_footer_check.setChecked(True)
        options_layout.addRow(show_footer_check)
        layout.addWidget(options_group)

        btn_layout = QHBoxLayout()
        preview_btn = QPushButton("معاينة")
        preview_btn.setObjectName("primary")
        print_btn = QPushButton("طباعة")
        cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(print_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        settings = {'printer_id': None, 'copies': 1, 'color': True,
                    'paper_size': 'A4', 'orientation': 0,
                    'show_logo': True, 'show_footer': True}

        def on_preview():
            settings['printer_id'] = printer_combo.currentData()
            settings['copies'] = copies_spin.value()
            settings['color'] = color_check.isChecked()
            settings['paper_size'] = paper_size_combo.currentText()
            settings['orientation'] = 1 if orientation_combo.currentIndex() == 1 else 0
            settings['show_logo'] = show_logo_check.isChecked()
            settings['show_footer'] = show_footer_check.isChecked()
            dialog.accept()
            return settings

        def on_print():
            settings.update(on_preview())
            dialog.done(2)

        preview_btn.clicked.connect(on_preview)
        print_btn.clicked.connect(on_print)
        cancel_btn.clicked.connect(dialog.reject)

        result = dialog.exec()
        if result == QDialog.Accepted:
            return settings
        elif result == 2:
            settings['direct_print'] = True
            return settings
        return None

    @staticmethod
    def create_printer(settings):
        printer = QPrinter(QPrinter.HighResolution)
        if settings.get('orientation', 0) == 1:
            printer.setOrientation(QPrinter.Landscape)
        else:
            printer.setOrientation(QPrinter.Portrait)
        printer.setCopyCount(settings.get('copies', 1))
        printer.setColorMode(QPrinter.Color if settings.get('color', True) else QPrinter.GrayScale)
        printer_id = settings.get('printer_id')
        if printer_id:
            from printer_manager import PrinterManager
            pm = PrinterManager()
            printer_info = pm.get_printer(printer_id)
            if printer_info and printer_info.type.value != 'pdf':
                printer.setPrinterName(printer_info.name)
        return printer

    @staticmethod
    def build_report_document(title, headers, data, parent=None, settings=None):
        if settings is None:
            settings = {'show_logo': True, 'show_footer': True}
        company_info = get_company_info()
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")

        doc = QTextDocument()
        doc.setDefaultFont(QFont("Tajawal", 10))
        # إعدادات LTR
        default_opt = doc.defaultTextOption()
        default_opt.setAlignment(Qt.AlignLeft)
        default_opt.setTextDirection(Qt.LeftToRight)
        doc.setDefaultTextOption(default_opt)

        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        # تنسيق الكتلة LTR
        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(Qt.AlignLeft)
        block_fmt.setLayoutDirection(Qt.LeftToRight)

        # اسم الشركة
        cursor.insertBlock(block_fmt)
        char_fmt_bold = QTextCharFormat()
        char_fmt_bold.setFontWeight(QFont.Bold)
        char_fmt_bold.setFontPointSize(16)
        cursor.setCharFormat(char_fmt_bold)
        cursor.insertText(clean_text(company_info.get('name', 'هوى الشام')))

        # تفاصيل الشركة
        cursor.insertBlock(block_fmt)
        char_fmt_normal = QTextCharFormat()
        char_fmt_normal.setFontPointSize(10)
        cursor.setCharFormat(char_fmt_normal)
        address = clean_text(company_info.get('address', ''))
        phone = clean_text(company_info.get('phone', ''))
        email = clean_text(company_info.get('email', ''))
        cursor.insertText(f"{address}\nهاتف: {phone} | بريد: {email}")

        # شعار الشركة
        if settings.get('show_logo') and company_info.get('logo_path') and os.path.exists(company_info['logo_path']):
            cursor.insertBlock(block_fmt)
            img = QPixmap(company_info['logo_path'])
            if not img.isNull():
                img = img.scaledToWidth(80, Qt.SmoothTransformation)
                cursor.insertImage(img)

        # عنوان التقرير
        cursor.insertBlock(block_fmt)
        char_fmt_title = QTextCharFormat()
        char_fmt_title.setFontWeight(QFont.Bold)
        char_fmt_title.setFontPointSize(14)
        cursor.setCharFormat(char_fmt_title)
        cursor.insertText(clean_text(title))

        # التاريخ
        cursor.insertBlock(block_fmt)
        cursor.setCharFormat(char_fmt_normal)
        cursor.insertText(f"التاريخ: {date_str}")

        cursor.insertBlock(block_fmt)
        cursor.insertText(" ")

        # إنشاء الجدول
        if headers and data:
            rows = len(data) + 1
            cols = len(headers)
            table_fmt = QTextTableFormat()
            table_fmt.setAlignment(Qt.AlignLeft)
            table_fmt.setHeaderRowCount(1)
            table_fmt.setCellPadding(4)
            table_fmt.setCellSpacing(0)
            table_fmt.setBorder(1)
            table_fmt.setBorderStyle(QTextTableFormat.BorderStyle_Solid)
            for _ in range(cols):
                table_fmt.setColumnWidthConstraints([QTextLength(QTextLength.PercentageLength, 100/cols)])

            table = cursor.insertTable(rows, cols, table_fmt)

            # رأس الجدول
            bold_char_fmt = QTextCharFormat()
            bold_char_fmt.setFontWeight(QFont.Bold)
            for c, header in enumerate(headers):
                cell = table.cellAt(0, c)
                cell_cursor = cell.firstCursorPosition()
                cell_cursor.setCharFormat(bold_char_fmt)
                cell_block_fmt = QTextBlockFormat()
                cell_block_fmt.setAlignment(Qt.AlignLeft)
                cell_cursor.setBlockFormat(cell_block_fmt)
                cell_cursor.insertText(clean_text(header))

            # البيانات
            for r, row in enumerate(data):
                for c, cell_text in enumerate(row):
                    cell = table.cellAt(r+1, c)
                    cell_cursor = cell.firstCursorPosition()
                    cell_cursor.setCharFormat(char_fmt_normal)
                    cell_block_fmt = QTextBlockFormat()
                    # محاذاة الأرقام وسطاً
                    if re.match(r'^[\d\.,\-\+]+$', clean_text(cell_text).strip()):
                        cell_block_fmt.setAlignment(Qt.AlignCenter)
                    else:
                        cell_block_fmt.setAlignment(Qt.AlignLeft)
                    cell_cursor.setBlockFormat(cell_block_fmt)
                    cell_cursor.insertText(clean_text(cell_text))

            cursor.movePosition(QTextCursor.End)

        cursor.insertBlock(block_fmt)

        # التذييل
        if settings.get('show_footer'):
            cursor.insertBlock(block_fmt)
            footer_fmt = QTextCharFormat()
            footer_fmt.setFontPointSize(8)
            footer_fmt.setForeground(Qt.gray)
            cursor.setCharFormat(footer_fmt)
            cursor.insertText(f"نظام هوى الشام - جميع الحقوق محفوظة © {now.year}\nطبعت: {date_str}")

        cursor.endEditBlock()
        return doc

    @staticmethod
    def print_report(title, headers, data, parent=None, direct=False):
        if not data:
            QMessageBox.warning(parent, "تنبيه", "لا توجد بيانات للطباعة")
            return False

        settings = PrintManager.get_printer_settings(parent)
        if not settings:
            return False

        doc = PrintManager.build_report_document(title, headers, data, parent, settings)
        printer = PrintManager.create_printer(settings)

        if settings.get('direct_print') or direct:
            dlg = QPrintDialog(printer, parent)
            if dlg.exec() == QPrintDialog.Accepted:
                doc.print(printer)
                QMessageBox.information(parent, "نجاح", "تمت الطباعة")
                return True
        else:
            preview = QPrintPreviewDialog(printer, parent)
            preview.setLayoutDirection(Qt.LeftToRight)
            preview.paintRequested.connect(lambda p: doc.print(p))
            preview.exec()
            return True
        return False

    @staticmethod
    def print_table(table_view, title, parent=None):
        model = table_view.model()
        if not model or model.rowCount() == 0:
            QMessageBox.warning(parent, "تنبيه", "لا توجد بيانات في الجدول")
            return False
        headers = [str(model.headerData(i, Qt.Horizontal, Qt.DisplayRole) or f"عمود{i+1}") for i in range(model.columnCount())]
        data = []
        for r in range(model.rowCount()):
            row = [str(model.data(model.index(r, c), Qt.DisplayRole) or '') for c in range(model.columnCount())]
            data.append(row)
        return PrintManager.print_report(title, headers, data, parent)

    @staticmethod
    def save_as_pdf(title, headers, data, parent=None):
        if not data:
            QMessageBox.warning(parent, "تنبيه", "لا توجد بيانات")
            return False
        filename, _ = QFileDialog.getSaveFileName(parent, "حفظ PDF", f"{title}.pdf", "PDF (*.pdf)")
        if not filename:
            return False
        settings = {'show_logo': True, 'show_footer': True}
        doc = PrintManager.build_report_document(title, headers, data, parent, settings)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(filename)
        doc.print(printer)
        QMessageBox.information(parent, "نجاح", f"تم الحفظ: {filename}")
        return True
