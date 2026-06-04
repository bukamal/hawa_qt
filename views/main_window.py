from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QPushButton, QLabel, QFrame, QMessageBox, QApplication
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation
from PyQt5.QtGui import QIcon
import qtawesome as qta
from auth.session import UserSession
from i18n.translator import translate, set_language
from database import SettingsRepository
from theme_manager import ThemeManager
from views.widgets.dashboard_widget import DashboardWidget
from views.widgets.accounts_widget import AccountsWidget
from views.widgets.users_widget import UsersWidget
from views.widgets.audit_log_widget import AuditLogWidget
from views.widgets.settings_widget import SettingsWidget
from views.dialogs.change_password_dialog import ChangePasswordDialog
from views.login_dialog import LoginDialog
from views.custom_table_view import CustomTableView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setLayoutDirection(Qt.LeftToRight)  # LTR
        self.setMinimumSize(1200, 700)
        self.resize(1400, 900)
        self.drag_pos = None
        self.sidebar_collapsed = False
        self.sidebar_width = 250
        self.sidebar_collapsed_width = 70

        repo = SettingsRepository()
        set_language(repo.get_language())
        theme = repo.get_theme()
        ThemeManager.apply_theme(theme)

        self.setup_ui()
        self.setup_sidebar()
        # فتح تبويب الحسابات افتراضياً
        self.switch_page('accounts')

        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress and event.key() == Qt.Key_Escape:
            self.switch_page('accounts')
            return True
        return super().eventFilter(obj, event)

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(50)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(15,0,10,0)

        icon_label = QLabel("🏢")
        icon_label.setFixedSize(24,24)
        title_layout.addWidget(icon_label)
        self.title_label = QLabel(translate('app_title'))
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.close_btn = QPushButton()
        self.close_btn.setIcon(qta.icon('fa5s.times'))
        self.close_btn.setFixedSize(32,32)
        self.close_btn.clicked.connect(self.close_app)
        title_layout.addWidget(self.close_btn)

        self.max_btn = QPushButton()
        self.max_btn.setIcon(qta.icon('fa5s.window-maximize'))
        self.max_btn.setFixedSize(32,32)
        self.max_btn.clicked.connect(self.toggle_maximize)
        title_layout.addWidget(self.max_btn)

        self.min_btn = QPushButton()
        self.min_btn.setIcon(qta.icon('fa5s.window-minimize'))
        self.min_btn.setFixedSize(32,32)
        self.min_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(self.min_btn)

        main_layout.addWidget(self.title_bar)

        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(self.sidebar_width)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10,20,10,20)
        self.sidebar_layout.setSpacing(8)

        self.stack = QStackedWidget()

        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.stack, 1)

        main_layout.addWidget(content_container)

        self.title_bar.mousePressEvent = self._mouse_press
        self.title_bar.mouseMoveEvent = self._mouse_move
        self.title_bar.mouseReleaseEvent = self._mouse_release

        self.pages = {}
        self.pages['dashboard'] = DashboardWidget(self)
        self.pages['accounts'] = AccountsWidget(self)
        if UserSession.is_admin():
            self.pages['users'] = UsersWidget(self)
            self.pages['audit_log'] = AuditLogWidget(self)
        self.pages['settings'] = SettingsWidget(self)
        self.pages['accounts'].data_changed.connect(self.pages['dashboard'].refresh_needed.emit)
        self.pages['settings'].rates_changed.connect(self.pages['accounts'].refresh_table)
        for page in self.pages.values():
            self.stack.addWidget(page)

    def close_app(self):
        QApplication.quit()

    def setup_sidebar(self):
        self.toggle_btn = QPushButton()
        self.toggle_btn.setIcon(qta.icon('fa5s.bars'))
        self.toggle_btn.setFixedSize(40,40)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        self.sidebar_layout.addWidget(self.toggle_btn, alignment=Qt.AlignRight)

        self.logo_label = QLabel("🏢 هوى الشام")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.logo_label)

        self.nav_buttons = {}
        pages = [('dashboard','📊',translate('dashboard')), ('accounts','📋',translate('accounts'))]
        if UserSession.is_admin():
            pages.append(('users','👥',translate('users')))
            pages.append(('audit_log','📜',translate('audit_log')))
        pages.append(('settings','⚙️',translate('settings')))

        for pid,icon,txt in pages:
            btn = QPushButton(f"{icon} {txt}")
            btn.setObjectName("nav_button")
            btn.setFixedHeight(45)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked,p=pid: self.switch_page(p))
            self.sidebar_layout.addWidget(btn)
            self.nav_buttons[pid] = btn

        self.sidebar_layout.addStretch()
        self.logout_btn = QPushButton("🚪 "+translate('logout'))
        self.logout_btn.setFixedHeight(40)
        self.logout_btn.clicked.connect(self.logout)
        self.sidebar_layout.addWidget(self.logout_btn)

        self.change_pwd_btn = QPushButton("🔑 "+translate('change_password'))
        self.change_pwd_btn.setFixedHeight(40)
        self.change_pwd_btn.clicked.connect(self.change_password)
        self.sidebar_layout.addWidget(self.change_pwd_btn)

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        target = self.sidebar_collapsed_width if self.sidebar_collapsed else self.sidebar_width
        self.anim = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim.setDuration(250)
        self.anim.setStartValue(self.sidebar.width())
        self.anim.setEndValue(target)
        self.anim.finished.connect(self._update_sidebar_buttons)
        self.anim.start()

    def _update_sidebar_buttons(self):
        if self.sidebar_collapsed:
            for pid,btn in self.nav_buttons.items():
                txt = btn.text()
                icon = txt.split(' ')[0]
                btn.setText(icon)
                btn.setToolTip(txt.split(' ',1)[1] if len(txt.split(' '))>1 else '')
            self.logout_btn.setText("🚪")
            self.change_pwd_btn.setText("🔑")
            self.logo_label.setText("🏢")
        else:
            texts = {'dashboard':('📊',translate('dashboard')), 'accounts':('📋',translate('accounts')),
                     'users':('👥',translate('users')), 'audit_log':('📜',translate('audit_log')), 'settings':('⚙️',translate('settings'))}
            for pid,btn in self.nav_buttons.items():
                if pid in texts:
                    icon,txt = texts[pid]
                    btn.setText(f"{icon} {txt}")
                btn.setToolTip('')
            self.logout_btn.setText("🚪 "+translate('logout'))
            self.change_pwd_btn.setText("🔑 "+translate('change_password'))
            self.logo_label.setText("🏢 هوى الشام")

    def _mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    def _mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
    def _mouse_release(self, event):
        self.drag_pos = None

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setIcon(qta.icon('fa5s.window-maximize'))
        else:
            self.showMaximized()
            self.max_btn.setIcon(qta.icon('fa5s.window-restore'))

    def switch_page(self, pid):
        if pid in self.pages:
            self.stack.setCurrentWidget(self.pages[pid])
            for pid2,btn in self.nav_buttons.items():
                btn.setProperty("active", pid2==pid)
                btn.style().unpolish(btn); btn.style().polish(btn)

    def change_password(self):
        dlg = ChangePasswordDialog(self)
        if dlg.exec():
            QMessageBox.information(self, translate('success'), "تم تغيير كلمة المرور")

    def logout(self):
        reply = QMessageBox.question(self, translate('logout'), "هل تريد تسجيل الخروج؟", QMessageBox.Yes|QMessageBox.No)
        if reply == QMessageBox.Yes:
            UserSession.logout()
            self.hide()
            login = LoginDialog()
            if login.exec() == LoginDialog.Accepted:
                self.refresh_pages_after_login()
                self.show()
                self.switch_page('accounts')
            else:
                self.close()

    def refresh_pages_after_login(self):
        for page in self.pages.values():
            self.stack.removeWidget(page); page.deleteLater()
        self.pages.clear()
        self.pages['dashboard'] = DashboardWidget(self)
        self.pages['accounts'] = AccountsWidget(self)
        if UserSession.is_admin():
            self.pages['users'] = UsersWidget(self)
            self.pages['audit_log'] = AuditLogWidget(self)
        self.pages['settings'] = SettingsWidget(self)
        self.pages['accounts'].data_changed.connect(self.pages['dashboard'].refresh_needed.emit)
        self.pages['settings'].rates_changed.connect(self.pages['accounts'].refresh_table)
        for page in self.pages.values():
            self.stack.addWidget(page)
        self.rebuild_sidebar_buttons()
        self.apply_theme_to_pages()

    def rebuild_sidebar_buttons(self):
        for i in reversed(range(self.sidebar_layout.count())):
            w = self.sidebar_layout.itemAt(i).widget()
            if w and w not in [self.toggle_btn, self.logo_label, self.logout_btn, self.change_pwd_btn]:
                w.deleteLater()
        self.nav_buttons.clear()
        pages = [('dashboard','📊',translate('dashboard')), ('accounts','📋',translate('accounts'))]
        if UserSession.is_admin():
            pages.append(('users','👥',translate('users')))
            pages.append(('audit_log','📜',translate('audit_log')))
        pages.append(('settings','⚙️',translate('settings')))
        for pid,icon,txt in pages:
            btn = QPushButton(f"{icon} {txt}")
            btn.setObjectName("nav_button")
            btn.setFixedHeight(45)
            btn.clicked.connect(lambda checked,p=pid: self.switch_page(p))
            self.sidebar_layout.insertWidget(self.sidebar_layout.count()-3, btn)
            self.nav_buttons[pid] = btn
        if self.sidebar_collapsed:
            self._update_sidebar_buttons()

    def apply_theme_to_pages(self):
        for page in self.pages.values():
            if hasattr(page, 'apply_theme_colors'):
                page.apply_theme_colors()
            for child in page.findChildren(CustomTableView):
                child.refresh_style()
        if 'accounts' in self.pages:
            self.pages['accounts'].apply_theme_colors()

    def apply_theme(self, theme):
        ThemeManager.apply_theme(theme)
        self.apply_theme_to_pages()
