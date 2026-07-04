# Phase 28 — Windows Network Settings UI + QR IP Selection Fix

## الهدف
إصلاح صفحة إعدادات الشبكة بعد اختبار Windows الفعلي، خصوصًا قسم ربط Android عبر QR.

## المشاكل التي ظهرت بصريًا
- عنوان الخادم في إعدادات الشبكة كان `192.168.x.x` بينما QR استخدم عنوانًا مختلفًا مثل `26.26.26.1` من واجهة VPN/افتراضية.
- QR كان مضغوطًا ومتداخلًا مع نص QR الطويل والأزرار.
- تاريخ انتهاء الرمز كان يظهر كـ ISO خام وغير مفهوم في RTL.
- نص QR كان ظاهرًا دائمًا ويشوّه الصفحة.
- أزرار الربط تحتاج صياغة عربية أوضح.

## ما تم إصلاحه
- إضافة اكتشاف LAN IPv4 آمن داخل `services/mobile_pairing_service.py`.
- استبعاد العناوين غير المناسبة للهاتف: localhost, loopback, link-local, public/VPN-like addresses.
- إضافة `server_url_options()` لعرض خيارات LAN قابلة للاختيار داخل الواجهة.
- جعل QR يستخدم العنوان المختار من الواجهة، وليس IP تلقائيًا من النظام.
- إضافة ComboBox لاختيار عنوان الربط.
- إضافة زر تحديث عناوين الشبكة.
- إخفاء نص الربط المتقدم افتراضيًا.
- إضافة زر “إظهار نص الربط المتقدم”.
- تكبير مساحة QR إلى 260x260 ومنع التداخل.
- إضافة عدّاد انتهاء بصيغة `MM:SS` بدل التاريخ الخام.
- منع إنشاء QR إذا كان العنوان `localhost` أو `127.0.0.1`.
- إضافة زر مسح الرمز.

## الملفات المعدلة
- `services/mobile_pairing_service.py`
- `ui/documents/settings_documents.py`
- `tests/test_mobile_pairing_service.py`
- `README.md`
- `WINDOWS_VISUAL_TEST_CHECKLIST.md`

## الفحص
تم تشغيل:

```bash
python3 scripts/check_project_readiness.py
python3 -m compileall -q .
PYTHONPATH=. pytest -q
```

النتيجة:

```text
OK: no readiness issues detected.
53 passed
```

## ملاحظة مهمة
الـ QR لا يحتوي كلمة مرور ولا JWT. هو يحتوي رمز ربط مؤقت فقط، وبعد الربط يجب تسجيل الدخول من Android باسم مستخدم وكلمة مرور.
