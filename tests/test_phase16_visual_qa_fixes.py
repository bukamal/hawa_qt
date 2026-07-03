from pathlib import Path


def test_splash_finish_does_not_use_zero_arg_super_in_lambda():
    source = Path('views/splash_screen.py').read_text(encoding='utf-8')
    assert 'lambda: super().finish' not in source
    assert 'QSplashScreen.finish(self, main_window)' in source


def test_global_theme_does_not_force_background_on_every_qwidget():
    source = Path('theme_manager.py').read_text(encoding='utf-8')
    assert 'QMainWindow, QDialog, QWidget {{' not in source
    assert 'QLabel, QCheckBox, QRadioButton {{' in source


def test_accounts_breadcrumb_uses_arabic_route_titles():
    source = Path('ui/shell/app_shell.py').read_text(encoding='utf-8')
    assert "'accounts': 'الحسابات'" in source
    assert "ROUTE_TITLES" in source


def test_accounts_summary_no_long_pipe_string_in_document():
    source = Path('ui/documents/accounts_document.py').read_text(encoding='utf-8')
    assert 'summary_label.setText' not in source
    assert 'AccountsSummaryStrip' in source
