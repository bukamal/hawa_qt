# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
from auth.session import UserSession
from currency import currency
import datetime
from typing import List, Dict

class ExpenseRepository(BaseRepository):
    def get_all(self, convert_to_display: bool = True) -> List[Dict]:
        # استخدم الدالة الجديدة في DatabaseConnection
        expenses = self.db.get_expenses()
        # التحويل للعرض إذا لزم (للوضع المحلي فقط، لأن REST يعيد البيانات كما هي)
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
        new_id = self.db.add_expense(data)
        # تسجيل التدقيق (محلياً فقط، لأن الخادم يسجل تلقائياً)
        if not self.db.is_remote():
            user = UserSession.get_current()
            self._execute("SELECT 1", audit_data={
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "إضافة قيد",
                'table_name': 'expenses',
                'record_id': new_id,
                'details': f"الشركة: {company_name}, المبلغ: {amount} {currency_code}"
            })
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
        self.db.update_expense(expense_id, data)
        if not self.db.is_remote():
            user = UserSession.get_current()
            self._execute("SELECT 1", audit_data={
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "تعديل قيد",
                'table_name': 'expenses',
                'record_id': expense_id,
                'details': f"الشركة: {company_name}, المبلغ: {amount} {currency_code}"
            })

    def delete(self, expense_id: int, user_id: int = None):
        if user_id is None:
            user = UserSession.get_current()
            user_id = user['id'] if user else None
        # جلب البيانات قبل الحذف للتسجيل (محلياً)
        if not self.db.is_remote():
            row = self._fetch_one("SELECT company_name, amount_original, currency_original FROM expenses WHERE id=?", (expense_id,))
        self.db.delete_expense(expense_id)
        if not self.db.is_remote() and row:
            user = UserSession.get_current()
            self._execute("SELECT 1", audit_data={
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "حذف قيد",
                'table_name': 'expenses',
                'record_id': expense_id,
                'details': f"الشركة: {row['company_name']}, المبلغ: {row['amount_original']} {row['currency_original']}"
            })

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
