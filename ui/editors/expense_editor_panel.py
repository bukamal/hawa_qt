# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QDoubleSpinBox, QDateEdit, QTextEdit,
    QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QLabel,
    QScrollArea, QSizePolicy
)
from PyQt5.QtCore import QDate, QSettings, Qt, pyqtSignal

from i18n.translator import translate
from currency import currency
from money import to_decimal
from services.currency_ledger_service import currency_ledger
from services.expense_service import expense_service
from services.validation_service import ValidationError, validation_service
from services.audio_service import audio_service


class ExpenseEditorPanel(QWidget):
    """Inline editor for financial entries.

    Phase 8 stabilizes this panel as the main entry UX:
    - no dialog required for normal add/edit;
    - visible historical-rate preview before saving;
    - inline field validation instead of interrupting message boxes;
    - dirty-state protection, Ctrl+S save and Esc cancel.
    """
    saved = pyqtSignal(dict)
    cancelled = pyqtSignal()

    def __init__(self, expense=None, company_name=None, parent=None):
        super().__init__(parent)
        self.expense = expense
        self.predefined_company = company_name
        self.saved_status = None
        self.saved_payment_due_date = None
        self.saved_message = None
        self.settings = QSettings("Hawaa", "Accounting")
        self._loading = True
        self._dirty = False
        self._initial_state = None
        self.field_error_labels = {}
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()
        self._load_initial_values()
        self._connect_dirty_signals()
        self._initial_state = self._current_state()
        self._dirty = False
        self._loading = False
        self._update_dirty_indicator()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(10)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.title_label = QLabel('تحرير قيد مالي' if self.expense else 'إضافة قيد مالي')
        self.title_label.setObjectName('InlineEditorTitle')
        self.dirty_label = QLabel('')
        self.dirty_label.setStyleSheet('color: #b45309; font-size: 11px;')
        header.addWidget(self.title_label, 1)
        header.addWidget(self.dirty_label)
        outer_layout.addLayout(header)

        self.feedback_label = QLabel('')
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setVisible(False)
        outer_layout.addWidget(self.feedback_label)

        self.snapshot_notice = QLabel(
            'يتم تثبيت سعر الصرف داخل القيد عند الحفظ. عملة العرض لا تغيّر أرصدة القيود التاريخية.'
        )
        self.snapshot_notice.setWordWrap(True)
        self.snapshot_notice.setStyleSheet(
            "color: #334155; background: #f8fafc; border: 1px solid #cbd5e1; "
            "border-radius: 8px; padding: 8px;"
        )
        outer_layout.addWidget(self.snapshot_notice)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        form_container = QWidget()
        layout = QVBoxLayout(form_container)
        layout.setSpacing(10)
        layout.setContentsMargins(6, 4, 6, 4)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setVerticalSpacing(8)
        form.setHorizontalSpacing(10)

        self.company_edit = QLineEdit()
        self._add_field(form, 'company_name', translate('company_name') + ':', self.company_edit)

        amount_layout = QHBoxLayout()
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.00, 999999999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSpecialValueText('0.00')
        amount_layout.addWidget(self.amount_spin, 1)

        self.currency_combo = QComboBox()
        self.currencies = ["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"]
        self.currency_combo.addItems(self.currencies)
        amount_layout.addWidget(self.currency_combo)
        amount_widget = QWidget()
        amount_widget.setLayout(amount_layout)
        self._add_field(form, 'amount', translate('amount') + ':', amount_widget)
        self.field_error_labels['currency_code'] = self.field_error_labels['amount']

        self.zero_amount_notice = QLabel(
            'يمكن حفظ مبلغ 0 كعملية بانتظار الدفع، ولن تؤثر على الأرصدة حتى إدخال مبلغ فعلي.'
        )
        self.zero_amount_notice.setWordWrap(True)
        self.zero_amount_notice.setStyleSheet(
            "color: #b45309; background: #fffbeb; border: 1px solid #f59e0b; "
            "border-radius: 8px; padding: 6px;"
        )
        self.zero_amount_notice.setMaximumHeight(60)
        form.addRow('', self.zero_amount_notice)

        self.conversion_label = QLabel()
        self.conversion_label.setWordWrap(True)
        self.conversion_label.setStyleSheet('color: #334155; font-size: 11px; background: #f8fafc; border-radius: 8px; padding: 6px;')
        form.addRow('', self.conversion_label)

        self.rate_label = QLabel()
        self.rate_label.setWordWrap(True)
        self.rate_label.setStyleSheet('color: #047857; font-size: 10px;')
        form.addRow('', self.rate_label)

        self.historical_rate_label = QLabel()
        self.historical_rate_label.setWordWrap(True)
        self.historical_rate_label.setStyleSheet('color: #b45309; font-size: 10px; font-weight: bold;')
        form.addRow('', self.historical_rate_label)

        self.currency_warning_label = QLabel('')
        self.currency_warning_label.setWordWrap(True)
        self.currency_warning_label.setVisible(False)
        self.currency_warning_label.setStyleSheet(
            "color: #92400e; background: #fffbeb; border: 1px solid #f59e0b; "
            "border-radius: 8px; padding: 6px;"
        )
        form.addRow('', self.currency_warning_label)

        self.type_combo = QComboBox()
        self.type_combo.addItems([translate('incoming'), translate('outgoing')])
        self._add_field(form, 'type_val', translate('type') + ':', self.type_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self._add_field(form, 'date', translate('date') + ':', self.date_edit)

        self.payment_due_edit = QDateEdit()
        self.payment_due_edit.setCalendarPopup(True)
        self.payment_due_edit.setDate(QDate.currentDate().addDays(7))
        self._add_field(form, 'payment_due_date', 'تاريخ تنبيه الدفع:', self.payment_due_edit)

        self.payment_note_edit = QLineEdit()
        self.payment_note_edit.setPlaceholderText('مثال: تذكير العميل بالدفعة الأولى')
        self._add_field(form, 'payment_reminder_note', 'ملاحظة التنبيه:', self.payment_note_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText('ملاحظات مختصرة عن العملية')
        self.notes_edit.setFixedHeight(86)
        self.notes_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._add_field(form, 'notes', translate('notes') + ':', self.notes_edit)

        layout.addLayout(form)
        layout.addStretch(1)
        scroll.setWidget(form_container)
        outer_layout.addWidget(scroll, 1)

        self.shortcut_hint = QLabel('اختصارات: Ctrl+S للحفظ، Esc للإغلاق')
        self.shortcut_hint.setStyleSheet('color: #64748b; font-size: 10px;')
        outer_layout.addWidget(self.shortcut_hint)

        btns = QHBoxLayout()
        self.save_btn = QPushButton('💾 ' + translate('save'))
        self.save_btn.clicked.connect(self.save)
        self.cancel_btn = QPushButton('✖ ' + translate('cancel'))
        self.cancel_btn.clicked.connect(self.request_cancel)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.cancel_btn)
        outer_layout.addLayout(btns)

        self.amount_spin.valueChanged.connect(self.update_labels)
        self.amount_spin.valueChanged.connect(self.update_payment_fields_visibility)
        self.currency_combo.currentTextChanged.connect(self.update_labels)

    def _add_field(self, form, field_key, label, widget):
        form.addRow(label, widget)
        err = QLabel('')
        err.setWordWrap(True)
        err.setVisible(False)
        err.setStyleSheet('color: #dc2626; font-size: 10px; padding-bottom: 4px;')
        form.addRow('', err)
        self.field_error_labels[field_key] = err

    def _load_initial_values(self):
        if self.predefined_company:
            self.company_edit.setText(self.predefined_company)
            self.company_edit.setEnabled(False)
        elif self.expense:
            self.company_edit.setText(self.expense.get('company_name', ''))

        if self.expense:
            curr = self.expense.get('currency_original', self.expense.get('currency', 'SAR'))
            self.currency_combo.setCurrentText(curr if curr in self.currencies else 'USD')
            self.amount_spin.setValue(float(to_decimal(self.expense.get('amount_original', self.expense.get('amount', 0)))))
            if self.expense.get('type') == 'outgoing':
                self.type_combo.setCurrentIndex(1)
            if self.expense.get('date'):
                self.date_edit.setDate(QDate.fromString(self.expense['date'], 'yyyy-MM-dd'))
            if self.expense.get('payment_due_date'):
                self.payment_due_edit.setDate(QDate.fromString(self.expense['payment_due_date'], 'yyyy-MM-dd'))
            if self.expense.get('payment_reminder_note'):
                self.payment_note_edit.setText(self.expense.get('payment_reminder_note') or '')
            self.notes_edit.setPlainText(self.expense.get('notes') or '')
            if self.expense.get('exchange_rate_to_usd'):
                curr_hist = self.expense.get('currency_original', self.expense.get('currency', 'SAR'))
                self.historical_rate_label.setText(
                    f"🗓️ سعر الصرف عند الإدراج: {currency_ledger.historical_rate_label(self.expense.get('exchange_rate_to_usd'), curr_hist)}"
                )
        else:
            last_currency = self.settings.value('last_used_currency', currency.get_display_currency())
            self.currency_combo.setCurrentText(last_currency if last_currency in self.currencies else currency.get_display_currency())

        self.update_labels()
        self.update_payment_fields_visibility()
        if self.company_edit.isEnabled():
            self.company_edit.setFocus()
        else:
            self.amount_spin.setFocus()

    def _connect_dirty_signals(self):
        self.company_edit.textChanged.connect(self._mark_dirty)
        self.amount_spin.valueChanged.connect(self._mark_dirty)
        self.currency_combo.currentTextChanged.connect(self._mark_dirty)
        self.type_combo.currentIndexChanged.connect(self._mark_dirty)
        self.date_edit.dateChanged.connect(self._mark_dirty)
        self.payment_due_edit.dateChanged.connect(self._mark_dirty)
        self.payment_note_edit.textChanged.connect(self._mark_dirty)
        self.notes_edit.textChanged.connect(self._mark_dirty)

    def _current_state(self):
        return {
            'company_name': self.predefined_company or self.company_edit.text().strip(),
            'amount': round(float(self.amount_spin.value()), 2),
            'currency_code': self.currency_combo.currentText(),
            'type_val': 'incoming' if self.type_combo.currentIndex() == 0 else 'outgoing',
            'date': self.date_edit.date().toString('yyyy-MM-dd'),
            'payment_due_date': self.payment_due_edit.date().toString('yyyy-MM-dd'),
            'payment_reminder_note': self.payment_note_edit.text().strip(),
            'notes': self.notes_edit.toPlainText().strip(),
        }

    def _mark_dirty(self, *_args):
        if self._loading:
            return
        self._dirty = self._current_state() != self._initial_state
        self._update_dirty_indicator()
        self.clear_field_errors()
        self.hide_feedback()

    def _update_dirty_indicator(self):
        self.dirty_label.setText('● تغييرات غير محفوظة' if self._dirty else '')
        self.save_btn.setText(('💾 حفظ *' if self._dirty else '💾 ' + translate('save')))

    def update_payment_fields_visibility(self):
        is_zero = self.amount_spin.value() == 0
        self.zero_amount_notice.setVisible(is_zero)
        self.payment_due_edit.setEnabled(is_zero)
        self.payment_note_edit.setEnabled(is_zero)

    def update_labels(self):
        amount = self.amount_spin.value()
        curr = self.currency_combo.currentText()
        existing = self.expense if self.expense else None
        try:
            preview = validation_service.expense_preview(amount, curr, existing_record=existing)
            if preview.rate_mode == 'historical':
                self.conversion_label.setText(
                    f"القيمة المحاسبية: {preview.base_amount_label} | العرض الحالي: {preview.display_amount_label}\n"
                    f"محسوبة بالسعر التاريخي المحفوظ."
                )
                self.rate_label.setText(
                    f"سيُحفظ السعر التاريخي للقيد: {preview.historical_rate_label} | "
                    f"السعر الحالي للمرجع فقط: {preview.current_rate_label}"
                )
            else:
                self.conversion_label.setText(
                    f"القيمة المحاسبية عند الحفظ: {preview.base_amount_label} | العرض الحالي: {preview.display_amount_label}\n"
                    f"سيتم تثبيت سعر الصرف الحالي داخل القيد."
                )
                self.rate_label.setText(f"سعر الصرف الحالي: {preview.current_rate_label}")
            self.currency_warning_label.setVisible(bool(preview.warning))
            self.currency_warning_label.setText('⚠️ ' + preview.warning if preview.warning else '')
        except Exception as exc:
            self.conversion_label.setText('تعذر حساب التحويل')
            self.rate_label.setText(str(exc))
            self.currency_warning_label.setVisible(False)

    def clear_field_errors(self):
        for label in set(self.field_error_labels.values()):
            label.clear()
            label.setVisible(False)

    def show_feedback(self, message, level='error'):
        styles = {
            'error': "color: #991b1b; background: #fee2e2; border: 1px solid #ef4444; border-radius: 8px; padding: 8px;",
            'warning': "color: #92400e; background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px; padding: 8px;",
            'success': "color: #065f46; background: #d1fae5; border: 1px solid #10b981; border-radius: 8px; padding: 8px;",
        }
        self.feedback_label.setStyleSheet(styles.get(level, styles['error']))
        self.feedback_label.setText(message)
        self.feedback_label.setVisible(True)

    def hide_feedback(self):
        self.feedback_label.clear()
        self.feedback_label.setVisible(False)

    def _show_validation_errors(self, field_errors):
        self.clear_field_errors()
        first_widget = None
        widget_map = {
            'company_name': self.company_edit,
            'amount': self.amount_spin,
            'currency_code': self.currency_combo,
            'type_val': self.type_combo,
            'date': self.date_edit,
            'payment_due_date': self.payment_due_edit,
            'payment_reminder_note': self.payment_note_edit,
            'notes': self.notes_edit,
        }
        for field, message in field_errors.items():
            label = self.field_error_labels.get(field)
            if label:
                label.setText(message)
                label.setVisible(True)
            first_widget = first_widget or widget_map.get(field)
        audio_service.play_error()
        self.show_feedback('راجع الحقول المعلّمة بالأحمر قبل الحفظ.', 'error')
        if first_widget:
            first_widget.setFocus()

    def _collect_payload(self):
        amount = self.amount_spin.value()
        return {
            'company': self.predefined_company or self.company_edit.text().strip(),
            'amount': amount,
            'type_val': 'incoming' if self.type_combo.currentIndex() == 0 else 'outgoing',
            'date': self.date_edit.date().toString('yyyy-MM-dd'),
            'notes': self.notes_edit.toPlainText().strip(),
            'currency_code': self.currency_combo.currentText(),
            'payment_due_date': self.payment_due_edit.date().toString('yyyy-MM-dd') if amount == 0 else None,
            'payment_note': self.payment_note_edit.text().strip() if amount == 0 else None,
        }

    def save(self):
        payload = self._collect_payload()
        self.settings.setValue('last_used_currency', payload['currency_code'])
        try:
            if self.expense:
                expense_service.update(
                    self.expense['id'], payload['company'], payload['amount'], payload['type_val'], payload['date'],
                    payload['notes'], payload['currency_code'], payment_due_date=payload['payment_due_date'],
                    payment_reminder_note=payload['payment_note']
                )
                expense_id = self.expense['id']
            else:
                expense_id = expense_service.add(
                    payload['company'], payload['amount'], payload['type_val'], payload['date'], payload['notes'],
                    payload['currency_code'], payment_due_date=payload['payment_due_date'],
                    payment_reminder_note=payload['payment_note']
                )

            if payload['amount'] == 0:
                self.saved_status = 'waiting_payment'
                self.saved_payment_due_date = payload['payment_due_date']
                self.saved_message = 'تم حفظ العملية بانتظار الدفع. لن تؤثر على الأرصدة أو التقارير المالية حتى إدخال مبلغ فعلي.'
            else:
                self.saved_status = 'approved'
                self.saved_payment_due_date = None
                self.saved_message = 'تم حفظ القيد المالي بنجاح.'

            self._dirty = False
            self._initial_state = self._current_state()
            self._update_dirty_indicator()
            self.saved.emit({
                'id': expense_id,
                'company_name': payload['company'],
                'status': self.saved_status,
                'payment_due_date': self.saved_payment_due_date,
                'message': self.saved_message,
            })
        except ValidationError as exc:
            self._show_validation_errors(exc.field_errors)
        except PermissionError as exc:
            audio_service.play_error()
            self.show_feedback(str(exc), 'error')
        except Exception as exc:
            audio_service.play_error()
            self.show_feedback(f"فشل حفظ القيد: {str(exc)}", 'error')

    def has_unsaved_changes(self):
        return self._dirty

    def confirm_discard_changes(self):
        if not self._dirty:
            return True
        audio_service.play_warning()
        reply = QMessageBox.question(
            self,
            'تغييرات غير محفوظة',
            'هناك تغييرات غير محفوظة. هل تريد إغلاق المحرر بدون حفظ؟',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def request_cancel(self):
        if not self.confirm_discard_changes():
            return
        self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.save()
            event.accept()
            return
        if event.key() == Qt.Key_Escape:
            self.request_cancel()
            event.accept()
            return
        super().keyPressEvent(event)
