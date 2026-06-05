from PyQt5.QtCore import Qt, QEvent, QObject
from views.frameless_dialog import FramelessDialog

class CenteredDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # لا نغير الاتجاه هنا، نتركه للفئة الأساسية (RTL)
        self.resize(500, 400)
        self._parent_move_filter = None
        if self.parent():
            self._install_parent_filter()
    
    def _install_parent_filter(self):
        if self._parent_move_filter is not None:
            return
        self._parent_move_filter = ParentMoveFilter(self)
        self.parent().installEventFilter(self._parent_move_filter)
    
    def showEvent(self, event):
        super().showEvent(event)
        if self.parent() and not self._parent_move_filter:
            self._install_parent_filter()
        self._center_on_main_window()
    
    def closeEvent(self, event):
        if self._parent_move_filter and self.parent():
            self.parent().removeEventFilter(self._parent_move_filter)
            self._parent_move_filter = None
        super().closeEvent(event)

class ParentMoveFilter(QObject):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Move:
            try:
                if self.dialog and self.dialog.isVisible():
                    self.dialog._center_on_main_window()
            except RuntimeError:
                pass
        return super().eventFilter(obj, event)
