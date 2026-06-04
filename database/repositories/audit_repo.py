# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
import datetime
from typing import List, Dict, Optional

class AuditRepository(BaseRepository):
    def log(self, user_id: Optional[int], username: str, action: str, table_name: str, record_id: int, details: str, ip: str = ''):
        now = datetime.datetime.now().isoformat()
        self._execute("""
            INSERT INTO audit_log (user_id, username, action, table_name, record_id, details, ip_address, timestamp)
            VALUES (?,?,?,?,?,?,?,?)
        """, (user_id, username, action, table_name, record_id, details, ip, now))
        self._commit()
    
    def get_all(self, limit: int = 1000, user_id: int = None, action: str = None,
                table_name: str = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        sql = "SELECT id, user_id, username, action, table_name, record_id, details, ip_address, timestamp FROM audit_log WHERE 1=1"
        params = []
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        if action and action != "الكل":
            # تعيين action كقيمة من القائمة (إضافة، تعديل، حذف، ...)
            sql += " AND action = ?"
            params.append(action)
        if table_name and table_name != "الكل":
            sql += " AND table_name = ?"
            params.append(table_name)
        if start_date:
            sql += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND timestamp <= ?"
            params.append(end_date + " 23:59:59")
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = self._fetch_all(sql, tuple(params))
        return rows
    
    def get_stats(self) -> Dict:
        """إرجاع إحصائيات: عدد العمليات لكل مستخدم، لكل نوع، لكل جدول"""
        stats = {}
        # لكل مستخدم
        rows = self._fetch_all("""
            SELECT username, COUNT(*) as count FROM audit_log 
            GROUP BY username ORDER BY count DESC LIMIT 10
        """)
        stats['by_user'] = rows
        # لكل نوع عملية
        rows = self._fetch_all("""
            SELECT action, COUNT(*) as count FROM audit_log 
            GROUP BY action ORDER BY count DESC
        """)
        stats['by_action'] = rows
        # لكل جدول
        rows = self._fetch_all("""
            SELECT table_name, COUNT(*) as count FROM audit_log 
            GROUP BY table_name ORDER BY count DESC
        """)
        stats['by_table'] = rows
        # العمليات اليومية خلال آخر 30 يوم
        rows = self._fetch_all("""
            SELECT DATE(timestamp) as day, COUNT(*) as count 
            FROM audit_log 
            WHERE timestamp >= date('now', '-30 days')
            GROUP BY DATE(timestamp) ORDER BY day
        """)
        stats['daily'] = rows
        return stats
    
    def delete_old_logs(self, days: int = 90):
        """حذف السجلات الأقدم من عدد محدد من الأيام"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        self._execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
        self._commit()
    
    def export_all(self) -> List[Dict]:
        """تصدير كامل السجل بدون حد (للاستخدام في ملفات CSV/Excel)"""
        return self._fetch_all("SELECT * FROM audit_log ORDER BY id DESC")
