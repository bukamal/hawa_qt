# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
from auth.session import UserSession
from currency import currency
import datetime
from typing import List, Dict

class ExpenseRepository(BaseRepository):
    def get_all(self, convert_to_display: bool = True) -> List[Dict]:
        expenses = self.db.get_expenses()
        if convert_to_display:
            for e in expenses:
                e['amount_display'] = e.get('amount_original', e['amount'])
                e['currency_display'] = e.get('currency_original', e.get('currency', 'SAR'))
        return expenses

    def get_by_company(self, company_name: str, convert_to_display: bool = True) -> List[Dict]:
        all_expenses = self.get_all(convert_to_display=False)
        filtered = [e for e in all_expenses if e['company_name'] == company_name]
        if convert_to_display:
            for e in filtered:
                e['amount_display'] = e.get('amount_original', e['amount'])
                e['currency_display'] = e.get('currency_original', e.get('currency', 'SAR'))
        return filtered

    def add(self, company_name: str, amount: float, type_val: str, date: str,
            notes: str, currency_code: str, user_id: int) -> int:
        rate_to_usd = currency.get_rate_to_usd(currency_code)
        if currency_code == 'USD':
            amount_usd = amount
        else:
            amount_usd = amount / rate_to_usd
        now = datetime.datetime.now().isoformat()
        data = {
            'company_name': company_name,
            'amount': amount_usd,
            'type': type_val,
            'date': date,
            'notes': notes,
            'currency': currency_code,
            'created_by': user_id,
            'created_at': now,
            'updated_by': user_id,
            'updated_at': now,
            'amount_original': amount,
            'currency_original': currency_code,
            'exchange_rate_to_usd': rate_to_usd
        }

        if self.db.is_remote():
            # وضع العميل: استخدم REST
            new_id = self.db.add_expense(data)
        else:
            # وضع محلي: استخدم SQL مباشرة مع audit_data
            user = UserSession.get_current()
            audit_data = {
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "إضافة قيد",
                'table_name': 'expenses',
                'record_id': None,  # سيتم تعيينه بعد الإدراج
                'details': f"الشركة: {company_name}, المبلغ: {amount} {currency_code}"
            }
            conn = self.db.get_connection()
            cursor = conn.execute('''
                INSERT INTO expenses
                (company_name, amount, type, date, notes, currency, created_by, created_at, updated_by, updated_at,
                 amount_original, currency_original, exchange_rate_to_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['company_name'], data['amount'], data['type'], data['date'],
                data.get('notes', ''), data['currency'], data['created_by'], data['created_at'],
                data['updated_by'], data['updated_at'], data['amount_original'],
                data['currency_original'], data['exchange_rate_to_usd']
            ))
            conn.commit()
            new_id = cursor.lastrowid
            # تسجيل التدقيق مع record_id الفعلي
            audit_data['record_id'] = new_id
            self.db._log_audit_local(
                audit_data['user_id'], audit_data['username'], audit_data['action'],
                audit_data['table_name'], audit_data['record_id'], audit_data['details']
            )
        return new_id

    def update(self, expense_id: int, company_name: str, amount: float, type_val: str,
               date: str, notes: str, currency_code: str, user_id: int):
        rate_to_usd = currency.get_rate_to_usd(currency_code)
        if currency_code == 'USD':
            amount_usd = amount
        else:
            amount_usd = amount / rate_to_usd
        now = datetime.datetime.now().isoformat()
        data = {
            'company_name': company_name,
            'amount': amount_usd,
            'type': type_val,
            'date': date,
            'notes': notes,
            'currency': currency_code,
            'updated_by': user_id,
            'updated_at': now,
            'amount_original': amount,
            'currency_original': currency_code,
            'exchange_rate_to_usd': rate_to_usd
        }

        if self.db.is_remote():
            self.db.update_expense(expense_id, data)
        else:
            user = UserSession.get_current()
            audit_data = {
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "تعديل قيد",
                'table_name': 'expenses',
                'record_id': expense_id,
                'details': f"الشركة: {company_name}, المبلغ: {amount} {currency_code}"
            }
            conn = self.db.get_connection()
            conn.execute('''
                UPDATE expenses SET
                    company_name=?, amount=?, type=?, date=?, notes=?, currency=?,
                    updated_by=?, updated_at=?, amount_original=?, currency_original=?, exchange_rate_to_usd=?
                WHERE id=?
            ''', (
                data['company_name'], data['amount'], data['type'], data['date'],
                data.get('notes', ''), data['currency'], data['updated_by'], data['updated_at'],
                data['amount_original'], data['currency_original'], data['exchange_rate_to_usd'],
                expense_id
            ))
            conn.commit()
            self.db._log_audit_local(
                audit_data['user_id'], audit_data['username'], audit_data['action'],
                audit_data['table_name'], audit_data['record_id'], audit_data['details']
            )

    def delete(self, expense_id: int, user_id: int = None):
        if user_id is None:
            user = UserSession.get_current()
            user_id = user['id'] if user else None

        if self.db.is_remote():
            self.db.delete_expense(expense_id)
        else:
            # جلب البيانات قبل الحذف للتسجيل
            conn = self.db.get_connection()
            row = conn.execute('SELECT company_name, amount_original, currency_original FROM expenses WHERE id=?', (expense_id,)).fetchone()
            details = f"الشركة: {row['company_name']}, المبلغ: {row['amount_original']} {row['currency_original']}" if row else ""
            conn.execute('DELETE FROM expenses WHERE id=?', (expense_id,))
            conn.commit()
            user = UserSession.get_current()
            self.db._log_audit_local(
                user_id, user['username'] if user else '', "حذف قيد",
                'expenses', expense_id, details
            )

    def get_summary(self, convert_to_display: bool = True) -> Dict:
        expenses = self.get_all(convert_to_display=False)
        total_in = sum(e['amount'] for e in expenses if e['type'] == 'incoming')
        total_out = sum(e['amount'] for e in expenses if e['type'] == 'outgoing')
        companies_count = len(set(e['company_name'] for e in expenses))
        return {
            'total_incoming': total_in,
            'total_outgoing': total_out,
            'net': total_in - total_out,
            'companies_count': companies_count
        }
