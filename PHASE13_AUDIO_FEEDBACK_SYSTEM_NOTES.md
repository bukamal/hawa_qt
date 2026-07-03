# Phase 13 — Audio Feedback System

## الهدف
إضافة مؤثرات صوتية قصيرة وهادئة للأحداث المهمة فقط، بدون تحويل التطبيق إلى واجهة مزعجة أو ربط الصوت بمنطق الأعمال.

## الملفات الجديدة

- `services/audio_service.py`
- `resources/sounds/`
- `resources/sounds/SOUND_MANIFEST.md`
- `tests/test_audio_service.py`

## الأصوات المضافة

- `success.wav` — حفظ/عملية ناجحة
- `error.wav` — خطأ أو فشل تحقق
- `warning.wav` — تحذير
- `delete.wav` — حذف/عملية مدمرة
- `notify.wav` — معلومة
- `backup_done.wav` — اكتمال النسخ الاحتياطي
- `export_done.wav` — اكتمال التصدير
- `login_ok.wav` — دخول ناجح
- `login_fail.wav` — دخول خاطئ
- `server_on.wav` — تشغيل الخادم
- `server_off.wav` — إيقاف الخادم
- `payment_due.wav` — تنبيه دفع

## الدمج البرمجي

- `AudioService` مسؤول مركزيًا عن تشغيل الصوت.
- الصوت Fail-safe: أي فشل في QtMultimedia أو ملفات الصوت لا يكسر التطبيق.
- تم ربط الصوت مع Toast، محرر القيود، تسجيل الدخول، التصدير، النسخ الاحتياطي، وتشغيل/إيقاف الخادم.
- تم إضافة صفحة إعدادات صوتية داخل Settings Shell.

## الإعدادات

صفحة جديدة:

- `settings.audio` — `🔊 الصوت`

تدعم:

- تفعيل/إيقاف الصوت
- مستوى الصوت 0–100
- أصوات النجاح
- أصوات الأخطاء
- أصوات التحذير
- أصوات التنبيه
- أصوات النظام
- أصوات الأمان
- زر اختبار الصوت

## Build Windows

تم تحديث `build/windows/hawaa_windows.spec` بإضافة:

- `PyQt5.QtMultimedia`

ومجلد `resources` موجود أصلًا ضمن ملفات PyInstaller، لذلك تدخل ملفات `resources/sounds` تلقائيًا في النسخة المبنية.

## الفحص

تم تحديث `scripts/check_project_readiness.py` ليفحص ملفات WAV والتأكد من ترويسة RIFF/WAVE.

نتيجة الفحص:

```text
OK: no readiness issues detected.
37 passed
```

## القاعدة المهنية

لا يوجد صوت عند كل نقرة أو كل انتقال صفحة. الصوت مخصص للأحداث المهمة فقط حتى يبقى البرنامج مناسبًا لبيئة المكتب.
