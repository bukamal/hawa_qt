# -*- coding: utf-8 -*-
from database.repositories.base_repo import BaseRepository
from auth.session import UserSession
from currency import currency
import datetime
from decimal import Decimal
from typing import List, Dict
from money import decimal_to_storage, quantize_money, to_decimal, rate_to_storage, base_amount
from services.currency_ledger_service import currency_ledger

STATUS_APPROVED = 'approved'
STATUS_WAITING_PAYMENT = 'waiting_payment'
STATUS_CANCELLED = 'cancelled'

class ExpenseRepository(BaseRepository):
    def get_by_id(self, expense_id: int, convert_to_display: bool = True) -> Dict:
        if self.db.is_remote():
            rows = self.db.get_expenses()
            record = next((dict(r) for r in rows if int(r.get('id', 0)) == int(expense_id)), None)
        else:
            conn = self.db.get_connection()
            row = conn.execute('SELECT * FROM expenses WHERE id=?', (expense_id,)).fetchone()
            record = dict(row) if row else None
        if not record:
            return None
        currency_ledger.normalize_record(record)
        if convert_to_display:
            record['amount_display'] = record.get('amount_original', record.get('amount'))
            record['currency_display'] = record.get('currency_original', record.get('currency', 'SAR'))
        return record

    def get_all(self, convert_to_display: bool = True) -> List[Dict]:
        expenses = self.db.get_expenses()
        for e in expenses:
            currency_ledger.normalize_record(e)
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

    def _resolve_status(self, amount_dec: Decimal, status: str = None) -> str:
        if status:
            return status
        return STATUS_WAITING_PAYMENT if amount_dec == Decimal('0.00') else STATUS_APPROVED

    def add(self, company_name: str, amount: float, type_val: str, date: str,
            notes: str, currency_code: str, user_id: int, payment_due_date: str = None,
            payment_reminder_note: str = None, status: str = None) -> int:
        amount_dec = quantize_money(amount)
        if amount_dec < Decimal('0.00'):
            raise ValueError('لا يمكن حفظ مبلغ سالب')
        snapshot = currency_ledger.make_snapshot(amount_dec, currency_code)
        amount_usd = snapshot.amount_base
        rate_to_usd = snapshot.exchange_rate_to_usd
        final_status = self._resolve_status(amount_dec, status)
        now = datetime.datetime.now().isoformat()
        data = {
            'company_name': company_name,
            'amount': decimal_to_storage(amount_usd),
            'amount_base': decimal_to_storage(amount_usd),
            'type': type_val,
            'date': date,
            'notes': notes,
            'currency': currency_code,
            'created_by': user_id,
            'created_at': now,
            'updated_by': user_id,
            'updated_at': now,
            'amount_original': decimal_to_storage(amount_dec),
            'currency_original': currency_code,
            'exchange_rate_to_usd': rate_to_storage(rate_to_usd),
            'status': final_status,
            'payment_due_date': payment_due_date if final_status == STATUS_WAITING_PAYMENT else None,
            'payment_reminder_note': payment_reminder_note if final_status == STATUS_WAITING_PAYMENT else None,
        }

        if self.db.is_remote():
            new_id = self.db.add_expense(data)
        else:
            user = UserSession.get_current()
            audit_data = {
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "إضافة قيد" if final_status == STATUS_APPROVED else "إضافة عملية بانتظار الدفع",
                'table_name': 'expenses',
                'record_id': None,
                'details': f"الشركة: {company_name}, المبلغ: {amount_dec} {currency_code}, الحالة: {final_status}"
            }
            conn = self.db.get_connection()
            cursor = conn.execute('''
                INSERT INTO expenses
                (company_name, amount, type, date, notes, currency, created_by, created_at, updated_by, updated_at,
                 amount_original, currency_original, exchange_rate_to_usd, amount_base, status, payment_due_date, payment_reminder_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['company_name'], data['amount'], data['type'], data['date'],
                data.get('notes', ''), data['currency'], data['created_by'], data['created_at'],
                data['updated_by'], data['updated_at'], data['amount_original'],
                data['currency_original'], data['exchange_rate_to_usd'], data['amount_base'], data['status'],
                data['payment_due_date'], data['payment_reminder_note']
            ))
            new_id = cursor.lastrowid
            if final_status == STATUS_WAITING_PAYMENT and payment_due_date:
                conn.execute('''
                    INSERT INTO payment_reminders (expense_id, reminder_date, note, is_done, created_at, updated_at)
                    VALUES (?, ?, ?, 0, ?, ?)
                ''', (new_id, payment_due_date, payment_reminder_note or 'بانتظار إدخال الدفعة الأولى', now, now))
            conn.commit()
            audit_data['record_id'] = new_id
            self.db._log_audit_local(
                audit_data['user_id'], audit_data['username'], audit_data['action'],
                audit_data['table_name'], audit_data['record_id'], audit_data['details']
            )
        return new_id

    def update(self, expense_id: int, company_name: str, amount: float, type_val: str,
               date: str, notes: str, currency_code: str, user_id: int,
               payment_due_date: str = None, payment_reminder_note: str = None, status: str = None):
        amount_dec = quantize_money(amount)
        if amount_dec < Decimal('0.00'):
            raise ValueError('لا يمكن حفظ مبلغ سالب')
        existing = self.get_by_id(expense_id, convert_to_display=False)
        snapshot = currency_ledger.make_snapshot(amount_dec, currency_code, existing_record=existing)
        amount_usd = snapshot.amount_base
        rate_to_usd = snapshot.exchange_rate_to_usd
        final_status = self._resolve_status(amount_dec, status)
        now = datetime.datetime.now().isoformat()
        data = {
            'company_name': company_name,
            'amount': decimal_to_storage(amount_usd),
            'amount_base': decimal_to_storage(amount_usd),
            'type': type_val,
            'date': date,
            'notes': notes,
            'currency': currency_code,
            'updated_by': user_id,
            'updated_at': now,
            'amount_original': decimal_to_storage(amount_dec),
            'currency_original': currency_code,
            'exchange_rate_to_usd': rate_to_storage(rate_to_usd),
            'status': final_status,
            'payment_due_date': payment_due_date if final_status == STATUS_WAITING_PAYMENT else None,
            'payment_reminder_note': payment_reminder_note if final_status == STATUS_WAITING_PAYMENT else None,
        }

        if self.db.is_remote():
            self.db.update_expense(expense_id, data)
        else:
            user = UserSession.get_current()
            audit_data = {
                'user_id': user_id,
                'username': user['username'] if user else '',
                'action': "تعديل قيد" if final_status == STATUS_APPROVED else "تعديل عملية بانتظار الدفع",
                'table_name': 'expenses',
                'record_id': expense_id,
                'details': f"الشركة: {company_name}, المبلغ: {amount_dec} {currency_code}, الحالة: {final_status}"
            }
            conn = self.db.get_connection()
            conn.execute('''
                UPDATE expenses SET
                    company_name=?, amount=?, type=?, date=?, notes=?, currency=?,
                    updated_by=?, updated_at=?, amount_original=?, currency_original=?, exchange_rate_to_usd=?,
                    amount_base=?, status=?, payment_due_date=?, payment_reminder_note=?
                WHERE id=?
            ''', (
                data['company_name'], data['amount'], data['type'], data['date'],
                data.get('notes', ''), data['currency'], data['updated_by'], data['updated_at'],
                data['amount_original'], data['currency_original'], data['exchange_rate_to_usd'], data['amount_base'],
                data['status'], data['payment_due_date'], data['payment_reminder_note'], expense_id
            ))
            conn.execute('DELETE FROM payment_reminders WHERE expense_id=?', (expense_id,))
            if final_status == STATUS_WAITING_PAYMENT and payment_due_date:
                conn.execute('''
                    INSERT INTO payment_reminders (expense_id, reminder_date, note, is_done, created_at, updated_at)
                    VALUES (?, ?, ?, 0, ?, ?)
                ''', (expense_id, payment_due_date, payment_reminder_note or 'بانتظار إدخال الدفعة الأولى', now, now))
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
            conn = self.db.get_connection()
            row = conn.execute('SELECT company_name, amount_original, currency_original FROM expenses WHERE id=?', (expense_id,)).fetchone()
            details = f"الشركة: {row['company_name']}, المبلغ: {row['amount_original']} {row['currency_original']}" if row else ""
            conn.execute('DELETE FROM payment_reminders WHERE expense_id=?', (expense_id,))
            conn.execute('DELETE FROM expenses WHERE id=?', (expense_id,))
            conn.commit()
            user = UserSession.get_current()
            self.db._log_audit_local(
                user_id, user['username'] if user else '', "حذف قيد",
                'expenses', expense_id, details
            )

    def get_payment_alerts(self) -> Dict:
        expenses = self.get_all(convert_to_display=False)
        today = datetime.date.today().isoformat()
        waiting = [e for e in expenses if e.get('status') == STATUS_WAITING_PAYMENT]
        overdue = [e for e in waiting if e.get('payment_due_date') and e['payment_due_date'] < today]
        due_today = [e for e in waiting if e.get('payment_due_date') == today]
        return {'waiting': waiting, 'overdue': overdue, 'due_today': due_today}

    def get_summary(self, convert_to_display: bool = True) -> Dict:
        expenses = [e for e in self.get_all(convert_to_display=False) if e.get('status', STATUS_APPROVED) == STATUS_APPROVED]
        total_in_dec = sum((base_amount(e) for e in expenses if e['type'] == 'incoming'), Decimal('0'))
        total_out_dec = sum((base_amount(e) for e in expenses if e['type'] == 'outgoing'), Decimal('0'))
        total_in = decimal_to_storage(total_in_dec)
        total_out = decimal_to_storage(total_out_dec)
        companies_count = len(set(e['company_name'] for e in expenses))
        return {
            'total_incoming': total_in,
            'total_outgoing': total_out,
            'net': total_in - total_out,
            'companies_count': companies_count
        }
