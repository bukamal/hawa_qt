# Phase 11 — Packaging, Logging, Error Boundary

## الهدف
تجهيز المشروع كنسخة Windows قابلة للتشخيص والدعم، وليس فقط نسخة تعمل من السورس.

## ما أُضيف

- `app_config.py` أصبح يدير مسارات runtime بشكل واضح:
  - `%APPDATA%/Hawaa/hawaa_data.db`
  - `%APPDATA%/Hawaa/logs/`
  - `%APPDATA%/Hawaa/backups/`
  - `%APPDATA%/Hawaa/config/`
  - دعم `HAWAA_DATA_DIR`
  - دعم `portable.flag`

- `logging_config.py` أصبح ينشئ:
  - `logs/app.log`
  - `logs/errors.log`
  - `logs/server.log` في وضع الخادم

- `error_handling.py` أضاف hooks عامة لـ:
  - `sys.excepthook`
  - `threading.excepthook`

- `ui/components/error_view.py` أضاف Error View داخل Document Shell عند فشل فتح مستند.

- `ui/shell/document_workspace.py` لم يعد يترك خطأ المستند يسقط الواجهة؛ يعرض صفحة خطأ Inline مع زر إعادة المحاولة.

- `scripts/build_windows.py` أصبح مسار Build موحدًا:
  - readiness check
  - pytest
  - PyInstaller
  - Inno Setup عند توفر ISCC

- `scripts/collect_support_bundle.py` يجمع Bundle دعم بدون قاعدة البيانات افتراضيًا.

- `build/windows/README.md` يوثق خطوات Build وPortable mode.

## قاعدة البيانات والخصوصية
Support bundle لا يضم قاعدة البيانات إلا إذا استُخدم `--include-db` صراحة.

## الاختبارات
أضيفت اختبارات لـ:
- مسارات runtime
- إنشاء ملفات log
- ErrorReport
- Support bundle
- ملفات packaging/readiness

