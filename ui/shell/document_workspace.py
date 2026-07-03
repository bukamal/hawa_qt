# -*- coding: utf-8 -*-
import logging
import traceback

from PyQt5.QtWidgets import QStackedWidget
from PyQt5.QtCore import pyqtSignal

from ui.effects import fade_in
from ui.components.error_view import ErrorView


class DocumentWorkspace(QStackedWidget):
    """Central document host for the new non-dialog UI model."""
    document_changed = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('DocumentWorkspace')
        self._documents = {}
        self._history = []
        self._logger = logging.getLogger(__name__)
        self._last_failed_route = None
        self._last_failed_params = {}
        self._error_view = ErrorView(self)
        self._error_view.retry_requested.connect(self._retry_last_failed)
        self.addWidget(self._error_view)

    def register_document(self, route: str, widget):
        if route in self._documents:
            old = self._documents[route]
            idx = self.indexOf(old)
            if idx >= 0:
                self.removeWidget(old)
        self._documents[route] = widget
        self.addWidget(widget)

    def open_document(self, route: str, **params):
        widget = self._documents.get(route)
        if widget is None:
            self._show_error(route, params, KeyError(f"Unknown document route: {route}"))
            return
        try:
            if hasattr(widget, 'activate'):
                widget.activate(**params)
            self.setCurrentWidget(widget)
            fade_in(widget, duration=130)
            self._history.append((route, dict(params)))
            self.document_changed.emit(route, dict(params))
            self._last_failed_route = None
            self._last_failed_params = {}
        except Exception as exc:
            self._show_error(route, params, exc)

    def _show_error(self, route: str, params: dict, exc: Exception) -> None:
        details = traceback.format_exc()
        self._logger.exception("Failed to open document route %s with params %s", route, params)
        self._last_failed_route = route
        self._last_failed_params = dict(params)
        self._error_view.set_error(
            "تعذر فتح الصفحة",
            f"تعذر فتح المسار: {route}. تم تسجيل التفاصيل في ملف الأخطاء.",
            details,
        )
        self.setCurrentWidget(self._error_view)
        fade_in(self._error_view, duration=130)

    def _retry_last_failed(self):
        if self._last_failed_route:
            self.open_document(self._last_failed_route, **self._last_failed_params)

    def current_route(self):
        current = self.currentWidget()
        for route, widget in self._documents.items():
            if widget is current:
                return route
        return None
