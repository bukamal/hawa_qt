from PyQt5.QtWidgets import QFormLayout, QLineEdit, QDoubleSpinBox, QDateEdit, QTextEdit, QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QLabel
from PyQt5.QtCore import QDate, QSettings, Qt
from database import ExpenseRepository
from auth.session import UserSession
from i18n.translator import translate
from views.centered_dialog import CenteredDialog
from currency import currency
from utils import apply_auto_select_to_widget

class AddEditExpenseDialog(CenteredDialog):
    def __init__(self, parent=None, expense=None, company_name=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LeftToRight)
        self.expense = expense
        self.predefined_company = company_name
        self.setWindowTitle(translate('add') if not expense else translate('edit'))
        self.resize(550, 520)
        self.settings = QSettings("Hawaa", "Accounting")
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20,20,20,20)
        
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        
        self.company_edit = QLineEdit()
        if self.predefined_company:
            self.company_edit.setText(self.predefined_company)
            self.company_edit.setEnabled(False)
            self.company_edit.setVisible(False)
        elif expense:
            self.company_edit.setText(expense['company_name'])
        form.addRow(translate('company_name')+":", self.company_edit)
        
        amount_layout = QHBoxLayout()
        amount_layout.setDirection(QHBoxLayout.LeftToRight)
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 999999999)
        self.amount_spin.setDecimals(2)
        amount_layout.addWidget(self.amount_spin)
        
        self.currency_combo = QComboBox()
        currencies = ["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"]
        self.currency_combo.addItems(currencies)
        
        if expense:
            if 'original_amount' in expense:
                self.amount_spin.setValue(expense['original_amount'])
            else:
                original_amount = currency.convert(expense['amount'], 'USD', expense['currency'])
                self.amount_spin.setValue(original_amount)
            self.currency_combo.setCurrentText(expense['currency'])
        else:
            last_currency = self.settings.value("last_used_currency", currency.get_display_currency())
            if last_currency in currencies:
                self.currency_combo.setCurrentText(last_currency)
            else:
                self.currency_combo.setCurrentText(currency.get_display_currency())
            self.amount_spin.setValue(0.0)
        
        amount_layout.addWidget(self.currency_combo)
        form.addRow(translate('amount')+":", amount_layout)
        
        self.conversion_label = QLabel()
        self.conversion_label.setStyleSheet("color: #64748b; font-size: 11px;")
        form.addRow("", self.conversion_label)
        
        self.rate_label = QLabel()
        self.rate_label.setStyleSheet("color: #10b981; font-size: 10px;")
        form.addRow("", self.rate_label)
        
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
        btns.setDirection(QHBoxLayout.LeftToRight)
        save_btn = QPushButton(translate('save'))
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton(translate('cancel'))
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        
        self.amount_spin.valueChanged.connect(self.update_labels)
        self.currency_combo.currentTextChanged.connect(self.update_labels)
        self.update_labels()
        
        # تطبيق التحديد التلقائي على جميع حقول الإدخال في هذا الحوار
        apply_auto_select_to_widget(self)
    
    def update_labels(self):
        amount = self.amount_spin.value()
        curr = self.currency_combo.currentText()
        display_curr = currency.get_display_currency()
        if curr != display_curr:
            converted = currency.convert(amount, curr, display_curr)
            self.conversion_label.setText(f"≈ {currency.format_amount(converted, display_curr)}")
        else:
            self.conversion_label.setText("")
        rate_to_usd = currency.get_rate_to_usd(curr)
        if curr == 'USD':
            self.rate_label.setText(f"سعر الصرف: 1 {curr} = 1 USD (العملة الأساسية)")
        else:
            usd_per_curr = 1.0 / rate_to_usd
            self.rate_label.setText(f"سعر الصرف: 1 {curr} = {usd_per_curr:.4f} USD | 1 USD = {rate_to_usd:.4f} {curr}")
    
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
        if self.expense:
            repo.update(self.expense['id'], company, amount, type_val, date, notes, currency_code, user_id)
        else:
            repo.add(company, amount, type_val, date, notes, currency_code, user_id)
        self.accept()
