# -*- coding: utf-8 -*-
"""Central role/permission checks shared by UI and local services."""
from __future__ import annotations

from typing import Iterable, Optional, Dict, Any

from auth.session import UserSession


ROLE_ADMIN = 'admin'
ROLE_USER = 'user'
ROLE_ACCOUNTANT = 'accountant'
ROLE_MANAGER = 'manager'
ROLE_VIEWER = 'viewer'
ROLE_AUDITOR = 'auditor'

WRITE_EXPENSE_ROLES = {ROLE_ADMIN, ROLE_USER, ROLE_ACCOUNTANT, ROLE_MANAGER}
ADMIN_ROLES = {ROLE_ADMIN}
READ_ONLY_ROLES = {ROLE_VIEWER, ROLE_AUDITOR}
AUDIT_VIEW_ROLES = {ROLE_ADMIN, ROLE_AUDITOR}
AUDIT_ADMIN_ROLES = {ROLE_ADMIN}


class PermissionService:
    def current_user(self) -> Optional[Dict[str, Any]]:
        return UserSession.get_current()

    def current_role(self) -> str:
        user = self.current_user() or {}
        return user.get('role') or ROLE_VIEWER

    def has_any_role(self, roles: Iterable[str]) -> bool:
        return self.current_role() in set(roles)

    def is_admin(self) -> bool:
        return self.has_any_role(ADMIN_ROLES)

    def can_write_expenses(self) -> bool:
        return self.has_any_role(WRITE_EXPENSE_ROLES)

    def can_manage_users(self) -> bool:
        return self.is_admin()

    def can_manage_settings(self) -> bool:
        return self.is_admin()

    def can_view_audit(self) -> bool:
        return self.has_any_role(AUDIT_VIEW_ROLES)

    def can_manage_audit(self) -> bool:
        return self.has_any_role(AUDIT_ADMIN_ROLES)

    def require_expense_write(self):
        if not self.can_write_expenses():
            raise PermissionError('ليس لديك صلاحية لإضافة أو تعديل أو حذف القيود المالية')

    def require_admin(self):
        if not self.is_admin():
            raise PermissionError('هذه العملية تتطلب صلاحية المدير')

    def require_audit_view(self):
        if not self.can_view_audit():
            raise PermissionError('سجل التدقيق متاح للمدير أو المدقق فقط')

    def require_audit_admin(self):
        if not self.can_manage_audit():
            raise PermissionError('تنظيف سجل التدقيق يتطلب صلاحية المدير')


permission_service = PermissionService()
