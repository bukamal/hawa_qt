# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt, pyqtSignal

from ui.effects import animate_width


class InlinePanel(QFrame):
    """Reusable right-side inline editor/preview host with a light slide effect."""
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('InlinePanel')
        self.expanded_width = 460
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)
        self.setVisible(False)
        self._content = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(10)
        self._empty = QLabel('لا يوجد محرر مفتوح')
        self._empty.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._empty)

    def set_content(self, widget: QWidget, title: str = None):
        self.clear()
        if title:
            label = QLabel(title)
            label.setObjectName('InlinePanelTitle')
            self._layout.addWidget(label)
        self._content = widget
        self._layout.addWidget(widget)
        self.setVisible(True)
        self.raise_()
        animate_width(self, max(0, self.width()), self.expanded_width, duration=190)

    def clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self._content = None

    def close_panel(self):
        if self._content and hasattr(self._content, 'confirm_discard_changes'):
            if not self._content.confirm_discard_changes():
                return False

        def finish_close():
            self.clear()
            self._layout.addWidget(self._empty)
            self.setVisible(False)
            self.closed.emit()

        animate_width(self, max(0, self.width()), 0, duration=160, finished=finish_close)
        return True
