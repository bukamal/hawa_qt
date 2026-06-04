# -*- coding: utf-8 -*-
from database.connection import DatabaseConnection
from typing import List, Dict, Optional

class BaseRepository:
    def __init__(self):
        self.db = DatabaseConnection()
    
    def _execute(self, sql: str, params: tuple = ()):
        return self.db.execute(sql, params)
    
    def _executemany(self, sql: str, params_list: list):
        return self.db.executemany(sql, params_list)
    
    def _fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        cur = self._execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
    
    def _fetch_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        cur = self._execute(sql, params)
        return [dict(row) for row in cur.fetchall()]
    
    def _commit(self):
        self.db.commit()
    
    def _rollback(self):
        self.db.rollback()
    
    def begin(self):
        self.db.begin()
