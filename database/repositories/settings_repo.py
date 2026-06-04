# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository

class SettingsRepository(BaseRepository):
    def get(self, key: str, default=None):
        row = self._fetch_one("SELECT value FROM settings WHERE key=?", (key,))
        return row['value'] if row else default
    
    def set(self, key: str, value: str):
        self._execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        self._commit()
    
    def get_currency_settings(self):
        return {
            'symbol': self.get('currency_symbol', '$'),
            'decimals': int(self.get('currency_decimals', '2')),
            'format': self.get('number_format', 'western')
        }
    
    def get_language(self):
        return self.get('language', 'ar')
    
    def get_theme(self):
        return self.get('theme', 'light')
