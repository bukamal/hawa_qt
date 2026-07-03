# -*- coding: utf-8 -*-
"""Audit-log service for document shell screens and reports."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from database import AuditRepository, UserRepository
from services.permission_service import permission_service
from services.print_service import print_service


class AuditService:
    def __init__(self, audit_repo: Optional[AuditRepository] = None, user_repo: Optional[UserRepository] = None):
        self._audit_repo = audit_repo
        self._user_repo = user_repo

    @property
    def audit_repo(self):
        return self._audit_repo or AuditRepository()

    @property
    def user_repo(self):
        return self._user_repo or UserRepository()

    def list_users_for_filter(self) -> List[Dict[str, Any]]:
        permission_service.require_audit_view()
        try:
            return self.user_repo.get_all()
        except Exception:
            return []

    def list_logs(
        self,
        limit: int = 2000,
        user_id: int = None,
        action: str = None,
        table_name: str = None,
        start_date: str = None,
        end_date: str = None,
    ) -> List[Dict[str, Any]]:
        permission_service.require_audit_view()
        logs = self.audit_repo.get_all(
            limit=limit,
            user_id=user_id,
            action=self._none_if_all(action),
            table_name=self._none_if_all(table_name),
            start_date=start_date,
            end_date=end_date,
        )
        return [self._format_log(dict(log)) for log in logs]

    def stats(self) -> Dict[str, List[Dict[str, Any]]]:
        permission_service.require_audit_view()
        return self.audit_repo.get_stats()

    def delete_old_logs(self, days: int = 90):
        permission_service.require_audit_admin()
        return self.audit_repo.delete_old_logs(days)

    def build_print_payload(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        permission_service.require_audit_view()
        headers = ['المستخدم', 'الإجراء', 'الجدول', 'رقم السجل', 'التفاصيل', 'عنوان IP', 'التاريخ والوقت']
        rows = [
            [
                log.get('username', ''),
                log.get('action', ''),
                log.get('table_name', ''),
                log.get('record_id', ''),
                log.get('details', ''),
                log.get('ip_address', ''),
                log.get('timestamp', ''),
            ]
            for log in logs
        ]
        subtitle = 'قراءة فقط. الحذف والتنظيف يتطلبان صلاحية المدير.'
        html = print_service.build_table_report('سجل التدقيق', headers, rows, subtitle=subtitle)
        return {
            'title': 'سجل التدقيق',
            'headers': headers,
            'rows': rows,
            'subtitle': subtitle,
            'html': html,
            'default_filename': 'audit_log',
        }

    def build_print_report(self, logs: List[Dict[str, Any]]) -> str:
        return self.build_print_payload(logs)['html']

    def build_stats_payload(self) -> Dict[str, Any]:
        permission_service.require_audit_view()
        stats = self.stats()
        rows = []
        for group_key, group_title in [
            ('by_user', 'حسب المستخدم'),
            ('by_action', 'حسب العملية'),
            ('by_table', 'حسب الجدول'),
            ('daily', 'حسب اليوم'),
        ]:
            for item in stats.get(group_key, []):
                label = item.get('username') or item.get('action') or item.get('table_name') or item.get('day') or '-'
                rows.append([group_title, label, item.get('count', 0)])
        headers = ['المجموعة', 'القيمة', 'العدد']
        html = print_service.build_table_report('إحصائيات سجل التدقيق', headers, rows)
        return {
            'title': 'إحصائيات سجل التدقيق',
            'headers': headers,
            'rows': rows,
            'subtitle': None,
            'html': html,
            'default_filename': 'audit_stats',
        }

    def export_rows(self) -> List[Dict[str, Any]]:
        permission_service.require_audit_view()
        return [self._format_log(dict(log)) for log in self.audit_repo.export_all()]

    def _format_log(self, log: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'id': log.get('id'),
            'user_id': log.get('user_id'),
            'username': log.get('username') or '-',
            'action': log.get('action') or '-',
            'table_name': log.get('table_name') or '-',
            'record_id': log.get('record_id') if log.get('record_id') is not None else '-',
            'details': log.get('details') or '',
            'ip_address': log.get('ip_address') or '-',
            'timestamp': (log.get('timestamp') or '')[:19],
        }

    def _none_if_all(self, value):
        if value in (None, '', 'الكل'):
            return None
        return value


audit_service = AuditService()
