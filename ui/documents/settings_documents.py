# -*- coding: utf-8 -*-
from __future__ import annotations

import requests

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QLineEdit, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QSlider,
    QPlainTextEdit, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap

from i18n.translator import set_language
from services.settings_service import settings_service, SUPPORTED_CURRENCIES, BASE_CURRENCY, NETWORK_MODES
from services.server_service import server_service
from services.audio_service import audio_service
from services.mobile_pairing_service import mobile_pairing_service


class _SettingsBaseDocument(QWidget):
    def __init__(self, shell=None, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.setLayoutDirection(Qt.RightToLeft)

    def _root(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        return layout

    def _title(self, layout, title: str, hint: str = None):
        label = QLabel(title)
        label.setObjectName('DocumentTitle')
        layout.addWidget(label)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setWordWrap(True)
            hint_label.setObjectName('DocumentHint')
            layout.addWidget(hint_label)

    def _show_error(self, exc):
        audio_service.play_error()
        QMessageBox.critical(self, 'خطأ', str(exc))

    def _show_info(self, message, sound_id='success'):
        audio_service.play(sound_id or 'success')
        QMessageBox.information(self, 'نجاح', message)


class CurrencySettingsDocument(_SettingsBaseDocument):
    rates_changed = pyqtSignal()

    def __init__(self, shell=None, parent=None):
        super().__init__(shell, parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = self._root()
        self._title(
            layout,
            'إعدادات العملات',
            'العملة المحاسبية الأساسية ثابتة على USD. عملة العرض تغيّر طريقة العرض فقط ولا تعيد تسعير القيود القديمة.'
        )

        group = QGroupBox('عملة العرض والتنسيق')
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)

        self.base_combo = QComboBox()
        self.base_combo.addItems(SUPPORTED_CURRENCIES)
        self.base_combo.setCurrentText(BASE_CURRENCY)
        self.base_combo.setEnabled(False)
        form.addRow('العملة الأساسية:', self.base_combo)

        self.display_combo = QComboBox()
        self.display_combo.addItems(SUPPORTED_CURRENCIES)
        form.addRow('العملة المعروضة:', self.display_combo)

        self.decimals_spin = QSpinBox()
        self.decimals_spin.setRange(0, 2)
        form.addRow('الخانات العشرية:', self.decimals_spin)

        self.format_combo = QComboBox()
        self.format_combo.addItem('غربية', 'western')
        self.format_combo.addItem('شرقية', 'arabic')
        form.addRow('تنسيق الأرقام:', self.format_combo)

        self.abbreviate_check = QCheckBox('اختصار الأعداد الكبيرة K / M')
        form.addRow(self.abbreviate_check)
        layout.addWidget(group)

        rates_group = QGroupBox('أسعار الصرف الحالية — 1 USD = ?')
        rates_layout = QVBoxLayout(rates_group)
        self.rates_table = QTableWidget()
        self.rates_table.setColumnCount(3)
        self.rates_table.setHorizontalHeaderLabels(['العملة', 'السعر', 'آخر تحديث'])
        self.rates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rates_layout.addWidget(self.rates_table)

        buttons = QHBoxLayout()
        save_btn = QPushButton('💾 حفظ إعدادات العملات والأسعار')
        save_btn.clicked.connect(self.save)
        online_btn = QPushButton('🌐 تحديث الأسعار من الإنترنت')
        online_btn.clicked.connect(self.fetch_online_rates)
        buttons.addWidget(save_btn)
        buttons.addWidget(online_btn)
        buttons.addStretch(1)
        rates_layout.addLayout(buttons)
        layout.addWidget(rates_group, 1)

        history_group = QGroupBox('آخر تعديلات أسعار الصرف')
        history_layout = QVBoxLayout(history_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(['العملة', 'السعر', 'التاريخ الفعّال', 'المصدر'])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        history_layout.addWidget(self.history_table)
        layout.addWidget(history_group, 1)

    def activate(self, **_params):
        self.load()

    def load(self):
        settings = settings_service.get_currency_settings()
        self.display_combo.setCurrentText(settings['display_currency'])
        self.decimals_spin.setValue(settings['decimals'])
        fmt_idx = self.format_combo.findData(settings['number_format'])
        self.format_combo.setCurrentIndex(max(fmt_idx, 0))
        self.abbreviate_check.setChecked(bool(settings['abbreviate_numbers']))
        self.load_rates()
        self.load_history()

    def load_rates(self):
        rates = settings_service.list_exchange_rates()
        self.rates_table.setRowCount(len(rates))
        for row, item in enumerate(rates):
            self.rates_table.setItem(row, 0, QTableWidgetItem(str(item.get('currency_code', ''))))
            rate_item = QTableWidgetItem(f"{float(item.get('rate_to_usd', 1)):.4f}")
            rate_item.setFlags(rate_item.flags() | Qt.ItemIsEditable)
            self.rates_table.setItem(row, 1, rate_item)
            self.rates_table.setItem(row, 2, QTableWidgetItem(str(item.get('updated_at') or '')[:19]))

    def load_history(self):
        history = settings_service.list_exchange_rate_history(limit=30)
        self.history_table.setRowCount(len(history))
        for row, item in enumerate(history):
            self.history_table.setItem(row, 0, QTableWidgetItem(str(item.get('currency_code', ''))))
            self.history_table.setItem(row, 1, QTableWidgetItem(f"{float(item.get('rate_to_usd', 1)):.4f}"))
            self.history_table.setItem(row, 2, QTableWidgetItem(str(item.get('effective_date', ''))))
            self.history_table.setItem(row, 3, QTableWidgetItem(str(item.get('source', ''))))

    def _table_rates(self):
        rates = []
        for row in range(self.rates_table.rowCount()):
            code_item = self.rates_table.item(row, 0)
            rate_item = self.rates_table.item(row, 1)
            if code_item and rate_item:
                rates.append((code_item.text(), rate_item.text()))
        return rates

    def save(self):
        try:
            result = settings_service.save_currency_settings(
                display_currency=self.display_combo.currentText(),
                decimals=self.decimals_spin.value(),
                number_format=self.format_combo.currentData(),
                abbreviate_numbers=self.abbreviate_check.isChecked(),
                rates=self._table_rates(),
            )
            self.load_history()
            self.rates_changed.emit()
            self._show_info('تم حفظ العملات والأسعار. ' + result['note'])
        except Exception as exc:
            self._show_error(exc)

    def fetch_online_rates(self):
        try:
            response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=10)
            response.raise_for_status()
            new_rates = settings_service.fetch_online_rates(response.json())
            for row in range(self.rates_table.rowCount()):
                code = self.rates_table.item(row, 0).text()
                if code in new_rates:
                    self.rates_table.item(row, 1).setText(f"{new_rates[code]:.4f}")
            self._show_info('تم جلب الأسعار. راجعها ثم اضغط حفظ لتثبيت التاريخ الجديد.')
        except Exception as exc:
            self._show_error(exc)


class BackupSettingsDocument(_SettingsBaseDocument):
    backup_settings_changed = pyqtSignal()

    def __init__(self, shell=None, parent=None):
        super().__init__(shell, parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = self._root()
        self._title(
            layout,
            'النسخ الاحتياطي والصيانة',
            'النسخ اليدوي يستخدم SQLite Backup API حتى تكون النسخة آمنة مع WAL. لا يتم نسخ ملف db وحده.'
        )

        self.warning_label = QLabel('')
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet('color: #92400e; background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px; padding: 8px;')
        layout.addWidget(self.warning_label)

        periodic = QGroupBox('النسخ الاحتياطي الدوري')
        form = QFormLayout(periodic)
        form.setLabelAlignment(Qt.AlignRight)
        self.enabled_check = QCheckBox('تفعيل النسخ الاحتياطي التلقائي')
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 720)
        self.interval_spin.setSuffix(' ساعة')
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText('مجلد حفظ النسخ الاحتياطية')
        browse_btn = QPushButton('استعراض')
        browse_btn.clicked.connect(self.browse_folder)
        save_btn = QPushButton('💾 حفظ إعدادات النسخ')
        save_btn.clicked.connect(self.save)
        form.addRow(self.enabled_check)
        form.addRow('كل:', self.interval_spin)
        form.addRow('مجلد الوجهة:', self.folder_edit)
        form.addRow('', browse_btn)
        form.addRow('', save_btn)
        layout.addWidget(periodic)

        actions = QGroupBox('عمليات قاعدة البيانات')
        action_layout = QHBoxLayout(actions)
        backup_btn = QPushButton('📀 إنشاء نسخة الآن')
        backup_btn.clicked.connect(self.create_backup_now)
        export_btn = QPushButton('📤 تصدير قاعدة البيانات')
        export_btn.clicked.connect(self.export_database)
        import_btn = QPushButton('📥 استيراد نسخة')
        import_btn.clicked.connect(self.import_database)
        action_layout.addWidget(backup_btn)
        action_layout.addWidget(export_btn)
        action_layout.addWidget(import_btn)
        action_layout.addStretch(1)
        layout.addWidget(actions)
        layout.addStretch(1)

    def activate(self, **_params):
        self.load()

    def load(self):
        settings = settings_service.get_backup_settings()
        self.enabled_check.setChecked(settings['enabled'])
        self.interval_spin.setValue(settings['interval_hours'])
        self.folder_edit.setText(settings['folder'])
        remote = settings['remote']
        self.warning_label.setVisible(remote)
        self.warning_label.setText('⚠️ أنت في وضع العميل. النسخ الاحتياطي يجب أن يتم من جهاز الخادم وليس من العميل.' if remote else '')

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'اختر مجلد النسخ الاحتياطي')
        if folder:
            self.folder_edit.setText(folder)

    def save(self):
        try:
            settings_service.save_backup_settings(self.enabled_check.isChecked(), self.interval_spin.value(), self.folder_edit.text())
            self.backup_settings_changed.emit()
            self._show_info('تم حفظ إعدادات النسخ الاحتياطي')
        except Exception as exc:
            self._show_error(exc)

    def create_backup_now(self):
        try:
            path = settings_service.create_backup_now(self.folder_edit.text())
            self._show_info(f'تم إنشاء النسخة بعد فحص السلامة:\n{path}', sound_id='backup_done')
        except Exception as exc:
            self._show_error(exc)

    def export_database(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'تصدير قاعدة البيانات', 'hawaa_data_backup.db', 'SQLite (*.db)')
        if not filename:
            return
        try:
            path = settings_service.export_database(filename)
            self._show_info(f'تم التصدير بعد فحص السلامة:\n{path}', sound_id='backup_done')
        except Exception as exc:
            self._show_error(exc)

    def import_database(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'استيراد قاعدة البيانات', '', 'SQLite (*.db)')
        if not filename:
            return
        reply = QMessageBox.question(
            self,
            'تأكيد الاستيراد',
            'سيتم استبدال قاعدة البيانات المحلية الحالية بعد فحص النسخة. يفضّل إغلاق الخادم قبل المتابعة. متابعة؟',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            settings_service.import_database(filename)
            self._show_info('تم الاستيراد بعد فحص سلامة النسخة. أعد تشغيل التطبيق لتحديث كل المكونات.')
        except Exception as exc:
            self._show_error(exc)


class NetworkSettingsDocument(_SettingsBaseDocument):
    def __init__(self, shell=None, parent=None):
        super().__init__(shell, parent)
        self.status_timer = None
        self._setup_ui()

    def _setup_ui(self):
        layout = self._root()
        self._title(layout, 'إعدادات الشبكة', 'تغيير وضع الشبكة يتطلب غالبًا إعادة تشغيل التطبيق حتى يعاد إنشاء اتصال قاعدة البيانات.')

        group = QGroupBox('وضع التشغيل والاتصال')
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem('محلي بدون شبكة', 'local')
        self.mode_combo.addItem('عميل يتصل بخادم', 'client')
        self.mode_combo.addItem('خادم محلي', 'server')
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText('http://192.168.1.100:8000')
        self.connection_label = QLabel('')
        test_btn = QPushButton('🔍 اختبار الاتصال')
        test_btn.clicked.connect(self.test_connection)
        save_btn = QPushButton('💾 حفظ إعدادات الشبكة')
        save_btn.clicked.connect(self.save)
        form.addRow('وضع التشغيل:', self.mode_combo)
        form.addRow('عنوان الخادم:', self.server_url_edit)
        form.addRow('', test_btn)
        form.addRow('', self.connection_label)
        form.addRow('', save_btn)
        layout.addWidget(group)

        server_group = QGroupBox('التحكم بالخادم المحلي')
        server_layout = QVBoxLayout(server_group)
        self.server_status_label = QLabel('الحالة: غير معروف')
        server_layout.addWidget(self.server_status_label)
        server_buttons = QHBoxLayout()
        start_btn = QPushButton('▶️ تشغيل الخادم')
        start_btn.clicked.connect(self.start_server)
        stop_btn = QPushButton('⏹️ إيقاف الخادم')
        stop_btn.clicked.connect(self.stop_server)
        server_buttons.addWidget(start_btn)
        server_buttons.addWidget(stop_btn)
        server_buttons.addStretch(1)
        server_layout.addLayout(server_buttons)
        self.server_group = server_group
        layout.addWidget(server_group)

        pairing_group = QGroupBox('ربط تطبيق Android عبر QR')
        pairing_layout = QVBoxLayout(pairing_group)
        self.pairing_hint = QLabel(
            'شغّل الخادم، ثم أنشئ رمز ربط مؤقت. امسح الكود من تطبيق Android أو الصق نص QR هناك. '
            'الرمز لا يسجل الدخول ولا يحتوي كلمة مرور، وينتهي خلال دقائق.'
        )
        self.pairing_hint.setWordWrap(True)
        pairing_layout.addWidget(self.pairing_hint)
        self.pairing_url_label = QLabel('عنوان الربط: —')
        self.pairing_expiry_label = QLabel('ينتهي: —')
        pairing_layout.addWidget(self.pairing_url_label)
        pairing_layout.addWidget(self.pairing_expiry_label)
        self.qr_image_label = QLabel('أنشئ رمز ربط لعرض QR')
        self.qr_image_label.setAlignment(Qt.AlignCenter)
        self.qr_image_label.setMinimumHeight(180)
        self.qr_image_label.setStyleSheet('background: #ffffff; border: 1px solid #d8e2e0; border-radius: 12px; padding: 8px;')
        pairing_layout.addWidget(self.qr_image_label)
        self.qr_text_box = QPlainTextEdit()
        self.qr_text_box.setReadOnly(True)
        self.qr_text_box.setMaximumHeight(96)
        self.qr_text_box.setPlaceholderText('سيظهر هنا نص QR لاستخدامه كخطة بديلة إذا لم يتوفر مسح الكاميرا.')
        pairing_layout.addWidget(self.qr_text_box)
        pairing_buttons = QHBoxLayout()
        generate_pair_btn = QPushButton('📱 إنشاء QR لربط الهاتف')
        generate_pair_btn.clicked.connect(self.generate_mobile_pairing_qr)
        copy_qr_btn = QPushButton('📋 نسخ نص QR')
        copy_qr_btn.clicked.connect(self.copy_pairing_qr_text)
        copy_url_btn = QPushButton('🔗 نسخ عنوان الخادم')
        copy_url_btn.clicked.connect(self.copy_pairing_server_url)
        pairing_buttons.addWidget(generate_pair_btn)
        pairing_buttons.addWidget(copy_qr_btn)
        pairing_buttons.addWidget(copy_url_btn)
        pairing_buttons.addStretch(1)
        pairing_layout.addLayout(pairing_buttons)
        self.pairing_group = pairing_group
        layout.addWidget(pairing_group)

        net_license = QGroupBox('تفعيل ميزة الشبكة')
        license_form = QFormLayout(net_license)
        self.network_status_label = QLabel('')
        self.network_key_edit = QLineEdit()
        self.network_key_edit.setEchoMode(QLineEdit.Password)
        self.network_key_edit.setPlaceholderText('XXXX-XXXX-XXXX-XXXX')
        activate_btn = QPushButton('🔐 تفعيل الشبكة')
        activate_btn.clicked.connect(self.activate_network)
        license_form.addRow('الحالة:', self.network_status_label)
        license_form.addRow('مفتاح الشبكة:', self.network_key_edit)
        license_form.addRow('', activate_btn)
        layout.addWidget(net_license)
        layout.addStretch(1)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_server_status)
        self.status_timer.start(3000)

    def activate(self, **_params):
        self.load()

    def load(self):
        settings = settings_service.get_network_settings()
        idx = self.mode_combo.findData(settings['mode'])
        self.mode_combo.setCurrentIndex(max(idx, 0))
        self.server_url_edit.setText(settings['server_url'])
        self._on_mode_changed()
        self.update_network_license_status()
        self.update_server_status()

    def _on_mode_changed(self):
        mode = self.mode_combo.currentData()
        self.server_url_edit.setEnabled(mode == 'client')
        self.server_group.setVisible(mode == 'server')

    def save(self):
        try:
            settings_service.save_network_settings(self.mode_combo.currentData(), self.server_url_edit.text())
            self._show_info('تم حفظ إعدادات الشبكة. أعد تشغيل التطبيق لتطبيق الوضع الجديد.')
        except Exception as exc:
            self._show_error(exc)

    def test_connection(self):
        url = self.server_url_edit.text().strip() or 'http://localhost:8000'
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'http://' + url
        result = server_service.health(url, timeout=3)
        if result['alive']:
            self.connection_label.setText('✅ متصل بالخادم')
            self.connection_label.setStyleSheet('color: green;')
        else:
            self.connection_label.setText('❌ ' + result['message'][:120])
            self.connection_label.setStyleSheet('color: red;')

    def update_server_status(self):
        if self.mode_combo.currentData() != 'server':
            return
        running = server_service.is_process_running() or server_service.health('http://localhost:8000', timeout=1)['alive']
        self.server_status_label.setText('الحالة: ✅ يعمل' if running else 'الحالة: ❌ لا يعمل')
        self.server_status_label.setStyleSheet('color: green; font-weight: bold;' if running else 'color: red; font-weight: bold;')

    def start_server(self):
        try:
            result = server_service.start()
            self.update_server_status()
            self._show_info(result['message'], sound_id='server_on')
        except Exception as exc:
            self._show_error(exc)

    def stop_server(self):
        try:
            result = server_service.stop()
            self.update_server_status()
            self._show_info(result['message'], sound_id='server_off')
        except Exception as exc:
            self._show_error(exc)

    def _pairing_server_url(self):
        # For QR pairing the phone must use a LAN IP, not localhost.
        return mobile_pairing_service.default_server_url(port=8000)

    def generate_mobile_pairing_qr(self):
        try:
            server_url = self._pairing_server_url()
            result = mobile_pairing_service.create_pairing_payload(server_url=server_url, ttl_minutes=5)
            self.pairing_url_label.setText('عنوان الربط: ' + result['server_url'])
            self.pairing_expiry_label.setText('ينتهي: ' + result['expires_at'])
            self.qr_text_box.setPlainText(result['qr_text'])
            qr_path = mobile_pairing_service.qr_image_path(result['qr_text'])
            if qr_path:
                pixmap = QPixmap(qr_path)
                if not pixmap.isNull():
                    self.qr_image_label.setPixmap(pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    self.qr_image_label.setText('تعذر تحميل صورة QR. استخدم نص QR أدناه.')
            else:
                self.qr_image_label.setText('مكتبة qrcode غير متوفرة. استخدم نص QR أدناه.')
            audio_service.play('notify')
        except Exception as exc:
            self._show_error(exc)

    def copy_pairing_qr_text(self):
        text = self.qr_text_box.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self._show_info('تم نسخ نص QR. الصقه في تطبيق Android إذا لم تستخدم الكاميرا.', sound_id='notify')
        else:
            QMessageBox.information(self, 'لا يوجد QR', 'أنشئ رمز ربط أولًا.')

    def copy_pairing_server_url(self):
        url = self._pairing_server_url()
        QApplication.clipboard().setText(url)
        self._show_info('تم نسخ عنوان الخادم: ' + url, sound_id='notify')

    def update_network_license_status(self):
        status = settings_service.get_network_license_status()
        self.network_status_label.setText(('✅ ' if status['valid'] else '❌ ') + status['message'])
        self.network_status_label.setStyleSheet('color: green;' if status['valid'] else 'color: red;')

    def activate_network(self):
        try:
            result = settings_service.activate_network(self.network_key_edit.text())
            self.update_network_license_status()
            if result['valid']:
                self.network_key_edit.clear()
                self._show_info(result['message'])
            else:
                QMessageBox.warning(self, 'فشل التفعيل', result['message'])
        except Exception as exc:
            self._show_error(exc)


class CompanySettingsDocument(_SettingsBaseDocument):
    def __init__(self, shell=None, parent=None):
        super().__init__(shell, parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = self._root()
        self._title(layout, 'معلومات الشركة للطباعة', 'هذه البيانات تظهر في التقارير ومعاينات الطباعة.')
        form_group = QGroupBox('بيانات الشركة')
        form = QFormLayout(form_group)
        form.setLabelAlignment(Qt.AlignRight)
        self.name_edit = QLineEdit()
        self.address_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.tax_edit = QLineEdit()
        self.logo_edit = QLineEdit()
        browse_btn = QPushButton('اختيار شعار')
        browse_btn.clicked.connect(self.browse_logo)
        save_btn = QPushButton('💾 حفظ معلومات الشركة')
        save_btn.clicked.connect(self.save)
        form.addRow('اسم الشركة:', self.name_edit)
        form.addRow('العنوان:', self.address_edit)
        form.addRow('الهاتف:', self.phone_edit)
        form.addRow('البريد الإلكتروني:', self.email_edit)
        form.addRow('الرقم الضريبي:', self.tax_edit)
        form.addRow('الشعار:', self.logo_edit)
        form.addRow('', browse_btn)
        form.addRow('', save_btn)
        layout.addWidget(form_group)
        layout.addStretch(1)

    def activate(self, **_params):
        self.load()

    def load(self):
        info = settings_service.get_company_info()
        self.name_edit.setText(info.get('name', ''))
        self.address_edit.setText(info.get('address', ''))
        self.phone_edit.setText(info.get('phone', ''))
        self.email_edit.setText(info.get('email', ''))
        self.tax_edit.setText(info.get('tax_number', ''))
        self.logo_edit.setText(info.get('logo_path', ''))

    def browse_logo(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'اختر شعار الشركة', '', 'Images (*.png *.jpg *.jpeg *.bmp)')
        if filename:
            self.logo_edit.setText(filename)

    def save(self):
        try:
            settings_service.save_company_info({
                'name': self.name_edit.text(),
                'address': self.address_edit.text(),
                'phone': self.phone_edit.text(),
                'email': self.email_edit.text(),
                'tax_number': self.tax_edit.text(),
                'logo_path': self.logo_edit.text(),
            })
            self._show_info('تم حفظ معلومات الشركة')
        except Exception as exc:
            self._show_error(exc)


class AppearanceSettingsDocument(_SettingsBaseDocument):
    def __init__(self, shell=None, parent=None):
        super().__init__(shell, parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = self._root()
        self._title(layout, 'اللغة والمظهر', 'تغيير اللغة قد يحتاج إعادة تشغيل حتى يعاد تطبيق اتجاه RTL/LTR على كل الواجهة.')
        group = QGroupBox('اللغة والثيم')
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem('العربية', 'ar')
        self.lang_combo.addItem('English', 'en')
        self.lang_combo.addItem('Français', 'fr')
        self.theme_combo = QComboBox()
        self.theme_combo.addItem('فاتح', 'light')
        self.theme_combo.addItem('داكن', 'dark')
        save_lang_btn = QPushButton('💾 حفظ اللغة')
        save_lang_btn.clicked.connect(self.save_language)
        save_theme_btn = QPushButton('🎨 تطبيق الثيم')
        save_theme_btn.clicked.connect(self.save_theme)
        form.addRow('اللغة:', self.lang_combo)
        form.addRow('', save_lang_btn)
        form.addRow('الثيم:', self.theme_combo)
        form.addRow('', save_theme_btn)
        layout.addWidget(group)
        layout.addStretch(1)

    def activate(self, **_params):
        self.load()

    def load(self):
        settings = settings_service.get_appearance_settings()
        self.lang_combo.setCurrentIndex(max(self.lang_combo.findData(settings['language']), 0))
        self.theme_combo.setCurrentIndex(max(self.theme_combo.findData(settings['theme']), 0))

    def save_language(self):
        try:
            lang = settings_service.save_language(self.lang_combo.currentData())
            set_language(lang)
            self._show_info('تم حفظ اللغة. أعد تشغيل التطبيق لتطبيق الاتجاه والترجمات بالكامل.')
        except Exception as exc:
            self._show_error(exc)

    def save_theme(self):
        try:
            theme = settings_service.save_theme(self.theme_combo.currentData())
            main_window = self.window()
            if hasattr(main_window, 'apply_theme'):
                main_window.apply_theme(theme)
            self._show_info('تم تطبيق الثيم')
        except Exception as exc:
            self._show_error(exc)


class AudioSettingsDocument(_SettingsBaseDocument):
    def __init__(self, shell=None, parent=None):
        super().__init__(shell, parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = self._root()
        self._title(
            layout,
            'المؤثرات الصوتية',
            'أصوات قصيرة وهادئة للأحداث المهمة فقط: الحفظ، الخطأ، النسخ الاحتياطي، التصدير، الشبكة، والتنبيهات.'
        )

        group = QGroupBox('التحكم العام')
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        self.enabled_check = QCheckBox('تفعيل المؤثرات الصوتية')
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_label = QLabel('35%')
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(f'{v}%'))
        volume_row = QHBoxLayout()
        volume_row.addWidget(self.volume_slider, 1)
        volume_row.addWidget(self.volume_label)
        form.addRow(self.enabled_check)
        form.addRow('مستوى الصوت:', volume_row)
        layout.addWidget(group)

        events = QGroupBox('أنواع الأصوات المسموحة')
        event_form = QFormLayout(events)
        event_form.setLabelAlignment(Qt.AlignRight)
        self.success_check = QCheckBox('الحفظ والعمليات الناجحة')
        self.error_check = QCheckBox('الأخطاء وفشل التحقق')
        self.warning_check = QCheckBox('التحذيرات والحذف')
        self.notification_check = QCheckBox('التنبيهات والدفعات المستحقة')
        self.system_check = QCheckBox('النظام: النسخ، التصدير، الشبكة')
        self.security_check = QCheckBox('الدخول والأمان')
        event_form.addRow(self.success_check)
        event_form.addRow(self.error_check)
        event_form.addRow(self.warning_check)
        event_form.addRow(self.notification_check)
        event_form.addRow(self.system_check)
        event_form.addRow(self.security_check)
        layout.addWidget(events)

        test_group = QGroupBox('اختبار الصوت')
        test_layout = QHBoxLayout(test_group)
        self.sound_combo = QComboBox()
        for item in settings_service.list_audio_sounds():
            self.sound_combo.addItem(item['description'], item['sound_id'])
        test_btn = QPushButton('🔊 اختبار')
        test_btn.clicked.connect(self.test_sound)
        save_btn = QPushButton('💾 حفظ إعدادات الصوت')
        save_btn.clicked.connect(self.save)
        test_layout.addWidget(self.sound_combo, 1)
        test_layout.addWidget(test_btn)
        test_layout.addWidget(save_btn)
        layout.addWidget(test_group)

        hint = QLabel('ملاحظة: لا يتم تشغيل صوت عند كل نقرة أو تنقل عادي. الصوت مرتبط بالأحداث المهمة فقط حتى يبقى البرنامج مناسبًا لبيئة المكتب.')
        hint.setWordWrap(True)
        hint.setObjectName('DocumentHint')
        layout.addWidget(hint)
        layout.addStretch(1)

    def activate(self, **_params):
        self.load()

    def load(self):
        settings = settings_service.get_audio_settings()
        self.enabled_check.setChecked(settings['enabled'])
        self.volume_slider.setValue(settings['volume'])
        self.success_check.setChecked(settings['success_enabled'])
        self.error_check.setChecked(settings['error_enabled'])
        self.warning_check.setChecked(settings['warning_enabled'])
        self.notification_check.setChecked(settings['notification_enabled'])
        self.system_check.setChecked(settings['system_enabled'])
        self.security_check.setChecked(settings['security_enabled'])

    def _payload(self):
        return {
            'enabled': self.enabled_check.isChecked(),
            'volume': self.volume_slider.value(),
            'success_enabled': self.success_check.isChecked(),
            'error_enabled': self.error_check.isChecked(),
            'warning_enabled': self.warning_check.isChecked(),
            'notification_enabled': self.notification_check.isChecked(),
            'system_enabled': self.system_check.isChecked(),
            'security_enabled': self.security_check.isChecked(),
        }

    def save(self):
        try:
            settings_service.save_audio_settings(self._payload())
            self._show_info('تم حفظ إعدادات المؤثرات الصوتية')
        except Exception as exc:
            self._show_error(exc)

    def test_sound(self):
        try:
            # Persist the current controls first so volume/mute are respected after save,
            # but force=True still lets the user test even when sound is disabled.
            settings_service.save_audio_settings(self._payload())
            played = settings_service.test_audio_sound(self.sound_combo.currentData())
            if not played:
                self._show_info('تم تنفيذ طلب الاختبار، لكن قد لا يعمل الصوت في هذه البيئة أو لا توجد سماعات.')
        except Exception as exc:
            self._show_error(exc)


class LicenseSettingsDocument(_SettingsBaseDocument):
    def __init__(self, shell=None, parent=None):
        super().__init__(shell, parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = self._root()
        self._title(layout, 'الترخيص', 'يعرض حالة ترخيص البرنامج وترخيص ميزة الشبكة. فحص الانتهاء يتم من خدمة الترخيص.')
        self.license_label = QLabel('')
        self.network_label = QLabel('')
        self.license_label.setWordWrap(True)
        self.network_label.setWordWrap(True)
        refresh_btn = QPushButton('🔄 تحديث الحالة')
        refresh_btn.clicked.connect(self.load)
        reactivate_btn = QPushButton('🔐 إعادة تفعيل البرنامج')
        reactivate_btn.clicked.connect(self.reactivate_main_license)
        layout.addWidget(self.license_label)
        layout.addWidget(self.network_label)
        row = QHBoxLayout()
        row.addWidget(refresh_btn)
        row.addWidget(reactivate_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(1)

    def activate(self, **_params):
        self.load()

    def load(self):
        app_status = settings_service.get_license_status()
        net_status = settings_service.get_network_license_status()
        self.license_label.setText(('✅ ' if app_status['valid'] else '❌ ') + 'ترخيص البرنامج: ' + app_status['message'])
        self.network_label.setText(('✅ ' if net_status['valid'] else '❌ ') + 'ترخيص الشبكة: ' + net_status['message'])
        self.license_label.setStyleSheet('color: green;' if app_status['valid'] else 'color: red;')
        self.network_label.setStyleSheet('color: green;' if net_status['valid'] else 'color: red;')

    def reactivate_main_license(self):
        try:
            from views.activation_dialog import ActivationDialog
            dlg = ActivationDialog(self)
            if dlg.exec() == ActivationDialog.Accepted:
                self.load()
                self._show_info('تم التفعيل بنجاح')
        except Exception as exc:
            self._show_error(exc)
