from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHeaderView, QMessageBox
from PyQt5.QtCore import Qt
from database import UserRepository, AuditRepository
from auth.session import UserSession
from i18n.translator import translate
from views.custom_table_view import CustomTableView
from models.table_models import GenericTableModel
from views.dialogs.user_dialog import UserDialog

class UsersWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)  # RTL
        layout = QVBoxLayout(self)
        add_btn = QPushButton("➕ " + translate('add'))
        add_btn.clicked.connect(self.add_user)
        layout.addWidget(add_btn)

        self.table = CustomTableView()
        self.table.setLayoutDirection(Qt.RightToLeft)  # RTL للجدول
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        self.table.doubleClicked.connect(self.edit_user)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        repo = UserRepository()
        users = repo.get_all()
        data = []
        for u in users:
            role_text = translate('admin') if u['role']=='admin' else translate('user') if u['role']=='user' else translate('viewer')
            data.append({
                'id': u['id'],
                'username': u['username'],
                'full_name': u['full_name'] or '',
                'role': role_text,
                'created_at': u['created_at'][:10] if u['created_at'] else '',
                'last_login': u['last_login'][:10] if u['last_login'] else '',
            })
        headers = ['username', 'full_name', 'role', 'created_at', 'last_login']
        display_headers = [translate('username'), translate('full_name'), translate('role'), 'تاريخ التسجيل', 'آخر دخول']
        data_keys = ['username', 'full_name', 'role', 'created_at', 'last_login']
        self.model = GenericTableModel(data, display_headers, key_fields=['id'], data_keys=data_keys)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # id is stored in key_fields, not as a visible column; do not hide username.
        self.table.refresh_style()

    def show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        user_id = self.model.get_id(row)
        if not user_id or user_id == 1:
            return
        menu = self.table.createStandardContextMenu()
        delete_action = menu.addAction("🗑 " + translate('delete'))
        delete_action.triggered.connect(lambda: self.delete_user(user_id))
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def delete_user(self, user_id):
        reply = QMessageBox.question(self, translate('confirm_delete'), translate('confirm_delete'), QMessageBox.Yes|QMessageBox.No)
        if reply == QMessageBox.Yes:
            repo = UserRepository()
            if repo.delete(user_id):
                QMessageBox.information(self, translate('success'), "تم حذف المستخدم")
                self.refresh()
            else:
                QMessageBox.warning(self, translate('error'), "فشل الحذف")

    def add_user(self):
        dialog = UserDialog(self)
        if dialog.exec():
            self.refresh()

    def edit_user(self, index):
        row = index.row()
        user_id = self.model.get_id(row)
        if user_id:
            dialog = UserDialog(self, user_id=user_id)
            if dialog.exec():
                self.refresh()
