# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer

class Toast(QLabel):
    def __init__(self, parent, message, kind='info', duration=4500):
        super().__init__(parent)
        colors = {
            'info': ('#1d4ed8', '#eff6ff', '#bfdbfe'),
            'success': ('#047857', '#ecfdf5', '#a7f3d0'),
            'warning': ('#b45309', '#fffbeb', '#fcd34d'),
            'error': ('#b91c1c', '#fef2f2', '#fecaca'),
        }
        fg, bg, border = colors.get(kind, colors['info'])
        self.setText(message)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setStyleSheet(f"""
            QLabel {{
                color: {fg}; background: {bg}; border: 1px solid {border};
                border-radius: 10px; padding: 12px 16px; font-size: 13px; font-weight: 600;
            }}
        """)
        self.adjustSize()
        self.setMinimumWidth(360)
        self.setMaximumWidth(560)
        self.move(max(12, parent.width() - self.width() - 24), 24)
        self.show()
        self.raise_()
        QTimer.singleShot(duration, self.close)
