# -*- coding: utf-8 -*-
"""Central audio feedback service.

The service is deliberately fail-safe: a missing QtMultimedia backend, missing
sound file, muted device, or headless test environment must never break a
financial workflow. Audio is optional feedback, not business logic.
"""
from __future__ import annotations

import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from branding import resource_path
from database import SettingsRepository


@dataclass(frozen=True)
class SoundEvent:
    sound_id: str
    filename: str
    category: str
    description: str


SOUND_EVENTS: Dict[str, SoundEvent] = {
    "success": SoundEvent("success", "success.wav", "success", "حفظ/عملية ناجحة"),
    "error": SoundEvent("error", "error.wav", "error", "خطأ أو فشل تحقق"),
    "warning": SoundEvent("warning", "warning.wav", "warning", "تحذير"),
    "delete": SoundEvent("delete", "delete.wav", "warning", "حذف/عملية مدمرة"),
    "notify": SoundEvent("notify", "notify.wav", "notification", "معلومة"),
    "backup_done": SoundEvent("backup_done", "backup_done.wav", "system", "اكتمل النسخ الاحتياطي"),
    "export_done": SoundEvent("export_done", "export_done.wav", "system", "اكتمل التصدير"),
    "login_ok": SoundEvent("login_ok", "login_ok.wav", "security", "دخول ناجح"),
    "login_fail": SoundEvent("login_fail", "login_fail.wav", "security", "دخول خاطئ"),
    "server_on": SoundEvent("server_on", "server_on.wav", "system", "تشغيل الخادم"),
    "server_off": SoundEvent("server_off", "server_off.wav", "system", "إيقاف الخادم"),
    "payment_due": SoundEvent("payment_due", "payment_due.wav", "notification", "تنبيه دفع"),
}

CATEGORY_KEYS = {
    "success": "audio/success_enabled",
    "error": "audio/error_enabled",
    "warning": "audio/warning_enabled",
    "notification": "audio/notification_enabled",
    "system": "audio/system_enabled",
    "security": "audio/security_enabled",
}


class AudioService:
    def __init__(self, repo: Optional[SettingsRepository] = None):
        self.repo = repo or SettingsRepository()
        self._effects = {}
        self._qt_ready = None
        self._lock = threading.RLock()

    def sound_path(self, sound_id: str) -> Path:
        event = SOUND_EVENTS.get(sound_id)
        if not event:
            raise KeyError(f"Unknown sound id: {sound_id}")
        return Path(resource_path("sounds", event.filename))

    def list_sounds(self):
        return [
            {
                "sound_id": event.sound_id,
                "filename": event.filename,
                "category": event.category,
                "description": event.description,
                "path": str(self.sound_path(event.sound_id)),
            }
            for event in SOUND_EVENTS.values()
        ]

    def get_settings(self) -> Dict:
        return {
            "enabled": self._bool("audio/enabled", True),
            "volume": self._int("audio/volume", 35, minimum=0, maximum=100),
            "success_enabled": self._bool(CATEGORY_KEYS["success"], True),
            "error_enabled": self._bool(CATEGORY_KEYS["error"], True),
            "warning_enabled": self._bool(CATEGORY_KEYS["warning"], True),
            "notification_enabled": self._bool(CATEGORY_KEYS["notification"], True),
            "system_enabled": self._bool(CATEGORY_KEYS["system"], True),
            "security_enabled": self._bool(CATEGORY_KEYS["security"], True),
        }

    def save_settings(self, settings: Dict) -> Dict:
        # SettingsService performs admin permission checks; keeping this method
        # permission-free lets non-GUI tests exercise pure audio normalization.
        enabled = bool(settings.get("enabled", True))
        volume = int(settings.get("volume", 35))
        volume = max(0, min(100, volume))
        self.repo.set("audio/enabled", "true" if enabled else "false")
        self.repo.set("audio/volume", str(volume))
        for category, key in CATEGORY_KEYS.items():
            field = f"{category}_enabled"
            self.repo.set(key, "true" if bool(settings.get(field, True)) else "false")
        self.repo.clear_cache()
        return self.get_settings()

    def is_enabled_for(self, sound_id: str) -> bool:
        event = SOUND_EVENTS.get(sound_id)
        if not event:
            return False
        settings = self.get_settings()
        if not settings["enabled"] or settings["volume"] <= 0:
            return False
        category_field = f"{event.category}_enabled"
        return bool(settings.get(category_field, True))

    def play(self, sound_id: str, force: bool = False) -> bool:
        """Play a registered sound.

        Returns True when a playback attempt was made. False means muted,
        disabled, missing resource, or unavailable backend. No exception is
        propagated to callers by design.
        """
        try:
            if not force and not self.is_enabled_for(sound_id):
                return False
            path = self.sound_path(sound_id)
            if not path.exists() or path.stat().st_size <= 0:
                return False
            volume = self.get_settings()["volume"] / 100.0
            return self._play_with_qt(path, volume) or self._play_with_winsound(path)
        except Exception:
            return False

    def play_success(self):
        return self.play("success")

    def play_error(self):
        return self.play("error")

    def play_warning(self):
        return self.play("warning")

    def play_delete(self):
        return self.play("delete")

    def play_notify(self):
        return self.play("notify")

    def play_backup_done(self):
        return self.play("backup_done")

    def play_export_done(self):
        return self.play("export_done")

    def play_login_ok(self):
        return self.play("login_ok")

    def play_login_fail(self):
        return self.play("login_fail")

    def play_server_on(self):
        return self.play("server_on")

    def play_server_off(self):
        return self.play("server_off")

    def play_payment_due(self):
        return self.play("payment_due")

    def _play_with_qt(self, path: Path, volume: float) -> bool:
        if self._qt_ready is False:
            return False
        try:
            from PyQt5.QtCore import QUrl
            from PyQt5.QtMultimedia import QSoundEffect
        except Exception:
            self._qt_ready = False
            return False

        self._qt_ready = True
        key = str(path)
        with self._lock:
            effect = self._effects.get(key)
            if effect is None:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(key))
                self._effects[key] = effect
            effect.setVolume(max(0.0, min(1.0, float(volume))))
            effect.play()
        return True

    def _play_with_winsound(self, path: Path) -> bool:
        if sys.platform != "win32":
            return False
        try:  # pragma: no cover - Windows-only fallback
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        except Exception:
            return False

    def _bool(self, key: str, default: bool) -> bool:
        val = self.repo.get(key, "true" if default else "false")
        return str(val).lower() in {"true", "1", "yes", "on"}

    def _int(self, key: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(self.repo.get(key, str(default)))
        except Exception:
            value = default
        return max(minimum, min(maximum, value))


audio_service = AudioService()
