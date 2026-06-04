from PyQt5.QtCore import Qt, QEvent, QObject
from PyQt5.QtWidgets import QApplication
from views.frameless_dialog import FramelessDialog

class CenteredDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LeftToRight)  # تغيير حسب الحاجة (LTR/RTl)
        self.resize(500, 400)
        self._parent_move_filter = None
    
    def showEvent(self, event):
        self.center_on_parent()
        # تتبع حركة النافذة الأم
        if self.parent() and not self._parent_move_filter:
            self._parent_move_filter = ParentMoveFilter(self)
            self.parent().installEventFilter(self._parent_move_filter)
        super().showEvent(event)
    
    def center_on_parent(self):
        parent = self.parent()
        if parent and parent.isVisible():
            geo = parent.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = self.screen().geometry()
            self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
    
    def closeEvent(self, event):
        if self._parent_move_filter and self.parent():
            self.parent().removeEventFilter(self._parent_move_filter)
        super().closeEvent(event)

class ParentMoveFilter(QObject):
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Move:
            self.dialog.center_on_parent()
        return super().eventFilter(obj, event)
