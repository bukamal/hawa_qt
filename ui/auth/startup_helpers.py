# -*- coding: utf-8 -*-
"""Helpers for branded startup/status messages.

Kept dependency-light so readiness tests can inspect the startup flow without
executing PyQt widgets.
"""
from __future__ import annotations

STARTUP_STEPS = (
    (8, "تهيئة المسارات وملفات السجل..."),
    (18, "تحميل الهوية البصرية..."),
    (30, "فحص قاعدة البيانات وتطبيق التحديثات..."),
    (44, "فحص الترخيص..."),
    (58, "تحميل الإعدادات..."),
    (68, "انتظار تسجيل الدخول..."),
    (82, "تحميل صلاحيات المستخدم..."),
    (92, "تجهيز الواجهة الرئيسية..."),
)

POST_LOGIN_STEPS = (
    (74, "تحميل صلاحيات المستخدم..."),
    (82, "تحميل لوحة التحكم..."),
    (90, "تجهيز الحسابات والتقارير..."),
    (96, "فتح الواجهة الرئيسية..."),
)


def describe_post_login_message(username: str | None) -> str:
    username = (username or "المستخدم").strip() or "المستخدم"
    return f"مرحبًا، {username} — جارٍ تجهيز مساحة العمل..."
