#!/usr/bin/env python3
import sys
import logging
import os
import subprocess
import time
import datetime
import requests
import tempfile
import threading
from logging_config import setup_logging
from error_handling import install_exception_hooks


def configure_qt_runtime_environment():
    """Prepare Linux/root Qt runtime before QApplication is created.

    Running from containers, root sessions, or lightweight Linux desktops often
    lacks XDG_RUNTIME_DIR and may trigger Chromium/QtWebEngine sandbox helper
    warnings. These settings are harmless on normal Windows builds and keep the
    startup log clean in root-based test environments.
    """
    if sys.platform.startswith('linux'):
        if not os.environ.get('XDG_RUNTIME_DIR'):
            user_name = os.environ.get('USER') or os.environ.get('USERNAME') or 'user'
            runtime_dir = os.path.join('/tmp', f'runtime-{user_name}')
            try:
                os.makedirs(runtime_dir, exist_ok=True)
                os.chmod(runtime_dir, 0o700)
                os.environ['XDG_RUNTIME_DIR'] = runtime_dir
            except Exception:
                pass

        try:
            is_root = hasattr(os, 'geteuid') and os.geteuid() == 0
        except Exception:
            is_root = False
        if is_root:
            os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')
            current_flags = os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS', '')
            required_flags = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            for flag in required_flags:
                if flag not in current_flags:
                    current_flags = (current_flags + ' ' + flag).strip()
            os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = current_flags


configure_qt_runtime_environment()

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, QSettings
from PyQt5.QtGui import QFont
from branding import APP_DISPLAY_NAME_AR, APP_DISPLAY_NAME_EN, safe_qicon
from database import ensure_db
from auth.activation import check_activation, start_license_checker, stop_license_checker, check_network_activation
from theme_manager import ThemeManager
from views.splash_screen import ModernSplashScreen
from views.activation_dialog import ActivationDialog
from views.login_dialog import LoginDialog
from views.main_window import MainWindow
from auth.session import UserSession
from utils import enable_auto_select_all
from ui.auth.startup_helpers import describe_post_login_message

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
    """Start the bundled Flask server safely.

    Older code used ``[sys.executable, '--server']``. Python interprets
    ``--server`` as an interpreter option, so the subprocess exits with:
    ``Unknown option: --server``. The script path must be passed before
    application arguments.
    """
    error_log = os.path.join(tempfile.gettempdir(), "hawaa_subprocess_error.log")
    try:
        exe_path = sys.executable or "python3"
        script_path = os.path.abspath(__file__)
        cmd = [exe_path, script_path, '--server']
        if sys.platform == 'win32':
            return subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
        return subprocess.Popen(cmd)
    except Exception as e:
        with open(error_log, "w", encoding='utf-8') as f:
            f.write(str(e))
        logging.getLogger(__name__).exception("فشل بدء خادم Flask")
        return None

def switch_to_local_mode(settings, db_conn, reason=None, notify=True):
    """Force the app back to local SQLite mode without closing it."""
    settings.setValue("network/mode", "local")
    settings.sync()
    db_conn.mode = "local"
    db_conn._rest_client = None
    os.environ['HAWAA_MODE'] = 'local'
    if notify and reason:
        QMessageBox.warning(
            None,
            "العودة للوضع المحلي",
            f"{reason}\n\nسيتم تشغيل التطبيق في الوضع المحلي باستخدام قاعدة البيانات المحلية."
        )

def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{url}/health", timeout=1)
            if resp.status_code == 200 and resp.json().get('status') == 'alive':
                return True
        except Exception:
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
                from services.backup_service import backup_service
                backup_service.create_backup(db_path, backup_path)
        except Exception:
            logging.getLogger(__name__).exception("Periodic backup failed")

def start_periodic_backup():
    global _backup_stop_event, _backup_thread
    from database.connection import DatabaseConnection
    db = DatabaseConnection()
    if db.is_remote():
        logging.getLogger(__name__).info("النسخ الاحتياطي الدوري معطل في وضع العميل")
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

def close_runtime_resources():
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.close_global()
    except Exception:
        logging.getLogger(__name__).exception("Failed to close runtime database resources")

def test_server_connection(url):
    try:
        resp = requests.get(f"{url}/health", timeout=3)
        return resp.status_code == 200 and resp.json().get("status") == "alive"
    except:
        return False

def main():
    server_mode = len(sys.argv) > 1 and sys.argv[1] == '--server'
    setup_logging(context='server' if server_mode else 'app')
    install_exception_hooks()
    logger = logging.getLogger(__name__)
    if server_mode:
        logger.info("تشغيل خادم هوى الشام")
        from services.server_runtime import write_server_pid, clear_server_pid
        write_server_pid()
        try:
            from database.migrations import ensure_db as ensure_db_remote
            ensure_db_remote()
            from waitress import serve
            from flask_server import app
            serve(app, host='0.0.0.0', port=8000, threads=4)
        finally:
            clear_server_pid(os.getpid())
            close_runtime_resources()
        return

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setApplicationName(APP_DISPLAY_NAME_EN)
    app.setApplicationDisplayName(APP_DISPLAY_NAME_AR)
    app.setOrganizationName("Hawaa")
    icon = safe_qicon()
    if icon is not None:
        app.setWindowIcon(icon)
    app.setFont(QFont("Tajawal", 10))
    enable_auto_select_all(app)

    settings = QSettings("Hawaa", "Accounting")
    
    from database.connection import DatabaseConnection
    db_conn = DatabaseConnection()
    mode = db_conn.mode
    server_url = db_conn.server_url

    # التحقق من تفعيل الشبكة قبل السماح بوضع عميل/خادم. عند الفشل نعود محليًا، لا نغلق التطبيق.
    if mode in ("client", "server"):
        network_ok, network_msg = check_network_activation()
        if not network_ok:
            switch_to_local_mode(settings, db_conn, network_msg)
            mode = "local"

    if mode == "server":
        server_process = run_flask_server()
        if server_process is None or not wait_for_server("http://localhost:8000"):
            switch_to_local_mode(
                settings,
                db_conn,
                "تعذر بدء الخادم الداخلي أو لم يستجب على المنفذ 8000."
            )
            mode = "local"
        else:
            QMessageBox.information(None, "خادم", "تم بدء الخادم بنجاح. يمكن للأجهزة الأخرى الاتصال به.")
            os.environ['HAWAA_MODE'] = 'server'
    elif mode == "client":
        os.environ['HAWAA_MODE'] = 'client'
        if not test_server_connection(server_url):
            switch_to_local_mode(
                settings,
                db_conn,
                f"لا يمكن الاتصال بالخادم المحدد:\n{server_url}"
            )
            mode = "local"

    if mode == "local":
        os.environ['HAWAA_MODE'] = 'local'
        db_conn.mode = "local"
        db_conn._rest_client = None

    ThemeManager.init_app(app)

    splash = ModernSplashScreen()
    splash.set_progress(8, "تهيئة مسارات التشغيل وملفات السجل...", "بدء التشغيل")
    QApplication.processEvents()

    splash.set_progress(18, "تحميل الهوية البصرية والموارد...", "الهوية البصرية")
    QApplication.processEvents()

    splash.set_progress(30, "فحص قاعدة البيانات وتطبيق التحديثات...", "قاعدة البيانات")
    try:
        ensure_db()
    except Exception as exc:
        splash.set_error(f"تعذر تهيئة قاعدة البيانات: {exc}")
        QMessageBox.critical(None, "خطأ في قاعدة البيانات", f"تعذر تهيئة قاعدة البيانات:\n{exc}")
        sys.exit(1)

    splash.set_progress(44, "فحص حالة الترخيص...", "الترخيص")
    activated, activation_msg = check_activation()
    if not activated:
        splash.set_progress(46, activation_msg or "الترخيص غير صالح. يلزم التفعيل.", "التفعيل مطلوب")
        old_splash = splash
        splash.hide()
        dlg = ActivationDialog(old_splash)
        if dlg.exec() != ActivationDialog.Accepted:
            old_splash.close()
            close_runtime_resources()
            sys.exit(0)
        old_splash.close()
        old_splash.deleteLater()
        splash = ModernSplashScreen()
        splash.set_progress(52, "تم التفعيل. جارٍ متابعة التشغيل...", "تم التفعيل")

    start_license_checker(24, on_license_invalid)

    splash.set_progress(66, "جاهز لتسجيل الدخول...", "تسجيل الدخول")
    login = LoginDialog(splash)
    splash.hide()
    if login.exec() != LoginDialog.Accepted:
        stop_license_checker()
        close_runtime_resources()
        sys.exit(0)

    current_user = UserSession.get_current() or {}
    splash.show()
    splash.raise_()
    splash.set_progress(74, describe_post_login_message(current_user.get('username')), "تحميل المستخدم")

    if UserSession.force_password_change():
        from views.dialogs.change_password_dialog import ChangePasswordDialog
        from database import UserRepository
        splash.hide()
        dlg = ChangePasswordDialog()
        if dlg.exec():
            repo = UserRepository()
            repo.set_force_password_change(UserSession.get_current()['id'], False)
        splash.show()
        splash.set_progress(80, "تم تحديث كلمة المرور. جارٍ تحميل الصلاحيات...", "تحميل المستخدم")

    splash.set_progress(86, "تحميل الصلاحيات وتجهيز لوحة التحكم...", "تهيئة المساحة")
    QApplication.processEvents()
    splash.set_progress(94, "تجهيز الحسابات والتقارير والإعدادات...", "فتح الواجهة")
    window = MainWindow()
    splash.set_progress(100, "تم التحميل. جارٍ فتح الواجهة الرئيسية...", "جاهز")
    splash.finish(window)
    window.show()

    backup_thread = start_periodic_backup()
    if backup_thread:
        window.backup_thread = backup_thread

    if hasattr(window, 'pages') and 'settings' in window.pages:
        settings_widget = window.pages['settings']
        if hasattr(settings_widget, 'backup_settings_changed'):
            settings_widget.backup_settings_changed.connect(restart_backup)

    exit_code = app.exec()
    try:
        stop_license_checker()
    finally:
        if _backup_stop_event is not None:
            _backup_stop_event.set()
        close_runtime_resources()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
