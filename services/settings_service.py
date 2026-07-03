# -*- coding: utf-8 -*-
"""Central settings service for the Document Shell settings pages.

Rules:
- USD remains the accounting/base currency.
- display_currency is presentation only and must not rewrite historical rows.
- exchange-rate changes are persisted through CurrencyManager so history is captured.
- dangerous settings are centralized here instead of being written directly by UI widgets.
"""
from __future__ import annotations

import os
import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from PyQt5.QtCore import QSettings

from app_config import DEFAULT_SERVER_URL
from auth.activation import check_activation, check_network_activation, activate_network
from config import get_company_info, save_company_info
from currency import currency
from database import SettingsRepository
from database.connection import DatabaseConnection, DB_PATH
from services.backup_service import backup_service
from services.audio_service import audio_service
from services.permission_service import permission_service

SUPPORTED_CURRENCIES = ["USD", "SAR", "SYP", "EUR", "GBP", "AED", "QAR", "KWD", "OMR"]
BASE_CURRENCY = "USD"
NETWORK_MODES = {"local": "محلي", "client": "عميل", "server": "خادم"}


class SettingsService:
    def __init__(self, repo: Optional[SettingsRepository] = None):
        self.repo = repo or SettingsRepository()

    # ---------- Currency ----------
    def get_currency_settings(self) -> Dict:
        return {
            "base_currency": BASE_CURRENCY,
            "display_currency": currency.get_display_currency(),
            "decimals": int(self.repo.get("currency_decimals", "2")),
            "number_format": self.repo.get("number_format", "western"),
            "abbreviate_numbers": self.repo.get("abbreviate_numbers", "false").lower() == "true",
            "supported_currencies": list(SUPPORTED_CURRENCIES),
        }

    def list_exchange_rates(self) -> List[Dict]:
        return list(currency.get_all_currencies())

    def list_exchange_rate_history(self, currency_code: str = None, limit: int = 30) -> List[Dict]:
        return list(currency.get_exchange_rate_history(currency_code=currency_code, limit=limit))

    def save_currency_settings(
        self,
        display_currency: str,
        decimals: int,
        number_format: str,
        abbreviate_numbers: bool,
        rates: Iterable[Tuple[str, float]],
    ) -> Dict:
        permission_service.require_admin()
        display_currency = (display_currency or BASE_CURRENCY).strip().upper()
        if display_currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"عملة العرض غير مدعومة: {display_currency}")
        decimals = int(decimals)
        if decimals < 0 or decimals > 2:
            raise ValueError("الخانات العشرية يجب أن تكون بين 0 و 2")
        if number_format not in {"western", "arabic"}:
            raise ValueError("تنسيق الأرقام غير صالح")

        self.repo.set("base_currency", BASE_CURRENCY)
        self.repo.set("display_currency", display_currency)
        self.repo.set("currency_decimals", str(decimals))
        self.repo.set("number_format", number_format)
        self.repo.set("abbreviate_numbers", "true" if abbreviate_numbers else "false")

        changed_rates = []
        for code, rate in rates:
            code = (code or "").strip().upper()
            if code not in SUPPORTED_CURRENCIES:
                raise ValueError(f"عملة غير مدعومة في جدول الأسعار: {code}")
            rate = float(str(rate).replace(",", "").strip())
            if rate <= 0:
                raise ValueError(f"سعر الصرف يجب أن يكون أكبر من صفر للعملة {code}")
            currency.update_rate(code, rate)
            changed_rates.append({"currency_code": code, "rate_to_usd": rate})

        self.repo.clear_cache()
        return {
            "base_currency": BASE_CURRENCY,
            "display_currency": display_currency,
            "changed_rates": changed_rates,
            "note": "عملة العرض لا تعيد تسعير القيود التاريخية؛ كل قيد يحتفظ بسعره التاريخي.",
        }

    def fetch_online_rates(self, payload: Dict) -> Dict[str, float]:
        """Normalize an external rates payload without coupling UI to any API shape."""
        rates = payload.get("rates", {}) if payload else {}
        return {code: float(rates[code]) for code in SUPPORTED_CURRENCIES if code in rates}

    # ---------- Company ----------
    def get_company_info(self) -> Dict:
        return get_company_info()

    def save_company_info(self, info: Dict) -> Dict:
        permission_service.require_admin()
        sanitized = {
            "name": (info.get("name") or "").strip(),
            "address": (info.get("address") or "").strip(),
            "phone": (info.get("phone") or "").strip(),
            "email": (info.get("email") or "").strip(),
            "tax_number": (info.get("tax_number") or "").strip(),
            "logo_path": (info.get("logo_path") or "").strip(),
        }
        save_company_info(sanitized)
        return sanitized

    # ---------- Appearance ----------
    def get_appearance_settings(self) -> Dict:
        return {
            "language": self.repo.get("language", "ar"),
            "theme": self.repo.get("theme", "light"),
            "direction": "rtl" if self.repo.get("language", "ar") == "ar" else "ltr",
        }

    def save_language(self, language: str) -> str:
        permission_service.require_admin()
        if language not in {"ar", "en", "fr"}:
            raise ValueError("لغة غير مدعومة")
        self.repo.set("language", language)
        self.repo.clear_cache()
        return language

    def save_theme(self, theme: str) -> str:
        permission_service.require_admin()
        if theme not in {"light", "dark"}:
            raise ValueError("ثيم غير مدعوم")
        self.repo.set("theme", theme)
        self.repo.clear_cache()
        try:
            from theme_manager import ThemeManager
            ThemeManager.apply_theme(theme)
        except Exception:
            # Service-level tests may run without QtWidgets; UI will apply the theme when available.
            pass
        return theme


    # ---------- Audio Feedback ----------
    def get_audio_settings(self) -> Dict:
        return audio_service.get_settings()

    def save_audio_settings(self, settings: Dict) -> Dict:
        permission_service.require_admin()
        return audio_service.save_settings(settings or {})

    def list_audio_sounds(self) -> List[Dict]:
        return audio_service.list_sounds()

    def test_audio_sound(self, sound_id: str = "success") -> bool:
        # Testing a sound is a UI convenience, not a persistent setting change.
        return audio_service.play(sound_id or "success", force=True)

    # ---------- Network ----------
    def _qsettings(self) -> QSettings:
        return QSettings("Hawaa", "Accounting")

    def get_network_settings(self) -> Dict:
        qs = self._qsettings()
        return {
            "mode": qs.value("network/mode", "local"),
            "server_url": qs.value("network/server_url", DEFAULT_SERVER_URL),
            "network_license": self.get_network_license_status(),
        }

    def save_network_settings(self, mode: str, server_url: str) -> Dict:
        permission_service.require_admin()
        if mode not in NETWORK_MODES:
            raise ValueError("وضع الشبكة غير صالح")
        server_url = (server_url or DEFAULT_SERVER_URL).strip()
        if mode == "client" and not (server_url.startswith("http://") or server_url.startswith("https://")):
            server_url = "http://" + server_url
        qs = self._qsettings()
        qs.setValue("network/mode", mode)
        qs.setValue("network/server_url", server_url)
        return {"mode": mode, "server_url": server_url, "requires_restart": True}

    def get_network_license_status(self) -> Dict:
        valid, msg = check_network_activation()
        return {"valid": bool(valid), "message": msg or "ميزة الشبكة مفعلة"}

    def activate_network(self, key: str) -> Dict:
        permission_service.require_admin()
        ok, msg = activate_network((key or "").strip())
        return {"valid": bool(ok), "message": msg or "تم تفعيل الشبكة"}

    # ---------- Backup ----------
    def get_backup_settings(self) -> Dict:
        qs = self._qsettings()
        return {
            "enabled": str(qs.value("backup/enabled", "false")).lower() in {"true", "1", "yes"},
            "interval_hours": int(qs.value("backup/interval_hours", 6)),
            "folder": qs.value("backup/folder", ""),
            "remote": DatabaseConnection().is_remote(),
        }

    def save_backup_settings(self, enabled: bool, interval_hours: int, folder: str) -> Dict:
        permission_service.require_admin()
        if DatabaseConnection().is_remote():
            raise RuntimeError("لا يمكن حفظ إعدادات النسخ الاحتياطي في وضع العميل")
        interval_hours = int(interval_hours)
        if interval_hours < 1 or interval_hours > 720:
            raise ValueError("فترة النسخ الاحتياطي يجب أن تكون بين 1 و 720 ساعة")
        qs = self._qsettings()
        qs.setValue("backup/enabled", bool(enabled))
        qs.setValue("backup/interval_hours", interval_hours)
        qs.setValue("backup/folder", (folder or "").strip())
        return self.get_backup_settings()

    def create_backup_now(self, folder: str) -> str:
        permission_service.require_admin()
        if DatabaseConnection().is_remote():
            raise RuntimeError("لا يمكن إنشاء نسخة احتياطية من جهاز عميل")
        folder = (folder or "").strip()
        if not folder:
            raise ValueError("يجب تحديد مجلد النسخ الاحتياطي")
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(folder, f"hawaa_backup_{timestamp}.db")
        return backup_service.create_backup(DB_PATH, backup_path)

    def export_database(self, target_path: str) -> str:
        permission_service.require_admin()
        if DatabaseConnection().is_remote():
            raise RuntimeError("لا يمكن تصدير قاعدة البيانات في وضع العميل")
        if not target_path:
            raise ValueError("مسار التصدير مطلوب")
        return backup_service.create_backup(DB_PATH, target_path)

    def import_database(self, source_path: str) -> str:
        permission_service.require_admin()
        if DatabaseConnection().is_remote():
            raise RuntimeError("لا يمكن استيراد قاعدة البيانات في وضع العميل")
        if not source_path:
            raise ValueError("مسار النسخة الاحتياطية مطلوب")
        db = DatabaseConnection()
        db.close()
        return backup_service.restore_backup(source_path, DB_PATH)

    # ---------- License ----------
    def get_license_status(self) -> Dict:
        valid, msg = check_activation()
        return {"valid": bool(valid), "message": msg or "الترخيص ساري"}


settings_service = SettingsService()
