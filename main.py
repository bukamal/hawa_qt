#!/usr/bin/env python3
import sys
import logging
import os
import subprocess
import time
import datetime
import shutil
import requests
import tempfile
import threading
from logging_config import setup_logging
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QDialogButtonBox
from PyQt5.QtCore import QTimer, QSettings, Qt
from PyQt5.QtGui import QFont
from database import ensure_db
from auth.activation import check_activation, start_license_checker, stop_license_checker, check_network_activation
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
    error_log = os.path.join(tempfile.gettempdir(), "hawaa_subprocess_error.log")
    try:
        exe_path = sys.executable
        if not os.path.exists(exe_path):
            exe_path = sys.executable
        cmd = [exe_path, '--server']
        if sys.platform == 'win32':
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen(cmd)
    except Exception as e:
        with open(error_log, "w", encoding='utf-8') as f:
            f.write(str(e))
        def show_error():
            QMessageBox.critical(None, "خطأ في الخادم",
                                f"فشل بدء خادم Flask.\nتم تسجيل الخطأ في:\n{error_log}")
        QTimer.singleShot(0, show_error)
        raise

def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{url}/health", timeout=1)
            if resp.status_code == 200 and resp.json().get('status') == 'alive':
                return True
        except:
            pass
        time.sleep(0.5)
    return False

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
        logger.info("النسخ الاحتياطي الدوري معطل في وضع العميل")
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
    try:
        resp = requests.get(f"{url}/health", timeout=3)
        return resp.status_code == 200 and resp.json().get("status") == "alive"
    except:
        return False

def open_network_settings():
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
    return dialog.exec() == QDialog.Accepted

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        logger.info("تشغيل خادم هوى الشام")
        from database.migrations import ensure_db as ensure_db_remote
        ensure_db_remote()
        from waitress import serve
        from flask_server import app
        serve(app, host='0.0.0.0', port=8000, threads=4)
        return

    app = QApplication(sys.argv)
    app.setFont(QFont("Tajawal", 10))
    enable_auto_select_all(app)

    settings = QSettings("Hawaa", "Accounting")
    
    from database.connection import DatabaseConnection
    db_conn = DatabaseConnection()
    mode = db_conn.mode
    server_url = db_conn.server_url

    # التحقق من تفعيل الشبكة قبل السماح بوضع عميل/خادم
    if mode in ("client", "server"):
        network_ok, network_msg = check_network_activation()
        if not network_ok:
            QMessageBox.critical(None, "تفعيل الشبكة مطلوب", 
                                 f"{network_msg}\n\nسيتم تشغيل التطبيق في الوضع المحلي.")
            mode = "local"
            settings.setValue("network/mode", "local")
            db_conn.mode = "local"

    if mode == "server":
        run_flask_server()
        if not wait_for_server("http://localhost:8000"):
            QMessageBox.critical(None, "خطأ", "فشل بدء الخادم الداخلي. تحقق من المنفذ 8000 أو جدار الحماية.")
            sys.exit(1)
        QMessageBox.information(None, "خادم", "تم بدء الخادم بنجاح. يمكن للأجهزة الأخرى الاتصال به.")
        os.environ['HAWAA_MODE'] = 'server'
    elif mode == "client":
        os.environ['HAWAA_MODE'] = 'client'
        if not test_server_connection(server_url):
            QMessageBox.critical(None, "خطأ في الاتصال",
                                 f"لا يمكن الاتصال بالخادم المحدد:\n{server_url}\n\n"
                                 "سيتم فتح إعدادات الشبكة لتعديل العنوان.")
            if open_network_settings():
                QMessageBox.information(None, "تم الحفظ", "سيتم إعادة تشغيل التطبيق لتطبيق الإعدادات.")
            sys.exit(0)
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
        dlg = ActivationDialog(old_splash)
        if dlg.exec() != ActivationDialog.Accepted:
            old_splash.close()
            sys.exit(0)
        old_splash.close()
        old_splash.deleteLater()
        splash = ModernSplashScreen()
        splash.set_progress(30, "تم التفعيل...")

    start_license_checker(24, on_license_invalid)

    splash.set_progress(60, "تسجيل الدخول...")
    login = LoginDialog(splash)
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
