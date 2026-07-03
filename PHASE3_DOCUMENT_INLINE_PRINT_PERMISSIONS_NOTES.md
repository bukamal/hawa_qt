# Phase 3 — Document Inline Printing, Permissions, Currency Ledger Unification

## الهدف
تثبيت مسار الحسابات الجديد داخل Document Shell وتقليل الاعتماد على النوافذ القديمة، مع جعل الحسابات المعروضة والمطبوعة تستخدم نفس مصدر الحقيقة المحاسبي.

## ما تم

### 1. توحيد كشف الشركة مع نظام العملات
تمت إضافة دالة مركزية في:

`services/currency_ledger_service.py`

- `company_ledger_display(records, display_currency=None)`
- `approved_records(records)`

هذه الدالة أصبحت مسؤولة عن:

- استبعاد عمليات `waiting_payment` من الرصيد.
- احترام السعر التاريخي `exchange_rate_to_usd` لكل قيد.
- استخدام المبلغ الأصلي فقط إذا كانت كل قيود الشركة بنفس العملة وكانت هي نفسها عملة العرض.
- التحويل من USD فقط عند اختلاف عملة العرض أو تعدد العملات.
- إنتاج صفوف جاهزة للواجهة والطباعة بنفس الحسابات.

### 2. معاينة الطباعة Inline
تمت إضافة:

`services/print_service.py`
`ui/components/print_preview_panel.py`

وأصبح `CompanyDocument.print_company_report()` يفتح معاينة داخل Inline Panel بدل استدعاء `CompanyDetailsDialog` أو `QPrintPreviewDialog` في مسار الحسابات الجديد.

### 3. صلاحيات مركزية
تمت إضافة:

`services/permission_service.py`
`services/expense_service.py`

المسار الجديد للواجهة صار:

`UI -> ExpenseService -> ExpenseRepository`

بدل أن تكتب الواجهة مباشرة في Repository. هذا يمنع أدوار القراءة فقط من عمليات الإضافة/التعديل/الحذف في مسار Document Shell.

### 4. حماية العملة الأساسية
في الإعدادات:

- تم تثبيت العملة المحاسبية الأساسية على USD.
- بقيت `display_currency` للعرض فقط.
- أضيف تنبيه واضح أن تغيير عملة العرض لا يعيد تسعير القيود القديمة.

### 5. سجل أسعار الصرف داخل الإعدادات
تمت إضافة جدول عرض آخر تعديلات أسعار الصرف في تبويب أسعار الصرف.

### 6. إصلاحات إضافية
- تم جعل `database` و `database.repositories` يستخدمان Lazy Exports لتقليل circular imports بين `currency.py` و `ExpenseRepository`.
- تم تحويل `CustomTableView.print_table()` لاستخدام `PrintService` بدل بناء HTML يدوي مكرر.
- تم ضبط API لإنتاج `waiting_payment` تلقائياً عند مبلغ صفر إذا لم ترسل الحالة صراحة، ومنع المبالغ السالبة.
- تم حذف تذكيرات الدفع المرتبطة عند حذف قيد من API.

## اختبارات تم تنفيذها

- `python -m compileall -q .`
- `pytest -q` مع QtCore QSettings stub داخل بيئة الفحص.
- اختبار Snapshot تاريخي:
  - إدخال 14000 SYP بسعر 14000 = 1 USD.
  - تغيير السعر إلى 15000.
  - تعديل نفس القيد إلى 28000 SYP.
  - بقي السعر التاريخي 14000 وصار amount_base = 2 USD.
- اختبار منع viewer من الكتابة عبر `ExpenseService`.
- اختبار HTML تقرير الشركة وخلوه من بقايا HTML المكسورة.

## لم يتم بعد

- تحويل تقارير الشركات العامة والتقارير المخصصة القديمة إلى Inline بالكامل.
- تحويل المستخدمين والإعدادات إلى Documents مستقلة.
- إزالة Dialogs القديمة نهائياً.
- اختبار Flask API فعلياً داخل بيئة الفحص لأن حزمة Flask غير مثبتة في البيئة الحالية.
