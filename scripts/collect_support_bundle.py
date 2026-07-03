#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect non-sensitive diagnostics for support.

The bundle intentionally excludes the database and backups by default. It only
includes logs, runtime path metadata and selected phase/readme notes.
"""
from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime
from pathlib import Path

from app_config import describe_runtime_paths, get_data_dir, get_log_dir

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def add_if_exists(zipf: zipfile.ZipFile, path: Path, arcname: str) -> None:
    if path.exists() and path.is_file():
        zipf.write(path, arcname)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create Hawaa support bundle")
    parser.add_argument("--output", default="", help="Output zip path")
    parser.add_argument("--include-db", action="store_true", help="Include database file; use only when explicitly needed")
    args = parser.parse_args(argv)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = Path(args.output) if args.output else get_data_dir() / f"hawaa_support_{stamp}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)

    runtime_paths = describe_runtime_paths()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("runtime_paths.json", json.dumps(runtime_paths, ensure_ascii=False, indent=2))
        for log_file in get_log_dir().glob("*.log*"):
            zipf.write(log_file, f"logs/{log_file.name}")
        for note in PROJECT_ROOT.glob("PHASE*_*.md"):
            zipf.write(note, f"notes/{note.name}")
        add_if_exists(zipf, PROJECT_ROOT / "README.md", "README.md")
        add_if_exists(zipf, PROJECT_ROOT / "WINDOWS_VISUAL_TEST_CHECKLIST.md", "WINDOWS_VISUAL_TEST_CHECKLIST.md")
        if args.include_db:
            db = Path(runtime_paths["db_path"])
            add_if_exists(zipf, db, f"database/{db.name}")

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
