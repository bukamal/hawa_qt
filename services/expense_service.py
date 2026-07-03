# -*- coding: utf-8 -*-
"""Application service for expense operations.

UI and API layers should call a service instead of writing directly through widgets.
The repository remains the persistence adapter; this service owns permission checks and
user-context plumbing for the desktop client.
"""
from __future__ import annotations

from typing import Optional

from auth.session import UserSession
from database import ExpenseRepository
from services.permission_service import permission_service
from services.validation_service import validation_service


class ExpenseService:
    def __init__(self, repo: Optional[ExpenseRepository] = None):
        self._repo = repo

    @property
    def repo(self):
        # Keep the module-level service safe across tests/session changes.
        return self._repo or ExpenseRepository()

    def current_user_id(self):
        user = UserSession.get_current()
        return user.get('id') if user else None

    def validate_preview(self, company_name, amount, type_val, date, notes, currency_code,
                         payment_due_date=None, payment_reminder_note=None, status=None, existing_record=None):
        """Validate a draft and return cleaned data + currency preview without writing."""
        return validation_service.validate_expense(
            company_name=company_name,
            amount=amount,
            type_val=type_val,
            date=date,
            notes=notes,
            currency_code=currency_code,
            payment_due_date=payment_due_date,
            payment_reminder_note=payment_reminder_note,
            status=status,
            existing_record=existing_record,
        )

    def add(self, company_name, amount, type_val, date, notes, currency_code,
            payment_due_date=None, payment_reminder_note=None, status=None):
        permission_service.require_expense_write()
        validation = self.validate_preview(
            company_name, amount, type_val, date, notes, currency_code,
            payment_due_date=payment_due_date,
            payment_reminder_note=payment_reminder_note,
            status=status,
        )
        data = validation.cleaned
        return self.repo.add(
            data['company_name'], data['amount'], data['type_val'], data['date'], data['notes'],
            data['currency_code'], self.current_user_id(),
            payment_due_date=data['payment_due_date'],
            payment_reminder_note=data['payment_reminder_note'],
            status=data['status'],
        )

    def update(self, expense_id, company_name, amount, type_val, date, notes, currency_code,
               payment_due_date=None, payment_reminder_note=None, status=None):
        permission_service.require_expense_write()
        existing = self.repo.get_by_id(expense_id, convert_to_display=False)
        validation = self.validate_preview(
            company_name, amount, type_val, date, notes, currency_code,
            payment_due_date=payment_due_date,
            payment_reminder_note=payment_reminder_note,
            status=status,
            existing_record=existing,
        )
        data = validation.cleaned
        return self.repo.update(
            expense_id, data['company_name'], data['amount'], data['type_val'], data['date'], data['notes'],
            data['currency_code'], self.current_user_id(),
            payment_due_date=data['payment_due_date'],
            payment_reminder_note=data['payment_reminder_note'],
            status=data['status'],
        )

    def delete(self, expense_id):
        permission_service.require_expense_write()
        return self.repo.delete(expense_id, self.current_user_id())

    def get_by_id(self, expense_id, convert_to_display=True):
        return self.repo.get_by_id(expense_id, convert_to_display=convert_to_display)

    def get_by_company(self, company_name, convert_to_display=True):
        return self.repo.get_by_company(company_name, convert_to_display=convert_to_display)

    def get_all(self, convert_to_display=True):
        return self.repo.get_all(convert_to_display=convert_to_display)

    def get_summary(self, convert_to_display=True):
        return self.repo.get_summary(convert_to_display=convert_to_display)


expense_service = ExpenseService()
