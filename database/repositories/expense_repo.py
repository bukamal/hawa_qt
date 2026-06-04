# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
from auth.session import UserSession
from currency import currency
import datetime
from typing import List, Dict

class ExpenseRepository(BaseRepository):
    def get_all(self, convert_to_display: bool = True) -> List[Dict]:
        rows = self._fetch_all("SELECT * FROM expenses ORDER BY id DESC")
        for r in rows:
            r['amount_display'] = r['amount_original']
            r['currency_display'] = r['currency_original']
        return rows
    
    def get_by_company(self, company_name: str, convert_to_display: bool = True) -> List[Dict]:
        rows = self._fetch_all("SELECT * FROM expenses WHERE company_name=? ORDER BY id DESC", (company_name,))
        for r in rows:
            r['amount_display'] = r['amount_original']
            r['currency_display'] = r['currency_original']
        return rows
    
    def add(self, company_name: str, amount: float, type_val: str, date: str, notes: str, currency_code: str, user_id: int) -> int:
        rate_to_usd = currency.get_rate_to_usd(currency_code)
        if currency_code == 'USD':
            amount_usd = amount
        else:
            amount_usd = amount / rate_to_usd
        now = datetime.datetime.now().isoformat()
        self.begin()
        try:
            cur = self._execute("""
                INSERT INTO expenses 
                (company_name, amount, type, date, notes, currency, created_by, created_at, updated_by, updated_at,
                 amount_original, currency_original, exchange_rate_to_usd)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (company_name, amount_usd, type_val, date, notes, currency_code, user_id, now, user_id, now,
                  amount, currency_code, rate_to_usd))
            exp_id = cur.lastrowid
            user = UserSession.get_current()
            audit_data = {
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "إضافة قيد",
                'table_name': 'expenses',
                'record_id': exp_id,
                'details': f"الشركة: {company_name}, المبلغ: {amount} {currency_code} (سعر الصرف: {rate_to_usd})"
            }
            self._execute("SELECT 1", audit_data=audit_data)
            self._commit()
            return exp_id
        except:
            self._rollback()
            raise
    
    def update(self, expense_id: int, company_name: str, amount: float, type_val: str, date: str, notes: str, currency_code: str, user_id: int):
        rate_to_usd = currency.get_rate_to_usd(currency_code)
        if currency_code == 'USD':
            amount_usd = amount
        else:
            amount_usd = amount / rate_to_usd
        now = datetime.datetime.now().isoformat()
        self.begin()
        try:
            self._execute("""
                UPDATE expenses SET company_name=?, type=?, date=?, notes=?, updated_by=?, updated_at=?, amount=?,
                amount_original=?, currency_original=?, exchange_rate_to_usd=?
                WHERE id=?
            """, (company_name, type_val, date, notes, user_id, now, amount_usd,
                  amount, currency_code, rate_to_usd, expense_id))
            user = UserSession.get_current()
            audit_data = {
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "تعديل قيد",
                'table_name': 'expenses',
                'record_id': expense_id,
                'details': f"الشركة: {company_name}, المبلغ: {amount} {currency_code} (سعر الصرف: {rate_to_usd})"
            }
            self._execute("SELECT 1", audit_data=audit_data)
            self._commit()
        except:
            self._rollback()
            raise
    
    def delete(self, expense_id: int, user_id: int = None):
        if user_id is None:
            user = UserSession.get_current()
            user_id = user['id'] if user else None
        self.begin()
        try:
            row = self._fetch_one("SELECT company_name, amount_original, currency_original FROM expenses WHERE id=?", (expense_id,))
            self._execute("DELETE FROM expenses WHERE id=?", (expense_id,))
            user = UserSession.get_current()
            audit_data = {
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "حذف قيد",
                'table_name': 'expenses',
                'record_id': expense_id,
                'details': f"الشركة: {row['company_name']}, المبلغ: {row['amount_original']} {row['currency_original']}" if row else ""
            }
            self._execute("SELECT 1", audit_data=audit_data)
            self._commit()
        except:
            self._rollback()
            raise
    
    def get_summary(self, convert_to_display: bool = True) -> Dict:
        rows = self._fetch_all("SELECT type, amount FROM expenses")
        total_in = 0.0
        total_out = 0.0
        for r in rows:
            if r['type'] == 'incoming':
                total_in += r['amount']
            else:
                total_out += r['amount']
        companies_count = len(set(r['company_name'] for r in self._fetch_all("SELECT DISTINCT company_name FROM expenses")))
        return {
            'total_incoming': total_in,
            'total_outgoing': total_out,
            'net': total_in - total_out,
            'companies_count': companies_count
        }
