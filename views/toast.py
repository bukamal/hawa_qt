# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from services.audio_service import audio_service


class Toast(QLabel):
    def __init__(self, parent, message, kind='info', duration=4500, sound_id=None, play_sound=True):
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
        self.setObjectName('Toast')
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setStyleSheet(f"""
            QLabel#Toast {{
                color: {fg}; background: {bg}; border: 1px solid {border};
                border-radius: 12px; padding: 12px 16px; font-size: 13px; font-weight: 600;
            }}
        """)
        self.adjustSize()
        self.setMinimumWidth(360)
        self.setMaximumWidth(560)
        self._target = QPoint(max(12, parent.width() - self.width() - 24), 24)
        self.move(self._target + QPoint(0, -18))
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0)
        self.show()
        self.raise_()
        if play_sound:
            mapped_sound = sound_id or {'success': 'success', 'error': 'error', 'warning': 'warning', 'info': 'notify'}.get(kind, 'notify')
            audio_service.play(mapped_sound)
        self._animate_in()
        QTimer.singleShot(duration, self._animate_out)

    def _animate_in(self):
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(160)
        self._fade.setStartValue(0)
        self._fade.setEndValue(1)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setDuration(160)
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(self._target)
        self._slide.setEasingCurve(QEasingCurve.OutCubic)
        self._fade.start()
        self._slide.start()

    def _animate_out(self):
        self._fade_out = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_out.setDuration(160)
        self._fade_out.setStartValue(1)
        self._fade_out.setEndValue(0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self.close)
        self._fade_out.start()
