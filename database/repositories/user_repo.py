# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
from database.repositories.audit_repo import AuditRepository
from auth.password import hash_password, verify_password
from auth.session import UserSession
import datetime
from typing import List, Dict, Optional

class UserRepository(BaseRepository):
    def get_all(self) -> List[Dict]:
        return self._fetch_all("SELECT id, username, full_name, role, created_at, last_login, force_password_change FROM users ORDER BY id")
    
    def get_by_id(self, user_id: int) -> Optional[Dict]:
        return self._fetch_one("SELECT * FROM users WHERE id=?", (user_id,))
    
    def get_by_username(self, username: str) -> Optional[Dict]:
        return self._fetch_one("SELECT * FROM users WHERE username=?", (username,))
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        user = self.get_by_username(username)
        if user and verify_password(password, user['password_hash'], user['salt']):
            now = datetime.datetime.now().isoformat()
            self._execute("UPDATE users SET last_login=? WHERE id=?", (now, user['id']))
            self._commit()
            return user
        return None
    
    def create(self, username: str, password: str, full_name: str, role: str) -> int:
        pwd_hash, salt = hash_password(password)
        now = datetime.datetime.now().isoformat()
        self.begin()
        try:
            cur = self._execute("INSERT INTO users (username, password_hash, salt, full_name, role, created_at) VALUES (?,?,?,?,?,?)",
                                (username, pwd_hash, salt, full_name, role, now))
            user_id = cur.lastrowid
            audit = AuditRepository()
            current = UserSession.get_current()
            audit.log(current['id'] if current else None, current['username'] if current else '', "إضافة مستخدم", 'users', user_id, f"المستخدم: {username}")
            self._commit()
            return user_id
        except Exception as e:
            self._rollback()
            if "UNIQUE" in str(e):
                raise ValueError("اسم المستخدم موجود")
            raise
    
    def update(self, user_id: int, full_name: str, role: str):
        self.begin()
        try:
            self._execute("UPDATE users SET full_name=?, role=? WHERE id=?", (full_name, role, user_id))
            audit = AuditRepository()
            current = UserSession.get_current()
            audit.log(current['id'] if current else None, current['username'] if current else '', "تعديل مستخدم", 'users', user_id, f"الاسم: {full_name}, صلاحية: {role}")
            self._commit()
        except Exception as e:
            self._rollback()
            raise
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        user = self.get_by_id(user_id)
        if not user or not verify_password(old_password, user['password_hash'], user['salt']):
            return False
        new_hash, new_salt = hash_password(new_password)
        self.begin()
        try:
            self._execute("UPDATE users SET password_hash=?, salt=?, force_password_change=0 WHERE id=?", (new_hash, new_salt, user_id))
            audit = AuditRepository()
            current = UserSession.get_current()
            audit.log(current['id'] if current else None, current['username'] if current else '', "تغيير كلمة المرور", 'users', user_id, "")
            self._commit()
            return True
        except:
            self._rollback()
            return False
    
    def delete(self, user_id: int) -> bool:
        if user_id == 1:
            return False
        self.begin()
        try:
            user = self.get_by_id(user_id)
            self._execute("DELETE FROM users WHERE id=?", (user_id,))
            audit = AuditRepository()
            current = UserSession.get_current()
            audit.log(current['id'] if current else None, current['username'] if current else '', "حذف مستخدم", 'users', user_id, f"المستخدم: {user['username']}")
            self._commit()
            return True
        except:
            self._rollback()
            return False
    
    def set_force_password_change(self, user_id: int, force: bool):
        val = 1 if force else 0
        self._execute("UPDATE users SET force_password_change=? WHERE id=?", (val, user_id))
        self._commit()
