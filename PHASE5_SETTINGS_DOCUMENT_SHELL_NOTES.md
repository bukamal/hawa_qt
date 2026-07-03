# Phase 5 — Settings Document Shell

## الهدف
تحويل الإعدادات من Widget تبويبي قديم إلى Document Shell مقسّم حسب مناطق الخطر: العملات، النسخ الاحتياطي، الشبكة، بيانات الشركة، المظهر، والترخيص.

## ما تغيّر

- أضيفت `services/settings_service.py` لتجميع عمليات الإعدادات الحساسة في طبقة خدمة واحدة.
- أضيفت `services/server_service.py` لإدارة تشغيل/إيقاف/فحص خادم Flask المحلي دون تكرار المنطق داخل الواجهة.
- أضيفت `ui/shell/settings_shell.py` وربطت داخل `views/main_window.py` بدل `SettingsWidget` في المسار الرئيسي.
- أضيفت `ui/documents/settings_documents.py` وفيها:
  - `CurrencySettingsDocument`
  - `BackupSettingsDocument`
  - `NetworkSettingsDocument`
  - `CompanySettingsDocument`
  - `AppearanceSettingsDocument`
  - `LicenseSettingsDocument`

## قاعدة العملات المثبتة

- `base_currency` يبقى دائمًا `USD`.
- `display_currency` للعرض فقط.
- أسعار الصرف تحفظ عبر `CurrencyManager.update_rate()` حتى يتم تسجيل `exchange_rate_history`.
- تغيير عملة العرض أو السعر الحالي لا يغير قيودًا تاريخية محفوظة سابقًا.

## الصلاحيات

كل عمليات الحفظ الحساسة في الإعدادات تمر عبر `SettingsService` وتحتاج دور `admin`:

- تغيير العملات والأسعار.
- تغيير النسخ الاحتياطي.
- تغيير الشبكة.
- تغيير بيانات الشركة.
- تغيير اللغة/الثيم.
- تفعيل الشبكة.

هذا يمنع الاكتفاء بإخفاء الأزرار في الواجهة.

## النسخ الاحتياطي

إنشاء النسخ والتصدير والاستيراد يمر عبر `BackupService` الذي يستخدم SQLite Backup API بدل نسخ ملف DB مباشرة، لحماية قواعد SQLite التي تعمل بـ WAL.

## الاختبارات

تمت إضافة `tests/test_settings_service.py`:

- تثبيت أن المدير يستطيع تغيير عملة العرض والأسعار مع بقاء العملة الأساسية USD.
- تثبيت أن سجل أسعار الصرف يكتب عند تغيير السعر.
- تثبيت أن viewer لا يستطيع تغيير إعدادات العملات.

## نتيجة الفحص

- `python -m compileall -q .` نجح.
- `PYTHONPATH=. pytest -q` نجح: 9 اختبارات.

## المتبقي بعد Phase 5

- تحويل Dashboard إلى `DashboardDocument`.
- تحويل Audit Log إلى `AuditDocument`.
- تنظيف Dialogs القديمة تدريجيًا.
- استبدال `GenericTableModel` بنماذج متخصصة.
- تشغيل اختبار بصري على Windows للتحقق من RTL/Inline/شفافية اللوحات.
