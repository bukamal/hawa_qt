# -*- coding: utf-8 -*-
"""Runtime helpers for managing the bundled local Waitress server.

The desktop UI may start the server in more than one way:
- main.py can spawn ``main.py --server`` when the saved mode is ``server``.
- Settings > Network can start ``run_server.py`` or ``main.py --server``.

Keeping only a ``subprocess.Popen`` object in memory is not enough, because the
settings page may be rebuilt later and lose the process handle.  This module
keeps a small PID file in the writable config directory and provides conservative
fallbacks for stopping a stale server that still owns the configured port.
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from app_config import get_config_dir

PID_FILE_NAME = "hawaa_server.pid"


def server_pid_path() -> Path:
    return get_config_dir() / PID_FILE_NAME


def write_server_pid(pid: Optional[int] = None) -> Path:
    path = server_pid_path()
    path.write_text(str(int(pid or os.getpid())), encoding="utf-8")
    return path


def read_server_pid() -> Optional[int]:
    path = server_pid_path()
    try:
        text = path.read_text(encoding="utf-8").strip()
        return int(text) if text else None
    except Exception:
        return None


def clear_server_pid(pid: Optional[int] = None) -> None:
    path = server_pid_path()
    try:
        if pid is not None and read_server_pid() not in {None, int(pid)}:
            return
        if path.exists():
            path.unlink()
    except Exception:
        pass


def is_pid_running(pid: Optional[int]) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        # Signal 0 does not terminate the process; it only probes existence.
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except Exception:
        return False


def _terminate_windows_pid(pid: int, timeout: float = 5.0) -> bool:
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_pid_running(pid):
            return True
        time.sleep(0.1)
    return not is_pid_running(pid)


def terminate_pid(pid: int, timeout: float = 5.0) -> bool:
    """Terminate a process by PID and wait briefly.

    Returns True if the process is no longer running after the attempt.
    """
    if not is_pid_running(pid):
        return True
    if os.name == "nt":
        return _terminate_windows_pid(pid, timeout=timeout)

    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_pid_running(pid):
            return True
        time.sleep(0.1)
    if is_pid_running(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
    deadline = time.time() + 1.5
    while time.time() < deadline:
        if not is_pid_running(pid):
            return True
        time.sleep(0.1)
    return not is_pid_running(pid)


def port_from_url(url: str, default_port: int = 8000) -> int:
    try:
        parsed = urlparse(url if "://" in url else "http://" + url)
        return int(parsed.port or default_port)
    except Exception:
        return default_port


def _cmdline_for_pid(pid: int) -> str:
    if pid <= 0:
        return ""
    if os.name != "nt":
        try:
            data = Path(f"/proc/{pid}/cmdline").read_bytes()
            return data.replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""
    try:
        result = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/value"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
            check=False,
        )
        return result.stdout or ""
    except Exception:
        return ""


def _looks_like_hawaa_server(pid: int) -> bool:
    cmdline = _cmdline_for_pid(pid).lower()
    if not cmdline:
        # If we cannot inspect the process, do not kill it unless it came from a PID file.
        return False
    needles = ("hawaa", "main.py --server", "run_server.py", "flask_server.py", "waitress")
    return any(token in cmdline for token in needles)


def listening_pids_for_port(port: int) -> List[int]:
    """Best-effort discovery of local processes listening on a TCP port."""
    pids: set[int] = set()
    if os.name != "nt":
        commands = [
            ["lsof", "-ti", f"tcp:{port}"],
            ["fuser", f"{port}/tcp"],
        ]
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=2,
                    check=False,
                )
                for part in result.stdout.replace("\n", " ").split():
                    if part.strip().isdigit():
                        pids.add(int(part.strip()))
            except Exception:
                pass
        return sorted(pids)

    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
        )
        for line in result.stdout.splitlines():
            low = line.lower()
            if "listening" not in low:
                continue
            cols = line.split()
            if len(cols) < 5:
                continue
            local_addr = cols[1]
            pid_text = cols[-1]
            if local_addr.endswith(f":{port}") and pid_text.isdigit():
                pids.add(int(pid_text))
    except Exception:
        pass
    return sorted(pids)


def stop_pidfile_server(timeout: float = 5.0) -> dict:
    pid = read_server_pid()
    if not pid:
        return {"attempted": False, "stopped": False, "pid": None, "message": "لا يوجد ملف PID للخادم"}
    stopped = terminate_pid(pid, timeout=timeout)
    if stopped:
        clear_server_pid(pid)
    return {
        "attempted": True,
        "stopped": stopped,
        "pid": pid,
        "message": "تم إيقاف الخادم من ملف PID" if stopped else "تعذر إيقاف الخادم من ملف PID",
    }


def stop_port_server(port: int = 8000, timeout: float = 5.0, *, hawaa_only: bool = True) -> dict:
    pids = listening_pids_for_port(port)
    stopped: list[int] = []
    skipped: list[int] = []
    for pid in pids:
        if hawaa_only and not _looks_like_hawaa_server(pid):
            skipped.append(pid)
            continue
        if terminate_pid(pid, timeout=timeout):
            stopped.append(pid)
            clear_server_pid(pid)
    return {
        "attempted": bool(pids),
        "stopped": bool(stopped),
        "pids": pids,
        "stopped_pids": stopped,
        "skipped_pids": skipped,
        "message": f"تم إيقاف الخادم على المنفذ {port}" if stopped else f"لم يتم العثور على خادم هوى الشام قابل للإيقاف على المنفذ {port}",
    }


def can_connect(host: str = "127.0.0.1", port: int = 8000, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False
