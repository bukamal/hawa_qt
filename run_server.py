#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""

import os
import sys
import logging

# إضافة المسار الحالي للـ PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waitress import serve
from logging_config import setup_logging
from flask_server import app
from services.server_runtime import write_server_pid, clear_server_pid


def close_runtime_resources():
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.close_global()
    except Exception:
        logging.getLogger(__name__).exception("Failed to close runtime database resources")

if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("تشغيل خادم هوى الشام")
    logger.info("المنفذ: 8000")
    logger.info("العنوان: 0.0.0.0")
    logger.info("لإيقاف الخادم: Ctrl+C")
    write_server_pid()
    try:
        serve(app, host='0.0.0.0', port=8000, threads=4)
    except KeyboardInterrupt:
        logger.info("تم إيقاف الخادم")
    except Exception as e:
        logger.exception("خطأ في الخادم: %s", e)
    finally:
        clear_server_pid(os.getpid())
        close_runtime_resources()
