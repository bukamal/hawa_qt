# -*- coding: utf-8 -*-
"""Application service for user-management operations.

The UI must not write users directly through UserRepository. This service centralizes
permission checks, role validation, and protection of the primary/last administrator.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from auth.session import UserSession
from database import UserRepository
from services.permission_service import permission_service


ROLE_LABELS = {
    'admin': 'مدير',
    'manager': 'مدير حسابات',
    'accountant': 'محاسب',
    'auditor': 'مدقق',
    'user': 'مستخدم',
    'viewer': 'مشاهد',
}

ROLE_ORDER = ['admin', 'manager', 'accountant', 'auditor', 'user', 'viewer']
ALLOWED_ROLES = set(ROLE_ORDER)


class UserService:
    def __init__(self, repo: Optional[UserRepository] = None):
        self._repo = repo

    @property
    def repo(self):
        return self._repo or UserRepository()

    def current_user(self) -> Optional[Dict]:
        return UserSession.get_current()

    def list_users(self) -> List[Dict]:
        permission_service.require_admin()
        return self.repo.get_all()

    def get_user(self, user_id: int) -> Optional[Dict]:
        permission_service.require_admin()
        return self.repo.get_by_id(user_id)

    def create_user(self, username: str, password: str, full_name: str = '', role: str = 'user') -> int:
        permission_service.require_admin()
        username = (username or '').strip()
        full_name = (full_name or '').strip()
        role = self._normalize_role(role)
        if not username:
            raise ValueError('اسم المستخدم مطلوب')
        if not password:
            raise ValueError('كلمة المرور مطلوبة')
        if len(password) < 6:
            raise ValueError('كلمة المرور يجب أن تكون 6 أحرف على الأقل')
        if self.repo.get_by_username(username):
            raise ValueError('اسم المستخدم موجود مسبقاً')
        return self.repo.create(username, password, full_name, role)

    def update_user(self, user_id: int, full_name: str = '', role: str = 'user'):
        permission_service.require_admin()
        role = self._normalize_role(role)
        user = self.repo.get_by_id(user_id)
        if not user:
            raise ValueError('المستخدم غير موجود')
        if user.get('id') == 1 and role != 'admin':
            raise ValueError('لا يمكن تغيير صلاحية المدير الأساسي')
        if user.get('role') == 'admin' and role != 'admin' and self._is_last_admin(user_id):
            raise ValueError('لا يمكن إزالة آخر مدير من النظام')
        return self.repo.update(user_id, (full_name or '').strip(), role)

    def delete_user(self, user_id: int) -> bool:
        permission_service.require_admin()
        user = self.repo.get_by_id(user_id)
        if not user:
            raise ValueError('المستخدم غير موجود')
        if user_id == 1:
            raise ValueError('لا يمكن حذف المدير الأساسي')
        current = self.current_user() or {}
        if current.get('id') == user_id:
            raise ValueError('لا يمكن حذف المستخدم الحالي أثناء الجلسة')
        if user.get('role') == 'admin' and self._is_last_admin(user_id):
            raise ValueError('لا يمكن حذف آخر مدير من النظام')
        return self.repo.delete(user_id)

    def role_label(self, role: str) -> str:
        return ROLE_LABELS.get(role, role or '')

    def available_roles(self):
        return [(role, ROLE_LABELS[role]) for role in ROLE_ORDER]

    def _normalize_role(self, role: str) -> str:
        role = (role or 'user').strip()
        if role not in ALLOWED_ROLES:
            raise ValueError(f'صلاحية غير معروفة: {role}')
        return role

    def _is_last_admin(self, user_id: int) -> bool:
        admins = [u for u in self.repo.get_all() if u.get('role') == 'admin']
        return len(admins) <= 1 and admins and admins[0].get('id') == user_id


user_service = UserService()
