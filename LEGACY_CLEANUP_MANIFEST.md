# Phase 9 — Legacy Cleanup Manifest

هذا الملف يحدد ما بقي من النظام القديم، وما تم عزله، وما لا يجوز حذفه بعد.

## المدخل القديم

`main_window.py` في جذر المشروع كان يحتوي مسار تشغيل كاملًا قديمًا. في Phase 9 تم تحويله إلى غلاف توافق فقط:

```python
from main import main

if __name__ == "__main__":
    main()
```

الهدف: أي اختصار قديم يشغّل `main_window.py` لن يدخل في مسار مختلف عن `main.py`.

## Widgets القديمة المعزولة

المجلد التالي ما زال موجودًا لكنه صار Legacy:

```text
views/widgets/
```

الملفات:

```text
accounts_widget.py
dashboard_widget.py
settings_widget.py
reports_widget.py
users_widget.py
audit_log_widget.py
```

في المسار الرئيسي الجديد، `views/main_window.py` يستخدم:

```text
DashboardShell
AccountingShell
ReportsShell
UsersShell
AuditShell
SettingsShell
```

ولا يستخدم Widgets القديمة مباشرة.

## Dialogs القديمة

ما زالت هذه الملفات موجودة احتياطيًا أو لعدم كسر مسارات قديمة:

```text
views/dialogs/add_edit_expense_dialog.py
views/dialogs/company_details_dialog.py
views/dialogs/user_dialog.py
views/dialogs/change_password_dialog.py
```

الحالة العملية:

- `change_password_dialog.py` ما زال مستخدمًا من `main.py` و`views/main_window.py`، فلا يُحذف الآن.
- `add_edit_expense_dialog.py`, `company_details_dialog.py`, `user_dialog.py` لا ينبغي استخدامها في مسار Document Shell الجديد.
- بعد اختبار Windows، يمكن نقل غير المستخدم منها إلى `legacy/` أو حذفها.

## الفحص الآلي

أضيف سكربت:

```text
scripts/check_project_readiness.py
```

يشغّل:

```bash
python scripts/check_project_readiness.py
```

ويفحص:

- أن `main_window.py` في الجذر غلاف توافق فقط.
- أن المسارات الجديدة لا تستورد `views.widgets`.
- أن المسارات الجديدة لا تستورد Dialogs القديمة الخاصة بالحسابات والمستخدمين.
- أن ملفات Python قابلة للترجمة نحويًا.

## سياسة الحذف لاحقًا

لا نحذف Legacy دفعة واحدة قبل اختبار Windows. الترتيب الصحيح:

1. تشغيل Checklist البصرية.
2. تشغيل `scripts/check_project_readiness.py`.
3. التأكد من أن الحسابات والمستخدمين والتقارير والإعدادات تعمل من Shell الجديد.
4. نقل الملفات القديمة إلى `legacy/` أو حذفها.
5. تشغيل `pytest` و`compileall` بعد كل حذف.

## الملفات التي لا تزال مسموحة مؤقتًا

- `views/login_dialog.py`
- `views/activation_dialog.py`
- `views/dialogs/change_password_dialog.py`

هذه ليست من مسار الحسابات القديم، ويمكن تحويلها لاحقًا في مرحلة Auth Shell.
