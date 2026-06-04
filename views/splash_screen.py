from PyQt5.QtWidgets import QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QWidget, QApplication
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QPixmap

class ModernSplashScreen(QSplashScreen):
    def __init__(self):
        pixmap = QPixmap(600, 400)
        pixmap.fill(Qt.transparent)
        super().__init__(pixmap)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        container = QWidget(self)
        container.setGeometry(0, 0, 600, 400)
        container.setStyleSheet("""
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #4f46e5, stop:1 #7c3aed);
            border-radius: 24px;
        """)
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        logo = QLabel("🏢 هوى الشام")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        layout.addWidget(logo)

        subtitle = QLabel("نظام الحسابات الداخلية")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: rgba(255,255,255,0.8);")
        layout.addWidget(subtitle)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setFixedWidth(400)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: rgba(255,255,255,0.2);
                border-radius: 4px;
                height: 8px;
                text-align: center;
                color: white;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: white;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        self.status_label = QLabel("جاري تهيئة النظام...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px;")
        layout.addWidget(self.status_label)

        self.setWindowOpacity(0)
        self.show()
        self._fade_in()

    def _fade_in(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(500)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()
        self.animation = anim

    def set_progress(self, value: int, message: str = None):
        value = max(0, min(100, value))
        self.progress.setValue(value)
        if message:
            self.status_label.setText(message)
        QApplication.processEvents()

    def finish(self, main_window):
        """تأثير تلاشي ثم إغلاق الشاشة وظهور النافذة الرئيسية"""
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.finished.connect(lambda: super().finish(main_window))
        anim.start()
