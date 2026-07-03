# استعادة كلمة المرور المحلية

إذا تم تغيير كلمة مرور المدير ونسيانها، لا يمكن استرجاعها لأنها مخزنة كـ PBKDF2 hash. الحل الصحيح هو إعادة تعيينها محليًا.

## الأمر

```bash
python scripts/reset_password.py --username admin --password "NewStrong123!"
```

إذا كانت قاعدة البيانات في مسار مختلف:

```bash
python scripts/reset_password.py --db "C:\Users\USER\AppData\Roaming\Hawaa\hawaa_data.db" --username admin --password "NewStrong123!"
```

الأداة تنشئ نسخة احتياطية من قاعدة البيانات قبل التعديل، وتفعّل `force_password_change` إن كان العمود موجودًا.
