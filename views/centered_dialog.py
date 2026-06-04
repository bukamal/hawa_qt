from PyQt5.QtCore import Qt, QEvent, QObject
from views.frameless_dialog import FramelessDialog

class CenteredDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LeftToRight)
        self.resize(500, 400)
        self._parent_move_filter = None
    
    def showEvent(self, event):
        super().showEvent(event)
        if self.parent() and not self._parent_move_filter:
            self._parent_move_filter = ParentMoveFilter(self)
            self.parent().installEventFilter(self._parent_move_filter)
    
    def closeEvent(self, event):
        if self._parent_move_filter and self.parent():
            self.parent().removeEventFilter(self._parent_move_filter)
            self._parent_move_filter = None
        super().closeEvent(event)

class ParentMoveFilter(QObject):
    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Move:
            try:
                if self.dialog and self.dialog.isVisible():
                    self.dialog._center_on_parent()
            except RuntimeError:
                pass
        return super().eventFilter(obj, event)

