from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QCheckBox, QComboBox, QMessageBox
from PyQt5.QtCore import Qt, QSettings
import qtawesome as qta
from views.frameless_dialog import FramelessDialog
from database import UserRepository
from auth.session import UserSession
from i18n.translator import translate, set_language
from theme_manager import ThemeManager

class LoginDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate('login'))
        self.resize(480, 520)
        self.setMinimumSize(420, 480)
        self.settings = QSettings("Hawaa", "Accounting")
        self.user_repo = UserRepository()

        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 20, 30, 30)

        # شعار
        logo = QLabel("🏢 هوى الشام")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {ThemeManager.get('primary')};")
        layout.addWidget(logo)

        subtitle = QLabel("نظام الحسابات الداخلية")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {ThemeManager.get('text_secondary')}; font-size: 13px;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # اسم المستخدم (قائمة منسدلة)
        self.username_combo = QComboBox()
        self.username_combo.setEditable(True)
        self.username_combo.setPlaceholderText(translate('username'))
        self.username_combo.setStyleSheet("padding: 8px; border-radius: 6px;")
        self._populate_users()
        layout.addWidget(self.username_combo)

        # كلمة المرور
        pwd_layout = QHBoxLayout()
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText(translate('password'))
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.show_pwd_btn = QPushButton()
        self.show_pwd_btn.setIcon(qta.icon('fa5s.eye'))
        self.show_pwd_btn.setFixedSize(40, 40)
        self.show_pwd_btn.setCheckable(True)
        self.show_pwd_btn.toggled.connect(self._toggle_password)
        pwd_layout.addWidget(self.password_edit)
        pwd_layout.addWidget(self.show_pwd_btn)
        layout.addLayout(pwd_layout)

        # خيارات
        options_layout = QHBoxLayout()
        self.remember_check = QCheckBox("تذكر المستخدم")
        self.remember_check.setStyleSheet(f"color: {ThemeManager.get('text_secondary')};")
        options_layout.addWidget(self.remember_check)
        options_layout.addStretch()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["العربية", "English", "Français"])
        self.lang_combo.setFixedWidth(100)
        self.lang_combo.currentIndexChanged.connect(self._change_lang)
        options_layout.addWidget(QLabel("اللغة:"))
        options_layout.addWidget(self.lang_combo)
        layout.addLayout(options_layout)

        self.error_label = QLabel()
        self.error_label.setStyleSheet(f"color: {ThemeManager.get('danger')}; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.error_label)
        layout.addSpacing(10)

        # زر تسجيل الدخول
        self.login_btn = QPushButton(translate('login'))
        self.login_btn.setObjectName("primary")
        self.login_btn.setMinimumHeight(45)
        self.login_btn.setStyleSheet(f"""
            QPushButton#primary {{
                background-color: {ThemeManager.get('primary')};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
            }}
            QPushButton#primary:hover {{
                background-color: {ThemeManager.get('primary_hover')};
            }}
        """)
        self.login_btn.clicked.connect(self._do_login)
        layout.addWidget(self.login_btn)

        # زر تبديل الحساب
        switch_btn = QPushButton("🔄 تبديل الحساب / مسح البيانات")
        switch_btn.setStyleSheet(f"background-color: transparent; color: {ThemeManager.get('text_muted')}; border: none; font-size: 12px;")
        switch_btn.clicked.connect(self._switch_account)
        layout.addWidget(switch_btn)

        self._load_saved_user()
        self.fade_in()

    def _populate_users(self):
        users = self.user_repo.get_all()
        self.username_combo.clear()
        for u in users:
            self.username_combo.addItem(u['username'])
        if users:
            self.username_combo.setCurrentIndex(0)

    def _toggle_password(self, checked):
        if checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
            self.show_pwd_btn.setIcon(qta.icon('fa5s.eye-slash'))
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
            self.show_pwd_btn.setIcon(qta.icon('fa5s.eye'))

    def _load_saved_user(self):
        saved = self.settings.value("login/username", "")
        if saved:
            idx = self.username_combo.findText(saved)
            if idx >= 0:
                self.username_combo.setCurrentIndex(idx)
            else:
                self.username_combo.setEditText(saved)
            self.remember_check.setChecked(True)
            self.password_edit.setFocus()

    def _save_user(self, username):
        if self.remember_check.isChecked():
            self.settings.setValue("login/username", username)
        else:
            self.settings.remove("login/username")

    def _switch_account(self):
        self.settings.remove("login/username")
        self.username_combo.setEditText("")
        self.password_edit.clear()
        self.remember_check.setChecked(False)
        self.error_label.setText("تم مسح بيانات المستخدم المخزنة")
        self.error_label.setStyleSheet(f"color: {ThemeManager.get('success')};")
        self._populate_users()

    def _change_lang(self, index):
        lang_map = {0: 'ar', 1: 'en', 2: 'fr'}
        new_lang = lang_map[index]
        set_language(new_lang)
        self.setWindowTitle(translate('login'))
        self.username_combo.setPlaceholderText(translate('username'))
        self.password_edit.setPlaceholderText(translate('password'))
        self.remember_check.setText("تذكر المستخدم")
        self.login_btn.setText(translate('login'))

    def _do_login(self):
        username = self.username_combo.currentText().strip()
        password = self.password_edit.text()
        if not username or not password:
            self.error_label.setText("يرجى إدخال اسم المستخدم وكلمة المرور")
            return
        user = self.user_repo.authenticate(username, password)
        if user:
            UserSession.login(user)
            self._save_user(username)
            self.accept()
        else:
            self.error_label.setText("اسم المستخدم أو كلمة المرور غير صحيحة")
            self.password_edit.clear()
            self.password_edit.setFocus()

    def showEvent(self, event):
        self.center()
        super().showEvent(event)

    def center(self):
        screen = self.screen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
