from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSpinBox, QComboBox,
    QPushButton, QMessageBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QLineEdit, QFileDialog, QTabWidget, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer
from database import SettingsRepository
from currency import currency
from i18n.translator import translate, set_language
from theme_manager import ThemeManager
from auth.session import UserSession
from config import get_company_info, save_company_info
import os
import shutil
import datetime
import requests

class SettingsWidget(QWidget):
    rates_changed = pyqtSignal()
    backup_settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        self.repo = SettingsRepository()

        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.RightToLeft)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.North)

        self.tabs.addTab(self.create_currency_tab(), "💰 العملات")
        self.tabs.addTab(self.create_rates_tab(), "💱 أسعار الصرف")
        self.tabs.addTab(self.create_company_tab(), "🏢 الشركة")
        self.tabs.addTab(self.create_lang_theme_tab(), "🌐 اللغة والمظهر")
        self.tabs.addTab(self.create_network_tab(), "🌐 الشبكة")
        self.tabs.addTab(self.create_backup_tab(), "🔄 النسخ الاحتياطي والصيانة")

        layout.addWidget(self.tabs)
        self.load_rates_table()

    # ---------- تبويب العملات ----------
    def create_currency_tab(self):
        tab = QWidget()
        tab.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(tab)
        group = QGroupBox("إعدادات العملات")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.base_curr_combo = QComboBox()
        self.base_curr_combo.addItems(["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"])
        self.base_curr_combo.setCurrentText(currency.get_base_currency())
        form.addRow("العملة الأساسية (للتخزين):", self.base_curr_combo)

        self.display_curr_combo = QComboBox()
        self.display_curr_combo.addItems(["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"])
        self.display_curr_combo.setCurrentText(currency.get_display_currency())
        form.addRow("العملة المعروضة:", self.display_curr_combo)

        self.decimals_spin = QSpinBox()
        self.decimals_spin.setRange(0, 2)
        self.decimals_spin.setValue(int(self.repo.get('currency_decimals', '2')))
        form.addRow("الخانات العشرية:", self.decimals_spin)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["غربية", "شرقية"])
        current = self.repo.get('number_format', 'western')
        self.format_combo.setCurrentIndex(0 if current == 'western' else 1)
        form.addRow("تنسيق الأرقام:", self.format_combo)

        self.abbreviate_check = QCheckBox("اختصار الأعداد الكبيرة (K, M)")
        self.abbreviate_check.setChecked(currency.abbreviate_numbers())
        form.addRow(self.abbreviate_check)

        save_currency = QPushButton("حفظ إعدادات العملة")
        save_currency.clicked.connect(self.save_currency_settings)
        form.addRow(save_currency)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        return tab

    # ---------- تبويب أسعار الصرف ----------
    def create_rates_tab(self):
        tab = QWidget()
        tab.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(tab)
        group = QGroupBox("أسعار الصرف (1 دولار = ?)")
        inner = QVBoxLayout()
        self.rates_table = QTableWidget()
        self.rates_table.setColumnCount(3)
        self.rates_table.setHorizontalHeaderLabels(["العملة", "السعر", "آخر تحديث"])
        self.rates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        inner.addWidget(self.rates_table)

        refresh_btn = QPushButton("تحديث الأسعار من الإنترنت")
        refresh_btn.clicked.connect(self.fetch_online_rates)
        inner.addWidget(refresh_btn)

        group.setLayout(inner)
        layout.addWidget(group)
        layout.addStretch()
        return tab

    # ---------- تبويب معلومات الشركة ----------
    def create_company_tab(self):
        tab = QWidget()
        tab.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(tab)
        group = QGroupBox("معلومات الشركة للطباعة")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        info = get_company_info()
        self.company_name_edit = QLineEdit(info.get('name', ''))
        form.addRow("اسم الشركة:", self.company_name_edit)

        self.company_address_edit = QLineEdit(info.get('address', ''))
        form.addRow("العنوان:", self.company_address_edit)

        self.company_phone_edit = QLineEdit(info.get('phone', ''))
        form.addRow("الهاتف:", self.company_phone_edit)

        self.company_email_edit = QLineEdit(info.get('email', ''))
        form.addRow("البريد الإلكتروني:", self.company_email_edit)

        self.company_logo_path_edit = QLineEdit(info.get('logo_path', ''))
        logo_btn = QPushButton("اختيار شعار")
        logo_btn.clicked.connect(self.browse_logo)
        form.addRow("شعار الشركة:", self.company_logo_path_edit)
        form.addRow("", logo_btn)

        save_company_btn = QPushButton("حفظ معلومات الشركة")
        save_company_btn.clicked.connect(self.save_company_info)
        form.addRow(save_company_btn)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()
        return tab

    # ---------- تبويب اللغة والمظهر ----------
    def create_lang_theme_tab(self):
        tab = QWidget()
        tab.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(tab)

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

        layout.addWidget(lang_group)
        layout.addWidget(theme_group)
        layout.addStretch()
        return tab

    # ---------- تبويب الشبكة ----------
    def create_network_tab(self):
        tab = QWidget()
        tab.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(tab)
        group = QGroupBox("إعدادات الشبكة")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.is_server_check = QCheckBox("تشغيل هذا الجهاز كخادم قاعدة بيانات مركزي")
        self.is_server_check.toggled.connect(self.on_server_toggled)
        form.addRow(self.is_server_check)

        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("http://192.168.1.100:8000")
        form.addRow("عنوان الخادم البعيد:", self.server_url_edit)

        # زر اختبار الاتصال
        self.test_btn = QPushButton("🔍 اختبار الاتصال")
        self.test_btn.clicked.connect(self.test_connection)
        form.addRow(self.test_btn)

        save_btn = QPushButton("حفظ الإعدادات")
        save_btn.clicked.connect(self.save_network_settings)
        form.addRow(save_btn)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

        settings = QSettings("Hawaa", "Accounting")
        is_server = settings.value("network/is_server", False, type=bool)
        self.is_server_check.setChecked(is_server)
        self.server_url_edit.setText(settings.value("network/server_url", "http://localhost:8000"))
        self.on_server_toggled(is_server)
        return tab

    def on_server_toggled(self, checked):
        self.server_url_edit.setEnabled(not checked)

    def test_connection(self):
        """اختبار الاتصال بالخادم البعيد"""
        url = self.server_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال عنوان الخادم")
            return
        # إضافة http:// إذا لم تكن موجودة
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        try:
            resp = requests.get(f"{url}/health", timeout=3)
            if resp.status_code == 200 and resp.json().get("status") == "alive":
                QMessageBox.information(self, "✅ نجاح", f"تم الاتصال بالخادم بنجاح\nالعنوان: {url}")
            else:
                QMessageBox.warning(self, "❌ فشل", f"الخادم لا يستجيب بشكل صحيح\nالعنوان: {url}\nالاستجابة: {resp.text[:100]}")
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "خطأ في الاتصال", f"لا يمكن الوصول إلى الخادم:\n{url}\n\nتأكد من:\n- أن الخادم قيد التشغيل\n- أن الجهازين على نفس الشبكة\n- أن جدار الحماية يسمح بالاتصال")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ: {str(e)}")

    def save_network_settings(self):
        settings = QSettings("Hawaa", "Accounting")
        settings.setValue("network/is_server", self.is_server_check.isChecked())
        settings.setValue("network/server_url", self.server_url_edit.text())
        QMessageBox.information(self, "نجاح", "سيتم تطبيق الإعدادات بعد إعادة تشغيل التطبيق")

    # ---------- تبويب النسخ الاحتياطي والصيانة ----------
    def create_backup_tab(self):
        tab = QWidget()
        tab.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(tab)

        periodic_group = QGroupBox("النسخ الاحتياطي الدوري")
        periodic_layout = QFormLayout()
        periodic_layout.setLabelAlignment(Qt.AlignRight)

        self.backup_enabled = QCheckBox("تفعيل النسخ الاحتياطي التلقائي")
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 720)
        self.backup_interval.setSuffix(" ساعة")
        self.backup_interval.setValue(6)
        self.backup_folder = QLineEdit()
        self.backup_folder.setPlaceholderText("مجلد حفظ النسخ الاحتياطية")

        browse_btn = QPushButton("استعراض")
        browse_btn.clicked.connect(lambda: self._select_backup_folder(self.backup_folder))

        periodic_layout.addRow(self.backup_enabled)
        periodic_layout.addRow("كل:", self.backup_interval)
        periodic_layout.addRow("مجلد الوجهة:", self.backup_folder)
        periodic_layout.addRow("", browse_btn)

        save_periodic_btn = QPushButton("حفظ إعدادات النسخ الاحتياطي")
        save_periodic_btn.clicked.connect(self.save_backup_settings)
        periodic_layout.addRow(save_periodic_btn)

        periodic_group.setLayout(periodic_layout)
        layout.addWidget(periodic_group)

        instant_group = QGroupBox("نسخ احتياطي فوري")
        instant_layout = QHBoxLayout()
        backup_now_btn = QPushButton("📀 إنشاء نسخة احتياطية الآن")
        backup_now_btn.clicked.connect(self.create_backup_now)
        instant_layout.addWidget(backup_now_btn)
        instant_group.setLayout(instant_layout)
        layout.addWidget(instant_group)

        manage_group = QGroupBox("إدارة قاعدة البيانات")
        manage_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("📤 تصدير قاعدة البيانات")
        self.export_btn.clicked.connect(self.export_database)
        self.import_btn = QPushButton("📥 استيراد قاعدة البيانات")
        self.import_btn.clicked.connect(self.import_database)
        self.reset_btn = QPushButton("⚠️ إعادة تهيئة قاعدة البيانات")
        self.reset_btn.setStyleSheet("background-color: #dc3545; color: white;")
        self.reset_btn.clicked.connect(self.reset_database)

        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.reset_btn)
        manage_layout.addLayout(btn_layout)
        manage_group.setLayout(manage_layout)
        layout.addWidget(manage_group)

        license_group = QGroupBox("الترخيص")
        license_layout = QVBoxLayout()
        self.license_status_label = QLabel("جاري التحقق...")
        license_layout.addWidget(self.license_status_label)
        reactivate_btn = QPushButton("🔄 إعادة التفعيل")
        reactivate_btn.clicked.connect(self.reactivate_license)
        license_layout.addWidget(reactivate_btn)
        license_group.setLayout(license_layout)
        layout.addWidget(license_group)

        layout.addStretch()

        self.load_backup_settings()
        self.update_license_status()
        return tab

    # ---------- دوال النسخ الاحتياطي ----------
    def _is_remote_client(self):
        from database.connection import DatabaseConnection
        db = DatabaseConnection()
        return db._use_http()

    def _select_backup_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد النسخ الاحتياطي")
        if folder:
            line_edit.setText(folder)

    def save_backup_settings(self):
        settings = QSettings("Hawaa", "Accounting")
        settings.setValue("backup/enabled", self.backup_enabled.isChecked())
        settings.setValue("backup/interval_hours", self.backup_interval.value())
        settings.setValue("backup/folder", self.backup_folder.text())
        QMessageBox.information(self, "نجاح", "تم حفظ إعدادات النسخ الاحتياطي")
        self.backup_settings_changed.emit()

    def load_backup_settings(self):
        settings = QSettings("Hawaa", "Accounting")
        self.backup_enabled.setChecked(settings.value("backup/enabled", False, type=bool))
        self.backup_interval.setValue(settings.value("backup/interval_hours", 6, type=int))
        self.backup_folder.setText(settings.value("backup/folder", ""))

    def create_backup_now(self):
        from database.connection import DB_PATH
        folder = self.backup_folder.text().strip()
        if not folder:
            QMessageBox.warning(self, "خطأ", "يرجى تحديد مجلد النسخ الاحتياطي أولاً")
            return
        if not os.path.exists(folder):
            os.makedirs(folder)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"hawaa_backup_{timestamp}.db"
        backup_path = os.path.join(folder, backup_name)
        try:
            shutil.copy2(DB_PATH, backup_path)
            QMessageBox.information(self, "نجاح", f"تم إنشاء النسخة الاحتياطية:\n{backup_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل النسخ الاحتياطي: {str(e)}")

    def export_database(self):
        if self._is_remote_client():
            QMessageBox.warning(self, "تنبيه", "أنت متصل بخادم بعيد (وضع عميل).\nعملية التصدير تؤثر فقط على قاعدة البيانات المحلية (إن وجدت).\nلتصدير قاعدة بيانات الخادم، يُرجى تنفيذ هذه العملية على جهاز الخادم.")
        from database.connection import DB_PATH
        filename, _ = QFileDialog.getSaveFileName(self, "تصدير قاعدة البيانات", "hawaa_data_backup.db", "SQLite (*.db)")
        if filename:
            try:
                if os.path.exists(DB_PATH):
                    shutil.copy2(DB_PATH, filename)
                    QMessageBox.information(self, "نجاح", f"تم التصدير إلى:\n{filename}")
                else:
                    QMessageBox.warning(self, "تنبيه", "لا توجد قاعدة بيانات محلية للتصدير (أنت في وضع عميل).")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل التصدير: {str(e)}")

    def import_database(self):
        if self._is_remote_client():
            QMessageBox.warning(self, "تنبيه", "أنت متصل بخادم بعيد (وضع عميل).\nعملية الاستيراد ستؤثر فقط على قاعدة البيانات المحلية (إن وجدت).\nلتغيير قاعدة بيانات الخادم، يُرجى تنفيذ هذه العملية على جهاز الخادم.")
        from database.connection import DB_PATH
        filename, _ = QFileDialog.getOpenFileName(self, "استيراد قاعدة البيانات", "", "SQLite (*.db)")
        if filename:
            reply = QMessageBox.question(self, "تأكيد", "سيتم استبدال قاعدة البيانات المحلية الحالية. تأكيد؟",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    shutil.copy2(filename, DB_PATH)
                    QMessageBox.information(self, "نجاح", "تم الاستيراد. يرجى إعادة تشغيل التطبيق.")
                except Exception as e:
                    QMessageBox.critical(self, "خطأ", f"فشل الاستيراد: {str(e)}")

    def reset_database(self):
        if self._is_remote_client():
            QMessageBox.warning(self, "عملية غير مسموحة", "لا يمكن إعادة تهيئة قاعدة البيانات من جهاز عميل.\nيُرجى تنفيذ هذه العملية مباشرة على جهاز الخادم.")
            return
        from database.connection import DB_PATH
        reply = QMessageBox.question(self, "تأكيد خطير", "سيتم حذف كل البيانات وإعادة تهيئة قاعدة البيانات المحلية.\nلا يمكن التراجع. متابعة؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                from database.migrations import init_database
                init_database()
                QMessageBox.information(self, "نجاح", "تم إعادة تهيئة قاعدة البيانات المحلية. يرجى إعادة تشغيل التطبيق.")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل إعادة التهيئة: {str(e)}")

    def update_license_status(self):
        from auth.activation import check_activation
        valid, msg = check_activation()
        if valid:
            self.license_status_label.setText("✅ الترخيص ساري")
            self.license_status_label.setStyleSheet("color: green;")
        else:
            self.license_status_label.setText(f"❌ الترخيص غير صالح: {msg}")
            self.license_status_label.setStyleSheet("color: red;")

    def reactivate_license(self):
        from views.activation_dialog import ActivationDialog
        dlg = ActivationDialog(self)
        if dlg.exec() == ActivationDialog.Accepted:
            self.update_license_status()
            QMessageBox.information(self, "نجاح", "تم التفعيل بنجاح")

    # ---------- الدوال المساعدة الأخرى ----------
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
            clean_rate_text = rate_text.replace(',', '').replace(' ', '').strip()
            try:
                rate = float(clean_rate_text)
                currency.update_rate(code, rate)
            except ValueError:
                QMessageBox.warning(self, "خطأ", f"سعر غير صالح للعملة {code}: {rate_text}")
                return

        QMessageBox.information(self, translate('success'), "تم حفظ إعدادات العملة وأسعار الصرف")
        main_window = self.window()
        if hasattr(main_window, 'apply_theme_to_pages'):
            main_window.apply_theme_to_pages()
        if hasattr(main_window, 'pages') and 'dashboard' in main_window.pages:
            main_window.pages['dashboard'].refresh()
        if hasattr(main_window, 'pages') and 'accounts' in main_window.pages:
            main_window.pages['accounts'].refresh_table()
        self.rates_changed.emit()

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
                        new_rate = rates[code]
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
