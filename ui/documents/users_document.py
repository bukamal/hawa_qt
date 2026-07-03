# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QHeaderView, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal

from i18n.translator import translate
from views.custom_table_view import CustomTableView
from models.table_models import UserTableModel
from views.toast import Toast
from services.user_service import user_service
from services.permission_service import permission_service
from ui.editors.user_editor_panel import UserEditorPanel


class UsersDocument(QWidget):
    """Document-shell user management page with inline editing."""
    data_changed = pyqtSignal()

    def __init__(self, shell=None, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.users = []
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.title_label = QLabel('إدارة المستخدمين')
        self.title_label.setObjectName('DocumentTitle')
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('بحث باسم المستخدم أو الاسم الكامل')
        self.search_edit.textChanged.connect(self.refresh_table)
        header.addWidget(self.title_label)
        header.addWidget(self.search_edit, 1)
        layout.addLayout(header)

        self.policy_label = QLabel('الأدوار الجديدة مدعومة: مدير، مدير حسابات، محاسب، مدقق، مستخدم، مشاهد. الحفظ والحذف يمران عبر UserService.')
        self.policy_label.setWordWrap(True)
        self.policy_label.setObjectName('DocumentHint')
        layout.addWidget(self.policy_label)

        self.table = CustomTableView()
        self.table.setSelectionBehavior(CustomTableView.SelectRows)
        self.table.doubleClicked.connect(lambda _idx: self.edit_user())
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        can_manage = permission_service.can_manage_users()
        self.add_btn = QPushButton('➕ ' + translate('add'))
        self.add_btn.clicked.connect(self.add_user)
        self.add_btn.setVisible(can_manage)

        self.edit_btn = QPushButton('✏️ ' + translate('edit'))
        self.edit_btn.clicked.connect(self.edit_user)
        self.edit_btn.setVisible(can_manage)

        self.delete_btn = QPushButton('🗑 ' + translate('delete'))
        self.delete_btn.clicked.connect(self.delete_user)
        self.delete_btn.setVisible(can_manage)

        actions.addWidget(self.add_btn)
        actions.addWidget(self.edit_btn)
        actions.addWidget(self.delete_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

    def activate(self, **_params):
        self.refresh_table()

    def refresh_table(self):
        try:
            self.users = user_service.list_users()
        except Exception as exc:
            QMessageBox.critical(self, translate('error'), str(exc))
            self.users = []

        query = (self.search_edit.text() if hasattr(self, 'search_edit') else '').strip().lower()
        data = []
        for user in self.users:
            username = user.get('username') or ''
            full_name = user.get('full_name') or ''
            if query and query not in username.lower() and query not in full_name.lower():
                continue
            data.append({
                'id': user.get('id'),
                'username': username,
                'full_name': full_name,
                'role': user_service.role_label(user.get('role')),
                'role_code': user.get('role'),
                'created_at': (user.get('created_at') or '')[:10],
                'last_login': (user.get('last_login') or '')[:10],
                'force_password_change': 'نعم' if user.get('force_password_change') else 'لا',
            })

        self.model = UserTableModel(data)
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.refresh_style()

    def _selected_user(self):
        selected = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not selected or not hasattr(self, 'model'):
            return None
        user_id = self.model.get_id(selected[0].row())
        if not user_id:
            return None
        return user_service.get_user(user_id)

    def add_user(self):
        if not permission_service.can_manage_users():
            QMessageBox.warning(self, translate('warning'), 'هذه العملية تتطلب صلاحية المدير')
            return
        editor = UserEditorPanel()
        editor.saved.connect(self._on_editor_saved)
        editor.cancelled.connect(self._close_inline)
        self._open_inline(editor, 'إضافة مستخدم')

    def edit_user(self):
        if not permission_service.can_manage_users():
            QMessageBox.warning(self, translate('warning'), 'هذه العملية تتطلب صلاحية المدير')
            return
        user = self._selected_user()
        if not user:
            QMessageBox.warning(self, translate('warning'), 'اختر مستخدماً للتعديل')
            return
        editor = UserEditorPanel(user=user)
        editor.saved.connect(self._on_editor_saved)
        editor.cancelled.connect(self._close_inline)
        self._open_inline(editor, 'تعديل مستخدم')

    def delete_user(self):
        if not permission_service.can_manage_users():
            QMessageBox.warning(self, translate('warning'), 'هذه العملية تتطلب صلاحية المدير')
            return
        user = self._selected_user()
        if not user:
            QMessageBox.warning(self, translate('warning'), 'اختر مستخدماً للحذف')
            return
        reply = QMessageBox.question(
            self,
            translate('confirm_delete'),
            f"حذف المستخدم: {user.get('username')}؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            user_service.delete_user(user['id'])
            self.refresh_table()
            self.data_changed.emit()
            self._close_inline()
            Toast(self, '✅ تم حذف المستخدم', 'success')
        except Exception as exc:
            QMessageBox.critical(self, translate('error'), str(exc))

    def _open_inline(self, widget, title):
        if self.shell:
            self.shell.open_inline(widget, title)
        else:
            widget.setWindowTitle(title)
            widget.show()

    def _close_inline(self):
        if self.shell:
            self.shell.close_inline()

    def _on_editor_saved(self, payload):
        self.refresh_table()
        self.data_changed.emit()
        self._close_inline()
        Toast(self, '✅ ' + payload.get('message', 'تم الحفظ'), 'success')
