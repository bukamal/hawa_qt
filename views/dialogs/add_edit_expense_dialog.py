from PyQt5.QtWidgets import QFormLayout, QLineEdit, QDoubleSpinBox, QDateEdit, QTextEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QLabel
from PyQt5.QtCore import QDate, QSettings
from database import ExpenseRepository
from auth.session import UserSession
from i18n.translator import translate
from views.centered_dialog import CenteredDialog
from currency import currency

class AddEditExpenseDialog(CenteredDialog):
    def __init__(self, parent=None, expense=None, company_name=None):
        super().__init__(parent=parent)
        self.expense = expense
        self.predefined_company = company_name
        self.setWindowTitle(translate('add') if not expense else translate('edit'))
        self.resize(550, 600)
        self.settings = QSettings("Hawaa", "Accounting")
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20,20,20,20)
        
        form = QFormLayout()
        
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
        self.amount_spin.setRange(0.01, 999999999)
        self.amount_spin.setDecimals(2)
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
            if last_currency in currencies:
                self.currency_combo.setCurrentText(last_currency)
            else:
                self.currency_combo.setCurrentText(currency.get_display_currency())
        amount_layout.addWidget(self.currency_combo)
        form.addRow(translate('amount')+":", amount_layout)
        
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
        if expense:
            self.date_edit.setDate(QDate.fromString(expense['date'], "yyyy-MM-dd"))
        form.addRow(translate('date')+":", self.date_edit)
        
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
        self.currency_combo.currentTextChanged.connect(self.update_labels)
        if expense:
            self.amount_spin.setValue(expense.get('amount_original', expense['amount']))
        self.update_labels()
    
    def update_labels(self):
        amount = self.amount_spin.value()
        curr = self.currency_combo.currentText()
        rate = currency.get_rate_to_usd(curr)
        usd_value = amount / rate if rate != 0 else 0
        self.conversion_label.setText(f"≈ {usd_value:.2f} USD (حسب سعر الصرف الحالي)")
        self.rate_label.setText(f"سعر الصرف الحالي: 1 USD = {rate:.4f} {curr}")
    
    def save(self):
        if self.predefined_company:
            company = self.predefined_company
        else:
            company = self.company_edit.text().strip()
            if not company:
                QMessageBox.warning(self, translate('error'), translate('company_name')+" "+translate('error'))
                return
        
        amount = self.amount_spin.value()
        if amount <= 0:
            QMessageBox.warning(self, translate('error'), translate('amount')+" "+translate('error'))
            return
        type_val = 'incoming' if self.type_combo.currentIndex() == 0 else 'outgoing'
        date = self.date_edit.date().toString("yyyy-MM-dd")
        notes = self.notes_edit.toPlainText().strip()
        currency_code = self.currency_combo.currentText()
        
        self.settings.setValue("last_used_currency", currency_code)
        
        user = UserSession.get_current()
        user_id = user['id'] if user else None
        repo = ExpenseRepository()
        try:
            if self.expense:
                repo.update(self.expense['id'], company, amount, type_val, date, notes, currency_code, user_id)
            else:
                repo.add(company, amount, type_val, date, notes, currency_code, user_id)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, translate('error'), f"فشل حفظ القيد: {str(e)}")
