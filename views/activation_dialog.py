from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QMessageBox, QHBoxLayout, QApplication
from PyQt5.QtCore import Qt
from views.frameless_dialog import FramelessDialog
from auth.activation import activate
from theme_manager import ThemeManager

class ActivationDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تفعيل النظام")
        self.resize(500, 400)
        self.setMinimumSize(450, 380)

        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        logo = QLabel("🔐")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"font-size: 48px;")
        layout.addWidget(logo)

        title = QLabel("تفعيل نظام هوى الشام")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {ThemeManager.get('primary')};")
        layout.addWidget(title)

        desc = QLabel("أدخل مفتاح الترخيص للتفعيل عبر الإنترنت")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet(f"color: {ThemeManager.get('text_secondary')};")
        layout.addWidget(desc)

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_edit.setEchoMode(QLineEdit.Password)  # إخفاء محتوى المفتاح
        self.key_edit.setStyleSheet(f"padding: 12px; border-radius: 8px; border: 1px solid {ThemeManager.get('border')}; font-size: 14px; background-color: {ThemeManager.get('bg_window')}; color: {ThemeManager.get('text_primary')};")
        layout.addWidget(self.key_edit)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet(f"QProgressBar {{ border: none; background-color: {ThemeManager.get('border')}; border-radius: 4px; height: 6px; }} QProgressBar::chunk {{ background-color: {ThemeManager.get('primary')}; border-radius: 4px; }}")
        layout.addWidget(self.progress)

        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {ThemeManager.get('danger')}; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.activate_btn = QPushButton("تفعيل")
        self.activate_btn.setObjectName("primary")
        self.activate_btn.setStyleSheet(f"""
            QPushButton#primary {{
                background-color: {ThemeManager.get('primary')};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton#primary:hover {{
                background-color: {ThemeManager.get('primary_hover')};
            }}
        """)
        self.activate_btn.clicked.connect(self._activate)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ThemeManager.get('bg_panel')};
                color: {ThemeManager.get('text_primary')};
                border: 1px solid {ThemeManager.get('border')};
                border-radius: 8px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {ThemeManager.get('border')};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.activate_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.fade_in()

    def _activate(self):
        key = self.key_edit.text().strip()
        if not key:
            self.status_label.setText("يرجى إدخال مفتاح الترخيص")
            return
        self.activate_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status_label.setText("جاري الاتصال بالخادم...")
        self.status_label.setStyleSheet(f"color: {ThemeManager.get('info')};")
        success, msg = activate(key)
        self.progress.setVisible(False)
        self.activate_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "نجاح", "تم التفعيل بنجاح! سيتم إعادة تشغيل التطبيق.")
            self.accept()
        else:
            self.status_label.setText(f"فشل التفعيل: {msg}")
            self.status_label.setStyleSheet(f"color: {ThemeManager.get('danger')};")
