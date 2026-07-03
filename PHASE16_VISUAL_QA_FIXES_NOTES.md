# Phase 16 — Visual QA Fixes From Windows Screenshots

هذه المرحلة تعالج المشاكل الظاهرة في صور الاختبار البصري على Windows/Linux Desktop بعد Phase 15.

## المشاكل التي ظهرت من الصور

1. شاشة الانتظار/Splash تعرض النصوص كشرائط بيضاء بدل نصوص مقروءة.
2. واجهة تسجيل الدخول تحمل الشعار، لكنها تعاني من تزاحم/تداخل في حقل كلمة المرور وخيارات اللغة/تذكر المستخدم.
3. بعد فتح الواجهة الرئيسية تبقى شاشة Splash بالخلفية، ثم يظهر خطأ من `views/splash_screen.py` عند انتهاء Animation.
4. شريط المسار داخل Document Shell يعرض `accounts` بالإنجليزية بدل العربية.
5. صفحة الحسابات تعرض ملخصًا طويلًا في سطر واحد، ما يسبب قصّ النص أو ازدحامه.

## الإصلاحات

### 1. إصلاح شرائط النص البيضاء

تم تعديل `theme_manager.py`:

- لم يعد الـ Theme يفرض `background-color` على كل `QWidget`.
- أضيفت قاعدة شفافية عامة لـ `QLabel`, `QCheckBox`, `QRadioButton`.

سبب المشكلة: قاعدة عامة مثل `QWidget { background-color: white; }` تؤثر على `QLabel` داخل Splash/Login فتظهر ككتل بيضاء فوق الخلفية.

### 2. إصلاح Splash Finish Crash

تم تعديل `views/splash_screen.py`:

- استبدال `lambda: super().finish(main_window)` باستدعاء صريح آمن: `QSplashScreen.finish(self, main_window)`.
- إضافة guard لمنع تنفيذ finish مرتين.
- إضافة safety timer حتى لا يبقى Splash عالقًا إذا لم تصل إشارة انتهاء الحركة.

### 3. تحسين Login Layout

تم تعديل `views/login_dialog.py`:

- زيادة حجم نافذة تسجيل الدخول قليلًا.
- تصغير شعار الدخول قليلًا لتقليل الضغط الرأسي.
- ضبط ارتفاع حقل كلمة المرور وحاويته.
- نقل خيارات اللغة/تذكر المستخدم إلى حاوية مستقلة بارتفاع واضح.
- جعل Labels وخلفيات العناصر شفافة.

### 4. تعريب Breadcrumb

تم تعديل `ui/shell/app_shell.py`:

- إضافة `ROUTE_TITLES` للمسارات.
- `accounts` تظهر الآن `الحسابات`.
- صفحة الشركة تظهر `الحسابات / اسم الشركة`.

### 5. تحسين ملخص الحسابات

تم تعديل `ui/documents/accounts_document.py` و `services/accounts_service.py`:

- استبدال نص الملخص الطويل بشريط Metrics مقسم.
- تقصير نص `subtitle` إلى: `الأساس: USD | العرض: <currency>`.
- إبقاء مبدأ عدم إعادة تسعير القيود التاريخية داخل الخدمة بدون حشره في شريط ضيق.

## الاختبارات

تمت إضافة:

- `tests/test_phase16_visual_qa_fixes.py`

وتشغيل:

```bash
python scripts/check_project_readiness.py
python -m compileall -q .
PYTHONPATH=. pytest -q
```

النتيجة:

```text
OK: no readiness issues detected.
46 passed
```

## المطلوب اختباره بصريًا مجددًا

1. هل تظهر نصوص Splash بدل الشرائط البيضاء؟
2. هل تختفي شاشة Splash بعد فتح MainWindow؟
3. هل لم يعد يظهر خطأ `views/splash_screen.py` بعد الدخول؟
4. هل حقل كلمة المرور في Login لم يعد يتداخل مع اللغة/تذكر المستخدم؟
5. هل Breadcrumb أصبح عربيًا؟
6. هل شريط ملخص الحسابات لم يعد مقصوصًا؟
