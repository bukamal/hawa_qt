# -*- coding: utf-8 -*-
import sqlite3
import os
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hawaa_data.db')

class DatabaseConnection:
    _instance = None
    _local = threading.local()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_connection(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            self._local.conn = sqlite3.connect(DB_PATH, isolation_level=None)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def execute(self, sql, params=()):
        return self.get_connection().execute(sql, params)
    
    def executemany(self, sql, params_list):
        return self.get_connection().executemany(sql, params_list)
    
    def commit(self):
        self.get_connection().commit()
    
    def rollback(self):
        self.get_connection().rollback()
    
    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    def begin(self):
        self.execute("BEGIN TRANSACTION")
