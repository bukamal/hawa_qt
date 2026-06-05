from PyQt5.QtWidgets import QFormLayout, QLineEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt
from database import UserRepository
from auth.session import UserSession
from i18n.translator import translate
from views.centered_dialog import CenteredDialog
from views.dialogs.change_password_dialog import ChangePasswordDialog

class UserDialog(CenteredDialog):
    def __init__(self, parent=None, user_id=None):
        super().__init__(parent=parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.user_id = user_id
        self.setWindowTitle(translate('edit') if user_id else translate('add'))
        self.resize(400, 350)
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20,20,20,20)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.username_edit = QLineEdit()
        if user_id:
            self.username_edit.setEnabled(False)
        form.addRow(translate('username'), self.username_edit)
        self.fullname_edit = QLineEdit()
        form.addRow(translate('full_name'), self.fullname_edit)
        self.role_combo = QComboBox()
        self.role_combo.addItems([translate('admin'), translate('user'), translate('viewer')])
        form.addRow(translate('role'), self.role_combo)
        
        if not user_id:
            self.password_edit = QLineEdit()
            self.password_edit.setEchoMode(QLineEdit.Password)
            form.addRow(translate('password'), self.password_edit)
            self.confirm_edit = QLineEdit()
            self.confirm_edit.setEchoMode(QLineEdit.Password)
            form.addRow("تأكيد "+translate('password'), self.confirm_edit)
        else:
            change_btn = QPushButton(translate('change_password'))
            change_btn.clicked.connect(self.change_password)
            form.addRow(change_btn)
        layout.addLayout(form)
        
        btns = QHBoxLayout()
        btns.setDirection(QHBoxLayout.RightToLeft)
        save_btn = QPushButton(translate('save'))
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton(translate('cancel'))
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        
        if user_id:
            self.load_user()
    
    def load_user(self):
        repo = UserRepository()
        user = repo.get_by_id(self.user_id)
        if user:
            self.username_edit.setText(user['username'])
            self.fullname_edit.setText(user['full_name'] or '')
            role_map = {'admin':0,'user':1,'viewer':2}
            self.role_combo.setCurrentIndex(role_map.get(user['role'],1))
    
    def save(self):
        username = self.username_edit.text().strip()
        full_name = self.fullname_edit.text().strip()
        role_map = {0:'admin',1:'user',2:'viewer'}
        role = role_map[self.role_combo.currentIndex()]
        repo = UserRepository()
        try:
            if not self.user_id:
                password = self.password_edit.text()
                confirm = self.confirm_edit.text()
                if not username or not password:
                    QMessageBox.warning(self, translate('error'), "اسم المستخدم وكلمة المرور مطلوبان")
                    return
                if password != confirm:
                    QMessageBox.warning(self, translate('error'), "كلمتا المرور غير متطابقتين")
                    return
                repo.create(username, password, full_name, role)
                QMessageBox.information(self, translate('success'), "تمت الإضافة")
            else:
                repo.update(self.user_id, full_name, role)
                QMessageBox.information(self, translate('success'), "تم التحديث")
            self.accept()
        except ValueError as e:
            QMessageBox.critical(self, translate('error'), str(e))
        except Exception as e:
            QMessageBox.critical(self, translate('error'), str(e))
    
    def change_password(self):
        dlg = ChangePasswordDialog(self, user_id=self.user_id)
        dlg.exec()
