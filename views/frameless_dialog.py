from PyQt5.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame, QWidget, QApplication
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QTimer
import qtawesome as qta
from theme_manager import ThemeManager

class FramelessDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        # RTL
        self.setLayoutDirection(Qt.RightToLeft)
        self.drag_pos = None
        
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("MainFrame")
        self.main_frame.setStyleSheet(f"""
            #MainFrame {{
                background-color: {ThemeManager.get('bg_sidebar')};
                border-radius: 16px;
                border: 1px solid {ThemeManager.get('border')};
            }}
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.main_frame)
        
        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(45)
        self.title_bar.setStyleSheet(f"""
            background-color: {ThemeManager.get('bg_panel')};
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        """)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        title_layout.addWidget(self.icon_label)
        
        self.title_label = QLabel("نافذة")
        self.title_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {ThemeManager.get('text_primary')};")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon('fa5s.times'))
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.clicked.connect(self.reject)
        title_layout.addWidget(self.close_btn)
        
        self.max_btn = QPushButton()
        self.max_btn.setIcon(qta.icon('fa5s.window-maximize'))
        self.max_btn.setFixedSize(32, 32)
        self.max_btn.setVisible(False)
        title_layout.addWidget(self.max_btn)
        
        self.min_btn = QPushButton()
        self.min_btn.setIcon(qta.icon('fa5s.window-minimize'))
        self.min_btn.setFixedSize(32, 32)
        self.min_btn.setStyleSheet(f"border: none; border-radius: 4px; color: {ThemeManager.get('text_secondary')};")
        self.min_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.min_btn)
        
        self.content_widget = QWidget()
        
        container_layout = QVBoxLayout(self.main_frame)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.title_bar)
        container_layout.addWidget(self.content_widget)
        
        self.title_bar.mousePressEvent = self._mouse_press
        self.title_bar.mouseMoveEvent = self._mouse_move
        self.title_bar.mouseReleaseEvent = self._mouse_release
        
        self.setStyleSheet(ThemeManager.get_stylesheet())
        
        # مؤقت للتحقق الدوري من موقع النافذة الرئيسية (حل احتياطي)
        self._position_timer = QTimer(self)
        self._position_timer.timeout.connect(self._check_main_window_position)
        self._position_timer.start(150)
        self._last_main_window_pos = None
    
    def _mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def _mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
    
    def _mouse_release(self, event):
        self.drag_pos = None
    
    def setWindowTitle(self, title):
        self.title_label.setText(title)
        super().setWindowTitle(title)
    
    def fade_in(self):
        self.setWindowOpacity(0)
        self.show()
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()
        self.animation = anim
    
    def _check_main_window_position(self):
        main_window = self.window()
        if main_window and main_window != self and main_window.isVisible() and not self.isHidden():
            current_pos = main_window.pos()
            if self._last_main_window_pos != current_pos:
                self._last_main_window_pos = current_pos
                self._center_on_main_window()
    
    def _center_on_main_window(self):
        main_window = self.window()
        if main_window and main_window != self and main_window.isVisible():
            main_geo = main_window.geometry()
            main_center = main_geo.center()
            dialog_geo = self.geometry()
            x = main_center.x() - dialog_geo.width() // 2
            y = main_center.y() - dialog_geo.height() // 2
            screen = self.screen().geometry()
            x = max(screen.left(), min(x, screen.right() - dialog_geo.width()))
            y = max(screen.top(), min(y, screen.bottom() - dialog_geo.height()))
            self.move(x, y)
        else:
            screen = self.screen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)
    
    def showEvent(self, event):
        super().showEvent(event)
        main_window = self.window()
        if main_window and main_window != self and hasattr(main_window, 'window_moved'):
            main_window.window_moved.connect(self._center_on_main_window)
        self._center_on_main_window()
    
    def exec(self):
        return super().exec()
    
    def exec_(self):
        return self.exec()
