#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
import os
import datetime
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET', 'hawaa-secret-key-change-me')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=8)
jwt = JWTManager(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'hawaa_data.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def verify_password(stored_hash, salt, password):
    from auth.password import verify_password as verify
    return verify(password, stored_hash, salt)

# ------------------- المصادقة -------------------
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    if verify_password(user['password_hash'], user['salt'], password):
        token = create_access_token(identity=user['id'])
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

# ------------------- المصروفات -------------------
@app.route('/api/expenses', methods=['GET'])
@jwt_required()
def get_expenses():
    conn = get_db()
    rows = conn.execute('SELECT * FROM expenses ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/expenses', methods=['POST'])
@jwt_required()
def add_expense():
    user_id = get_jwt_identity()
    data = request.get_json()
    required_fields = ['company_name', 'amount', 'type', 'date', 'currency']
    for f in required_fields:
        if f not in data:
            return jsonify({'error': f'Missing field: {f}'}), 400
    conn = get_db()
    now = datetime.datetime.now().isoformat()
    cursor = conn.execute('''
        INSERT INTO expenses
        (company_name, amount, type, date, notes, currency, created_by, created_at, updated_by, updated_at,
         amount_original, currency_original, exchange_rate_to_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['company_name'], data['amount'], data['type'], data['date'],
        data.get('notes', ''), data['currency'], user_id, now, user_id, now,
        data.get('amount_original', data['amount']),
        data.get('currency_original', data['currency']),
        data.get('exchange_rate_to_usd', 1.0)
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({'id': new_id}), 201

@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@jwt_required()
def update_expense(expense_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    conn = get_db()
    now = datetime.datetime.now().isoformat()
    conn.execute('''
        UPDATE expenses SET
            company_name=?, amount=?, type=?, date=?, notes=?, currency=?,
            updated_by=?, updated_at=?, amount_original=?, currency_original=?, exchange_rate_to_usd=?
        WHERE id=?
    ''', (
        data['company_name'], data['amount'], data['type'], data['date'],
        data.get('notes', ''), data['currency'], user_id, now,
        data.get('amount_original', data['amount']),
        data.get('currency_original', data['currency']),
        data.get('exchange_rate_to_usd', 1.0),
        expense_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@jwt_required()
def delete_expense(expense_id):
    user_id = get_jwt_identity()
    conn = get_db()
    # تسجيل التدقيق (يمكن إضافته إذا لزم الأمر)
    conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# ------------------- المستخدمين -------------------
@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    conn = get_db()
    rows = conn.execute('SELECT id, username, full_name, role, created_at, last_login FROM users').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/users', methods=['POST'])
@jwt_required()
def add_user():
    current_user_id = get_jwt_identity()
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
    conn.close()
    return jsonify({'id': new_id}), 201

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    conn = get_db()
    conn.execute('UPDATE users SET full_name=?, role=? WHERE id=?',
                 (data.get('full_name', ''), data.get('role', 'user'), user_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user_id = get_jwt_identity()
    if user_id == 1:
        return jsonify({'error': 'Cannot delete admin'}), 400
    conn = get_db()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/api/users/change_password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    conn = get_db()
    user = conn.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user or not verify_password(user['password_hash'], user['salt'], old_password):
        conn.close()
        return jsonify({'error': 'Invalid old password'}), 401
    from auth.password import hash_password
    new_hash, new_salt = hash_password(new_password)
    conn.execute('UPDATE users SET password_hash=?, salt=?, force_password_change=0 WHERE id=?',
                 (new_hash, new_salt, user_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# ------------------- سجل التدقيق -------------------
@app.route('/api/audit_log', methods=['GET'])
@jwt_required()
def get_audit_log():
    conn = get_db()
    rows = conn.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 2000').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/audit_log/old', methods=['DELETE'])
@jwt_required()
def delete_old_audit_logs():
    current_user_id = get_jwt_identity()
    # يمكن التحقق من صلاحية admin
    data = request.get_json()
    days = data.get('days', 90)
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    conn = get_db()
    conn.execute('DELETE FROM audit_log WHERE timestamp < ?', (cutoff,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# ------------------- الإعدادات -------------------
@app.route('/api/settings/<key>', methods=['GET'])
@jwt_required()
def get_setting(key):
    conn = get_db()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return jsonify({'value': row['value'] if row else None})

@app.route('/api/settings/<key>', methods=['POST'])
@jwt_required()
def set_setting(key):
    data = request.get_json()
    value = data.get('value')
    conn = get_db()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

# ------------------- الصحة -------------------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'alive'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, threaded=True, debug=False)
