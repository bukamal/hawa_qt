# -*- coding: utf-8 -*-
"""Small process/connection service for local Flask server management."""
from __future__ import annotations

import subprocess
import sys
import time
from typing import Dict, Optional

import requests


class ServerService:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None

    def command(self):
        if getattr(sys, "frozen", False):
            return [sys.executable, "--server"]
        return [sys.executable, "run_server.py"]

    def is_process_running(self) -> bool:
        return bool(self.process and self.process.poll() is None)

    def health(self, url: str = "http://localhost:8000", timeout: int = 1) -> Dict:
        try:
            resp = requests.get(f"{url.rstrip('/')}/health", timeout=timeout)
            alive = resp.status_code == 200 and resp.json().get("status") == "alive"
            return {"alive": alive, "status_code": resp.status_code, "message": "alive" if alive else "استجابة غير صالحة"}
        except Exception as exc:
            return {"alive": False, "status_code": None, "message": str(exc)}


    def capabilities(self, url: str = "http://localhost:8000", timeout: int = 2) -> Dict:
        try:
            resp = requests.get(f"{url.rstrip('/')}/api/capabilities", timeout=timeout)
            ok = resp.status_code == 200
            payload = resp.json() if ok else {}
            return {"ok": ok, "status_code": resp.status_code, "payload": payload, "message": "ok" if ok else resp.text[:200]}
        except Exception as exc:
            return {"ok": False, "status_code": None, "payload": {}, "message": str(exc)}

    def start(self) -> Dict:
        if self.is_process_running():
            return {"started": False, "running": True, "message": "الخادم يعمل بالفعل"}
        cmd = self.command()
        if sys.platform == "win32":
            self.process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            self.process = subprocess.Popen(cmd)
        time.sleep(0.5)
        return {"started": True, "running": self.is_process_running(), "message": "تم تشغيل الخادم"}

    def stop(self) -> Dict:
        if not self.is_process_running():
            self.process = None
            return {"stopped": False, "running": False, "message": "الخادم غير قيد التشغيل"}
        self.process.terminate()
        time.sleep(1)
        if self.process.poll() is None:
            self.process.kill()
        self.process = None
        return {"stopped": True, "running": False, "message": "تم إيقاف الخادم"}


server_service = ServerService()
