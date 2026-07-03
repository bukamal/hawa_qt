# -*- coding: utf-8 -*-
"""Reusable inline error panel for Document Shell failures."""
from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal


class ErrorView(QWidget):
    retry_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ErrorView")
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self.title = QLabel("تعذر فتح هذا المستند")
        self.title.setObjectName("DocumentTitle")
        self.message = QLabel("حدث خطأ أثناء تحميل الصفحة. تم تسجيل التفاصيل في ملف الأخطاء.")
        self.message.setWordWrap(True)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setVisible(False)
        self.details.setMinimumHeight(180)
        self.retry_button = QPushButton("إعادة المحاولة")
        self.details_button = QPushButton("عرض التفاصيل التقنية")
        self.details_button.clicked.connect(self._toggle_details)
        self.retry_button.clicked.connect(self.retry_requested.emit)

        layout.addWidget(self.title)
        layout.addWidget(self.message)
        layout.addWidget(self.details)
        layout.addWidget(self.retry_button)
        layout.addWidget(self.details_button)
        layout.addStretch(1)

    def set_error(self, title: str, message: str, details: str = "") -> None:
        self.title.setText(title or "تعذر فتح هذا المستند")
        self.message.setText(message or "حدث خطأ أثناء تحميل الصفحة.")
        self.details.setPlainText(details or "")
        self.details_button.setVisible(bool(details))

    def _toggle_details(self):
        self.details.setVisible(not self.details.isVisible())
        self.details_button.setText("إخفاء التفاصيل التقنية" if self.details.isVisible() else "عرض التفاصيل التقنية")
