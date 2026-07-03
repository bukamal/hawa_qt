# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QHBoxLayout,
    QApplication, QFrame, QTextEdit
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPixmap, QDesktopServices

from views.frameless_dialog import FramelessDialog
from auth.activation import activate, get_device_id, describe_license_state, get_license_file_paths
from theme_manager import ThemeManager
from branding import APP_DISPLAY_NAME_AR, APP_TAGLINE_AR, branding_path
from ui.auth.brand_panel import BrandHeader, BrandCard, StatusPill
from services.audio_service import audio_service


class ActivationDialog(FramelessDialog):
    """Branded activation screen with diagnostics and clear recovery actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تفعيل النظام")
        self.resize(680, 660)
        self.setMinimumSize(600, 600)
        self.setLayoutDirection(Qt.RightToLeft)

        try:
            icon = QPixmap(branding_path("app_icon_32.png"))
            if not icon.isNull():
                self.icon_label.setPixmap(icon.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass

        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(14)
        layout.setContentsMargins(34, 24, 34, 28)

        layout.addWidget(BrandHeader("تفعيل الترخيص وربط النظام بهذا الجهاز", logo_size=80))

        status_row = QHBoxLayout()
        self.program_status_pill = StatusPill("ترخيص البرنامج: جارٍ الفحص", "info")
        self.network_status_pill = StatusPill("ترخيص الشبكة: جارٍ الفحص", "info")
        status_row.addWidget(self.program_status_pill)
        status_row.addWidget(self.network_status_pill)
        layout.addLayout(status_row)

        card = BrandCard()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        title = QLabel("مفتاح الترخيص")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {ThemeManager.get('text_primary')};")
        card_layout.addWidget(title)

        desc = QLabel("أدخل مفتاح الترخيص ثم اضغط تفعيل. سيتم حفظ الترخيص في مجلد إعدادات ويندوز حتى لا يطلبه البرنامج عند كل تشغيل.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: 12px; color: {ThemeManager.get('text_secondary')};")
        card_layout.addWidget(desc)

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setMinimumHeight(44)
        self.key_edit.setStyleSheet(self._input_style())
        self.key_edit.returnPressed.connect(self._activate)
        card_layout.addWidget(self.key_edit)

        show_row = QHBoxLayout()
        self.show_key_btn = QPushButton("إظهار المفتاح")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.clicked.connect(self._toggle_key_visibility)
        show_row.addWidget(self.show_key_btn)
        show_row.addStretch()
        card_layout.addLayout(show_row)

        device_label = QLabel("معرّف الجهاز")
        device_label.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {ThemeManager.get('text_secondary')};")
        card_layout.addWidget(device_label)

        device_row = QHBoxLayout()
        self.device_edit = QLineEdit(get_device_id())
        self.device_edit.setReadOnly(True)
        self.device_edit.setStyleSheet(self._input_style())
        self.copy_device_btn = QPushButton("نسخ")
        self.copy_device_btn.clicked.connect(self._copy_device_id)
        device_row.addWidget(self.device_edit)
        device_row.addWidget(self.copy_device_btn)
        card_layout.addLayout(device_row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet(f"QProgressBar {{ border: none; background-color: {ThemeManager.get('border')}; border-radius: 4px; height: 7px; }} QProgressBar::chunk {{ background-color: {ThemeManager.get('primary')}; border-radius: 4px; }}")
        card_layout.addWidget(self.progress)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setVisible(False)
        card_layout.addWidget(self.status_label)

        diagnostics_title = QLabel("تشخيص الترخيص")
        diagnostics_title.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {ThemeManager.get('text_primary')};")
        card_layout.addWidget(diagnostics_title)

        self.diagnostics = QTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setFixedHeight(112)
        self.diagnostics.setStyleSheet(f"""
            QTextEdit {{
                background-color: {ThemeManager.get('bg_window')};
                color: {ThemeManager.get('text_secondary')};
                border: 1px solid {ThemeManager.get('border')};
                border-radius: 9px;
                padding: 8px;
                font-size: 11px;
            }}
        """)
        card_layout.addWidget(self.diagnostics)

        btn_layout = QHBoxLayout()
        self.activate_btn = QPushButton("🔐 تفعيل البرنامج")
        self.activate_btn.setObjectName("primary")
        self.activate_btn.setMinimumHeight(42)
        self.activate_btn.clicked.connect(self._activate)
        btn_layout.addWidget(self.activate_btn)

        refresh_btn = QPushButton("تحديث الحالة")
        refresh_btn.clicked.connect(self._refresh_status)
        btn_layout.addWidget(refresh_btn)

        open_folder_btn = QPushButton("فتح مجلد الترخيص")
        open_folder_btn.clicked.connect(self._open_license_folder)
        btn_layout.addWidget(open_folder_btn)

        cancel_btn = QPushButton("إغلاق")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        card_layout.addLayout(btn_layout)

        layout.addWidget(card)

        footer = QLabel(f"{APP_DISPLAY_NAME_AR} • {APP_TAGLINE_AR}")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"font-size: 11px; color: {ThemeManager.get('text_muted')};")
        layout.addWidget(footer)

        self._refresh_status()
        self.fade_in()

    def _input_style(self):
        return f"""
            QLineEdit {{
                background-color: {ThemeManager.get('bg_window')};
                color: {ThemeManager.get('text_primary')};
                border: 1px solid {ThemeManager.get('border')};
                border-radius: 9px;
                padding: 8px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 2px solid {ThemeManager.get('primary')}; }}
        """

    def _message_style(self, tone="danger"):
        color = ThemeManager.get(tone) or ThemeManager.get('danger')
        bg = {
            'danger': 'rgba(239, 68, 68, 0.08)',
            'warning': 'rgba(245, 158, 11, 0.10)',
            'success': 'rgba(16, 185, 129, 0.10)',
            'info': 'rgba(15, 118, 110, 0.08)',
        }.get(tone, 'rgba(15, 118, 110, 0.08)')
        return f"background-color: {bg}; color: {color}; border: 1px solid {color}; border-radius: 9px; padding: 8px; font-size: 12px; font-weight: 700;"

    def _set_status_message(self, message, tone="info"):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(self._message_style(tone))
        self.status_label.setVisible(True)

    def _toggle_key_visibility(self, checked):
        self.key_edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.show_key_btn.setText("إخفاء المفتاح" if checked else "إظهار المفتاح")

    def _copy_device_id(self):
        QApplication.clipboard().setText(self.device_edit.text())
        audio_service.play_notify()
        self._set_status_message("تم نسخ معرّف الجهاز.", "success")

    def _open_license_folder(self):
        paths = get_license_file_paths()
        target = paths.get('program') or ''
        import os
        folder = os.path.dirname(target)
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _refresh_status(self):
        program = describe_license_state(False)
        network = describe_license_state(True)
        self._update_pill(self.program_status_pill, "ترخيص البرنامج", program)
        self._update_pill(self.network_status_pill, "ترخيص الشبكة", network)
        paths = get_license_file_paths()
        lines = [
            f"ترخيص البرنامج: {program.get('message', '')}",
            f"انتهاء البرنامج: {program.get('expiration') or 'غير محدد'}",
            f"ملف البرنامج: {program.get('source_path') or paths.get('program', '')}",
            "",
            f"ترخيص الشبكة: {network.get('message', '')}",
            f"انتهاء الشبكة: {network.get('expiration') or 'غير محدد'}",
            f"ملف الشبكة: {network.get('source_path') or paths.get('network', '')}",
        ]
        self.diagnostics.setPlainText("\n".join(lines))

    def _update_pill(self, pill, prefix, state):
        # Rebuild the pill content by replacing stylesheet/text of child label.
        tone = "success" if state.get('valid') else "warning"
        color = ThemeManager.get('success') if tone == 'success' else ThemeManager.get('warning')
        pill.setStyleSheet(f"""
            QFrame#StatusPill {{
                background-color: rgba(15, 118, 110, 0.08);
                border: 1px solid {color};
                border-radius: 13px;
            }}
            QLabel {{ color: {color}; font-size: 11px; font-weight: 700; }}
        """)
        for child in pill.findChildren(QLabel):
            child.setText(f"{prefix}: {'صالح' if state.get('valid') else 'غير صالح'}")

    def _activate(self):
        key = self.key_edit.text().strip()
        if not key:
            audio_service.play_warning()
            self._set_status_message("يرجى إدخال مفتاح الترخيص.", "warning")
            return
        self.activate_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self._set_status_message("جارٍ الاتصال بخدمة الترخيص وحفظ ملف التفعيل...", "info")
        QApplication.processEvents()
        success, msg = activate(key)
        self.progress.setVisible(False)
        self.activate_btn.setEnabled(True)
        self._refresh_status()
        if success:
            audio_service.play_success()
            self._set_status_message("تم التفعيل بنجاح. سيتم متابعة فتح البرنامج.", "success")
            QApplication.processEvents()
            self.accept()
        else:
            audio_service.play_error()
            friendly = msg or "فشل التفعيل"
            self._set_status_message(f"فشل التفعيل: {friendly}", "danger")
