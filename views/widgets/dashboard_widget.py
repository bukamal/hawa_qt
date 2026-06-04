from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from database import ExpenseRepository, UserRepository
from currency import currency
from i18n.translator import translate

class DashboardWidget(QWidget):
    refresh_needed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)  # RTL
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.card_layout = QGridLayout()
        self.card_layout.setSpacing(15)
        
        self.incoming_card = self._create_card(translate('total_incoming'), "0")
        self.outgoing_card = self._create_card(translate('total_outgoing'), "0")
        self.net_card = self._create_card(translate('net_profit'), "0")
        self.companies_card = self._create_card("عدد الشركات", "0")
        self.users_card = self._create_card("عدد المستخدمين", "0")
        
        self.card_layout.addWidget(self.incoming_card, 0, 0)
        self.card_layout.addWidget(self.outgoing_card, 0, 1)
        self.card_layout.addWidget(self.net_card, 0, 2)
        self.card_layout.addWidget(self.companies_card, 1, 0)
        self.card_layout.addWidget(self.users_card, 1, 1)
        
        layout.addLayout(self.card_layout)
        self.refresh_needed.connect(self.refresh)
        self.refresh()
    
    def _create_card(self, title, value):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("background-color: palette(base); border-radius: 16px; padding: 16px;")
        vbox = QVBoxLayout(frame)
        vbox.setAlignment(Qt.AlignRight)  # محاذاة النص لليمين
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: palette(mid);")
        title_lbl.setAlignment(Qt.AlignRight)
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet("font-size: 28px; font-weight: bold;")
        value_lbl.setAlignment(Qt.AlignRight)
        vbox.addWidget(title_lbl)
        vbox.addWidget(value_lbl)
        return frame
    
    def refresh(self):
        expense_repo = ExpenseRepository()
        user_repo = UserRepository()
        summary = expense_repo.get_summary(convert_to_display=True)
        users = user_repo.get_all()
        self._set_card_value(self.incoming_card, currency.format_amount(summary['total_incoming']))
        self._set_card_value(self.outgoing_card, currency.format_amount(summary['total_outgoing']))
        net_val = summary['net']
        net_lbl = self._get_card_label(self.net_card)
        net_lbl.setText(currency.format_amount(net_val))
        net_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {'#10b981' if net_val >= 0 else '#ef4444'};")
        self._set_card_value(self.companies_card, str(summary['companies_count']))
        self._set_card_value(self.users_card, str(len(users)))
    
    def _set_card_value(self, card, value):
        self._get_card_label(card).setText(value)
    
    def _get_card_label(self, card):
        return card.findChild(QLabel, None, Qt.FindDirectChildrenOnly)
    
    def apply_theme_colors(self):
        pass
