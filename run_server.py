#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
"""

import os
import sys

# إضافة المسار الحالي للـ PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waitress import serve
from flask_server import app

if __name__ == '__main__':
    print("🚀 تشغيل خادم هوى الشام...")
    print("المنفذ: 8000")
    print("العنوان: 0.0.0.0")
    print("لإيقاف الخادم: Ctrl+C")
    try:
        serve(app, host='0.0.0.0', port=8000, threads=4)
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف الخادم.")
    except Exception as e:
        print(f"❌ خطأ: {e}")
