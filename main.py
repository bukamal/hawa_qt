#!/usr/bin/env python3
import sys
import os
import threading
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, QSettings, QObject, pyqtSignal
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

def on_license_invalid():
    def show():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("ترخيص منتهي")
        msg.setText("انتهت صلاحية الترخيص.\nسيتم إغلاق التطبيق.")
        msg.exec()
        sys.exit(1)
    QTimer.singleShot(0, show)

def run_server():
    """تشغيل خادم FastAPI في خيط منفصل"""
    import uvicorn
    from server import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

class BackupManager(QObject):
    """إدارة النسخ الاحتياطي الدوري"""
    def __init__(self):
        super().__init__()
        self.timer = None
        self.update_timer()

    def update_timer(self):
        """إعادة تشغيل المؤقت بناءً على الإعدادات الحالية"""
        if self.timer:
            self.timer.stop()
            self.timer = None

        settings = QSettings("Hawaa", "Accounting")
        enabled = settings.value("backup/enabled", False, type=bool)
        if not enabled:
            return
        interval_hours = settings.value("backup/interval_hours", 6, type=int)
        folder = settings.value("backup/folder", "")
        if not folder:
            return

        from database.connection import DB_PATH
        import shutil, datetime, os

        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except:
                return

        def backup_task():
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"hawaa_auto_backup_{timestamp}.db"
            backup_path = os.path.join(folder, backup_name)
            try:
                if os.path.exists(DB_PATH):
                    shutil.copy2(DB_PATH, backup_path)
            except:
                pass

        self.timer = QTimer()
        self.timer.timeout.connect(backup_task)
        self.timer.start(interval_hours * 3600 * 1000)

    def stop(self):
        if self.timer:
            self.timer.stop()
            self.timer = None

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Tajawal", 10))
    enable_auto_select_all(app)

    settings = QSettings("Hawaa", "Accounting")
    is_server = settings.value("network/is_server", False, type=bool)
    server_url = settings.value("network/server_url", "http://localhost:8000")

    if is_server:
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(2)
        os.environ['HAWAA_SERVER'] = 'http://localhost:8000'
    else:
        os.environ['HAWAA_SERVER'] = server_url

    ThemeManager.init_app(app)

    splash = ModernSplashScreen()
    splash.set_progress(10, "جاري تهيئة قاعدة البيانات...")
    ensure_db()

    splash.set_progress(30, "التحقق من الترخيص...")
    activated, _ = check_activation()
    if not activated:
        splash.hide()
        dlg = ActivationDialog()
        if dlg.exec() != ActivationDialog.Accepted:
            sys.exit(0)
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

    # إدارة النسخ الاحتياطي الدوري
    backup_manager = BackupManager()
    window.backup_manager = backup_manager  # الاحتفاظ بالمرجع

    # ربط إشارة تغيير الإعدادات من نافذة الإعدادات
    if hasattr(window, 'pages') and 'settings' in window.pages:
        settings_widget = window.pages['settings']
        settings_widget.backup_settings_changed.connect(backup_manager.update_timer)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
