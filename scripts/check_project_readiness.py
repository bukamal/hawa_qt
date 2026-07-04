#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project readiness checks for the Document Shell migration.

This script is intentionally dependency-light. It does not import PyQt5 and can
be run on CI or from a plain terminal before building the Windows executable.
"""

from __future__ import annotations

import argparse
import json
import py_compile
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]

LEGACY_IMPORT_MARKERS = (
    "from views.widgets",
    "import views.widgets",
    "from views.dialogs.add_edit_expense_dialog",
    "from views.dialogs.company_details_dialog",
    "from views.dialogs.user_dialog",
)

ALLOWED_LEGACY_RELATIVE_PREFIXES = (
    "views/widgets/",
    "views/dialogs/",
)

EXCLUDED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    "build",
    "dist",
    ".venv",
    "venv",
}

PACKAGING_FILES = (
    "build/windows/hawaa_windows.spec",
    "build/windows/hawaa_installer.iss",
    "build/windows/README.md",
    "scripts/build_windows.py",
    "scripts/collect_support_bundle.py",
    "logging_config.py",
    "error_handling.py",
)

PRINT_EXPORT_FILES = (
    "services/export_service.py",
    "services/print_service.py",
    "printing/templates/base.html",
    "printing/templates/table_report.html",
    "printing/templates/company_ledger.html",
)

SOUND_FILES = (
    "resources/sounds/success.wav",
    "resources/sounds/error.wav",
    "resources/sounds/warning.wav",
    "resources/sounds/delete.wav",
    "resources/sounds/notify.wav",
    "resources/sounds/backup_done.wav",
    "resources/sounds/export_done.wav",
    "resources/sounds/login_ok.wav",
    "resources/sounds/login_fail.wav",
    "resources/sounds/server_on.wav",
    "resources/sounds/server_off.wav",
    "resources/sounds/payment_due.wav",
    "resources/sounds/SOUND_MANIFEST.md",
)

AUTH_STARTUP_FILES = (
    "ui/auth/__init__.py",
    "ui/auth/brand_panel.py",
    "ui/auth/startup_helpers.py",
    "views/login_dialog.py",
    "views/activation_dialog.py",
    "views/splash_screen.py",
)


MOBILE_PAIRING_FILES = (
    "services/api_contract.py",
    "services/mobile_pairing_service.py",
    "tests/test_mobile_pairing_service.py",
)

BRANDING_FILES = (
    "resources/branding/app.ico",
    "resources/branding/installer.ico",
    "resources/branding/project_file.ico",
    "resources/branding/backup_file.ico",
    "resources/branding/app_icon_256.png",
    "resources/branding/app_logo.png",
    "resources/branding/app_symbol.svg",
)


@dataclass
class ReadinessIssue:
    code: str
    path: str
    line: int
    detail: str


def iter_python_files(root: Path = PROJECT_ROOT) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & EXCLUDED_DIRS:
            continue
        yield path


def is_allowed_legacy_file(path: Path, root: Path = PROJECT_ROOT) -> bool:
    rel = path.relative_to(root).as_posix()
    return rel.startswith(ALLOWED_LEGACY_RELATIVE_PREFIXES) or rel == "scripts/check_project_readiness.py"


def collect_legacy_imports(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    for path in iter_python_files(root):
        if is_allowed_legacy_file(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if any(marker in stripped for marker in LEGACY_IMPORT_MARKERS):
                issues.append(ReadinessIssue(
                    code="LEGACY_IMPORT",
                    path=path.relative_to(root).as_posix(),
                    line=lineno,
                    detail=stripped,
                ))
    return issues


def check_entrypoint_wrapper(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    path = root / "main_window.py"
    if not path.exists():
        return [ReadinessIssue("ENTRYPOINT_MISSING", "main_window.py", 0, "Compatibility wrapper is missing.")]
    text = path.read_text(encoding="utf-8")
    issues: List[ReadinessIssue] = []
    if "from main import main" not in text:
        issues.append(ReadinessIssue(
            "ENTRYPOINT_DIVERGED",
            "main_window.py",
            1,
            "Root main_window.py must remain a thin wrapper around main.main().",
        ))
    if "PyQt5" in text or "views.main_window" in text:
        issues.append(ReadinessIssue(
            "ENTRYPOINT_DUPLICATES_STARTUP",
            "main_window.py",
            1,
            "Root main_window.py should not contain a second GUI startup path.",
        ))
    return issues



def check_auth_startup_files(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    for rel in AUTH_STARTUP_FILES:
        path = root / rel
        if not path.exists():
            issues.append(ReadinessIssue("AUTH_STARTUP_FILE_MISSING", rel, 0, "Required branded auth/startup file is missing."))
        elif path.stat().st_size <= 0:
            issues.append(ReadinessIssue("AUTH_STARTUP_FILE_EMPTY", rel, 0, "Required branded auth/startup file is empty."))
    return issues

def check_brand_assets(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    for rel in BRANDING_FILES:
        path = root / rel
        if not path.exists():
            issues.append(ReadinessIssue("BRAND_ASSET_MISSING", rel, 0, "Required branding asset is missing."))
            continue
        if path.stat().st_size <= 0:
            issues.append(ReadinessIssue("BRAND_ASSET_EMPTY", rel, 0, "Branding asset is empty."))
            continue
        data = path.read_bytes()[:8]
        if rel.endswith(".ico") and data[:4] != b"\x00\x00\x01\x00":
            issues.append(ReadinessIssue("BRAND_ASSET_INVALID", rel, 0, "ICO file does not have a Windows icon header."))
        if rel.endswith(".png") and data != b"\x89PNG\r\n\x1a\n":
            issues.append(ReadinessIssue("BRAND_ASSET_INVALID", rel, 0, "PNG file does not have a PNG header."))
        if rel.endswith(".svg") and b"<svg" not in path.read_bytes()[:512].lower():
            issues.append(ReadinessIssue("BRAND_ASSET_INVALID", rel, 0, "SVG file does not contain an SVG root."))
    return issues



def check_sound_assets(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    for rel in SOUND_FILES:
        path = root / rel
        if not path.exists():
            issues.append(ReadinessIssue("SOUND_ASSET_MISSING", rel, 0, "Required audio feedback asset is missing."))
            continue
        if path.stat().st_size <= 0:
            issues.append(ReadinessIssue("SOUND_ASSET_EMPTY", rel, 0, "Audio feedback asset is empty."))
            continue
        if rel.endswith(".wav"):
            data = path.read_bytes()[:12]
            if not (data[:4] == b"RIFF" and data[8:12] == b"WAVE"):
                issues.append(ReadinessIssue("SOUND_ASSET_INVALID", rel, 0, "WAV file does not have a RIFF/WAVE header."))
    return issues

def check_packaging_files(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    for rel in PACKAGING_FILES:
        path = root / rel
        if not path.exists():
            issues.append(ReadinessIssue("PACKAGING_FILE_MISSING", rel, 0, "Required packaging/logging file is missing."))
        elif path.stat().st_size <= 0:
            issues.append(ReadinessIssue("PACKAGING_FILE_EMPTY", rel, 0, "Required packaging/logging file is empty."))
    return issues



def check_mobile_pairing_files(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    for rel in MOBILE_PAIRING_FILES:
        path = root / rel
        if not path.exists():
            issues.append(ReadinessIssue("MOBILE_PAIRING_FILE_MISSING", rel, 0, "Required Windows mobile QR pairing file is missing."))
        elif path.stat().st_size <= 0:
            issues.append(ReadinessIssue("MOBILE_PAIRING_FILE_EMPTY", rel, 0, "Required Windows mobile QR pairing file is empty."))
    flask_path = root / "flask_server.py"
    if flask_path.exists():
        text = flask_path.read_text(encoding="utf-8", errors="ignore")
        for marker in ("/api/capabilities", "/api/mobile/pair", "/api/mobile/pairing-token"):
            if marker not in text:
                issues.append(ReadinessIssue("MOBILE_PAIRING_ENDPOINT_MISSING", "flask_server.py", 0, f"Missing endpoint marker: {marker}"))
    return issues

def check_print_export_files(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    for rel in PRINT_EXPORT_FILES:
        path = root / rel
        if not path.exists():
            issues.append(ReadinessIssue("PRINT_EXPORT_FILE_MISSING", rel, 0, "Required print/export file is missing."))
        elif path.stat().st_size <= 0:
            issues.append(ReadinessIssue("PRINT_EXPORT_FILE_EMPTY", rel, 0, "Required print/export file is empty."))
    return issues


def collect_compile_errors(root: Path = PROJECT_ROOT) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    for path in iter_python_files(root):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            issues.append(ReadinessIssue(
                "COMPILE_ERROR",
                path.relative_to(root).as_posix(),
                getattr(exc.exc_value, "lineno", 0) or 0,
                str(exc.exc_value),
            ))
    return issues


def run_checks(root: Path = PROJECT_ROOT, compile_files: bool = True) -> List[ReadinessIssue]:
    issues: List[ReadinessIssue] = []
    issues.extend(check_entrypoint_wrapper(root))
    issues.extend(collect_legacy_imports(root))
    issues.extend(check_auth_startup_files(root))
    issues.extend(check_brand_assets(root))
    issues.extend(check_sound_assets(root))
    issues.extend(check_packaging_files(root))
    issues.extend(check_print_export_files(root))
    issues.extend(check_mobile_pairing_files(root))
    if compile_files:
        issues.extend(collect_compile_errors(root))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Hawaa Document Shell build readiness.")
    parser.add_argument("--root", default=str(PROJECT_ROOT), help="Project root directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--no-compile", action="store_true", help="Skip py_compile checks")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    issues = run_checks(root, compile_files=not args.no_compile)

    if args.json:
        print(json.dumps([asdict(issue) for issue in issues], ensure_ascii=False, indent=2))
    else:
        if not issues:
            print("OK: no readiness issues detected.")
        else:
            print(f"Found {len(issues)} readiness issue(s):")
            for issue in issues:
                print(f"- [{issue.code}] {issue.path}:{issue.line} — {issue.detail}")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
