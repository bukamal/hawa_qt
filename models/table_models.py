from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Dict, Any, Optional

class GenericTableModel(QAbstractTableModel):
    def __init__(self, data: List[Dict], headers: List[str], key_fields: List[str] = None, data_keys: List[str] = None):
        super().__init__()
        self._data = data
        self._headers = headers
        self._key_fields = key_fields or []
        self._data_keys = data_keys if data_keys is not None else headers
        # تأكد من تطابق الأطوال
        if len(self._data_keys) < len(self._headers):
            self._data_keys.extend([''] * (len(self._headers) - len(self._data_keys)))

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._data) or col >= len(self._data_keys):
            return None
        record = self._data[row]
        key = self._data_keys[col]
        value = record.get(key, '')
        return str(value) if value is not None else ''

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        row = index.row()
        col = index.column()
        if row >= len(self._data) or col >= len(self._data_keys):
            return False
        key = self._data_keys[col]
        self._data[row][key] = value
        self.dataChanged.emit(index, index)
        return True

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < len(self._headers):
                return self._headers[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def refresh_data(self, new_data: List[Dict]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_row(self, row: int) -> Dict:
        if 0 <= row < len(self._data):
            return self._data[row]
        return {}

    def get_id(self, row: int) -> Any:
        if self._key_fields and row < len(self._data):
            return self._data[row].get(self._key_fields[0])
        return None



# ---------------------------------------------------------------------------
# Document Shell table models
# ---------------------------------------------------------------------------
# These models are intentionally explicit. GenericTableModel is still kept for
# legacy widgets, but new Document Shell pages should use specialized models so
# hidden ids, display fields and semantic columns are not confused.
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TableColumn:
    key: str
    header: str
    formatter: Optional[Callable[[Any, Dict[str, Any]], Any]] = None
    alignment: int = Qt.AlignCenter


class StructuredTableModel(QAbstractTableModel):
    """Read-only table model with explicit columns and hidden key fields."""
    columns: List[TableColumn] = []
    primary_key: str = 'id'

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, columns: Optional[List[TableColumn]] = None, primary_key: Optional[str] = None):
        super().__init__()
        self._data = list(data or [])
        self._columns = list(columns or self.columns)
        if primary_key is not None:
            self.primary_key = primary_key

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row_idx = index.row()
        col_idx = index.column()
        if row_idx >= len(self._data) or col_idx >= len(self._columns):
            return None
        row = self._data[row_idx]
        column = self._columns[col_idx]
        if role in (Qt.DisplayRole, Qt.EditRole):
            value = row.get(column.key, '')
            if column.formatter:
                value = column.formatter(value, row)
            return '' if value is None else str(value)
        if role == Qt.TextAlignmentRole:
            return column.alignment
        if role == Qt.UserRole:
            return row.get(column.key)
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and section < len(self._columns):
            return self._columns[section].header
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def refresh_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = list(new_data or [])
        self.endResetModel()

    def get_row(self, row: int) -> Dict[str, Any]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return {}

    def get_id(self, row: int) -> Any:
        return self.get_row(row).get(self.primary_key)


class CompanySummaryTableModel(StructuredTableModel):
    primary_key = 'company'
    columns = [
        TableColumn('company', 'الشركة'),
        TableColumn('incoming', 'إجمالي الوارد'),
        TableColumn('outgoing', 'إجمالي الصادر'),
        TableColumn('net', 'الصافي'),
        TableColumn('payment_status', 'تنبيهات الدفع'),
    ]


class CompanyLedgerTableModel(StructuredTableModel):
    columns = [
        TableColumn('serial', '#'),
        TableColumn('date', 'التاريخ'),
        TableColumn('notes', 'ملاحظات'),
        TableColumn('incoming', 'لنا'),
        TableColumn('outgoing', 'له'),
        TableColumn('running', 'الرصيد التراكمي'),
        TableColumn('historical_rate', 'سعر القيد'),
    ]


class UserTableModel(StructuredTableModel):
    columns = [
        TableColumn('username', 'اسم المستخدم'),
        TableColumn('full_name', 'الاسم الكامل'),
        TableColumn('role', 'الدور'),
        TableColumn('created_at', 'تاريخ التسجيل'),
        TableColumn('last_login', 'آخر دخول'),
        TableColumn('force_password_change', 'تغيير كلمة المرور'),
    ]


class AuditLogTableModel(StructuredTableModel):
    columns = [
        TableColumn('username', 'المستخدم'),
        TableColumn('action', 'الإجراء'),
        TableColumn('table_name', 'الجدول'),
        TableColumn('record_id', 'رقم السجل'),
        TableColumn('details', 'التفاصيل'),
        TableColumn('ip_address', 'عنوان IP'),
        TableColumn('timestamp', 'التاريخ والوقت'),
    ]


class DashboardTrendTableModel(StructuredTableModel):
    primary_key = 'month'
    columns = [
        TableColumn('month', 'الشهر'),
        TableColumn('incoming', 'الوارد'),
        TableColumn('outgoing', 'الصادر'),
        TableColumn('net', 'الصافي'),
    ]


class DashboardRecentTableModel(StructuredTableModel):
    columns = [
        TableColumn('date', 'التاريخ'),
        TableColumn('company_name', 'الشركة'),
        TableColumn('amount_original', 'المبلغ الأصلي'),
        TableColumn('type', 'الحالة'),
        TableColumn('historical_rate', 'سعر القيد'),
    ]


class ReportTableModel(StructuredTableModel):
    """Dynamic model for report rows where headers vary by report type."""
    def __init__(self, headers: List[str], rows: List[List[Any]]):
        columns = [TableColumn(f'c{i}', header) for i, header in enumerate(headers)]
        data = []
        for idx, row in enumerate(rows, start=1):
            item = {'id': idx}
            for col, value in enumerate(row):
                item[f'c{col}'] = value
            data.append(item)
        super().__init__(data=data, columns=columns, primary_key='id')
