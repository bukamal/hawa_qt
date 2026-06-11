# -*- coding: utf-8 -*-
import sqlite3
import os
import datetime
import logging
from database.connection import DatabaseConnection, DB_PATH
from auth.password import hash_password

logger = logging.getLogger(__name__)

def init_database():
    db = DatabaseConnection()
    if db.is_remote():
        logger.info("وضع العميل: قاعدة البيانات على الخادم، لا حاجة لإنشاء محلي.")
        return

    # إغلاق أي اتصال مفتوح قبل إنشاء الجداول
    db.close()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
            updated_at TEXT,
            amount_original REAL NOT NULL DEFAULT 0,
            currency_original TEXT NOT NULL DEFAULT 'SAR',
            exchange_rate_to_usd REAL NOT NULL DEFAULT 1.0,
            amount_base REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'approved',
            payment_due_date TEXT,
            payment_reminder_note TEXT
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

        CREATE TABLE IF NOT EXISTS token_blacklist (
            jti TEXT PRIMARY KEY,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS payment_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            reminder_date TEXT NOT NULL,
            note TEXT,
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(expense_id) REFERENCES expenses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );
    ''')

    cursor.executescript('''
        CREATE INDEX IF NOT EXISTS idx_expenses_company ON expenses(company_name);
        CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
        CREATE INDEX IF NOT EXISTS idx_expenses_status ON expenses(status);
        CREATE INDEX IF NOT EXISTS idx_expenses_payment_due_date ON expenses(payment_due_date);
        CREATE INDEX IF NOT EXISTS idx_payment_reminders_date ON payment_reminders(reminder_date);
        CREATE INDEX IF NOT EXISTS idx_payment_reminders_expense ON payment_reminders(expense_id);
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

    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('company_name', 'هوى الشام للسياحة والسفر')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('company_address', 'المملكة العربية السعودية - الرياض')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('company_phone', '+966 12 3456789')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('company_email', 'info@hawaa.com')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('company_tax_number', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('company_logo_path', '')")

    cursor.execute("DELETE FROM schema_version")
    cursor.execute("INSERT INTO schema_version(version) VALUES (3)")

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
    conn.close()
    logger.info("تم تهيئة قاعدة البيانات المحلية في: %s", DB_PATH)

def _column_names(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]


def _table_exists(cursor, table_name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def _backup_before_migration():
    """Create a safety copy of the current SQLite DB before schema changes."""
    if not os.path.exists(DB_PATH):
        return None
    backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"backup_before_migration_{stamp}.db")
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    logger.info("تم إنشاء نسخة احتياطية قبل الترحيل: %s", backup_path)
    return backup_path


def _get_schema_version(cursor):
    if not _table_exists(cursor, "schema_version"):
        return 1
    cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
    row = cursor.fetchone()
    return int(row[0]) if row else 1


def _set_schema_version(cursor, version):
    cursor.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    cursor.execute("DELETE FROM schema_version")
    cursor.execute("INSERT INTO schema_version(version) VALUES (?)", (int(version),))


def _add_column_if_missing(cursor, table_name, column_name, ddl):
    columns = _column_names(cursor, table_name)
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def _run_schema_migrations(cursor):
    """Idempotent migrations for old local databases.

    v2: Adds payment/reminder-compatible fields without deleting old data.
    Old rows with amount > 0 are treated as approved.
    Old rows with amount = 0 are treated as waiting_payment.
    """
    cursor.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    current_version = _get_schema_version(cursor)

    if not _table_exists(cursor, "expenses"):
        _set_schema_version(cursor, 3)
        return

    _add_column_if_missing(cursor, "expenses", "amount_original", "amount_original REAL NOT NULL DEFAULT 0")
    _add_column_if_missing(cursor, "expenses", "currency_original", "currency_original TEXT NOT NULL DEFAULT 'SAR'")
    _add_column_if_missing(cursor, "expenses", "exchange_rate_to_usd", "exchange_rate_to_usd REAL NOT NULL DEFAULT 1.0")
    _add_column_if_missing(cursor, "expenses", "amount_base", "amount_base REAL NOT NULL DEFAULT 0")
    _add_column_if_missing(cursor, "expenses", "status", "status TEXT DEFAULT 'approved'")
    _add_column_if_missing(cursor, "expenses", "payment_due_date", "payment_due_date TEXT")
    _add_column_if_missing(cursor, "expenses", "payment_reminder_note", "payment_reminder_note TEXT")

    # Normalize legacy rows so reports using status do not hide old records.
    cursor.execute("""
        UPDATE expenses
        SET amount_original = amount
        WHERE (amount_original IS NULL OR amount_original = 0) AND amount IS NOT NULL
    """)
    cursor.execute("""
        UPDATE expenses
        SET currency_original = COALESCE(NULLIF(currency_original, ''), COALESCE(currency, 'SAR'))
        WHERE currency_original IS NULL OR currency_original = ''
    """)
    cursor.execute("""
        UPDATE expenses
        SET exchange_rate_to_usd = 1.0
        WHERE exchange_rate_to_usd IS NULL OR exchange_rate_to_usd = 0
    """)
    # amount_base is the canonical base amount (USD) used by balances/reports.
    cursor.execute("""
        UPDATE expenses
        SET amount_base = CASE
            WHEN COALESCE(currency_original, currency, 'USD') = 'USD' THEN COALESCE(amount_original, amount, 0)
            WHEN COALESCE(exchange_rate_to_usd, 0) = 0 THEN COALESCE(amount, 0)
            ELSE ROUND(COALESCE(amount_original, amount, 0) / exchange_rate_to_usd, 2)
        END
        WHERE amount_base IS NULL OR amount_base = 0
    """)
    cursor.execute("""
        UPDATE expenses
        SET amount = amount_base
        WHERE amount_base IS NOT NULL
    """)
    cursor.execute("""
        UPDATE expenses
        SET status = CASE
            WHEN COALESCE(amount, 0) = 0 THEN 'waiting_payment'
            ELSE 'approved'
        END
        WHERE status IS NULL OR status = ''
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            reminder_date TEXT NOT NULL,
            note TEXT,
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(expense_id) REFERENCES expenses(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_company ON expenses(company_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_status ON expenses(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_payment_due_date ON expenses(payment_due_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_reminders_date ON payment_reminders(reminder_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_reminders_expense ON payment_reminders(expense_id)")

    if not _table_exists(cursor, "token_blacklist"):
        cursor.execute("""
            CREATE TABLE token_blacklist (
                jti TEXT PRIMARY KEY,
                created_at TEXT
            )
        """)

    if current_version < 2:
        _set_schema_version(cursor, 3)
    else:
        _set_schema_version(cursor, max(current_version, 3))


def ensure_db():
    db = DatabaseConnection()
    if db.is_remote():
        return
    if not os.path.exists(DB_PATH):
        init_database()
        return

    backup_path = None
    conn = None
    try:
        backup_path = _backup_before_migration()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        _run_schema_migrations(cursor)
        conn.commit()
        logger.info("تم تحديث بنية قاعدة البيانات بنجاح")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("فشل ترحيل قاعدة البيانات القديمة: %s", e)
        if backup_path:
            logger.error("تم الاحتفاظ بالنسخة الاحتياطية قبل الترحيل في: %s", backup_path)
        raise
    finally:
        if conn:
            conn.close()
