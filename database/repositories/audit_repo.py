# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
import datetime
from typing import List, Dict, Optional

class AuditRepository(BaseRepository):
    def log(self, user_id: Optional[int], username: str, action: str, table_name: str,
            record_id: int, details: str, ip: str = ''):
        if self.db.is_remote():
            # الخادم يسجل تلقائياً عند تنفيذ العمليات، لا حاجة لفعل شيء هنا
            return
        now = datetime.datetime.now().isoformat()
        self._execute("""
            INSERT INTO audit_log (user_id, username, action, table_name, record_id, details, ip_address, timestamp)
            VALUES (?,?,?,?,?,?,?,?)
        """, (user_id, username, action, table_name, record_id, details, ip, now))
        self._commit()

    def get_all(self, limit: int = 1000, user_id: int = None, action: str = None,
                table_name: str = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        if self.db.is_remote():
            logs = self.db.get_rest_client().get_audit_log()
            # تطبيق الفلاتر
            filtered = logs[:limit]
            if user_id:
                filtered = [l for l in filtered if l.get('user_id') == user_id]
            if action and action != "الكل":
                filtered = [l for l in filtered if l.get('action') == action]
            if table_name and table_name != "الكل":
                filtered = [l for l in filtered if l.get('table_name') == table_name]
            if start_date:
                filtered = [l for l in filtered if l.get('timestamp', '')[:10] >= start_date]
            if end_date:
                filtered = [l for l in filtered if l.get('timestamp', '')[:10] <= end_date]
            return filtered
        else:
            sql = "SELECT id, user_id, username, action, table_name, record_id, details, ip_address, timestamp FROM audit_log WHERE 1=1"
            params = []
            if user_id:
                sql += " AND user_id = ?"
                params.append(user_id)
            if action and action != "الكل":
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
        if self.db.is_remote():
            logs = self.db.get_rest_client().get_audit_log()
            stats = {}
            # حسب المستخدم
            user_count = {}
            for l in logs:
                user = l.get('username', 'unknown')
                user_count[user] = user_count.get(user, 0) + 1
            stats['by_user'] = [{'username': k, 'count': v} for k, v in sorted(user_count.items(), key=lambda x: -x[1])[:10]]
            # حسب العملية
            action_count = {}
            for l in logs:
                act = l.get('action', 'unknown')
                action_count[act] = action_count.get(act, 0) + 1
            stats['by_action'] = [{'action': k, 'count': v} for k, v in action_count.items()]
            # حسب الجدول
            table_count = {}
            for l in logs:
                tbl = l.get('table_name', 'unknown')
                table_count[tbl] = table_count.get(tbl, 0) + 1
            stats['by_table'] = [{'table_name': k, 'count': v} for k, v in table_count.items()]
            # يومياً (آخر 30 يوماً)
            from collections import defaultdict
            daily = defaultdict(int)
            today = datetime.datetime.now().date()
            for l in logs:
                ts = l.get('timestamp', '')
                if ts:
                    d = ts[:10]
                    daily[d] += 1
            stats['daily'] = [{'day': d, 'count': c} for d, c in sorted(daily.items()) if d >= (today - datetime.timedelta(days=30)).isoformat()]
            return stats
        else:
            stats = {}
            rows = self._fetch_all("""
                SELECT username, COUNT(*) as count FROM audit_log 
                GROUP BY username ORDER BY count DESC LIMIT 10
            """)
            stats['by_user'] = rows
            rows = self._fetch_all("""
                SELECT action, COUNT(*) as count FROM audit_log 
                GROUP BY action ORDER BY count DESC
            """)
            stats['by_action'] = rows
            rows = self._fetch_all("""
                SELECT table_name, COUNT(*) as count FROM audit_log 
                GROUP BY table_name ORDER BY count DESC
            """)
            stats['by_table'] = rows
            rows = self._fetch_all("""
                SELECT DATE(timestamp) as day, COUNT(*) as count 
                FROM audit_log 
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY DATE(timestamp) ORDER BY day
            """)
            stats['daily'] = rows
            return stats

    def delete_old_logs(self, days: int = 90):
        if self.db.is_remote():
            self.db.get_rest_client().delete_old_audit_logs(days)
        else:
            cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
            self._execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
            self._commit()

    def export_all(self) -> List[Dict]:
        if self.db.is_remote():
            return self.db.get_rest_client().get_audit_log()
        else:
            return self._fetch_all("SELECT * FROM audit_log ORDER BY id DESC")
