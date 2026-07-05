# -*- coding: utf-8 -*-
"""Small process/connection service for local Flask server management."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Dict, Optional

import requests

from services.server_runtime import (
    port_from_url,
    stop_pidfile_server,
    stop_port_server,
    write_server_pid,
)


class ServerService:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None

    def command(self):
        if getattr(sys, "frozen", False):
            return [sys.executable, "--server"]
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return [sys.executable, os.path.join(root, "run_server.py")]

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
        try:
            # Keep a parent-side PID reference as an immediate fallback.  The child
            # process also writes its own PID when it enters server mode.
            write_server_pid(self.process.pid)
        except Exception:
            pass
        time.sleep(0.5)
        return {"started": True, "running": self.is_process_running(), "message": "تم تشغيل الخادم"}

    def stop(self, url: str = "http://localhost:8000") -> Dict:
        """Stop the local server even if the settings page lost the Popen handle.

        The old implementation only stopped ``self.process``.  That fails when the
        server was started by main.py during application startup, because the
        rebuilt settings document has no subprocess handle.  This method now tries:
        1. the in-memory Popen handle,
        2. the persistent PID file,
        3. the listener owning the configured port, if it looks like Hawaa.
        """
        messages = []
        stopped_any = False

        if self.is_process_running():
            try:
                self.process.terminate()
                time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
                stopped_any = True
                messages.append("تم إيقاف الخادم من جلسة التطبيق")
            finally:
                self.process = None

        pid_result = stop_pidfile_server(timeout=5)
        if pid_result.get("attempted"):
            messages.append(pid_result.get("message", ""))
            stopped_any = stopped_any or bool(pid_result.get("stopped"))

        # If the health endpoint is still alive, the process may be a stale server
        # started by a previous version without a PID file.  Stop the Hawaa process
        # that owns the port.
        port = port_from_url(url, default_port=8000)
        if self.health(url, timeout=1).get("alive"):
            port_result = stop_port_server(port=port, timeout=5, hawaa_only=True)
            if port_result.get("attempted"):
                messages.append(port_result.get("message", ""))
                stopped_any = stopped_any or bool(port_result.get("stopped"))

        running = self.health(url, timeout=1).get("alive")
        if not running:
            return {
                "stopped": stopped_any,
                "running": False,
                "message": "تم إيقاف الخادم" if stopped_any else "الخادم غير قيد التشغيل",
                "details": " | ".join(m for m in messages if m),
            }
        return {
            "stopped": False,
            "running": True,
            "message": "تعذر إيقاف الخادم؛ ما زال المنفذ يستجيب",
            "details": " | ".join(m for m in messages if m),
        }


server_service = ServerService()
