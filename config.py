# -*- coding: utf-8 -*-
from PyQt5.QtCore import QSettings

def get_company_info():
    settings = QSettings("Hawaa", "Accounting")
    return {
        'name': settings.value("company/name", "هوى الشام للسياحة والسفر"),
        'address': settings.value("company/address", "المملكة العربية السعودية - الرياض"),
        'phone': settings.value("company/phone", "+966 12 3456789"),
        'email': settings.value("company/email", "info@hawaa.com"),
        'tax_number': settings.value("company/tax_number", ""),
        'logo_path': settings.value("company/logo_path", ""),
    }

def save_company_info(info):
    settings = QSettings("Hawaa", "Accounting")
    settings.setValue("company/name", info.get('name', ''))
    settings.setValue("company/address", info.get('address', ''))
    settings.setValue("company/phone", info.get('phone', ''))
    settings.setValue("company/email", info.get('email', ''))
    settings.setValue("company/tax_number", info.get('tax_number', ''))
    settings.setValue("company/logo_path", info.get('logo_path', ''))
