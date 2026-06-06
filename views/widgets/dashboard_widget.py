from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, QComboBox, QHBoxLayout, QHeaderView, QSizePolicy
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from database import ExpenseRepository, UserRepository
from currency import currency
from i18n.translator import translate
from views.custom_table_view import CustomTableView
from models.table_models import GenericTableModel
from datetime import datetime, timedelta
import pyqtgraph as pg
from pyqtgraph import PlotWidget, BarGraphItem

class DashboardWidget(QWidget):
    refresh_needed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # شريط الفلترة
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("الفترة:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["الكل", "الشهر الحالي", "الشهر الماضي", "السنة الحالية"])
        self.period_combo.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.period_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # بطاقات الإحصائيات (الصف الأول)
        self.card_layout = QGridLayout()
        self.card_layout.setSpacing(15)
        # تعيين تمدد الأعمدة لتوزيع المساحة بالتساوي
        for i in range(3):
            self.card_layout.setColumnStretch(i, 1)
        # تعيين تمدد الصفوف
        self.card_layout.setRowStretch(0, 1)
        self.card_layout.setRowStretch(1, 1)
        self.card_layout.setRowStretch(2, 1)
        
        self.incoming_card = self._create_card(translate('total_incoming'), "0")
        self.outgoing_card = self._create_card(translate('total_outgoing'), "0")
        self.net_card = self._create_card(translate('net_profit'), "0")
        self.companies_card = self._create_card("عدد الشركات", "0")
        self.users_card = self._create_card("عدد المستخدمين", "0")
        self.avg_card = self._create_card("متوسط قيمة القيد", "0")
        self.top_company_card = self._create_card("أعلى شركة صافي", "0")
        self.exchange_rate_card = self._create_card("سعر الصرف (1 USD)", "0")
        
        self.card_layout.addWidget(self.incoming_card, 0, 0)
        self.card_layout.addWidget(self.outgoing_card, 0, 1)
        self.card_layout.addWidget(self.net_card, 0, 2)
        self.card_layout.addWidget(self.companies_card, 1, 0)
        self.card_layout.addWidget(self.users_card, 1, 1)
        self.card_layout.addWidget(self.avg_card, 1, 2)
        self.card_layout.addWidget(self.top_company_card, 2, 0, 1, 2)
        self.card_layout.addWidget(self.exchange_rate_card, 2, 2)
        
        layout.addLayout(self.card_layout)
        
        # الرسم البياني
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', f'المبلغ ({currency.get_display_currency()})')
        self.plot_widget.setLabel('bottom', 'الشهر')
        self.plot_widget.setTitle('اتجاه الإيرادات والمصروفات (آخر 6 أشهر)')
        self.plot_widget.getAxis('bottom').setTicks([])
        layout.addWidget(self.plot_widget)
        
        # جدول آخر 5 قيود
        self.recent_table = CustomTableView()
        self.recent_table.setMinimumHeight(200)
        layout.addWidget(QLabel("آخر 5 قيود مضافة:"))
        layout.addWidget(self.recent_table)
        
        self.refresh_needed.connect(self.refresh)
        self.refresh()
    
    def _create_card(self, title, value):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("background-color: palette(base); border-radius: 16px; padding: 16px;")
        # سياسة الحجم لتمدد أفقياً
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        frame.setMinimumHeight(100)
        frame.setMinimumWidth(180)
        
        vbox = QVBoxLayout(frame)
        vbox.setAlignment(Qt.AlignRight)
        vbox.setContentsMargins(10, 10, 10, 10)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: palette(mid);")
        title_lbl.setAlignment(Qt.AlignRight)
        title_lbl.setWordWrap(True)
        vbox.addWidget(title_lbl)
        
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet("font-size: 28px; font-weight: bold;")
        value_lbl.setAlignment(Qt.AlignRight)
        value_lbl.setWordWrap(True)
        value_lbl.setMinimumWidth(120)
        vbox.addWidget(value_lbl)
        
        return frame
    
    def get_date_filter(self):
        today = QDate.currentDate()
        period = self.period_combo.currentIndex()
        if period == 1:  # الشهر الحالي
            start = QDate(today.year(), today.month(), 1)
            end = QDate(today.year(), today.month(), start.daysInMonth())
        elif period == 2:  # الشهر الماضي
            if today.month() == 1:
                start = QDate(today.year()-1, 12, 1)
            else:
                start = QDate(today.year(), today.month()-1, 1)
            end = QDate(start.year(), start.month(), start.daysInMonth())
        elif period == 3:  # السنة الحالية
            start = QDate(today.year(), 1, 1)
            end = QDate(today.year(), 12, 31)
        else:  # الكل
            start = None
            end = None
        return (start.toString("yyyy-MM-dd") if start else None,
                end.toString("yyyy-MM-dd") if end else None)
    
    def refresh(self):
        expense_repo = ExpenseRepository()
        user_repo = UserRepository()
        
        all_expenses = expense_repo.get_all(convert_to_display=False)
        start_date, end_date = self.get_date_filter()
        filtered = []
        for e in all_expenses:
            if start_date and e['date'] < start_date:
                continue
            if end_date and e['date'] > end_date:
                continue
            filtered.append(e)
        
        total_in_usd = sum(e['amount'] for e in filtered if e['type'] == 'incoming')
        total_out_usd = sum(e['amount'] for e in filtered if e['type'] == 'outgoing')
        net_usd = total_in_usd - total_out_usd
        
        display_currency = currency.get_display_currency()
        total_in = currency.convert(total_in_usd, 'USD', display_currency)
        total_out = currency.convert(total_out_usd, 'USD', display_currency)
        net = currency.convert(net_usd, 'USD', display_currency)
        
        companies = set(e['company_name'] for e in filtered)
        companies_count = len(companies)
        users = user_repo.get_all()
        users_count = len(users)
        
        if filtered:
            avg_usd = sum(e['amount'] for e in filtered) / len(filtered)
            avg = currency.convert(avg_usd, 'USD', display_currency)
        else:
            avg = 0
        
        company_net = {}
        for e in filtered:
            company_net[e['company_name']] = company_net.get(e['company_name'], 0) + (e['amount'] if e['type'] == 'incoming' else -e['amount'])
        if company_net:
            top_company = max(company_net.items(), key=lambda x: x[1])
            top_net = currency.convert(top_company[1], 'USD', display_currency)
            top_text = f"{top_company[0]} ({currency.format_amount(top_net, display_currency)})"
        else:
            top_text = "—"
        
        base_currency = currency.get_base_currency()
        rate = currency.get_rate_to_usd(display_currency)
        rate_text = f"1 {display_currency} = {rate:.4f} USD" if display_currency != 'USD' else f"1 USD = 1.00 USD"
        
        self._set_card_value(self.incoming_card, currency.format_amount(total_in, display_currency))
        self._set_card_value(self.outgoing_card, currency.format_amount(total_out, display_currency))
        net_lbl = self._get_card_label(self.net_card)
        net_lbl.setText(currency.format_amount(net, display_currency))
        net_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {'#10b981' if net >= 0 else '#ef4444'};")
        self._set_card_value(self.companies_card, str(companies_count))
        self._set_card_value(self.users_card, str(users_count))
        self._set_card_value(self.avg_card, currency.format_amount(avg, display_currency))
        self._set_card_value(self.top_company_card, top_text)
        self._set_card_value(self.exchange_rate_card, rate_text)
        
        # إعادة تخطيط البطاقات بعد تغيير القيم
        for card in [self.incoming_card, self.outgoing_card, self.net_card,
                     self.companies_card, self.users_card, self.avg_card,
                     self.top_company_card, self.exchange_rate_card]:
            card.updateGeometry()
        
        self.plot_monthly_trend(all_expenses)
        
        recent = sorted(all_expenses, key=lambda x: x['id'], reverse=True)[:5]
        recent_data = []
        for r in recent:
            amount_original = r['amount_original']
            currency_original = r['currency_original']
            amount_str = f"{amount_original:,.2f} {currency_original}"
            recent_data.append({
                'id': r['id'],
                'date': r['date'],
                'company': r['company_name'],
                'amount': amount_str,
                'type': 'لنا' if r['type'] == 'incoming' else 'له'
            })
        headers = ['date', 'company', 'amount', 'type']
        display_headers = [translate('date'), translate('company_name'), translate('amount'), 'النوع']
        model = GenericTableModel(recent_data, display_headers, key_fields=['id'], data_keys=headers)
        self.recent_table.setModel(model)
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recent_table.setColumnHidden(0, True)
        self.recent_table.refresh_style()
    
    def plot_monthly_trend(self, all_expenses):
        monthly_in = {}
        monthly_out = {}
        for e in all_expenses:
            date_str = e['date']
            try:
                month_key = date_str[:7]
                amount_usd = e['amount']
                if e['type'] == 'incoming':
                    monthly_in[month_key] = monthly_in.get(month_key, 0) + amount_usd
                else:
                    monthly_out[month_key] = monthly_out.get(month_key, 0) + amount_usd
            except:
                continue
        
        today = datetime.now()
        last_6_months = []
        for i in range(5, -1, -1):
            d = today - timedelta(days=30*i)
            month_key = d.strftime("%Y-%m")
            last_6_months.append(month_key)
        
        months = []
        in_vals = []
        out_vals = []
        for m in last_6_months:
            months.append(m[5:7] + "/" + m[2:4])
            in_vals.append(monthly_in.get(m, 0))
            out_vals.append(monthly_out.get(m, 0))
        
        display_currency = currency.get_display_currency()
        in_display = [currency.convert(v, 'USD', display_currency) for v in in_vals]
        out_display = [currency.convert(v, 'USD', display_currency) for v in out_vals]
        
        self.plot_widget.clear()
        x = list(range(len(months)))
        bg_in = pg.BarGraphItem(x=x, height=in_display, width=0.4, brush='#28a745', name=translate('total_incoming'))
        bg_out = pg.BarGraphItem(x=[i+0.4 for i in x], height=out_display, width=0.4, brush='#dc3545', name=translate('total_outgoing'))
        self.plot_widget.addItem(bg_in)
        self.plot_widget.addItem(bg_out)
        self.plot_widget.setLabel('left', f'المبلغ ({display_currency})')
        self.plot_widget.setLabel('bottom', 'الشهر')
        self.plot_widget.setTitle('اتجاه الإيرادات والمصروفات (آخر 6 أشهر)')
        ax = self.plot_widget.getAxis('bottom')
        ticks = [list(zip(range(len(months)), months))]
        ax.setTicks(ticks)
        self.plot_widget.addLegend()
    
    def _set_card_value(self, card, value):
        self._get_card_label(card).setText(value)
    
    def _get_card_label(self, card):
        return card.findChild(QLabel, None, Qt.FindDirectChildrenOnly)
    
    def apply_theme_colors(self):
        pass
