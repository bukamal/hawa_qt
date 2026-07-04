#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import os
import sys
import datetime
import logging
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app_config import get_db_path, get_jwt_secret, is_default_jwt_secret
from logging_config import setup_logging
from money import quantize_money, decimal_to_storage, rate_to_storage, to_decimal, convert_to_usd
from services.api_contract import capabilities_payload
from services.mobile_pairing_service import mobile_pairing_service

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = get_jwt_secret()
if is_default_jwt_secret(app.config['JWT_SECRET_KEY']):
    logger.warning('Using development JWT secret. Set HAWAA_JWT_SECRET before using network/server mode.')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=8)
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']

jwt = JWTManager(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["500 per minute", "30 per second"],
    storage_uri="memory://",
)

DB_PATH = get_db_path()

def init_db():
    from database.migrations import ensure_db
    ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS token_blacklist (
            jti TEXT PRIMARY KEY,
            created_at TEXT
        )
    ''')
    conn.close()

init_db()

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def verify_password(stored_hash, salt, password):
    from auth.password import verify_password as verify
    return verify(password, stored_hash, salt)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    conn = get_db()
    row = conn.execute('SELECT 1 FROM token_blacklist WHERE jti = ?', (jti,)).fetchone()
    return row is not None

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        conn = get_db()
        user = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        return fn(*args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            conn = get_db()
            user = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user or user['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient privileges'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

write_required = role_required('admin', 'user', 'accountant', 'manager')


def _current_rate_to_usd(conn, currency_code):
    code = (currency_code or 'USD').upper()
    if code == 'USD':
        return to_decimal(1)
    row = conn.execute('SELECT rate_to_usd FROM exchange_rates WHERE currency_code=?', (code,)).fetchone()
    return to_decimal(row['rate_to_usd'] if row else 1)




def _resolve_expense_status(amount_original, requested_status=None):
    if requested_status in {'approved', 'waiting_payment', 'cancelled'}:
        return requested_status
    return 'waiting_payment' if quantize_money(amount_original) == 0 else 'approved'

def _expense_snapshot(conn, data, existing=None):
    amount_original = quantize_money(data.get('amount_original', data.get('amount', 0)))
    currency_original = (data.get('currency_original') or data.get('currency') or 'USD').upper()
    rate = _current_rate_to_usd(conn, currency_original)
    if existing and (existing['currency_original'] or existing['currency'] or '').upper() == currency_original:
        old_rate = to_decimal(existing['exchange_rate_to_usd'], 0)
        if old_rate > 0:
            # Preserve the row historical rate when editing the same original currency.
            rate = old_rate
    amount_base = convert_to_usd(amount_original, currency_original, rate)
    return {
        'amount_original': decimal_to_storage(amount_original),
        'currency_original': currency_original,
        'exchange_rate_to_usd': rate_to_storage(rate),
        'amount_base': decimal_to_storage(amount_base),
        'amount': decimal_to_storage(amount_base),
        'currency': currency_original,
    }


def log_audit(action, table_name, record_id, details, request_obj):
    user_id = get_jwt_identity() if request_obj.headers.get('Authorization') else None
    username = None
    if user_id:
        conn = get_db()
        user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
        username = user['username'] if user else None
    ip = request_obj.remote_addr
    now = datetime.datetime.now().isoformat()
    conn = get_db()
    conn.execute('''
        INSERT INTO audit_log (user_id, username, action, table_name, record_id, details, ip_address, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, action, table_name, record_id, details, ip, now))
    conn.commit()

@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    conn = get_db()
    now = datetime.datetime.now().isoformat()
    conn.execute('INSERT INTO token_blacklist (jti, created_at) VALUES (?, ?)', (jti, now))
    conn.commit()
    log_audit('تسجيل خروج', 'auth', 0, '', request)
    return jsonify({'status': 'logged out'}), 200

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    if verify_password(user['password_hash'], user['salt'], password):
        token = create_access_token(identity=str(user['id']))
        log_audit('تسجيل دخول', 'users', user['id'], f'المستخدم {username}', request)
        return jsonify({
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'full_name': user['full_name'],
                'role': user['role']
            }
        })
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/expenses', methods=['GET'])
@jwt_required()
@limiter.limit("100 per minute")
def get_expenses():
    conn = get_db()
    rows = conn.execute('SELECT * FROM expenses ORDER BY id DESC').fetchall()
    return jsonify([dict(row) for row in rows])

@app.route('/api/expenses', methods=['POST'])
@write_required
@limiter.limit("50 per minute")
def add_expense():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    required_fields = ['company_name', 'amount', 'type', 'date', 'currency']
    for f in required_fields:
        if f not in data:
            return jsonify({'error': f'Missing field: {f}'}), 400
    conn = get_db()
    now = datetime.datetime.now().isoformat()
    snapshot = _expense_snapshot(conn, data)
    if to_decimal(snapshot['amount_original']) < 0:
        return jsonify({'error': 'Amount cannot be negative'}), 400
    final_status = _resolve_expense_status(snapshot['amount_original'], data.get('status'))
    cursor = conn.execute('''
        INSERT INTO expenses
        (company_name, amount, type, date, notes, currency, created_by, created_at, updated_by, updated_at,
         amount_original, currency_original, exchange_rate_to_usd, amount_base, status, payment_due_date, payment_reminder_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['company_name'], snapshot['amount'], data['type'], data['date'],
        data.get('notes', ''), snapshot['currency'], user_id, now, user_id, now,
        snapshot['amount_original'], snapshot['currency_original'], snapshot['exchange_rate_to_usd'], snapshot['amount_base'],
        final_status,
        data.get('payment_due_date') if final_status == 'waiting_payment' else None,
        data.get('payment_reminder_note') if final_status == 'waiting_payment' else None
    ))
    conn.commit()
    new_id = cursor.lastrowid
    log_audit('إضافة قيد', 'expenses', new_id, f"الشركة: {data['company_name']}, المبلغ: {data['amount']} {data['currency']}", request)
    return jsonify({'id': new_id}), 201

@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@write_required
@limiter.limit("50 per minute")
def update_expense(expense_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    conn = get_db()
    now = datetime.datetime.now().isoformat()
    existing = conn.execute('SELECT * FROM expenses WHERE id=?', (expense_id,)).fetchone()
    if not existing:
        return jsonify({'error': 'Expense not found'}), 404
    snapshot = _expense_snapshot(conn, data, existing=existing)
    if to_decimal(snapshot['amount_original']) < 0:
        return jsonify({'error': 'Amount cannot be negative'}), 400
    final_status = _resolve_expense_status(snapshot['amount_original'], data.get('status'))
    conn.execute('''
        UPDATE expenses SET
            company_name=?, amount=?, type=?, date=?, notes=?, currency=?,
            updated_by=?, updated_at=?, amount_original=?, currency_original=?, exchange_rate_to_usd=?,
            amount_base=?, status=?, payment_due_date=?, payment_reminder_note=?
        WHERE id=?
    ''', (
        data['company_name'], snapshot['amount'], data['type'], data['date'],
        data.get('notes', ''), snapshot['currency'], user_id, now,
        snapshot['amount_original'], snapshot['currency_original'], snapshot['exchange_rate_to_usd'], snapshot['amount_base'],
        final_status,
        data.get('payment_due_date') if final_status == 'waiting_payment' else None,
        data.get('payment_reminder_note') if final_status == 'waiting_payment' else None,
        expense_id
    ))
    conn.commit()
    log_audit('تعديل قيد', 'expenses', expense_id, f"الشركة: {data['company_name']}, المبلغ: {data['amount']} {data['currency']}", request)
    return jsonify({'status': 'ok'})

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@write_required
@limiter.limit("30 per minute")
def delete_expense(expense_id):
    user_id = int(get_jwt_identity())
    conn = get_db()
    row = conn.execute('SELECT company_name, amount_original, currency_original FROM expenses WHERE id = ?', (expense_id,)).fetchone()
    if row:
        details = f"الشركة: {row['company_name']}, المبلغ: {row['amount_original']} {row['currency_original']}"
    else:
        details = ''
    conn.execute('DELETE FROM payment_reminders WHERE expense_id = ?', (expense_id,))
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    log_audit('حذف قيد', 'expenses', expense_id, details, request)
    return jsonify({'status': 'ok'})

@app.route('/api/users', methods=['GET'])
@admin_required
@limiter.limit("60 per minute")
def get_users():
    conn = get_db()
    rows = conn.execute('SELECT id, username, full_name, role, created_at, last_login FROM users').fetchall()
    return jsonify([dict(row) for row in rows])

@app.route('/api/users', methods=['POST'])
@admin_required
@limiter.limit("20 per minute")
def add_user():
    data = request.get_json()
    from auth.password import hash_password
    pwd_hash, salt = hash_password(data['password'])
    conn = get_db()
    now = datetime.datetime.now().isoformat()
    cursor = conn.execute('''
        INSERT INTO users (username, password_hash, salt, full_name, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data['username'], pwd_hash, salt, data.get('full_name', ''), data.get('role', 'user'), now))
    conn.commit()
    new_id = cursor.lastrowid
    log_audit('إضافة مستخدم', 'users', new_id, f"المستخدم: {data['username']}", request)
    return jsonify({'id': new_id}), 201

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
@limiter.limit("30 per minute")
def update_user(user_id):
    data = request.get_json()
    conn = get_db()
    conn.execute('UPDATE users SET full_name=?, role=? WHERE id=?',
                 (data.get('full_name', ''), data.get('role', 'user'), user_id))
    conn.commit()
    log_audit('تعديل مستخدم', 'users', user_id, f"الاسم: {data.get('full_name')}, صلاحية: {data.get('role')}", request)
    return jsonify({'status': 'ok'})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
@limiter.limit("20 per minute")
def delete_user(user_id):
    if user_id == 1:
        return jsonify({'error': 'Cannot delete admin'}), 400
    conn = get_db()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    log_audit('حذف مستخدم', 'users', user_id, f"المستخدم: {user['username'] if user else ''}", request)
    return jsonify({'status': 'ok'})

@app.route('/api/users/change_password', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def change_password():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    conn = get_db()
    user = conn.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not verify_password(user['password_hash'], user['salt'], old_password):
        return jsonify({'error': 'Invalid old password'}), 401
    from auth.password import hash_password
    new_hash, new_salt = hash_password(new_password)
    conn.execute('UPDATE users SET password_hash=?, salt=?, force_password_change=0 WHERE id=?',
                 (new_hash, new_salt, user_id))
    conn.commit()
    log_audit('تغيير كلمة مرور', 'users', user_id, '', request)
    return jsonify({'status': 'ok'})

@app.route('/api/audit_log', methods=['GET'])
@admin_required
@limiter.limit("30 per minute")
def get_audit_log():
    conn = get_db()
    rows = conn.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 2000').fetchall()
    return jsonify([dict(row) for row in rows])

@app.route('/api/audit_log/old', methods=['DELETE'])
@admin_required
@limiter.limit("10 per minute")
def delete_old_audit_logs():
    data = request.get_json()
    days = data.get('days', 90)
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    conn = get_db()
    conn.execute('DELETE FROM audit_log WHERE timestamp < ?', (cutoff,))
    conn.commit()
    log_audit('حذف سجلات تدقيق قديمة', 'audit_log', 0, f'أقدم من {days} يوماً', request)
    return jsonify({'status': 'ok'})

@app.route('/api/settings/<key>', methods=['GET'])
@jwt_required()
@limiter.limit("500 per minute")
def get_setting(key):
    conn = get_db()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    return jsonify({'value': row['value'] if row else None})

@app.route('/api/settings/<key>', methods=['POST'])
@admin_required
@limiter.limit("50 per minute")
def set_setting(key):
    data = request.get_json()
    value = data.get('value')
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    log_audit('تعديل إعداد', 'settings', 0, f'{key} = {value}', request)
    return jsonify({'status': 'ok'})

@app.route('/api/exchange_rates', methods=['GET'])
@jwt_required()
@limiter.limit("200 per minute")
def get_exchange_rates():
    conn = get_db()
    rows = conn.execute('SELECT currency_code, rate_to_usd, updated_at FROM exchange_rates ORDER BY currency_code').fetchall()
    return jsonify([dict(row) for row in rows])

@app.route('/api/exchange_rates/<currency_code>', methods=['PUT'])
@admin_required
def update_exchange_rate(currency_code):
    data = request.get_json()
    rate_to_usd = data.get('rate_to_usd')
    if rate_to_usd is None:
        return jsonify({'error': 'rate_to_usd required'}), 400
    now = datetime.datetime.now().isoformat()
    conn = get_db()
    stored_rate = rate_to_storage(rate_to_usd)
    conn.execute('INSERT OR REPLACE INTO exchange_rates (currency_code, rate_to_usd, updated_at) VALUES (?, ?, ?)',
                 (currency_code, stored_rate, now))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exchange_rate_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency_code TEXT NOT NULL,
            rate_to_usd REAL NOT NULL,
            effective_date TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            created_at TEXT NOT NULL
        )
    ''')
    conn.execute('''
        INSERT INTO exchange_rate_history (currency_code, rate_to_usd, effective_date, source, created_at)
        VALUES (?, ?, ?, 'manual', ?)
    ''', (currency_code, stored_rate, now[:10], now))
    conn.commit()
    log_audit('تحديث سعر صرف', 'exchange_rates', 0, f'{currency_code} = {rate_to_usd}', request)
    return jsonify({'status': 'ok'})

@app.route('/api/exchange_rate_history', methods=['GET'])
@jwt_required()
@limiter.limit("100 per minute")
def get_exchange_rate_history():
    conn = get_db()
    currency_code = request.args.get('currency_code')
    limit = min(int(request.args.get('limit', 500)), 2000)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exchange_rate_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency_code TEXT NOT NULL,
            rate_to_usd REAL NOT NULL,
            effective_date TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            created_at TEXT NOT NULL
        )
    ''')
    if currency_code:
        rows = conn.execute('''
            SELECT currency_code, rate_to_usd, effective_date, source, created_at
            FROM exchange_rate_history
            WHERE currency_code=?
            ORDER BY effective_date DESC, id DESC
            LIMIT ?
        ''', (currency_code, limit)).fetchall()
    else:
        rows = conn.execute('''
            SELECT currency_code, rate_to_usd, effective_date, source, created_at
            FROM exchange_rate_history
            ORDER BY effective_date DESC, id DESC
            LIMIT ?
        ''', (limit,)).fetchall()
    return jsonify([dict(row) for row in rows])


@app.route('/api/capabilities', methods=['GET'])
@limiter.limit("200 per minute")
def api_capabilities():
    server_url = request.args.get('server_url')
    return jsonify(capabilities_payload(server_url))


@app.route('/api/mobile/pairing-token', methods=['POST'])
@role_required('admin', 'manager')
@limiter.limit("20 per hour")
def create_mobile_pairing_token():
    data = request.get_json(silent=True) or {}
    server_url = data.get('server_url') or request.host_url.rstrip('/')
    ttl_minutes = int(data.get('ttl_minutes') or 5)
    result = mobile_pairing_service.create_pairing_payload(
        server_url=server_url,
        ttl_minutes=ttl_minutes,
        created_by=str(get_jwt_identity()),
        client_label=data.get('client_label') or 'Android',
    )
    log_audit('إنشاء رمز ربط Android', 'mobile_pairing_tokens', 0, f"الخادم: {result['server_url']}", request)
    return jsonify(result)


@app.route('/api/mobile/pair', methods=['POST'])
@limiter.limit("60 per hour")
def pair_mobile_client():
    data = request.get_json(silent=True) or {}
    token = data.get('pairing_token') or data.get('token')
    result = mobile_pairing_service.validate_pairing_token(token, consume=True)
    status = 200 if result.get('ok') else 400
    return jsonify(result), status

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'alive'})

if __name__ == '__main__':
    pass
