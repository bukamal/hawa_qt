from PyQt5.QtWidgets import QFormLayout, QLineEdit, QDoubleSpinBox, QDateEdit, QTextEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QLabel, QCheckBox
from PyQt5.QtCore import QDate, QSettings, Qt
from database import ExpenseRepository
from auth.session import UserSession
from i18n.translator import translate
from views.centered_dialog import CenteredDialog
from currency import currency
from money import convert_to_usd, to_decimal

class AddEditExpenseDialog(CenteredDialog):
    def __init__(self, parent=None, expense=None, company_name=None):
        super().__init__(parent=parent)
        self.expense = expense
        self.predefined_company = company_name
        self.saved_status = None
        self.saved_payment_due_date = None
        self.saved_message = None
        self.setWindowTitle(translate('add') if not expense else translate('edit'))
        self.resize(550, 660)
        self.settings = QSettings("Hawaa", "Accounting")
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20,20,20,20)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        
        self.company_edit = QLineEdit()
        if self.predefined_company:
            self.company_edit.setText(self.predefined_company)
            self.company_edit.setEnabled(False)
            self.company_edit.setVisible(False)
        elif expense:
            self.company_edit.setText(expense['company_name'])
        form.addRow(translate('company_name')+":", self.company_edit)
        
        amount_layout = QHBoxLayout()
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.00, 999999999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSpecialValueText("0.00")
        amount_layout.addWidget(self.amount_spin)
        
        self.currency_combo = QComboBox()
        currencies = ["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"]
        self.currency_combo.addItems(currencies)
        if expense:
            curr = expense.get('currency_original', expense.get('currency', 'SAR'))
            idx = currencies.index(curr) if curr in currencies else 0
            self.currency_combo.setCurrentIndex(idx)
        else:
            last_currency = self.settings.value("last_used_currency", currency.get_display_currency())
            self.currency_combo.setCurrentText(last_currency if last_currency in currencies else currency.get_display_currency())
        amount_layout.addWidget(self.currency_combo)
        form.addRow(translate('amount')+":", amount_layout)
        
        self.zero_amount_notice = QLabel("يمكن حفظ مبلغ 0 كعملية بانتظار الدفع، ولن تؤثر على الأرصدة حتى إدخال مبلغ فعلي.")
        self.zero_amount_notice.setWordWrap(True)
        self.zero_amount_notice.setStyleSheet("color: #b45309; background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px; padding: 8px;")
        form.addRow("", self.zero_amount_notice)
        
        self.conversion_label = QLabel()
        self.conversion_label.setStyleSheet("color: #64748b; font-size: 11px;")
        form.addRow("", self.conversion_label)
        
        self.rate_label = QLabel()
        self.rate_label.setStyleSheet("color: #10b981; font-size: 10px;")
        form.addRow("", self.rate_label)
        
        self.historical_rate_label = QLabel()
        self.historical_rate_label.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: bold;")
        if expense and expense.get('exchange_rate_to_usd'):
            rate_hist = expense['exchange_rate_to_usd']
            curr_hist = expense.get('currency_original', expense.get('currency', 'SAR'))
            self.historical_rate_label.setText(f"🗓️ سعر الصرف عند الإدراج: 1 USD = {rate_hist:.4f} {curr_hist}")
        form.addRow("", self.historical_rate_label)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([translate('incoming'), translate('outgoing')])
        if expense and expense['type'] == 'outgoing':
            self.type_combo.setCurrentIndex(1)
        form.addRow(translate('type')+":", self.type_combo)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        if expense:
            self.date_edit.setDate(QDate.fromString(expense['date'], "yyyy-MM-dd"))
        form.addRow(translate('date')+":", self.date_edit)

        self.payment_due_edit = QDateEdit()
        self.payment_due_edit.setCalendarPopup(True)
        self.payment_due_edit.setDate(QDate.currentDate().addDays(7))
        if expense and expense.get('payment_due_date'):
            self.payment_due_edit.setDate(QDate.fromString(expense['payment_due_date'], "yyyy-MM-dd"))
        form.addRow("تاريخ تنبيه الدفع:", self.payment_due_edit)

        self.payment_note_edit = QLineEdit()
        self.payment_note_edit.setPlaceholderText("مثال: تذكير العميل بالدفعة الأولى")
        if expense and expense.get('payment_reminder_note'):
            self.payment_note_edit.setText(expense.get('payment_reminder_note') or '')
        form.addRow("ملاحظة التنبيه:", self.payment_note_edit)
        
        self.notes_edit = QTextEdit()
        if expense:
            self.notes_edit.setPlainText(expense['notes'] or '')
        form.addRow(translate('notes')+":", self.notes_edit)
        
        layout.addLayout(form)
        
        btns = QHBoxLayout()
        save_btn = QPushButton(translate('save'))
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton(translate('cancel'))
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        
        self.amount_spin.valueChanged.connect(self.update_labels)
        self.amount_spin.valueChanged.connect(self.update_payment_fields_visibility)
        self.currency_combo.currentTextChanged.connect(self.update_labels)
        if expense:
            self.amount_spin.setValue(expense.get('amount_original', expense['amount']))
        self.update_labels()
        self.update_payment_fields_visibility()
        self.company_edit.setFocus()
    
    def update_payment_fields_visibility(self):
        is_zero = self.amount_spin.value() == 0
        self.zero_amount_notice.setVisible(is_zero)
        self.payment_due_edit.setEnabled(is_zero)
        self.payment_note_edit.setEnabled(is_zero)
    
    def update_labels(self):
        amount = self.amount_spin.value()
        curr = self.currency_combo.currentText()
        rate = currency.get_rate_to_usd(curr)
        usd_value = convert_to_usd(amount, curr, rate)
        self.conversion_label.setText(f"≈ {float(usd_value):.2f} USD (حسب سعر الصرف الحالي)")
        self.rate_label.setText(f"سعر الصرف الحالي: 1 USD = {float(to_decimal(rate)):.4f} {curr}")
    
    def save(self):
        if self.predefined_company:
            company = self.predefined_company
        else:
            company = self.company_edit.text().strip()
            if not company:
                QMessageBox.warning(self, translate('error'), translate('company_name')+" "+translate('error'))
                return
        
        amount = self.amount_spin.value()
        if amount < 0:
            QMessageBox.warning(self, translate('error'), "لا يمكن حفظ مبلغ سالب")
            return
        type_val = 'incoming' if self.type_combo.currentIndex() == 0 else 'outgoing'
        date = self.date_edit.date().toString("yyyy-MM-dd")
        notes = self.notes_edit.toPlainText().strip()
        currency_code = self.currency_combo.currentText()
        payment_due_date = self.payment_due_edit.date().toString("yyyy-MM-dd") if amount == 0 else None
        payment_note = self.payment_note_edit.text().strip() if amount == 0 else None
        
        self.settings.setValue("last_used_currency", currency_code)
        
        user = UserSession.get_current()
        user_id = user['id'] if user else None
        repo = ExpenseRepository()
        try:
            if self.expense:
                repo.update(self.expense['id'], company, amount, type_val, date, notes, currency_code, user_id,
                            payment_due_date=payment_due_date, payment_reminder_note=payment_note)
            else:
                repo.add(company, amount, type_val, date, notes, currency_code, user_id,
                         payment_due_date=payment_due_date, payment_reminder_note=payment_note)
            if amount == 0:
                self.saved_status = 'waiting_payment'
                self.saved_payment_due_date = payment_due_date
                self.saved_message = "تم حفظ العملية بانتظار الدفع. لن تؤثر على الأرصدة أو التقارير المالية حتى إدخال مبلغ فعلي."
            else:
                self.saved_status = 'approved'
                self.saved_message = "تم حفظ القيد المالي بنجاح."
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, translate('error'), f"فشل حفظ القيد: {str(e)}")
