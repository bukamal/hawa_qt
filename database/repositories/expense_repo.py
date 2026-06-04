# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
from database.repositories.audit_repo import AuditRepository
from auth.session import UserSession
from currency import currency
import datetime
from typing import List, Dict

class ExpenseRepository(BaseRepository):
    def get_all(self, convert_to_display: bool = True) -> List[Dict]:
        rows = self._fetch_all("SELECT * FROM expenses ORDER BY id DESC")
        if convert_to_display:
            display_curr = currency.get_display_currency()
            for r in rows:
                r['amount_original'] = currency.convert(r['amount'], 'USD', r['currency'])
                r['amount'] = currency.convert(r['amount'], 'USD', display_curr)
                r['currency_display'] = display_curr
        return rows
    
    def get_by_company(self, company_name: str, convert_to_display: bool = True) -> List[Dict]:
        rows = self._fetch_all("SELECT * FROM expenses WHERE company_name=? ORDER BY id DESC", (company_name,))
        if convert_to_display:
            display_curr = currency.get_display_currency()
            for r in rows:
                r['amount_original'] = currency.convert(r['amount'], 'USD', r['currency'])
                r['amount'] = currency.convert(r['amount'], 'USD', display_curr)
                r['currency_display'] = display_curr
        return rows
    
    def add(self, company_name: str, amount: float, type_val: str, date: str, notes: str, currency_code: str, user_id: int) -> int:
        base_curr = currency.get_base_currency()
        amount_usd = currency.convert(amount, currency_code, base_curr)
        now = datetime.datetime.now().isoformat()
        self.begin()
        try:
            cur = self._execute("""
                INSERT INTO expenses (company_name, amount, type, date, notes, currency, created_by, created_at, updated_by, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (company_name, amount_usd, type_val, date, notes, currency_code, user_id, now, user_id, now))
            exp_id = cur.lastrowid
            audit = AuditRepository()
            user = UserSession.get_current()
            audit.log(user_id, user['username'] if user else '', "إضافة قيد", 'expenses', exp_id,
                      f"الشركة: {company_name}, المبلغ: {amount} {currency_code}")
            self._commit()
            return exp_id
        except:
            self._rollback()
            raise
    
    def update(self, expense_id: int, company_name: str, amount: float, type_val: str, date: str, notes: str, currency_code: str, user_id: int):
        base_curr = currency.get_base_currency()
        amount_usd = currency.convert(amount, currency_code, base_curr)
        now = datetime.datetime.now().isoformat()
        self.begin()
        try:
            self._execute("""
                UPDATE expenses SET company_name=?, amount=?, type=?, date=?, notes=?, currency=?, updated_by=?, updated_at=?
                WHERE id=?
            """, (company_name, amount_usd, type_val, date, notes, currency_code, user_id, now, expense_id))
            audit = AuditRepository()
            user = UserSession.get_current()
            audit.log(user_id, user['username'] if user else '', "تعديل قيد", 'expenses', expense_id,
                      f"الشركة: {company_name}, المبلغ: {amount} {currency_code}")
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
            row = self._fetch_one("SELECT company_name, amount, currency FROM expenses WHERE id=?", (expense_id,))
            self._execute("DELETE FROM expenses WHERE id=?", (expense_id,))
            audit = AuditRepository()
            user = UserSession.get_current()
            audit.log(user_id, user['username'] if user else '', "حذف قيد", 'expenses', expense_id,
                      f"الشركة: {row['company_name']}, المبلغ: {row['amount']} {row['currency']}" if row else "")
            self._commit()
        except:
            self._rollback()
            raise
    
    def get_summary(self, convert_to_display: bool = True) -> Dict:
        rows = self._fetch_all("SELECT type, amount, currency FROM expenses")
        total_in = 0.0
        total_out = 0.0
        display_curr = currency.get_display_currency()
        for r in rows:
            amt = r['amount']
            if convert_to_display:
                amt = currency.convert(amt, 'USD', display_curr)
            if r['type'] == 'incoming':
                total_in += amt
            else:
                total_out += amt
        companies_count = len(set(r['company_name'] for r in self._fetch_all("SELECT DISTINCT company_name FROM expenses")))
        return {
            'total_incoming': total_in,
            'total_outgoing': total_out,
            'net': total_in - total_out,
            'companies_count': companies_count
        }
