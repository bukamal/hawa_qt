from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Dict, Any, Optional

class GenericTableModel(QAbstractTableModel):
    def __init__(self, data: List[Dict], headers: List[str], key_fields: List[str] = None, data_keys: List[str] = None):
        """
        نموذج جدول عام
        :param data: قائمة القواميس (البيانات)
        :param headers: العناوين التي ستظهر في الواجهة
        :param key_fields: الحقول التي تمثل المفاتيح الأساسية (للتحديد)
        :param data_keys: مفاتيح البيانات الفعلية (إذا كانت مختلفة عن headers)
        """
        super().__init__()
        self._data = data
        self._headers = headers
        self._key_fields = key_fields or []
        # إذا لم يتم تحديد data_keys، نستخدم headers كمفاتيح (للتوافق مع الكود القديم)
        self._data_keys = data_keys if data_keys is not None else headers

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._data):
            return None
        record = self._data[row]
        # استخدام مفتاح البيانات الفعلي
        key = self._data_keys[col]
        value = record.get(key, '')
        return str(value) if value is not None else ''

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        row = index.row()
        col = index.column()
        if row >= len(self._data):
            return False
        key = self._data_keys[col]
        self._data[row][key] = value
        self.dataChanged.emit(index, index)
        return True

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
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
