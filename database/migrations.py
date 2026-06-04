# -*- coding: utf-8 -*-
import sqlite3
import os
import datetime
from database.connection import DatabaseConnection, DB_PATH
from auth.password import hash_password

def init_database():
    db = DatabaseConnection()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT,
            last_login TEXT,
            force_password_change INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT,
            table_name TEXT,
            record_id INTEGER,
            details TEXT,
            ip_address TEXT,
            timestamp TEXT
        );
        
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('incoming', 'outgoing')),
            date TEXT NOT NULL,
            notes TEXT,
            currency TEXT DEFAULT 'SAR',
            created_by INTEGER,
            created_at TEXT,
            updated_by INTEGER,
            updated_at TEXT
        );
        
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        
        CREATE TABLE IF NOT EXISTS exchange_rates (
            currency_code TEXT PRIMARY KEY,
            rate_to_usd REAL NOT NULL,
            updated_at TEXT
        );
    ''')
    
    cursor.executescript('''
        CREATE INDEX IF NOT EXISTS idx_expenses_company ON expenses(company_name);
        CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
        CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_log_table ON audit_log(table_name);
    ''')
    
    cursor.executescript('''
        INSERT OR IGNORE INTO settings (key, value) VALUES ('currency_decimals', '2');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('number_format', 'western');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('language', 'ar');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'light');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('base_currency', 'USD');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('display_currency', 'USD');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('abbreviate_numbers', 'false');
    ''')
    
    now = datetime.datetime.now().isoformat()
    default_rates = [
        ('USD', 1.0), ('SAR', 3.75), ('SYP', 14000.0), ('EUR', 0.92),
        ('GBP', 0.79), ('AED', 3.67), ('QAR', 3.64), ('KWD', 0.31), ('OMR', 0.38),
    ]
    for code, rate in default_rates:
        cursor.execute("INSERT OR IGNORE INTO exchange_rates (currency_code, rate_to_usd, updated_at) VALUES (?,?,?)",
                       (code, rate, now))
    
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        pwd_hash, salt = hash_password('admin123')
        now = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO users (username, password_hash, salt, full_name, role, created_at, force_password_change)
            VALUES (?,?,?,?,?,?,?)
        ''', ('admin', pwd_hash, salt, 'المدير العام', 'admin', now, 1))
    
    conn.commit()
    print("✅ تم تهيئة قاعدة البيانات مع دعم العملات المتعددة واختصار الأعداد")

def ensure_db():
    if not os.path.exists(DB_PATH):
        init_database()
    else:
        init_database()
