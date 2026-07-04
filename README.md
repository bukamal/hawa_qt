# Hawaa Accounting

تطبيق حسابات مكتبي مبني بـ PyQt5، تم نقله تدريجيًا إلى بنية:

```text
Document Shell + Inline Panels + Service Layer + Historical Currency Snapshot
```

## التشغيل

```bash
python main.py
```

`main_window.py` في جذر المشروع موجود فقط كغلاف توافق قديم ويستدعي `main.py`.

## الدخول الافتراضي

```text
Username: admin
Password: admin123
```

بعد أول دخول أو عند فقدان كلمة المرور، استخدم أداة إعادة التعيين:

```bash
python scripts/reset_password.py --username admin --password "NewStrong123!"
```

## قاعدة العملات

العملة المحاسبية الأساسية ثابتة:

```text
USD
```

كل قيد يحفظ:

```text
amount_original
currency_original
exchange_rate_to_usd
amount_base
```

تغيير سعر الصرف لاحقًا لا يغيّر القيود القديمة. `display_currency` عملة عرض فقط.

## الفحوصات قبل التسليم

```bash
python scripts/check_project_readiness.py
python -m compileall -q .
PYTHONPATH=. pytest -q
```

ثم نفّذ يدويًا:

```text
WINDOWS_VISUAL_TEST_CHECKLIST.md
```

## وثائق المراحل

- `PHASE1_DOCUMENT_SHELL_CURRENCY_NOTES.md`
- `PHASE2_DOCUMENT_INLINE_ACCOUNTS_NOTES.md`
- `PHASE3_DOCUMENT_INLINE_PRINT_PERMISSIONS_NOTES.md`
- `PHASE4_DOCUMENT_REPORTS_USERS_NOTES.md`
- `PHASE5_SETTINGS_DOCUMENT_SHELL_NOTES.md`
- `PHASE6_DASHBOARD_AUDIT_DOCUMENTS_NOTES.md`
- `PHASE7_LEGACY_CLEANUP_TABLE_MODELS_NOTES.md`
- `PHASE8_INLINE_EDITOR_UX_VALIDATION_NOTES.md`
- `PHASE9_LEGACY_CLEANUP_VISUAL_TEST_NOTES.md`

## ملاحظات مهمة

- لا تعتمد على Widgets القديمة داخل `views/widgets/` في التطوير الجديد.
- لا تستخدم Dialogs الحسابات القديمة في مسار Document Shell.
- `LoginDialog`, `ActivationDialog`, و`ChangePasswordDialog` مسموحة مؤقتًا حتى مرحلة Auth Shell.


## Branding and Windows icons

Phase 10 adds a project-specific branding package under:

```text
resources/branding/
```

Important files:

```text
app.ico              Windows EXE/taskbar icon
installer.ico        Installer icon
project_file.ico     Optional .hawa file association icon
backup_file.ico      Optional backup-file icon
app_logo.png         Splash/sidebar logo
app_symbol.svg       Source symbol
```

The application loads the icon through `branding.py`, which is safe for development and PyInstaller builds.

### Windows build

PyInstaller spec:

```bash
pyinstaller build/windows/hawaa_windows.spec --clean --noconfirm
```

Installer script:

```text
build/windows/hawaa_installer.iss
```

The installer script uses the custom installer icon and can register `.hawa` files with the project-file icon.

### Visual effects

Light effects were added only where they improve interaction clarity:

- Document fade-in
- Inline panel slide
- Toast fade/slide
- Hover/active states

Effects should remain short and functional; avoid heavy blur/glow animations in this accounting UI.

## Phase 11 — Packaging / Logging / Support

### Windows build

```bash
python -m pip install -r requirements-build.txt
python scripts/check_project_readiness.py
python scripts/build_windows.py
```

PyInstaller output:

```text
dist/Hawaa/Hawaa.exe
```

Installer output, when Inno Setup is available:

```text
dist/installer/Hawaa_Setup.exe
```

### Runtime data layout

By default, Windows runtime data is stored outside the installation folder:

```text
%APPDATA%/Hawaa/
  hawaa_data.db
  backups/
  logs/
    app.log
    errors.log
    server.log
  config/
```

Portable mode: create a file named `portable.flag` beside `Hawaa.exe`; data will be stored in `Hawaa/data/` beside the executable.

### Support bundle

```bash
python scripts/collect_support_bundle.py
```

The support bundle excludes the database by default. Use `--include-db` only when you explicitly need to inspect user data.

## Phase 12 — Printing and export finalization

Phase 12 unifies print/export paths around:

```text
services/print_service.py
services/export_service.py
printing/templates/
```

Supported report outputs from the inline preview panel:

```text
Print
PDF
Excel .xlsx
CSV .csv
HTML .html
```

Rules preserved in all exports:

- `amount_base` remains the internal USD accounting source of truth.
- `display_currency` is presentation only.
- Historical exchange-rate snapshots are shown where relevant, especially in company ledgers.
- User-facing reports must not expose internal fields such as `amount_base`.

PyInstaller now includes the whole `printing/` folder so HTML templates are available in packaged builds.

## Phase 13 — المؤثرات الصوتية

تمت إضافة نظام صوت مركزي اختياري داخل `services/audio_service.py` مع ملفات WAV قصيرة داخل `resources/sounds/`.

الأصوات مخصصة للأحداث المهمة فقط: الحفظ، الخطأ، التحذير، الحذف، النسخ الاحتياطي، التصدير، تسجيل الدخول، تشغيل/إيقاف الخادم، وتنبيهات الدفع. يمكن التحكم بها من الإعدادات عبر صفحة `🔊 الصوت`.

الأوامر المهمة:

```bash
python scripts/check_project_readiness.py
PYTHONPATH=. pytest -q
```

## Phase 15 — تجربة التشغيل والتسجيل بهوية المشروع

تم تحديث مرحلة ما قبل الدخول لتستخدم هوية هوى الشام كاملة:

- شاشة تشغيل/انتظار بالشعار ومراحل تحميل واضحة.
- واجهة تفعيل محسنة تعرض حالة الترخيص ومعرّف الجهاز ومسار ملف الترخيص.
- واجهة تسجيل دخول بالشعار وبطاقة دخول موحدة.
- شاشة انتقال بعد تسجيل الدخول قبل فتح الواجهة الرئيسية.

يجب اختبارها على Windows عبر تشغيل:

```bash
python main.py
```

ثم فحص: التفعيل، تسجيل الدخول، شاشة الانتظار، ومسار الترخيص داخل `%APPDATA%/Hawaa/config`.

## Phase 16 — Visual QA fixes

تمت معالجة مشاكل اختبار الصور: شرائط النص البيضاء في Splash/Login، بقاء Splash بالخلفية، خطأ `splash.finish`, مسار `accounts` الإنجليزي، وازدحام ملخص الحسابات. راجع `PHASE16_VISUAL_QA_FIXES_NOTES.md`.

## ربط Android مع Windows عبر QR

من نسخة Phase 27 يمكن ربط تطبيق Android بخادم Windows من داخل:

`الإعدادات > الشبكة > ربط تطبيق Android عبر QR`

الخطوات المختصرة:

1. شغل وضع الخادم على Windows.
2. اضغط `إنشاء QR لربط الهاتف`.
3. امسح QR من Android أو الصق نص QR داخل شاشة الربط.
4. بعد نجاح الربط، سجّل الدخول من Android بحساب مستخدم عادي.

تنبيه أمني: QR لا يحتوي كلمة مرور ولا يسجل الدخول. هو فقط يثبت عنوان الخادم ويتحقق من عقد API ودعم السعر التاريخي للعملات.

