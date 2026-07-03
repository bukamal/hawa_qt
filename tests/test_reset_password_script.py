# -*- coding: utf-8 -*-
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reset_password import reset_password
from auth.password import verify_password


def test_reset_password_updates_hash_and_sets_force_change(tmp_path):
    db_path = tmp_path / "hawaa_data.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT,
            role TEXT,
            force_password_change INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        "INSERT INTO users (username, password_hash, salt, full_name, role, force_password_change) VALUES (?,?,?,?,?,?)",
        ("admin", "old", "oldsalt", "Admin", "admin", 0),
    )
    conn.commit()
    conn.close()

    reset_password(db_path, "admin", "NewStrong123!", force_change=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT password_hash, salt, force_password_change FROM users WHERE username='admin'").fetchone()
    conn.close()

    assert row["force_password_change"] == 1
    assert verify_password("NewStrong123!", row["password_hash"], row["salt"])
    assert list(tmp_path.glob("hawaa_data_before_password_reset_*.db"))
