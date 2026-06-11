# -*- coding: utf-8 -*-
from database import SettingsRepository
import logging
from PyQt5.QtCore import QObject, QTimer, Qt
import logging
from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QAbstractSpinBox
import re

_currency_symbol = None
_currency_decimals = None
_number_format = None


def update_currency_format():
    global _currency_symbol, _currency_decimals, _number_format
    repo = SettingsRepository()
    _currency_symbol = repo.get('currency_symbol', '$')
    _currency_decimals = int(repo.get('currency_decimals', '2'))
    _number_format = repo.get('number_format', 'western')


def format_currency(amount: float) -> str:
    if _currency_symbol is None:
        update_currency_format()
    formatted = f"{amount:,.{_currency_decimals}f}"
    if _number_format == 'arabic':
        formatted = formatted.replace('0', '٠').replace('1', '١').replace('2', '٢').replace('3', '٣').replace('4', '٤') \
            .replace('5', '٥').replace('6', '٦').replace('7', '٧').replace('8', '٨').replace('9', '٩')
    return f"{formatted} {_currency_symbol}"


def format_date(date_str: str) -> str:
    if not date_str:
        return ''
    try:
        import datetime
        dt = datetime.datetime.fromisoformat(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return date_str


def clean_text(text: str) -> str:
    if not text:
        return ''
    text = str(text)
    bad_chars = ['浏', '�', '\u200e', '\u200f', '\ufeff', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e']
    for ch in bad_chars:
        text = text.replace(ch, '')
    text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9\s\-\.\,\:\;\(\)\/\+%]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ========== تحديد النص تلقائياً ==========

class AutoSelectManager(QObject):
    """
    مدير تحديد النص تلقائياً عند التركيز.
    يستخدم إشارة focusChanged بدلاً من eventFilter لموثوقية أعلى.
    """
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.app.focusChanged.connect(self.on_focus_changed)

    def on_focus_changed(self, old, new):
        """عند تغيير التركيز، إذا كان الجديد من نوع LineEdit أو نحوه، نحدد نصه بعد فترة قصيرة"""
        if new is None:
            return
        # الحصول على كائن QLineEdit الحقيقي (قد يكون داخل QComboBox, QDateEdit, QSpinBox)
        line_edit = self._get_line_edit(new)
        if line_edit:
            # تأخير 100ms لضمان اكتمال حدث الماوس وعدم تعارض المؤشر
            QTimer.singleShot(100, lambda: self._select_all(line_edit))

    def _get_line_edit(self, widget):
        """استخراج QLineEdit من الودجت المختلفة"""
        if isinstance(widget, QLineEdit):
            return widget
        elif isinstance(widget, QTextEdit):
            return widget  # QTextEdit لا يمتلك selectAll؟ لديه selectAll()
        elif isinstance(widget, QComboBox):
            if widget.isEditable():
                return widget.lineEdit()
        elif isinstance(widget, QDateEdit):
            return widget.findChild(QLineEdit)
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.findChild(QLineEdit)
        elif isinstance(widget, QAbstractSpinBox):
            return widget.findChild(QLineEdit)
        return None

    def _select_all(self, line_edit):
        """تحديد النص إذا كان LineEdit وله نص"""
        if line_edit and hasattr(line_edit, 'selectAll'):
            # تجنب تحديد النص إذا كان المستخدم قد حدد جزءاً منه يدوياً بالفعل (اختياري)
            # لكننا نريد دائماً تحديد الكل عند التركيز، لذا ننفذه مباشرة
            line_edit.selectAll()


def enable_auto_select_all(app):
    """تفعيل خاصية التحديد التلقائي (مرة واحدة للتطبيق)"""
    manager = AutoSelectManager(app)
    # حفظ المدير في التطبيق لمنعه من التجميع
    app.auto_select_manager = manager
    logging.getLogger(__name__).info("تم تفعيل تحديد النص تلقائياً عند التركيز")


def apply_auto_select_to_widget(widget):
    """
    لا حاجة لهذه الدالة الآن لأننا نستخدم focusChanged على مستوى التطبيق.
    تُترك للتوافق مع الكود القديم.
    """
    pass
