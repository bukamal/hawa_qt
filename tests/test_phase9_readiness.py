# -*- coding: utf-8 -*-
from pathlib import Path

from scripts.check_project_readiness import (
    check_entrypoint_wrapper,
    collect_legacy_imports,
    run_checks,
    check_brand_assets,
    check_packaging_files,
    check_sound_assets,
    check_auth_startup_files,
)


def test_root_main_window_is_thin_wrapper(project_root: Path):
    issues = check_entrypoint_wrapper(project_root)
    assert issues == []


def test_no_new_shell_imports_legacy_widgets_or_dialogs(project_root: Path):
    issues = collect_legacy_imports(project_root)
    assert issues == []


def test_phase9_readiness_checks_pass_without_compile(project_root: Path):
    issues = run_checks(project_root, compile_files=False)
    assert issues == []


def test_branding_assets_are_present_and_valid(project_root: Path):
    issues = check_brand_assets(project_root)
    assert issues == []


def test_packaging_and_logging_files_are_present(project_root: Path):
    issues = check_packaging_files(project_root)
    assert issues == []


def test_sound_assets_are_present_and_valid(project_root: Path):
    issues = check_sound_assets(project_root)
    assert issues == []


def test_branded_auth_startup_files_are_present(project_root: Path):
    issues = check_auth_startup_files(project_root)
    assert issues == []
