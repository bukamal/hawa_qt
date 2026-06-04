# -*- coding: utf-8 -*-
import sqlite3
import requests
import threading
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hawaa_data.db')
SERVER_URL = os.environ.get('HAWAA_SERVER', '')

class DatabaseConnection:
    _instance = None
    _local = threading.local()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _use_http(self):
        return SERVER_URL and SERVER_URL != ''

    def get_connection(self):
        if not self._use_http():
            if not hasattr(self._local, 'conn') or self._local.conn is None:
                os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
                self._local.conn = sqlite3.connect(DB_PATH, isolation_level=None)
                self._local.conn.row_factory = sqlite3.Row
            return self._local.conn
        else:
            if not hasattr(self._local, 'conn_id'):
                try:
                    resp = requests.post(f"{SERVER_URL}/connect", timeout=5)
                    if resp.status_code == 200:
                        self._local.conn_id = resp.json()["connection_id"]
                    else:
                        raise Exception("فشل الاتصال بالخادم")
                except Exception as e:
                    raise Exception(f"لا يمكن الاتصال بخادم قاعدة البيانات: {e}")
            return self._local

    def execute(self, sql, params=(), audit_data=None):
        if not self._use_http():
            conn = self.get_connection()
            return conn.execute(sql, params)
        else:
            conn_id = self.get_connection().conn_id
            payload = {
                "connection_id": conn_id,
                "sql": sql,
                "params": list(params)
            }
            if audit_data:
                payload["audit"] = audit_data
            resp = requests.post(f"{SERVER_URL}/execute", json=payload)
            if resp.status_code != 200:
                raise Exception(f"خطأ في الخادم: {resp.text}")
            data = resp.json()
            if not data.get("success"):
                raise Exception(data.get("error", "خطأ غير معروف"))
            return MockCursor(data.get("rows"), data.get("rowcount"), data.get("lastrowid"))

    def executemany(self, sql, params_list, audit_data=None):
        if not self._use_http():
            return self.get_connection().executemany(sql, params_list)
        else:
            for params in params_list:
                self.execute(sql, params, audit_data)
            return MockCursor(None, len(params_list), None)

    def commit(self):
        if not self._use_http():
            self.get_connection().commit()
        else:
            conn_id = self.get_connection().conn_id
            requests.post(f"{SERVER_URL}/commit", params={"conn_id": conn_id})

    def rollback(self):
        if not self._use_http():
            self.get_connection().rollback()
        else:
            conn_id = self.get_connection().conn_id
            requests.post(f"{SERVER_URL}/rollback", params={"conn_id": conn_id})

    def close(self):
        if not self._use_http():
            if hasattr(self._local, 'conn') and self._local.conn:
                self._local.conn.close()
                self._local.conn = None
        else:
            if hasattr(self._local, 'conn_id'):
                try:
                    requests.post(f"{SERVER_URL}/disconnect", params={"conn_id": self._local.conn_id})
                except:
                    pass
                del self._local.conn_id

    def begin(self):
        self.execute("BEGIN TRANSACTION")

class MockCursor:
    def __init__(self, rows, rowcount, lastrowid):
        self._rows = rows if rows is not None else []
        self._index = 0
        self.rowcount = rowcount
        self.lastrowid = lastrowid

    def fetchone(self):
        if self._index < len(self._rows):
            row = self._rows[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self):
        return self._rows

    def close(self):
        pass
