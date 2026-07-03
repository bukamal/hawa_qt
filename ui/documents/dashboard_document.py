# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFrame, QSizePolicy, QGridLayout, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt

from models.table_models import DashboardTrendTableModel, DashboardRecentTableModel
from services.dashboard_service import dashboard_service, PERIOD_LABELS
from views.custom_table_view import CustomTableView


class DashboardDocument(QWidget):
    """Dashboard document backed by DashboardService, not ad-hoc widget math."""
    def __init__(self, shell=None, parent=None):
        super().__init__(parent)
        self.shell = shell
        self.current_data = None
        self.card_widgets = {}
        self.setLayoutDirection(Qt.RightToLeft)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel('لوحة التحكم')
        title.setObjectName('DocumentTitle')
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(QLabel('الفترة:'))
        self.period_combo = QComboBox()
        for key, label in PERIOD_LABELS.items():
            self.period_combo.addItem(label, key)
        self.period_combo.currentIndexChanged.connect(self.refresh_dashboard)
        header.addWidget(self.period_combo)
        refresh_btn = QPushButton('🔄 تحديث')
        refresh_btn.clicked.connect(self.refresh_dashboard)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        self.subtitle_label = QLabel('')
        self.subtitle_label.setObjectName('DocumentHint')
        self.subtitle_label.setWordWrap(True)
        root.addWidget(self.subtitle_label)

        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(10)
        root.addLayout(self.cards_grid)

        trend_title = QLabel('اتجاه آخر 6 أشهر')
        trend_title.setObjectName('SectionTitle')
        root.addWidget(trend_title)
        self.trend_table = CustomTableView()
        self.trend_table.setMinimumHeight(150)
        root.addWidget(self.trend_table)

        recent_title = QLabel('آخر 5 قيود')
        recent_title.setObjectName('SectionTitle')
        root.addWidget(recent_title)
        self.recent_table = CustomTableView()
        self.recent_table.setMinimumHeight(180)
        root.addWidget(self.recent_table, 1)

    def activate(self, **_params):
        self.refresh_dashboard()

    def refresh_dashboard(self):
        period = self.period_combo.currentData() or 'all'
        try:
            self.current_data = dashboard_service.build(period)
            self.subtitle_label.setText(self.current_data['subtitle'] + ' | كل القيود التاريخية محفوظة بسعرها الأصلي.')
            self._render_cards(self.current_data['cards'])
            self._render_trend(self.current_data['trend'])
            self._render_recent(self.current_data['recent'])
        except Exception as exc:
            QMessageBox.critical(self, 'خطأ', str(exc))

    def _render_cards(self, cards):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.card_widgets.clear()
        for idx, card in enumerate(cards):
            widget = self._create_card(card)
            self.cards_grid.addWidget(widget, idx // 5, idx % 5)
            self.card_widgets[card['key']] = widget

    def _create_card(self, card):
        frame = QFrame()
        frame.setObjectName('DashboardCard')
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        frame.setMinimumHeight(100)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        title = QLabel(card.get('title', ''))
        title.setObjectName('DashboardCardTitle')
        title.setAlignment(Qt.AlignRight)
        title.setWordWrap(True)
        value = QLabel(str(card.get('value', '')))
        value.setObjectName('DashboardCardValue')
        value.setAlignment(Qt.AlignRight)
        value.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(value, 1)
        return frame

    def _render_trend(self, rows):
        data = []
        for idx, row in enumerate(rows, start=1):
            data.append({
                'id': idx,
                'month': row['month'],
                'incoming': row['incoming'],
                'outgoing': row['outgoing'],
                'net': row['net'],
            })
        model = DashboardTrendTableModel(data)
        self.trend_table.setModel(model)
        self.trend_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trend_table.refresh_style()

    def _render_recent(self, rows):
        data = []
        for row in rows:
            data.append({
                'id': row.get('id'),
                'date': row.get('date'),
                'company_name': row.get('company_name'),
                'amount_original': row.get('amount_original'),
                'type': row.get('type'),
                'historical_rate': row.get('historical_rate'),
            })
        model = DashboardRecentTableModel(data)
        self.recent_table.setModel(model)
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recent_table.refresh_style()
