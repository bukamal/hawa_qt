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


def detect_lan_ip() -> str:
    """Return the best LAN IPv4 for QR pairing, falling back safely."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        if host_ip and not host_ip.startswith("127."):
            return host_ip
    except Exception:
        pass
    return "127.0.0.1"


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
        server_url = (server_url or self.default_server_url()).strip().rstrip("/")
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
