# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository

class SettingsRepository(BaseRepository):
    def get(self, key: str, default=None):
        return self.db.get_setting(key, default)
    
    def set(self, key: str, value: str):
        self.db.set_setting(key, value)
    
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
