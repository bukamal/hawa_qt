# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QWidget, QApplication, QFrame
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer
from PyQt5.QtGui import QPixmap
from branding import APP_DISPLAY_NAME_AR, APP_TAGLINE_AR, branding_path


class ModernSplashScreen(QSplashScreen):
    """Branded startup/loading screen.

    Used both before activation/login and again after login while the main
    Document Shell is prepared. It is intentionally lightweight and does not
    execute startup logic itself.
    """

    def __init__(self):
        pixmap = QPixmap(680, 440)
        pixmap.fill(Qt.transparent)
        super().__init__(pixmap)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        container = QWidget(self)
        container.setGeometry(0, 0, 680, 440)
        container.setObjectName("SplashContainer")
        container.setStyleSheet("""
            QWidget#SplashContainer {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f172a, stop:0.42 #134e4a, stop:0.78 #0f766e, stop:1 #d97706);
                border-radius: 26px;
            }
            QWidget#SplashContainer QLabel {
                background: transparent;
            }
        """)
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(46, 34, 46, 34)
        layout.setSpacing(16)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        symbol = QPixmap(branding_path("app_symbol_512.png"))
        if not symbol.isNull():
            logo.setPixmap(symbol.scaled(92, 92, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo.setText(APP_DISPLAY_NAME_AR)
            logo.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        layout.addWidget(logo)

        title = QLabel(APP_DISPLAY_NAME_AR)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: 900; color: white;")
        layout.addWidget(title)

        subtitle = QLabel(APP_TAGLINE_AR)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: rgba(255,255,255,0.82);")
        layout.addWidget(subtitle)

        status_card = QFrame()
        status_card.setObjectName("SplashStatusCard")
        status_card.setStyleSheet("""
            QFrame#SplashStatusCard {
                background-color: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.22);
                border-radius: 14px;
            }
        """)
        card_layout = QVBoxLayout(status_card)
        card_layout.setContentsMargins(22, 16, 22, 16)
        card_layout.setSpacing(9)

        self.phase_label = QLabel("مرحلة التشغيل")
        self.phase_label.setAlignment(Qt.AlignCenter)
        self.phase_label.setStyleSheet("color: white; font-weight: 800; font-size: 13px;")
        card_layout.addWidget(self.phase_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setFixedWidth(460)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: rgba(255,255,255,0.22);
                border-radius: 5px;
                height: 10px;
                text-align: center;
                color: white;
                font-size: 10px;
                font-weight: 700;
            }
            QProgressBar::chunk {
                background-color: white;
                border-radius: 5px;
            }
        """)
        card_layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        self.status_label = QLabel("جارٍ تهيئة النظام...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.78); font-size: 12px;")
        card_layout.addWidget(self.status_label)
        layout.addWidget(status_card, alignment=Qt.AlignCenter)

        self.footer_label = QLabel("يرجى الانتظار — يتم فحص البيانات والترخيص قبل فتح الواجهة")
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet("color: rgba(255,255,255,0.64); font-size: 11px;")
        layout.addWidget(self.footer_label)

        self.setWindowOpacity(0)
        self._is_finishing = False
        self.show()
        self._fade_in()

    def _fade_in(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(350)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()
        self.animation = anim

    def set_progress(self, value: int, message: str = None, phase: str = None):
        value = max(0, min(100, value))
        self.progress.setValue(value)
        if message:
            self.status_label.setText(message)
        if phase:
            self.phase_label.setText(phase)
        QApplication.processEvents()

    def set_error(self, message: str):
        self.phase_label.setText("تعذر إكمال التشغيل")
        self.status_label.setText(message)
        self.progress.setStyleSheet("""
            QProgressBar { border: none; background-color: rgba(255,255,255,0.22); border-radius: 5px; height: 10px; color: white; }
            QProgressBar::chunk { background-color: #ef4444; border-radius: 5px; }
        """)
        QApplication.processEvents()

    def finish(self, main_window):
        """Fade out, close safely, then release the splash screen.

        PyQt's zero-argument ``super()`` is unsafe inside nested lambdas; it
        caused a runtime exception after the main window had already opened.
        We keep an explicit slot and call ``QSplashScreen.finish`` directly.
        """
        if getattr(self, '_is_finishing', False):
            return
        self._is_finishing = True

        completed = {'value': False}

        def _complete_finish():
            if completed['value']:
                return
            completed['value'] = True
            try:
                if main_window is not None and not main_window.isVisible():
                    main_window.show()
                QSplashScreen.finish(self, main_window)
            except RuntimeError:
                # The splash may already be closing/deleted on some platforms.
                pass
            finally:
                self.close()
                self.deleteLater()

        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(220)
        anim.setStartValue(max(0.0, float(self.windowOpacity())))
        anim.setEndValue(0)
        anim.finished.connect(_complete_finish)
        anim.start()
        self.animation = anim
        # Safety net: do not leave a splash behind if the animation signal is
        # swallowed by the window manager.
        QTimer.singleShot(320, _complete_finish)
