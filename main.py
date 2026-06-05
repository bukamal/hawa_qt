#!/usr/bin/env python3
import sys
import os
import threading
import time
import datetime
import shutil
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QDialogButtonBox
from PyQt5.QtCore import QTimer, QSettings, Qt
from PyQt5.QtGui import QFont
from database import ensure_db
from auth.activation import check_activation, start_license_checker, stop_license_checker
from theme_manager import ThemeManager
from views.splash_screen import ModernSplashScreen
from views.activation_dialog import ActivationDialog
from views.login_dialog import LoginDialog
from views.main_window import MainWindow
from auth.session import UserSession
from utils import enable_auto_select_all

_backup_stop_event = None
_backup_thread = None

def on_license_invalid():
    def show():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("ترخيص منتهي")
        msg.setText("انتهت صلاحية الترخيص.\nسيتم إغلاق التطبيق.")
        msg.exec()
        sys.exit(1)
    QTimer.singleShot(0, show)

def run_flask_server():
    from flask_server import app
    app.run(host='0.0.0.0', port=8000, threaded=True, debug=False, use_reloader=False)

def periodic_backup_worker(interval_seconds, folder, db_path):
    global _backup_stop_event
    while not _backup_stop_event.is_set():
        time.sleep(interval_seconds)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"hawaa_auto_backup_{timestamp}.db"
        backup_path = os.path.join(folder, backup_name)
        try:
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_path)
        except:
            pass

def start_periodic_backup():
    global _backup_stop_event, _backup_thread
    from database.connection import DatabaseConnection
    db = DatabaseConnection()
    if db.is_remote():
        print("⚠️ النسخ الاحتياطي الدوري معطل في وضع العميل")
        return None

    settings = QSettings("Hawaa", "Accounting")
    enabled = settings.value("backup/enabled", False, type=bool)
    if not enabled:
        return None
    interval_hours = settings.value("backup/interval_hours", 6, type=int)
    folder = settings.value("backup/folder", "")
    if not folder:
        return None
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except:
            return None
    from database.connection import DB_PATH
    if _backup_stop_event is not None:
        _backup_stop_event.set()
        if _backup_thread and _backup_thread.is_alive():
            _backup_thread.join(timeout=1)
    _backup_stop_event = threading.Event()
    _backup_thread = threading.Thread(
        target=periodic_backup_worker,
        args=(interval_hours * 3600, folder, DB_PATH),
        daemon=True
    )
    _backup_thread.start()
    return _backup_thread

def restart_backup():
    new_thread = start_periodic_backup()
    return new_thread

def test_server_connection(url):
    import requests
    try:
        resp = requests.get(f"{url}/health", timeout=3)
        return resp.status_code == 200 and resp.json().get("status") == "alive"
    except:
        return False

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Tajawal", 10))
    enable_auto_select_all(app)

    settings = QSettings("Hawaa", "Accounting")
    
    # قراءة وضع الشبكة من الإعدادات
    from database.connection import DatabaseConnection
    db_conn = DatabaseConnection()  # يقرأ الوضع من QSettings
    mode = db_conn.mode  # local, client, server
    server_url = db_conn.server_url

    if mode == "server":
        # تشغيل خادم Flask في thread منفصل
        server_thread = threading.Thread(target=run_flask_server, daemon=True)
        server_thread.start()
        time.sleep(2)  # انتظار بدء الخادم
        # في وضع الخادم، التطبيق يعمل محلياً (لا يستخدم REST)
        os.environ['HAWAA_MODE'] = 'server'
    elif mode == "client":
        os.environ['HAWAA_MODE'] = 'client'
        # التحقق من الاتصال بالخادم
        if not test_server_connection(server_url):
            reply = QMessageBox.question(None, "تحذير الاتصال بالخادم",
                f"لا يمكن الاتصال بالخادم المحدد:\n{server_url}\n\n"
                "هل تريد المتابعة باستخدام قاعدة البيانات المحلية؟\n"
                "(اختر 'لا' لفتح إعدادات الشبكة وتعديل العنوان)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)
            if reply == QMessageBox.No:
                from views.widgets.settings_widget import SettingsWidget
                dialog = QDialog()
                dialog.setWindowTitle("إعدادات الشبكة")
                dialog.setLayoutDirection(Qt.RightToLeft)
                dialog.resize(600, 500)
                layout = QVBoxLayout(dialog)
                settings_widget = SettingsWidget(dialog)
                layout.addWidget(settings_widget)
                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                layout.addWidget(button_box)
                if dialog.exec() == QDialog.Accepted:
                    QMessageBox.information(None, "تم الحفظ", "سيتم إعادة تشغيل التطبيق لتطبيق الإعدادات.")
                sys.exit(0)
            else:
                # تبديل إلى الوضع المحلي
                db_conn.mode = 'local'
                os.environ['HAWAA_MODE'] = 'local'
                QMessageBox.information(None, "تنبيه", "سيتم استخدام قاعدة البيانات المحلية.")
    else:  # local
        os.environ['HAWAA_MODE'] = 'local'

    ThemeManager.init_app(app)

    splash = ModernSplashScreen()
    splash.set_progress(10, "جاري تهيئة قاعدة البيانات...")
    ensure_db()

    splash.set_progress(30, "التحقق من الترخيص...")
    activated, _ = check_activation()
    if not activated:
        old_splash = splash
        splash.hide()
        dlg = ActivationDialog()
        if dlg.exec() != ActivationDialog.Accepted:
            old_splash.close()
            sys.exit(0)
        old_splash.close()
        old_splash.deleteLater()
        splash = ModernSplashScreen()
        splash.set_progress(30, "تم التفعيل...")

    start_license_checker(24, on_license_invalid)

    splash.set_progress(60, "تسجيل الدخول...")
    login = LoginDialog()
    splash.hide()
    if login.exec() != LoginDialog.Accepted:
        stop_license_checker()
        sys.exit(0)

    if UserSession.force_password_change():
        from views.dialogs.change_password_dialog import ChangePasswordDialog
        from database import UserRepository
        dlg = ChangePasswordDialog()
        if dlg.exec():
            repo = UserRepository()
            repo.set_force_password_change(UserSession.get_current()['id'], False)

    splash.set_progress(90, "جاري تحميل الواجهة...")
    window = MainWindow()
    splash.finish(window)
    window.show()

    backup_thread = start_periodic_backup()
    if backup_thread:
        window.backup_thread = backup_thread

    if hasattr(window, 'pages') and 'settings' in window.pages:
        settings_widget = window.pages['settings']
        settings_widget.backup_settings_changed.connect(restart_backup)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
