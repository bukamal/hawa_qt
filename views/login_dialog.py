# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QCheckBox,
    QComboBox, QFrame, QSizePolicy, QWidget
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPixmap
import qtawesome as qta

from views.frameless_dialog import FramelessDialog
from database import UserRepository
from database.connection import DatabaseConnection
from auth.session import UserSession
from i18n.translator import translate, set_language
from theme_manager import ThemeManager
from services.audio_service import audio_service
from branding import APP_DISPLAY_NAME_AR, APP_TAGLINE_AR, branding_path
from ui.auth.brand_panel import BrandHeader, BrandCard, StatusPill


class LoginDialog(FramelessDialog):
    """Branded login screen.

    The old dialog was functional but visually disconnected from the project
    identity. This class keeps the existing authentication logic while making
    the first screen use the same logo, palette, inline errors and audio cues as
    the Document Shell.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("تسجيل الدخول")
        self.resize(600, 720)
        self.setMinimumSize(540, 660)
        self.settings = QSettings("Hawaa", "Accounting")
        self.user_repo = UserRepository()
        self.db_conn = DatabaseConnection()

        try:
            icon = QPixmap(branding_path("app_icon_32.png"))
            if not icon.isNull():
                self.icon_label.setPixmap(icon.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass

        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(34, 20, 34, 24)

        layout.addWidget(BrandHeader("تسجيل آمن إلى مساحة الحسابات", logo_size=78))

        mode_text = "وضع محلي" if not self.db_conn.is_remote() else "اتصال شبكي"
        mode_tone = "success" if not self.db_conn.is_remote() else "info"
        mode_layout = QHBoxLayout()
        mode_layout.addStretch()
        mode_layout.addWidget(StatusPill(mode_text, mode_tone))
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        card = BrandCard()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 22, 26, 22)
        card_layout.setSpacing(14)

        title = QLabel("بيانات الدخول")
        title.setAlignment(Qt.AlignRight)
        title.setStyleSheet(f"background: transparent; font-size: 16px; font-weight: 800; color: {ThemeManager.get('text_primary')};")
        card_layout.addWidget(title)

        self.username_combo = QComboBox()
        self.username_combo.setEditable(True)
        self.username_combo.setPlaceholderText(translate('username'))
        self.username_combo.setMinimumHeight(44)
        self.username_combo.setStyleSheet(self._input_style())
        self._populate_users()
        card_layout.addWidget(self._field_with_label("اسم المستخدم", self.username_combo))

        pwd_layout = QHBoxLayout()
        pwd_layout.setContentsMargins(0, 0, 0, 0)
        pwd_layout.setSpacing(8)
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText(translate('password'))
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(44)
        self.password_edit.setStyleSheet(self._input_style())
        self.password_edit.returnPressed.connect(self._do_login)
        self.show_pwd_btn = QPushButton()
        self.show_pwd_btn.setIcon(qta.icon('fa5s.eye'))
        self.show_pwd_btn.setFixedSize(44, 44)
        self.show_pwd_btn.setCursor(Qt.PointingHandCursor)
        self.show_pwd_btn.setStyleSheet("QPushButton { border-radius: 9px; padding: 0; }")
        self.show_pwd_btn.setCheckable(True)
        self.show_pwd_btn.setToolTip("إظهار/إخفاء كلمة المرور")
        self.show_pwd_btn.toggled.connect(self._toggle_password)
        pwd_layout.addWidget(self.password_edit)
        pwd_layout.addWidget(self.show_pwd_btn)
        pwd_widget = QWidget()
        pwd_widget.setLayout(pwd_layout)
        pwd_widget.setMinimumHeight(48)
        pwd_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card_layout.addWidget(self._field_with_label("كلمة المرور", pwd_widget))

        options_frame = QWidget()
        options_frame.setMinimumHeight(44)
        options_layout = QHBoxLayout(options_frame)
        options_layout.setContentsMargins(0, 4, 0, 0)
        options_layout.setSpacing(10)
        self.remember_check = QCheckBox("تذكر المستخدم")
        self.remember_check.setStyleSheet(f"background: transparent; color: {ThemeManager.get('text_secondary')}; font-weight: 600;")
        options_layout.addWidget(self.remember_check)
        options_layout.addStretch()
        lang_label = QLabel("اللغة:")
        lang_label.setStyleSheet(f"background: transparent; color: {ThemeManager.get('text_secondary')}; font-weight: 700;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["العربية", "English", "Français"])
        self.lang_combo.setFixedWidth(126)
        self.lang_combo.setMinimumHeight(36)
        self.lang_combo.currentIndexChanged.connect(self._change_lang)
        options_layout.addWidget(lang_label)
        options_layout.addWidget(self.lang_combo)
        card_layout.addWidget(options_frame)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setVisible(False)
        self.error_label.setStyleSheet(self._message_style("danger"))
        card_layout.addWidget(self.error_label)

        self.login_btn = QPushButton("تسجيل الدخول")
        self.login_btn.setObjectName("primary")
        self.login_btn.setMinimumHeight(46)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._do_login)
        card_layout.addWidget(self.login_btn)

        switch_btn = QPushButton("مسح المستخدم المحفوظ")
        switch_btn.setCursor(Qt.PointingHandCursor)
        switch_btn.clicked.connect(self._switch_account)
        card_layout.addWidget(switch_btn)

        reset_hint = QLabel("نسيت كلمة المرور؟ استخدم أداة scripts/reset_password.py من مجلد المشروع.")
        reset_hint.setWordWrap(True)
        reset_hint.setAlignment(Qt.AlignCenter)
        reset_hint.setStyleSheet(f"background: transparent; font-size: 11px; color: {ThemeManager.get('text_muted')};")
        card_layout.addWidget(reset_hint)

        layout.addWidget(card)
        footer = QLabel(f"{APP_DISPLAY_NAME_AR} • {APP_TAGLINE_AR}")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"background: transparent; font-size: 11px; color: {ThemeManager.get('text_muted')};")
        layout.addWidget(footer)

        self._load_saved_user()
        self.fade_in()

    def _input_style(self):
        return f"""
            QLineEdit, QComboBox {{
                background-color: {ThemeManager.get('bg_window')};
                color: {ThemeManager.get('text_primary')};
                border: 1px solid {ThemeManager.get('border')};
                border-radius: 9px;
                padding: 8px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid {ThemeManager.get('primary')};
            }}
        """

    def _message_style(self, tone="danger"):
        color = ThemeManager.get(tone) or ThemeManager.get('danger')
        return f"""
            QLabel {{
                background-color: rgba(239, 68, 68, 0.08);
                color: {color};
                border: 1px solid {color};
                border-radius: 9px;
                padding: 8px;
                font-size: 12px;
                font-weight: 700;
            }}
        """

    def _field_with_label(self, label_text, widget):
        container = QFrame()
        container.setObjectName('LoginFieldContainer')
        container.setFrameShape(QFrame.NoFrame)
        container.setMinimumHeight(76)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        label = QLabel(label_text)
        label.setStyleSheet(f"background: transparent; font-size: 12px; font-weight: 700; color: {ThemeManager.get('text_secondary')};")
        v.addWidget(label)
        v.addWidget(widget)
        return container

    def _show_message(self, text, tone="danger"):
        self.error_label.setStyleSheet(self._message_style(tone))
        self.error_label.setText(text)
        self.error_label.setVisible(True)

    def _populate_users(self):
        if self.db_conn.is_remote():
            self.username_combo.setEditable(True)
            self.username_combo.clear()
            self.username_combo.addItem("")
            self.username_combo.setCurrentText("")
        else:
            users = self.user_repo.get_all()
            self.username_combo.clear()
            for u in users:
                self.username_combo.addItem(u['username'])

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
        self._show_message("تم مسح اسم المستخدم المحفوظ.", "success")
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
            audio_service.play_warning()
            self._show_message("يرجى إدخال اسم المستخدم وكلمة المرور.", "warning")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("جارٍ التحقق...")
        try:
            if self.db_conn.is_remote():
                rest_client = self.db_conn.get_rest_client()
                user = rest_client.login(username, password)
            else:
                user = self.user_repo.authenticate(username, password)

            if user:
                UserSession.login(user)
                self._save_user(username)
                audio_service.play_login_ok()
                self.accept()
            else:
                audio_service.play_login_fail()
                self._show_message("اسم المستخدم أو كلمة المرور غير صحيحة.", "danger")
                self.password_edit.clear()
                self.password_edit.setFocus()
        except Exception as e:
            audio_service.play_login_fail()
            self._show_message(f"فشل تسجيل الدخول: {str(e)}", "danger")
            self.password_edit.clear()
            self.password_edit.setFocus()
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("تسجيل الدخول")

    def showEvent(self, event):
        self.center_on_parent()
        super().showEvent(event)

    def center_on_parent(self):
        parent = self.parent()
        if parent and parent.isVisible():
            geo = parent.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = self.screen().geometry()
            self.move((screen.width() - self.width()) // 2,
                      (screen.height() - self.height()) // 2)
