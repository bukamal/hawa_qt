# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
from auth.password import hash_password, verify_password
from auth.session import UserSession
import datetime
from typing import List, Dict, Optional

class UserRepository(BaseRepository):
    def get_all(self) -> List[Dict]:
        if self.db.is_remote():
            return self.db.get_rest_client().get_users()
        else:
            return self._fetch_all("SELECT id, username, full_name, role, created_at, last_login, force_password_change FROM users ORDER BY id")

    def get_by_id(self, user_id: int) -> Optional[Dict]:
        if self.db.is_remote():
            users = self.get_all()
            for u in users:
                if u['id'] == user_id:
                    return u
            return None
        else:
            return self._fetch_one("SELECT * FROM users WHERE id=?", (user_id,))

    def get_by_username(self, username: str) -> Optional[Dict]:
        if self.db.is_remote():
            users = self.get_all()
            for u in users:
                if u['username'] == username:
                    return u
            return None
        else:
            return self._fetch_one("SELECT * FROM users WHERE username=?", (username,))

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        if self.db.is_remote():
            raise NotImplementedError("Use RestClient.login() for remote mode")
        user = self.get_by_username(username)
        if user and verify_password(password, user['password_hash'], user['salt']):
            now = datetime.datetime.now().isoformat()
            self._execute("UPDATE users SET last_login=? WHERE id=?", (now, user['id']))
            self._commit()
            return user
        return None

    def create(self, username: str, password: str, full_name: str, role: str) -> int:
        if self.db.is_remote():
            data = {
                'username': username,
                'password': password,
                'full_name': full_name,
                'role': role
            }
            return self.db.get_rest_client().add_user(data)
        else:
            pwd_hash, salt = hash_password(password)
            now = datetime.datetime.now().isoformat()
            conn = self.db.get_connection()
            cursor = conn.execute('''
                INSERT INTO users (username, password_hash, salt, full_name, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, pwd_hash, salt, full_name, role, now))
            conn.commit()
            user_id = cursor.lastrowid
            # تسجيل التدقيق
            current = UserSession.get_current()
            self.db._log_audit_local(
                current['id'] if current else None,
                current['username'] if current else '',
                "إضافة مستخدم",
                'users', user_id, f"المستخدم: {username}"
            )
            return user_id

    def update(self, user_id: int, full_name: str, role: str):
        if self.db.is_remote():
            data = {'full_name': full_name, 'role': role}
            self.db.get_rest_client().update_user(user_id, data)
        else:
            conn = self.db.get_connection()
            conn.execute('UPDATE users SET full_name=?, role=? WHERE id=?', (full_name, role, user_id))
            conn.commit()
            current = UserSession.get_current()
            self.db._log_audit_local(
                current['id'] if current else None,
                current['username'] if current else '',
                "تعديل مستخدم",
                'users', user_id, f"الاسم: {full_name}, صلاحية: {role}"
            )

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        if self.db.is_remote():
            try:
                self.db.get_rest_client().change_password(old_password, new_password)
                return True
            except:
                return False
        else:
            user = self.get_by_id(user_id)
            if not user or not verify_password(old_password, user['password_hash'], user['salt']):
                return False
            new_hash, new_salt = hash_password(new_password)
            conn = self.db.get_connection()
            conn.execute('UPDATE users SET password_hash=?, salt=?, force_password_change=0 WHERE id=?',
                         (new_hash, new_salt, user_id))
            conn.commit()
            current = UserSession.get_current()
            self.db._log_audit_local(
                current['id'] if current else None,
                current['username'] if current else '',
                "تغيير كلمة المرور",
                'users', user_id, ""
            )
            return True

    def delete(self, user_id: int) -> bool:
        if self.db.is_remote():
            if user_id == 1:
                return False
            try:
                self.db.get_rest_client().delete_user(user_id)
                return True
            except:
                return False
        else:
            if user_id == 1:
                return False
            user = self.get_by_id(user_id)
            conn = self.db.get_connection()
            conn.execute('DELETE FROM users WHERE id=?', (user_id,))
            conn.commit()
            current = UserSession.get_current()
            self.db._log_audit_local(
                current['id'] if current else None,
                current['username'] if current else '',
                "حذف مستخدم",
                'users', user_id, f"المستخدم: {user['username']}"
            )
            return True

    def set_force_password_change(self, user_id: int, force: bool):
        if self.db.is_remote():
            pass
        else:
            val = 1 if force else 0
            self._execute("UPDATE users SET force_password_change=? WHERE id=?", (val, user_id))
            self._commit()
