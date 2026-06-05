# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt
from views.frameless_dialog import FramelessDialog
from database import UserRepository
from auth.session import UserSession
from i18n.translator import translate

class ChangePasswordDialog(FramelessDialog):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.user_id = user_id or (UserSession.get_current()['id'] if UserSession.get_current() else None)
        self.setWindowTitle(translate('change_password'))
        self.resize(450, 400)
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.old_edit = QLineEdit()
        self.old_edit.setEchoMode(QLineEdit.Password)
        form.addRow(translate('old_password')+":", self.old_edit)
        self.new_edit = QLineEdit()
        self.new_edit.setEchoMode(QLineEdit.Password)
        form.addRow(translate('new_password')+":", self.new_edit)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow(translate('confirm_password')+":", self.confirm_edit)
        layout.addLayout(form)
        
        btns = QHBoxLayout()
        btns.setDirection(QHBoxLayout.RightToLeft)
        save_btn = QPushButton(translate('save'))
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton(translate('cancel'))
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        self.fade_in()
    
    def save(self):
        old = self.old_edit.text()
        new = self.new_edit.text()
        confirm = self.confirm_edit.text()
        if not old or not new:
            QMessageBox.warning(self, translate('error'), "جميع الحقول مطلوبة")
            return
        if new != confirm:
            QMessageBox.warning(self, translate('error'), "كلمتا المرور غير متطابقتين")
            return
        repo = UserRepository()
        if repo.change_password(self.user_id, old, new):
            QMessageBox.information(self, translate('success'), "تم تغيير كلمة المرور")
            self.accept()
        else:
            QMessageBox.warning(self, translate('error'), "كلمة المرور الحالية غير صحيحة")
