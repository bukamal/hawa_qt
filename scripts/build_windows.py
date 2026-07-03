#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Windows build orchestration for Hawaa.

Run from the project root on Windows:
    python scripts/build_windows.py

The script intentionally performs readiness checks before packaging so a build
cannot silently ship with missing branding assets, legacy imports, or syntax
errors.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_FILE = PROJECT_ROOT / "build" / "windows" / "hawaa_windows.spec"
INSTALLER_SCRIPT = PROJECT_ROOT / "build" / "windows" / "hawaa_installer.iss"
DIST_DIR = PROJECT_ROOT / "dist"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=PROJECT_ROOT, check=check)


def ensure_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"Required tool not found on PATH: {name}")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Hawaa Windows package")
    parser.add_argument("--skip-tests", action="store_true", help="Do not run pytest before packaging")
    parser.add_argument("--skip-installer", action="store_true", help="Only build the PyInstaller folder")
    parser.add_argument("--clean", action="store_true", default=True, help="Clean PyInstaller build output")
    parser.add_argument("--no-clean", action="store_false", dest="clean", help="Do not pass --clean to PyInstaller")
    args = parser.parse_args(argv)

    if not SPEC_FILE.exists():
        raise SystemExit(f"Missing PyInstaller spec: {SPEC_FILE}")

    run([sys.executable, "scripts/check_project_readiness.py"])
    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "-q"])

    ensure_tool("pyinstaller")
    pyinstaller_cmd = ["pyinstaller", str(SPEC_FILE), "--noconfirm"]
    if args.clean:
        pyinstaller_cmd.append("--clean")
    run(pyinstaller_cmd)

    exe = DIST_DIR / "Hawaa" / "Hawaa.exe"
    if not exe.exists():
        raise SystemExit(f"Expected executable was not created: {exe}")

    if not args.skip_installer:
        compiler = shutil.which("ISCC") or shutil.which("iscc")
        if compiler:
            run([compiler, str(INSTALLER_SCRIPT)])
        else:
            print("Inno Setup compiler not found. Skipping installer creation.")
            print("Install Inno Setup and run: ISCC build/windows/hawaa_installer.iss")

    print("Build completed.")
    print(f"Folder build: {exe.parent}")
    print(f"Installer output: {DIST_DIR / 'installer'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
