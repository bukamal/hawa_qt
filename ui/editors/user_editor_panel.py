# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton,
    QHBoxLayout, QMessageBox, QLabel
)
from PyQt5.QtCore import pyqtSignal, Qt

from i18n.translator import translate
from services.user_service import user_service


class UserEditorPanel(QWidget):
    """Inline editor for creating/updating users.

    Password fields are shown only while creating a user. Password change for an
    existing account remains a separate account-security workflow.
    """
    saved = pyqtSignal(dict)
    cancelled = pyqtSignal()

    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()
        self._load_initial_values()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        notice = QLabel('إدارة المستخدمين تتم هنا Inline بدون نوافذ. الصلاحيات تُفحص من الخدمة وليس من الزر فقط.')
        notice.setWordWrap(True)
        notice.setObjectName('InlineNotice')
        layout.addWidget(notice)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText('مثال: ahmad')
        form.addRow(translate('username') + ':', self.username_edit)

        self.fullname_edit = QLineEdit()
        self.fullname_edit.setPlaceholderText('الاسم الكامل')
        form.addRow(translate('full_name') + ':', self.fullname_edit)

        self.role_combo = QComboBox()
        for role, label in user_service.available_roles():
            self.role_combo.addItem(label, role)
        form.addRow(translate('role') + ':', self.role_combo)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText('6 أحرف على الأقل')
        form.addRow(translate('password') + ':', self.password_edit)

        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow('تأكيد ' + translate('password') + ':', self.confirm_edit)

        layout.addLayout(form)
        layout.addStretch(1)

        btns = QHBoxLayout()
        save_btn = QPushButton('💾 ' + translate('save'))
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton('✖ ' + translate('cancel'))
        cancel_btn.clicked.connect(self.cancelled.emit)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _load_initial_values(self):
        if not self.user:
            return
        self.username_edit.setText(self.user.get('username') or '')
        self.username_edit.setEnabled(False)
        self.fullname_edit.setText(self.user.get('full_name') or '')
        role = self.user.get('role') or 'user'
        idx = self.role_combo.findData(role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)
        self.password_edit.setVisible(False)
        self.confirm_edit.setVisible(False)

    def save(self):
        username = self.username_edit.text().strip()
        full_name = self.fullname_edit.text().strip()
        role = self.role_combo.currentData()
        try:
            if self.user:
                user_service.update_user(self.user['id'], full_name, role)
                user_id = self.user['id']
                message = 'تم تحديث المستخدم'
            else:
                password = self.password_edit.text()
                confirm = self.confirm_edit.text()
                if password != confirm:
                    QMessageBox.warning(self, translate('error'), 'كلمتا المرور غير متطابقتين')
                    return
                user_id = user_service.create_user(username, password, full_name, role)
                message = 'تم إنشاء المستخدم'
            self.saved.emit({'id': user_id, 'message': message})
        except Exception as exc:
            QMessageBox.critical(self, translate('error'), str(exc))
