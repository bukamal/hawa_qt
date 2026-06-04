from database import SettingsRepository
from PyQt5.QtCore import QObject, QEvent, QTimer
from PyQt5.QtWidgets import QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QAbstractSpinBox, QApplication
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
        formatted = formatted.replace('0','٠').replace('1','١').replace('2','٢').replace('3','٣').replace('4','٤')\
                             .replace('5','٥').replace('6','٦').replace('7','٧').replace('8','٨').replace('9','٩')
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

class FocusSelectFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            QTimer.singleShot(0, lambda: self._select_all_text(obj))
        return super().eventFilter(obj, event)
    
    def _select_all_text(self, obj):
        try:
            if QApplication.mouseButtons() != Qt.NoButton:
                QTimer.singleShot(100, lambda: self._select_all_text(obj))
                return
            if isinstance(obj, QLineEdit):
                obj.selectAll()
            elif isinstance(obj, QTextEdit):
                obj.selectAll()
            elif isinstance(obj, QComboBox):
                if obj.isEditable():
                    le = obj.lineEdit()
                    if le:
                        le.selectAll()
            elif isinstance(obj, QDateEdit):
                le = obj.findChild(QLineEdit)
                if le:
                    le.selectAll()
            elif isinstance(obj, (QSpinBox, QDoubleSpinBox)):
                obj.selectAll()
            elif isinstance(obj, QAbstractSpinBox):
                le = obj.findChild(QLineEdit)
                if le:
                    le.selectAll()
        except:
            pass

def enable_auto_select_all(app):
    filter_obj = FocusSelectFilter()
    app.installEventFilter(filter_obj)
    print("✅ تم تفعيل خاصية تحديد النص تلقائياً عند التركيز")

def apply_auto_select_to_widget(widget):
    filter_obj = FocusSelectFilter()
    if isinstance(widget, (QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox)):
        widget.installEventFilter(filter_obj)
    for child in widget.findChildren((QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox)):
        child.installEventFilter(filter_obj)
