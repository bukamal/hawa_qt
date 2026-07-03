# -*- coding: utf-8 -*-
import logging
import os
import zipfile
from pathlib import Path

import pytest

import app_config
from error_handling import build_error_report
from logging_config import setup_logging


def test_runtime_paths_respect_hawaa_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HAWAA_DATA_DIR", str(tmp_path / "runtime"))
    paths = app_config.describe_runtime_paths()
    assert Path(paths["data_dir"]).name == "runtime"
    assert Path(paths["log_dir"]).exists()
    assert Path(paths["backup_dir"]).exists()
    assert paths["db_path"].endswith("hawaa_data.db")


def test_logging_creates_app_and_error_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("HAWAA_DATA_DIR", str(tmp_path))
    setup_logging(force=True)
    logger = logging.getLogger("test.phase11")
    logger.info("phase11 app log message")
    logger.error("phase11 error log message")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert (tmp_path / "logs" / "app.log").exists()
    assert (tmp_path / "logs" / "errors.log").exists()
    assert "phase11 error log message" in (tmp_path / "logs" / "errors.log").read_text(encoding="utf-8")


def test_error_report_contains_log_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HAWAA_DATA_DIR", str(tmp_path))
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        report = build_error_report(type(exc), exc, exc.__traceback__)
    assert report.log_path.endswith("errors.log")
    assert "RuntimeError" in report.technical_details
    assert "boom" in report.technical_details


def test_support_bundle_excludes_database_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HAWAA_DATA_DIR", str(tmp_path / "runtime"))
    from scripts.collect_support_bundle import main

    output = tmp_path / "support.zip"
    assert main(["--output", str(output)]) == 0
    with zipfile.ZipFile(output) as zipf:
        names = set(zipf.namelist())
    assert "runtime_paths.json" in names
    assert not any(name.startswith("database/") for name in names)
