# -*- coding: utf-8 -*-
"""Global error handling for desktop and command-line entry points."""
from __future__ import annotations

import logging
import sys
import threading
import traceback
from dataclasses import dataclass
from types import TracebackType
from typing import Optional, Type

from app_config import get_error_log_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ErrorReport:
    title: str
    message: str
    technical_details: str
    log_path: str


def build_error_report(exc_type: Type[BaseException], exc: BaseException, tb: Optional[TracebackType]) -> ErrorReport:
    technical = "".join(traceback.format_exception(exc_type, exc, tb))
    return ErrorReport(
        title="خطأ غير متوقع",
        message="حدث خطأ غير متوقع. تم تسجيل التفاصيل في ملف الأخطاء.",
        technical_details=technical,
        log_path=get_error_log_path(),
    )


def log_exception(exc_type: Type[BaseException], exc: BaseException, tb: Optional[TracebackType]) -> ErrorReport:
    report = build_error_report(exc_type, exc, tb)
    logger.error("Unhandled exception\n%s", report.technical_details)
    return report


def _show_gui_error(report: ErrorReport) -> None:
    """Show a minimal GUI message without importing PyQt at module import time."""
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
    except Exception:
        return

    app = QApplication.instance()
    if app is None:
        return
    box = QMessageBox()
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle(report.title)
    box.setText(report.message)
    box.setInformativeText(f"ملف السجل:\n{report.log_path}")
    box.setDetailedText(report.technical_details[-8000:])
    box.exec()


def handle_unhandled_exception(exc_type: Type[BaseException], exc: BaseException, tb: Optional[TracebackType]) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    report = log_exception(exc_type, exc, tb)
    _show_gui_error(report)


def handle_thread_exception(args: threading.ExceptHookArgs) -> None:
    handle_unhandled_exception(args.exc_type, args.exc_value, args.exc_traceback)


def install_exception_hooks() -> None:
    sys.excepthook = handle_unhandled_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = handle_thread_exception
