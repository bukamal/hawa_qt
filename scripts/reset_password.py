# -*- coding: utf-8 -*-
"""Local recovery utility for resetting a Hawaa user password.

Usage examples:
    python scripts/reset_password.py --username admin --password "NewStrong123!"
    python scripts/reset_password.py --db "C:\\Users\\USER\\AppData\\Roaming\\Hawaa\\hawaa_data.db" --username admin --password "NewStrong123!"

The script works only on the local SQLite database. It creates a safety backup
before changing the password and sets force_password_change=1 when the column exists.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import os
import secrets
import shutil
import sqlite3
from pathlib import Path
from typing import Tuple

APP_NAME = "Hawaa"
DB_NAME = "hawaa_data.db"


def default_db_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / APP_NAME / DB_NAME
    return Path.home() / ".hawaa" / DB_NAME


def hash_password(password: str, salt: str | None = None) -> Tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return pwd_hash, salt


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def create_backup(db_path: Path) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}_before_password_reset_{stamp}{db_path.suffix}")
    with sqlite3.connect(str(db_path)) as src, sqlite3.connect(str(backup_path)) as dst:
        src.backup(dst)
    return backup_path


def reset_password(db_path: Path, username: str, password: str, force_change: bool = True) -> int:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    if len(password) < 8:
        raise ValueError("New password must be at least 8 characters.")

    backup_path = create_backup(db_path)
    pwd_hash, salt = hash_password(password)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        columns = table_columns(conn, "users")
        if not {"username", "password_hash", "salt"}.issubset(columns):
            raise RuntimeError("Invalid users table schema: expected username, password_hash and salt columns.")

        row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            raise LookupError(f"User not found: {username}")

        if "force_password_change" in columns:
            conn.execute(
                "UPDATE users SET password_hash=?, salt=?, force_password_change=? WHERE username=?",
                (pwd_hash, salt, 1 if force_change else 0, username),
            )
        else:
            conn.execute(
                "UPDATE users SET password_hash=?, salt=? WHERE username=?",
                (pwd_hash, salt, username),
            )
        conn.commit()
        print(f"Password reset succeeded for user: {username}")
        print(f"Safety backup created: {backup_path}")
        if force_change and "force_password_change" in columns:
            print("The user will be asked to change the password after login.")
        return int(row["id"])
    finally:
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset a local Hawaa SQLite user password.")
    parser.add_argument("--db", default=str(default_db_path()), help="Path to hawaa_data.db")
    parser.add_argument("--username", default="admin", help="Username to reset. Default: admin")
    parser.add_argument("--password", required=True, help="New password. Minimum 8 characters.")
    parser.add_argument("--no-force-change", action="store_true", help="Do not require password change after next login.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        reset_password(Path(args.db), args.username, args.password, force_change=not args.no_force_change)
        return 0
    except Exception as exc:
        print(f"Password reset failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
