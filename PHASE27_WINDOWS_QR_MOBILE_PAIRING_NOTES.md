# Phase 27 — Windows QR Mobile Pairing

## الهدف
إضافة دعم ربط تطبيق Android مع خادم Windows عبر QR/نص QR، مع إبقاء تسجيل الدخول منفصلًا عن الربط.

## القاعدة الأمنية
- QR لا يحتوي كلمة مرور.
- QR لا يحتوي JWT أو Token دائم.
- QR يحتوي `pairing_token` مؤقتًا فقط.
- رمز الربط صالح لمدة قصيرة، ويستخدم مرة واحدة.
- Android يجب أن يسجل الدخول بعد نجاح الربط.

## الملفات الجديدة
- `services/api_contract.py`
- `services/mobile_pairing_service.py`
- `tests/test_mobile_pairing_service.py`

## تحديثات Windows Server
أضيفت endpoints إلى `flask_server.py`:

- `GET /api/capabilities`
- `POST /api/mobile/pairing-token`
- `POST /api/mobile/pair`

`/api/capabilities` يعلن دعم الخادم لعقد Android الحديث:

- `api_contract_version = 2026.07.mobile-v1`
- `currency_contract = historic-currency-snapshot-v1`
- `supports_amount_base = true`
- `supports_exchange_rate_history = true`
- `supports_mobile_pairing = true`

## تحديثات واجهة Windows
داخل:

`الإعدادات > الشبكة`

أضيف قسم:

`ربط تطبيق Android عبر QR`

يعرض:
- عنوان الخادم المحلي عبر LAN IP.
- تاريخ انتهاء الرمز.
- صورة QR إذا كانت مكتبة `qrcode` متوفرة.
- نص QR كخطة بديلة.
- زر نسخ نص QR.
- زر نسخ عنوان الخادم.

## Build
تمت إضافة `qrcode[pil]` إلى `requirements.txt` و `requirements-build.txt`.

كما تمت إضافة hidden imports إلى PyInstaller spec:

- `qrcode`
- `PIL.Image`

## الاختبارات
تم تشغيل:

```bash
python3 scripts/check_project_readiness.py
python3 -m compileall -q .
PYTHONPATH=. pytest -q
```

النتيجة:

```text
OK: no readiness issues detected.
50 passed
```

## طريقة الاختبار اليدوي
1. شغل Windows في وضع Server.
2. افتح `الإعدادات > الشبكة`.
3. اضغط `إنشاء QR لربط الهاتف`.
4. من Android افتح ربط QR والصق النص أو امسح الكود.
5. تحقق أن Android يحفظ `server_url` ثم يطلب تسجيل الدخول.
