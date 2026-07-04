# -*- coding: utf-8 -*-
"""Mobile QR pairing support for Windows/server mode.

The pairing token is intentionally short-lived and one-time-use. It only stores
server connection settings on Android; it never authenticates a user and never
contains credentials.
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import os
import secrets
import socket
import sqlite3
import tempfile
import ipaddress
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional

from app_config import get_db_path
from services.api_contract import (
    APP_ID,
    API_CONTRACT_VERSION,
    BASE_CURRENCY,
    CURRENCY_CONTRACT,
    PAIRING_CONTRACT,
    SERVER_NAME,
    capabilities_payload,
)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def iso_utc(dt: _dt.datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.astimezone(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> _dt.datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = _dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def _is_usable_lan_ipv4(value: str) -> bool:
    """Return True for addresses that a phone can normally reach on LAN.

    QR pairing must not auto-pick loopback, link-local, or public/VPN-like
    addresses.  This intentionally prefers RFC1918 LAN ranges (192.168/16,
    10/8, 172.16/12), because Android is expected to be on the same Wi-Fi/LAN.
    """
    try:
        ip = ipaddress.ip_address(str(value or "").strip())
    except Exception:
        return False
    if ip.version != 4:
        return False
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return False
    return ip.is_private


def _host_from_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    return parsed.hostname or ""


def _port_from_url(url: str, default_port: int = 8000) -> int:
    try:
        return int(urlparse(str(url or "").strip()).port or default_port)
    except Exception:
        return int(default_port)


def normalize_server_url(url: str, default_port: int = 8000, *, for_client: bool = False) -> str:
    """Normalize a server URL for QR payloads.

    Localhost addresses are accepted for same-device/emulator QA.  When the
    input host is 0.0.0.0 we normalize it to 127.0.0.1 for client use, because
    0.0.0.0 is a bind address and is not normally a valid destination URL.
    """
    text = str(url or "").strip().rstrip("/")
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = "http://" + text
    parsed = urlparse(text)
    host = parsed.hostname or ""
    if not host:
        return ""
    if for_client and host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    scheme = parsed.scheme or "http"
    port = parsed.port or int(default_port)
    return f"{scheme}://{host}:{port}"


def discover_lan_ipv4_addresses() -> list[str]:
    """Discover likely LAN IPv4 addresses, filtered for phone reachability."""
    candidates: list[str] = []

    def add(ip: str):
        ip = str(ip or "").strip()
        if _is_usable_lan_ipv4(ip) and ip not in candidates:
            candidates.append(ip)

    # The UDP socket trick usually returns the active outbound interface.
    for target in (("8.8.8.8", 80), ("1.1.1.1", 80)):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(target)
                add(sock.getsockname()[0])
        except Exception:
            pass

    try:
        add(socket.gethostbyname(socket.gethostname()))
    except Exception:
        pass

    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(item[4][0])
    except Exception:
        pass

    # Prefer common Wi-Fi/home LAN addresses before 10.x and 172.16/12.
    def score(ip: str) -> tuple[int, str]:
        if ip.startswith("192.168."):
            return (0, ip)
        if ip.startswith("10."):
            return (1, ip)
        return (2, ip)

    return sorted(candidates, key=score)


def detect_lan_ip() -> str:
    """Return the best LAN IPv4 for QR pairing, falling back safely."""
    ips = discover_lan_ipv4_addresses()
    return ips[0] if ips else "127.0.0.1"


class MobilePairingService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path()

    def _connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mobile_pairing_tokens (
                token TEXT PRIMARY KEY,
                server_url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_by TEXT,
                client_label TEXT
            )
            """
        )
        conn.commit()

    def default_server_url(self, port: int = 8000, host: Optional[str] = None) -> str:
        ip = host or detect_lan_ip()
        return f"http://{ip}:{int(port)}"

    def server_url_options(self, port: int = 8000, preferred_url: Optional[str] = None) -> list[dict]:
        """Return user-facing LAN URLs for Android pairing.

        The first option is the recommended URL.  A saved/preferred URL is only
        included if its host is a usable LAN IPv4, preventing accidental QR
        generation for localhost, VPN/public adapters, or Docker addresses.
        """
        options: list[dict] = []

        def add(url: str, label: str, source: str, recommended: bool = False, allow_local: bool = False):
            url = normalize_server_url(url, default_port=port, for_client=True)
            host = _host_from_url(url)
            is_local = host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
            if not url or (not _is_usable_lan_ipv4(host) and not (allow_local and is_local)):
                return
            if any(item["url"] == url for item in options):
                return
            options.append({
                "url": url,
                "host": host,
                "label": label,
                "source": source,
                "recommended": bool(recommended),
            })

        if preferred_url:
            add(preferred_url, "العنوان المحفوظ/المحدد في الصفحة", "configured", True, allow_local=True)

        for ip in discover_lan_ipv4_addresses():
            add(f"http://{ip}:{int(port)}", f"شبكة محلية: {ip}", "detected", not options)

        if not options:
            # Keep a visible fallback for diagnostics, but UI should warn that a
            # phone cannot use it until a LAN address is selected manually.
            options.append({
                "url": f"http://127.0.0.1:{int(port)}",
                "host": "127.0.0.1",
                "label": "لا يوجد عنوان LAN صالح — تحقق من الشبكة",
                "source": "fallback",
                "recommended": False,
                "unsafe": True,
            })
        return options

    def _new_token(self) -> str:
        raw = secrets.token_urlsafe(32)
        return raw.rstrip("=")

    def create_pairing_payload(
        self,
        server_url: Optional[str] = None,
        ttl_minutes: int = 5,
        created_by: Optional[str] = None,
        client_label: str = "Android",
    ) -> dict:
        server_url = normalize_server_url(server_url or self.default_server_url(), default_port=8000, for_client=True)
        if not server_url:
            raise ValueError("عنوان الخادم غير صالح")
        ttl_minutes = max(1, min(int(ttl_minutes or 5), 60))
        created_at = utc_now()
        expires_at = created_at + _dt.timedelta(minutes=ttl_minutes)
        token = self._new_token()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mobile_pairing_tokens
                (token, server_url, created_at, expires_at, created_by, client_label)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (token, server_url, iso_utc(created_at), iso_utc(expires_at), created_by, client_label),
            )
            conn.commit()
        payload = {
            "app": APP_ID,
            "kind": "mobile_pairing",
            "pairing_contract": PAIRING_CONTRACT,
            "api_contract_version": API_CONTRACT_VERSION,
            "server_name": SERVER_NAME,
            "server_url": server_url,
            "pairing_token": token,
            "expires_at": iso_utc(expires_at),
            "base_currency": BASE_CURRENCY,
            "currency_contract": CURRENCY_CONTRACT,
            "supports_historic_currency_snapshot": True,
            "supports_amount_base": True,
            "supports_exchange_rate_history": True,
        }
        qr_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return {
            "ok": True,
            "server_url": server_url,
            "pairing_token": token,
            "expires_at": iso_utc(expires_at),
            "qr_text": qr_text,
            "payload": payload,
        }

    def validate_pairing_token(self, token: str, consume: bool = True) -> dict:
        token = (token or "").strip()
        if not token:
            return {"ok": False, "error": "pairing_token required"}
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM mobile_pairing_tokens WHERE token=?",
                (token,),
            ).fetchone()
            if not row:
                return {"ok": False, "error": "Invalid or expired pairing token"}
            if row["used_at"]:
                return {"ok": False, "error": "Pairing token already used"}
            expires_at = parse_utc(row["expires_at"])
            if utc_now() > expires_at:
                return {"ok": False, "error": "Pairing token expired"}
            if consume:
                conn.execute(
                    "UPDATE mobile_pairing_tokens SET used_at=? WHERE token=?",
                    (iso_utc(utc_now()), token),
                )
                conn.commit()
            payload = capabilities_payload(row["server_url"])
            payload.update({
                "ok": True,
                "paired": True,
                "message": "تم ربط الهاتف بالخادم. سجّل الدخول بحسابك.",
                "server_url": row["server_url"],
                "expires_at": row["expires_at"],
            })
            return payload

    def cleanup_expired(self) -> int:
        cutoff = iso_utc(utc_now())
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM mobile_pairing_tokens WHERE expires_at < ? OR used_at IS NOT NULL",
                (cutoff,),
            )
            conn.commit()
            return cur.rowcount or 0

    def qr_image_path(self, qr_text: str, filename: str = "hawaa_mobile_pairing_qr.png") -> Optional[str]:
        """Create a temporary QR image if the optional qrcode package exists."""
        try:
            import qrcode
        except Exception:
            return None
        out = Path(tempfile.gettempdir()) / filename
        img = qrcode.make(qr_text)
        img.save(str(out))
        return str(out)


mobile_pairing_service = MobilePairingService()
