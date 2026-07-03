# Phase 9 — Legacy Cleanup + Visual Test Preparation

## الهدف

تثبيت مسار التشغيل الجديد، عزل بقايا الواجهة القديمة، وتجهيز المشروع لاختبار Windows البصري قبل الانتقال إلى Build.

## التغييرات

### 1. توحيد مدخل التشغيل

تم تحويل `main_window.py` في جذر المشروع إلى غلاف توافق فقط يستدعي `main.main()`.

السبب: كان هناك مساران لتشغيل التطبيق، أحدهما يتجاوز منطق الشبكة والترخيص والنسخ الاحتياطي. هذا خطر عند بناء نسخة Windows.

### 2. إزالة استدعاء قديم للإعدادات

تم حذف الدالة غير المستخدمة `open_network_settings()` من `main.py` لأنها كانت تستورد `SettingsWidget` القديم. المسار الرئيسي يستخدم الآن `SettingsShell`.

### 3. إصلاح logging في النسخ الاحتياطي الدوري

تم إصلاح استخدام متغير `logger` غير محلي داخل `start_periodic_backup()` باستبداله بـ `logging.getLogger(__name__)`.

### 4. إضافة فحص جاهزية آلي

أضيف:

```text
scripts/check_project_readiness.py
```

ويكشف الرجوع غير المقصود إلى Legacy imports.

### 5. إضافة Checklist اختبار Windows

أضيف:

```text
WINDOWS_VISUAL_TEST_CHECKLIST.md
```

وهو مطلوب قبل Phase 10 / Build.

### 6. إضافة Manifest للـ Legacy

أضيف:

```text
LEGACY_CLEANUP_MANIFEST.md
```

يوضح ما هو Legacy، وما لا يجوز حذفه بعد، وما يمكن تنظيفه لاحقًا.

## الاختبارات

تم تشغيل:

```bash
python scripts/check_project_readiness.py
python -m compileall -q .
PYTHONPATH=. pytest -q
```

النتيجة:

```text
24 passed
```

## ملاحظة مهمة

لم يتم حذف Widgets/Dialogs القديمة جذريًا في هذه المرحلة، لأن الحذف النهائي يجب أن يأتي بعد اختبار Windows بصريًا. الهدف الآن هو منع المسار الجديد من الاعتماد عليها، وليس المخاطرة بكسر ملفات قديمة قبل التأكد.
