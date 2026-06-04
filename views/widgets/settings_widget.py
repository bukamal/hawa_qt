from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QSpinBox, QComboBox, QPushButton, QMessageBox, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QLineEdit, QFileDialog, QTabWidget
from PyQt5.QtCore import Qt
from database import SettingsRepository
from currency import currency
from i18n.translator import translate, set_language
from theme_manager import ThemeManager
from auth.session import UserSession
from config import get_company_info, save_company_info

class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        self.repo = SettingsRepository()

        # إنشاء التبويبات
        tabs = QTabWidget()
        tabs.setLayoutDirection(Qt.RightToLeft)
        tabs.setDocumentMode(True)
        tabs.setTabPosition(QTabWidget.North)

        # تبويب العملات
        currency_tab = QWidget()
        currency_tab.setLayoutDirection(Qt.RightToLeft)
        currency_layout = QVBoxLayout(currency_tab)
        currency_layout.setSpacing(20)
        currency_layout.setContentsMargins(15, 15, 15, 15)

        currency_group = QGroupBox("إعدادات العملات")
        currency_form = QFormLayout()
        currency_form.setLabelAlignment(Qt.AlignRight)
        currency_form.setSpacing(12)
        self.base_curr_combo = QComboBox()
        self.base_curr_combo.addItems(["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"])
        self.base_curr_combo.setCurrentText(currency.get_base_currency())
        currency_form.addRow("العملة الأساسية (للتخزين):", self.base_curr_combo)
        self.display_curr_combo = QComboBox()
        self.display_curr_combo.addItems(["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"])
        self.display_curr_combo.setCurrentText(currency.get_display_currency())
        currency_form.addRow("العملة المعروضة:", self.display_curr_combo)
        self.decimals_spin = QSpinBox()
        self.decimals_spin.setRange(0, 2)
        self.decimals_spin.setValue(int(self.repo.get('currency_decimals', '2')))
        currency_form.addRow("الخانات العشرية:", self.decimals_spin)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["غربية", "شرقية"])
        current = self.repo.get('number_format', 'western')
        self.format_combo.setCurrentIndex(0 if current == 'western' else 1)
        currency_form.addRow("تنسيق الأرقام:", self.format_combo)
        self.abbreviate_check = QCheckBox("اختصار الأعداد الكبيرة (K, M)")
        self.abbreviate_check.setChecked(currency.abbreviate_numbers())
        currency_form.addRow(self.abbreviate_check)
        save_currency = QPushButton("حفظ إعدادات العملة")
        save_currency.clicked.connect(self.save_currency_settings)
        currency_form.addRow(save_currency)
        currency_group.setLayout(currency_form)
        currency_layout.addWidget(currency_group)
        currency_layout.addStretch()
        tabs.addTab(currency_tab, "💰 العملات")

        # تبويب أسعار الصرف
        rates_tab = QWidget()
        rates_tab.setLayoutDirection(Qt.RightToLeft)
        rates_layout = QVBoxLayout(rates_tab)
        rates_layout.setSpacing(15)
        rates_layout.setContentsMargins(15, 15, 15, 15)

        rates_group = QGroupBox("أسعار الصرف (1 دولار = ?)")
        rates_inner_layout = QVBoxLayout()
        self.rates_table = QTableWidget()
        self.rates_table.setLayoutDirection(Qt.RightToLeft)
        self.rates_table.setColumnCount(3)
        self.rates_table.setHorizontalHeaderLabels(["العملة", "السعر", "آخر تحديث"])
        self.rates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rates_inner_layout.addWidget(self.rates_table)
        refresh_rates_btn = QPushButton("تحديث الأسعار من الإنترنت")
        refresh_rates_btn.clicked.connect(self.fetch_online_rates)
        rates_inner_layout.addWidget(refresh_rates_btn)
        rates_group.setLayout(rates_inner_layout)
        rates_layout.addWidget(rates_group)
        rates_layout.addStretch()
        tabs.addTab(rates_tab, "💱 أسعار الصرف")

        # تبويب معلومات الشركة
        company_tab = QWidget()
        company_tab.setLayoutDirection(Qt.RightToLeft)
        company_layout = QVBoxLayout(company_tab)
        company_layout.setSpacing(15)
        company_layout.setContentsMargins(15, 15, 15, 15)

        company_group = QGroupBox("معلومات الشركة للطباعة")
        company_form = QFormLayout()
        company_form.setLabelAlignment(Qt.AlignRight)
        company_form.setSpacing(12)
        info = get_company_info()
        self.company_name_edit = QLineEdit(info.get('name', ''))
        company_form.addRow("اسم الشركة:", self.company_name_edit)
        self.company_address_edit = QLineEdit(info.get('address', ''))
        company_form.addRow("العنوان:", self.company_address_edit)
        self.company_phone_edit = QLineEdit(info.get('phone', ''))
        company_form.addRow("الهاتف:", self.company_phone_edit)
        self.company_email_edit = QLineEdit(info.get('email', ''))
        company_form.addRow("البريد الإلكتروني:", self.company_email_edit)
        self.company_logo_path_edit = QLineEdit(info.get('logo_path', ''))
        logo_btn = QPushButton("اختيار شعار")
        logo_btn.clicked.connect(self.browse_logo)
        company_form.addRow("شعار الشركة:", self.company_logo_path_edit)
        company_form.addRow("", logo_btn)
        save_company_btn = QPushButton("حفظ معلومات الشركة")
        save_company_btn.clicked.connect(self.save_company_info)
        company_form.addRow(save_company_btn)
        company_group.setLayout(company_form)
        company_layout.addWidget(company_group)
        company_layout.addStretch()
        tabs.addTab(company_tab, "🏢 الشركة")

        # تبويب اللغة والمظهر
        lang_theme_tab = QWidget()
        lang_theme_tab.setLayoutDirection(Qt.RightToLeft)
        lang_theme_layout = QVBoxLayout(lang_theme_tab)
        lang_theme_layout.setSpacing(20)
        lang_theme_layout.setContentsMargins(15, 15, 15, 15)

        lang_group = QGroupBox("اللغة")
        lang_form = QFormLayout()
        lang_form.setLabelAlignment(Qt.AlignRight)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["العربية", "English", "Français"])
        cur_lang = self.repo.get('language', 'ar')
        idx_map = {'ar': 0, 'en': 1, 'fr': 2}
        self.lang_combo.setCurrentIndex(idx_map.get(cur_lang, 0))
        lang_form.addRow("اختر اللغة:", self.lang_combo)
        save_lang = QPushButton("تغيير اللغة")
        save_lang.clicked.connect(self.save_language)
        lang_form.addRow(save_lang)
        lang_group.setLayout(lang_form)

        theme_group = QGroupBox("المظهر")
        theme_form = QFormLayout()
        theme_form.setLabelAlignment(Qt.AlignRight)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["فاتح", "داكن"])
        cur_theme = self.repo.get('theme', 'light')
        self.theme_combo.setCurrentIndex(0 if cur_theme == 'light' else 1)
        theme_form.addRow("الثيم:", self.theme_combo)
        save_theme = QPushButton("تطبيق الثيم")
        save_theme.clicked.connect(self.save_theme)
        theme_form.addRow(save_theme)
        theme_group.setLayout(theme_form)

        lang_theme_layout.addWidget(lang_group)
        lang_theme_layout.addWidget(theme_group)
        lang_theme_layout.addStretch()
        tabs.addTab(lang_theme_tab, "🌐 اللغة والمظهر")

        layout.addWidget(tabs)
        self.load_rates_table()

    def load_rates_table(self):
        rates = currency.get_all_currencies()
        self.rates_table.setRowCount(len(rates))
        for row, r in enumerate(rates):
            self.rates_table.setItem(row, 0, QTableWidgetItem(r['currency_code']))
            rate_item = QTableWidgetItem(f"{r['rate_to_usd']:.4f}")
            rate_item.setFlags(rate_item.flags() | Qt.ItemIsEditable)
            self.rates_table.setItem(row, 1, rate_item)
            self.rates_table.setItem(row, 2, QTableWidgetItem(r['updated_at'][:19] if r['updated_at'] else ''))

    def save_currency_settings(self):
        base_curr = self.base_curr_combo.currentText()
        display_curr = self.display_curr_combo.currentText()
        decimals = self.decimals_spin.value()
        fmt = 'western' if self.format_combo.currentIndex() == 0 else 'arabic'
        abbrev = 'true' if self.abbreviate_check.isChecked() else 'false'

        self.repo.set('base_currency', base_curr)
        self.repo.set('display_currency', display_curr)
        self.repo.set('currency_decimals', str(decimals))
        self.repo.set('number_format', fmt)
        self.repo.set('abbreviate_numbers', abbrev)

        for row in range(self.rates_table.rowCount()):
            code = self.rates_table.item(row, 0).text()
            rate_text = self.rates_table.item(row, 1).text()
            try:
                rate = float(rate_text)
                currency.update_rate(code, rate)
            except:
                pass

        QMessageBox.information(self, translate('success'), "تم حفظ إعدادات العملة وأسعار الصرف")
        main_window = self.window()
        if hasattr(main_window, 'apply_theme_to_pages'):
            main_window.apply_theme_to_pages()
        if hasattr(main_window, 'pages') and 'dashboard' in main_window.pages:
            main_window.pages['dashboard'].refresh()
        if hasattr(main_window, 'pages') and 'accounts' in main_window.pages:
            main_window.pages['accounts'].refresh_table()

    def fetch_online_rates(self):
        import requests
        try:
            response = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
            if response.status_code == 200:
                data = response.json()
                rates = data.get('rates', {})
                for row in range(self.rates_table.rowCount()):
                    code = self.rates_table.item(row, 0).text()
                    if code in rates:
                        new_rate = 1.0 / rates[code]
                        self.rates_table.item(row, 1).setText(f"{new_rate:.4f}")
                QMessageBox.information(self, "نجاح", "تم تحديث الأسعار من الإنترنت")
            else:
                QMessageBox.warning(self, "خطأ", "فشل الاتصال بالخادم")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"حدث خطأ: {str(e)}")

    def save_language(self):
        lang_map = {0: 'ar', 1: 'en', 2: 'fr'}
        new_lang = lang_map[self.lang_combo.currentIndex()]
        self.repo.set('language', new_lang)
        set_language(new_lang)
        QMessageBox.information(self, translate('success'), "سيتم تطبيق اللغة بعد إعادة التشغيل")

    def save_theme(self):
        theme = 'light' if self.theme_combo.currentIndex() == 0 else 'dark'
        self.repo.set('theme', theme)
        main_window = self.window()
        if hasattr(main_window, 'apply_theme'):
            main_window.apply_theme(theme)
        QMessageBox.information(self, translate('success'), "تم تغيير الثيم")

    def browse_logo(self):
        filename, _ = QFileDialog.getOpenFileName(self, "اختر شعار الشركة", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if filename:
            self.company_logo_path_edit.setText(filename)

    def save_company_info(self):
        info = {
            'name': self.company_name_edit.text(),
            'address': self.company_address_edit.text(),
            'phone': self.company_phone_edit.text(),
            'email': self.company_email_edit.text(),
            'logo_path': self.company_logo_path_edit.text(),
        }
        save_company_info(info)
        QMessageBox.information(self, "نجاح", "تم حفظ معلومات الشركة")
