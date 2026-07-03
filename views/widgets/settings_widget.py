# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QSpinBox, QComboBox,
    QPushButton, QMessageBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QLineEdit, QFileDialog, QTabWidget, QLabel, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings, QTimer
from database import SettingsRepository
from currency import currency
from i18n.translator import translate, set_language
from theme_manager import ThemeManager
from auth.session import UserSession
from config import get_company_info, save_company_info
from auth.activation import check_network_activation, activate_network
import os
import shutil
import datetime
import requests
import socket
import subprocess
import sys
import time

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
        self.server_process = None
        self.status_timer = None

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

    def create_currency_tab(self):
        tab = QWidget()
        tab.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(tab)
        group = QGroupBox("إعدادات العملات")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.base_curr_combo = QComboBox()
        self.base_curr_combo.addItems(["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"])
        self.base_curr_combo.setCurrentText("USD")
        self.base_curr_combo.setEnabled(False)
        self.base_curr_combo.setToolTip("ثابتة محاسبياً: كل الأرصدة تحفظ بالدولار، أما العملة المعروضة فهي للعرض فقط")
        form.addRow("العملة المحاسبية الأساسية:", self.base_curr_combo)

        base_note = QLabel("العملة الأساسية مثبتة على USD لحماية السعر التاريخي. تغيير عملة العرض لا يعيد تسعير القيود القديمة.")
        base_note.setWordWrap(True)
        base_note.setStyleSheet("color: #92400e; background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px; padding: 8px;")
        form.addRow("", base_note)

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

        history_label = QLabel("آخر تعديلات أسعار الصرف — تستخدم للرجوع والتدقيق، أما القيود القديمة فتحتفظ بسعرها داخل القيد نفسه.")
        history_label.setWordWrap(True)
        history_label.setStyleSheet("color: #475569; margin-top: 8px;")
        inner.addWidget(history_label)

        self.rate_history_table = QTableWidget()
        self.rate_history_table.setColumnCount(4)
        self.rate_history_table.setHorizontalHeaderLabels(["العملة", "السعر", "التاريخ الفعّال", "المصدر"])
        self.rate_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rate_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        inner.addWidget(self.rate_history_table)

        refresh_btn = QPushButton("تحديث الأسعار من الإنترنت")
        refresh_btn.clicked.connect(self.fetch_online_rates)
        inner.addWidget(refresh_btn)

        group.setLayout(inner)
        layout.addWidget(group)
        layout.addStretch()
        return tab

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

    def create_network_tab(self):
        tab = QWidget()
        tab.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(tab)
        group = QGroupBox("إعدادات الشبكة")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        # عرض IP المحلي
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = "غير متوفر"
        ip_label = QLabel(f"عنوان هذا الجهاز: {local_ip}")
        ip_label.setStyleSheet("color: #64748b; font-size: 12px;")
        form.addRow(ip_label)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["محلي (بدون شبكة)", "عميل (اتصال بخادم)", "خادم (تشغيل خدمة)"])
        qsettings = QSettings("Hawaa", "Accounting")
        current_mode = qsettings.value("network/mode", "local")
        mode_idx = {'local': 0, 'client': 1, 'server': 2}
        self.mode_combo.setCurrentIndex(mode_idx.get(current_mode, 0))
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        form.addRow("وضع التشغيل:", self.mode_combo)

        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("http://192.168.1.100:8000")
        server_url = qsettings.value("network/server_url", "http://localhost:8000")
        self.server_url_edit.setText(server_url)
        form.addRow("عنوان الخادم البعيد:", self.server_url_edit)

        # التحقق من تفعيل الشبكة
        network_ok, network_msg = check_network_activation()
        if not network_ok:
            self.mode_combo.setItemText(1, "عميل (غير متاح - قم بالتفعيل)")
            self.mode_combo.setItemText(2, "خادم (غير متاح - قم بالتفعيل)")
            self.mode_combo.setCurrentIndex(0)
            self.mode_combo.setEnabled(False)
            warning_label = QLabel(f"⚠️ {network_msg}. يرجى تفعيل ميزة الشبكة.")
            warning_label.setStyleSheet("color: orange; font-weight: bold; margin: 5px;")
            form.addRow(warning_label)

            # زر تفعيل الشبكة (سيتم فتح حوار مخصص)
            activate_btn = QPushButton("🔓 تفعيل الشبكة")
            activate_btn.clicked.connect(self._activate_network_dialog)
            form.addRow(activate_btn)

        self.connection_test_label = QLabel("")
        self.connection_test_label.setStyleSheet("font-size: 10px;")
        form.addRow(self.connection_test_label)
        self.server_url_edit.textChanged.connect(self.auto_test_connection)

        self.test_btn = QPushButton("🔍 اختبار الاتصال")
        self.test_btn.clicked.connect(self.test_connection)
        form.addRow(self.test_btn)

        # مجموعة التحكم بالخادم (تظهر فقط في وضع الخادم)
        self.server_control_group = QGroupBox("التحكم بالخادم المحلي")
        control_layout = QVBoxLayout()
        self.server_status_label = QLabel("الحالة: غير معروف")
        self.server_status_label.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(self.server_status_label)

        btn_layout = QHBoxLayout()
        self.start_server_btn = QPushButton("▶️ تشغيل الخادم")
        self.start_server_btn.clicked.connect(self.start_server_process)
        self.stop_server_btn = QPushButton("⏹️ إيقاف الخادم")
        self.stop_server_btn.clicked.connect(self.stop_server_process)
        btn_layout.addWidget(self.start_server_btn)
        btn_layout.addWidget(self.stop_server_btn)
        control_layout.addLayout(btn_layout)
        self.server_control_group.setLayout(control_layout)
        form.addRow(self.server_control_group)
        self.server_control_group.setVisible(False)

        save_btn = QPushButton("حفظ الإعدادات")
        save_btn.clicked.connect(self.save_network_settings)
        form.addRow(save_btn)

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

        self.on_mode_changed()
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_server_status)
        self.status_timer.start(3000)
        return tab

    def _activate_network_dialog(self):
        """حوار مخصص لتفعيل الشبكة مع إخفاء المفتاح"""
        dialog = QDialog(self)
        dialog.setWindowTitle("تفعيل الشبكة")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.resize(400, 200)
        layout = QVBoxLayout(dialog)
        
        desc = QLabel("أدخل مفتاح تفعيل ميزة الشبكة")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        key_edit = QLineEdit()
        key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        key_edit.setEchoMode(QLineEdit.Password)  # إخفاء المفتاح
        layout.addWidget(key_edit)
        
        status_label = QLabel()
        status_label.setStyleSheet("color: red; font-size: 12px;")
        status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(status_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(lambda: self._perform_network_activation(key_edit.text().strip(), status_label, dialog))
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()

    def _perform_network_activation(self, key, status_label, dialog):
        if not key:
            status_label.setText("يرجى إدخال مفتاح التفعيل")
            return
        success, msg = activate_network(key)
        if success:
            QMessageBox.information(self, "نجاح", "تم تفعيل الشبكة بنجاح. يرجى إعادة تشغيل التطبيق.")
            # تحديث تبويب الشبكة
            index = self.tabs.currentIndex()
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, self.create_network_tab(), "🌐 الشبكة")
            self.tabs.setCurrentIndex(index)
            dialog.accept()
        else:
            status_label.setText(f"فشل التفعيل: {msg}")

    def on_mode_changed(self):
        is_client = self.mode_combo.currentIndex() == 1
        is_server = self.mode_combo.currentIndex() == 2
        self.server_url_edit.setEnabled(is_client)
        self.test_btn.setEnabled(is_client)
        self.server_control_group.setVisible(is_server)
        if is_server:
            self.update_server_status()
        else:
            self.server_status_label.setText("الحالة: غير متاح (ليس في وضع خادم)")

    def start_server_process(self):
        if self.server_process and self.server_process.poll() is None:
            QMessageBox.information(self, "تنبيه", "الخادم يعمل بالفعل.")
            return
        try:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                cmd = [exe_path, '--server']
            else:
                cmd = [sys.executable, 'run_server.py']
            if sys.platform == 'win32':
                self.server_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                self.server_process = subprocess.Popen(cmd)
            self.update_server_status()
            QMessageBox.information(self, "نجاح", "تم تشغيل الخادم بنجاح.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تشغيل الخادم: {str(e)}")

    def stop_server_process(self):
        if not self.server_process or self.server_process.poll() is not None:
            self.server_process = None
            self.update_server_status()
            QMessageBox.information(self, "تنبيه", "الخادم غير قيد التشغيل.")
            return
        try:
            self.server_process.terminate()
            import time
            time.sleep(1)
            if self.server_process.poll() is None:
                self.server_process.kill()
            self.server_process = None
            self.update_server_status()
            QMessageBox.information(self, "نجاح", "تم إيقاف الخادم.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل إيقاف الخادم: {str(e)}")

    def update_server_status(self):
        if self.mode_combo.currentIndex() != 2:
            return
        running = False
        if self.server_process and self.server_process.poll() is None:
            running = True
        else:
            try:
                resp = requests.get("http://localhost:8000/health", timeout=1)
                if resp.status_code == 200 and resp.json().get("status") == "alive":
                    running = True
            except:
                pass
        if running:
            self.server_status_label.setText("الحالة: ✅ يعمل")
            self.server_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.server_status_label.setText("الحالة: ❌ لا يعمل")
            self.server_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.server_process = None

    def auto_test_connection(self):
        if self.mode_combo.currentIndex() != 1:
            self.connection_test_label.setText("")
            return
        url = self.server_url_edit.text().strip()
        if not url:
            self.connection_test_label.setText("")
            return
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        try:
            resp = requests.get(f"{url}/health", timeout=2)
            if resp.status_code == 200 and resp.json().get("status") == "alive":
                self.connection_test_label.setText("✅ متصل")
                self.connection_test_label.setStyleSheet("color: green; font-size: 10px;")
            else:
                self.connection_test_label.setText("❌ غير متصل (استجابة غير صالحة)")
                self.connection_test_label.setStyleSheet("color: red; font-size: 10px;")
        except Exception as e:
            self.connection_test_label.setText(f"❌ خطأ: {str(e)[:30]}")
            self.connection_test_label.setStyleSheet("color: red; font-size: 10px;")

    def test_connection(self):
        url = self.server_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال عنوان الخادم")
            return
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        try:
            resp = requests.get(f"{url}/health", timeout=3)
            if resp.status_code == 200 and resp.json().get("status") == "alive":
                QMessageBox.information(self, "✅ نجاح", f"تم الاتصال بالخادم بنجاح\nالعنوان: {url}")
            else:
                QMessageBox.warning(self, "❌ فشل", f"الخادم لا يستجيب بشكل صحيح\nالعنوان: {url}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"لا يمكن الاتصال بالخادم:\n{url}\n\n{str(e)}")

    def save_network_settings(self):
        mode_map = {0: 'local', 1: 'client', 2: 'server'}
        mode = mode_map[self.mode_combo.currentIndex()]
        qsettings = QSettings("Hawaa", "Accounting")
        qsettings.setValue("network/mode", mode)
        qsettings.setValue("network/server_url", self.server_url_edit.text())
        if mode == 'server':
            try:
                resp = requests.get("http://localhost:8000/health", timeout=1)
                if resp.status_code != 200:
                    QMessageBox.information(self, "تنبيه", "الخادم المحلي ليس قيد التشغيل حالياً. استخدم زر 'تشغيل الخادم' لتشغيله.")
            except:
                QMessageBox.information(self, "تنبيه", "الخادم المحلي ليس قيد التشغيل حالياً. استخدم زر 'تشغيل الخادم' لتشغيله.")
        QMessageBox.information(self, "نجاح", "سيتم تطبيق الإعدادات بعد إعادة تشغيل التطبيق")

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
        browse_btn.clicked.connect(self._browse_backup_folder)
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

        from database.connection import DatabaseConnection
        if DatabaseConnection().is_remote():
            self._disable_backup_controls(periodic_group)
            self._disable_backup_controls(instant_group)
            self._disable_backup_controls(manage_group)

        self.load_backup_settings()
        self.update_license_status()
        return tab

    def _browse_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد النسخ الاحتياطي")
        if folder:
            self.backup_folder.setText(folder)

    def _disable_backup_controls(self, container):
        for child in container.findChildren(QPushButton):
            child.setEnabled(False)
        for child in container.findChildren(QCheckBox):
            child.setEnabled(False)
        for child in container.findChildren(QSpinBox):
            child.setEnabled(False)
        for child in container.findChildren(QLineEdit):
            child.setEnabled(False)
        if not hasattr(self, '_backup_warning_label'):
            label = QLabel("⚠️ أنت متصل بخادم بعيد. يتم إجراء النسخ الاحتياطي مركزيًا على الخادم.")
            label.setStyleSheet("color: orange; font-weight: bold; margin: 10px;")
            label.setWordWrap(True)
            container.parentWidget().layout().insertWidget(0, label)
            self._backup_warning_label = label

    def save_backup_settings(self):
        from database.connection import DatabaseConnection
        if DatabaseConnection().is_remote():
            QMessageBox.warning(self, "تنبيه", "لا يمكن حفظ إعدادات النسخ الاحتياطي في وضع العميل.")
            return
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
        from database.connection import DatabaseConnection
        if DatabaseConnection().is_remote():
            QMessageBox.warning(self, "تنبيه", "لا يمكن إنشاء نسخة احتياطية من جهاز عميل.")
            return
        from database.connection import DB_PATH
        from services.backup_service import backup_service
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
            backup_service.create_backup(DB_PATH, backup_path)
            QMessageBox.information(self, "نجاح", f"تم إنشاء النسخة الاحتياطية بعد فحص السلامة:\n{backup_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل النسخ الاحتياطي: {str(e)}")

    def export_database(self):
        from database.connection import DatabaseConnection
        if DatabaseConnection().is_remote():
            QMessageBox.warning(self, "تنبيه", "لا يمكن تصدير قاعدة البيانات في وضع العميل.")
            return
        from database.connection import DB_PATH
        from services.backup_service import backup_service
        filename, _ = QFileDialog.getSaveFileName(self, "تصدير قاعدة البيانات", "hawaa_data_backup.db", "SQLite (*.db)")
        if filename:
            try:
                if os.path.exists(DB_PATH):
                    backup_service.create_backup(DB_PATH, filename)
                    QMessageBox.information(self, "نجاح", f"تم التصدير بعد فحص السلامة إلى:\n{filename}")
                else:
                    QMessageBox.warning(self, "تنبيه", "لا توجد قاعدة بيانات محلية للتصدير")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل التصدير: {str(e)}")

    def import_database(self):
        from database.connection import DatabaseConnection
        if DatabaseConnection().is_remote():
            QMessageBox.warning(self, "تنبيه", "لا يمكن استيراد قاعدة البيانات في وضع العميل.")
            return
        from database.connection import DB_PATH
        from services.backup_service import backup_service
        filename, _ = QFileDialog.getOpenFileName(self, "استيراد قاعدة البيانات", "", "SQLite (*.db)")
        if filename:
            reply = QMessageBox.question(self, "تأكيد", 
                "سيتم استبدال قاعدة البيانات المحلية الحالية.\n"
                "إذا كان خادم Flask يعمل، سيتم إيقافه مؤقتاً ثم إعادة تشغيله.\n"
                "تأكيد الاستيراد؟",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                was_running = self._stop_backend_server(show_message=False)
                try:
                    db_conn = DatabaseConnection()
                    db_conn.close()
                    time.sleep(0.5)
                    backup_service.restore_backup(filename, DB_PATH)
                    QMessageBox.information(self, "نجاح", "تم الاستيراد بعد فحص سلامة النسخة.")
                except Exception as e:
                    QMessageBox.critical(self, "خطأ", f"فشل الاستيراد: {str(e)}")
                    if was_running:
                        self._start_backend_server()
                    return
                if was_running:
                    self._start_backend_server()
                self.load_rates_table()
                self.repo.clear_cache()
                QMessageBox.information(self, "تنبيه", "يرجى إعادة تشغيل التطبيق لتحديث جميع المكونات.")

    def reset_database(self):
        from database.connection import DatabaseConnection
        if DatabaseConnection().is_remote():
            QMessageBox.warning(self, "تنبيه", "لا يمكن إعادة تهيئة قاعدة البيانات في وضع العميل.")
            return
        from database.connection import DB_PATH
        reply = QMessageBox.question(self, "تأكيد خطير", 
            "سيتم حذف كل البيانات وإعادة تهيئة قاعدة البيانات المحلية.\n"
            "إذا كان خادم Flask يعمل، سيتم إيقافه مؤقتاً ثم إعادة تشغيله.\n"
            "لا يمكن التراجع. متابعة؟",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            was_running = self._stop_backend_server(show_message=False)
            try:
                db_conn = DatabaseConnection()
                db_conn.close()
                time.sleep(0.5)
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                from database.migrations import init_database
                init_database()
                QMessageBox.information(self, "نجاح", "تم إعادة تهيئة قاعدة البيانات المحلية.")
            except PermissionError as e:
                QMessageBox.critical(self, "خطأ", f"لا يمكن حذف الملف لأنه مستخدم من عملية أخرى.\n{str(e)}\nيرجى إغلاق أي تطبيق آخر يصل إلى قاعدة البيانات (مثل خادم Flask) ثم حاول مجدداً.")
                if was_running:
                    self._start_backend_server()
                return
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل إعادة التهيئة: {str(e)}")
                if was_running:
                    self._start_backend_server()
                return
            if was_running:
                self._start_backend_server()
            self.load_rates_table()
            self.repo.clear_cache()
            QMessageBox.information(self, "تنبيه", "يرجى إعادة تشغيل التطبيق لتحديث جميع المكونات.")

    def _is_backend_server_running(self):
        if self.server_process and self.server_process.poll() is None:
            return True
        try:
            resp = requests.get("http://localhost:8000/health", timeout=1)
            return resp.status_code == 200 and resp.json().get("status") == "alive"
        except:
            return False

    def _stop_backend_server(self, show_message=True):
        if self.server_process and self.server_process.poll() is None:
            try:
                self.server_process.terminate()
                time.sleep(1)
                if self.server_process.poll() is None:
                    self.server_process.kill()
                self.server_process = None
                if show_message:
                    QMessageBox.information(self, "إيقاف الخادم", "تم إيقاف خادم Flask الخلفي مؤقتاً.")
                return True
            except Exception as e:
                if show_message:
                    QMessageBox.warning(self, "تحذير", f"فشل إيقاف الخادم: {str(e)}")
                return False
        return False

    def _start_backend_server(self, show_message=True):
        from database.connection import DatabaseConnection
        db = DatabaseConnection()
        if db.mode != "server":
            return
        if self._is_backend_server_running():
            return
        try:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                cmd = [exe_path, '--server']
            else:
                cmd = [sys.executable, 'run_server.py']
            if sys.platform == 'win32':
                self.server_process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                self.server_process = subprocess.Popen(cmd)
            time.sleep(2)
            if show_message:
                QMessageBox.information(self, "تشغيل الخادم", "تم إعادة تشغيل خادم Flask الخلفي.")
        except Exception as e:
            if show_message:
                QMessageBox.critical(self, "خطأ", f"فشل تشغيل الخادم: {str(e)}")

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

    def load_rates_table(self):
        rates = currency.get_all_currencies()
        self.rates_table.setRowCount(len(rates))
        for row, r in enumerate(rates):
            self.rates_table.setItem(row, 0, QTableWidgetItem(r['currency_code']))
            rate_item = QTableWidgetItem(f"{float(r['rate_to_usd']):.4f}")
            rate_item.setFlags(rate_item.flags() | Qt.ItemIsEditable)
            self.rates_table.setItem(row, 1, rate_item)
            self.rates_table.setItem(row, 2, QTableWidgetItem(r['updated_at'][:19] if r['updated_at'] else ''))
        self.load_rate_history_table()

    def load_rate_history_table(self):
        if not hasattr(self, 'rate_history_table'):
            return
        try:
            history = currency.get_exchange_rate_history(limit=30)
        except Exception:
            history = []
        self.rate_history_table.setRowCount(len(history))
        for row, item in enumerate(history):
            self.rate_history_table.setItem(row, 0, QTableWidgetItem(str(item.get('currency_code', ''))))
            self.rate_history_table.setItem(row, 1, QTableWidgetItem(f"{float(item.get('rate_to_usd', 0)):.4f}"))
            self.rate_history_table.setItem(row, 2, QTableWidgetItem(str(item.get('effective_date', ''))))
            self.rate_history_table.setItem(row, 3, QTableWidgetItem(str(item.get('source', ''))))

    def save_currency_settings(self):
        base_curr = "USD"
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

        self.repo.clear_cache()
        self.load_rates_table()
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
        self.repo.clear_cache()
        set_language(new_lang)
        QMessageBox.information(self, translate('success'), "سيتم تطبيق اللغة بعد إعادة التشغيل")

    def save_theme(self):
        theme = 'light' if self.theme_combo.currentIndex() == 0 else 'dark'
        self.repo.set('theme', theme)
        self.repo.clear_cache()
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
        self.repo.clear_cache()
        QMessageBox.information(self, "نجاح", "تم حفظ معلومات الشركة")
