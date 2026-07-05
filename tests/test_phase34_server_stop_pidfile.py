# -*- coding: utf-8 -*-
import importlib
import os
from pathlib import Path


def test_server_runtime_pidfile_uses_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HAWAA_DATA_DIR", str(tmp_path))
    import app_config
    import services.server_runtime as runtime

    importlib.reload(app_config)
    runtime = importlib.reload(runtime)

    path = runtime.write_server_pid(12345)
    assert path == tmp_path / "config" / "hawaa_server.pid"
    assert runtime.read_server_pid() == 12345
    runtime.clear_server_pid(12345)
    assert runtime.read_server_pid() is None


def test_port_from_url_accepts_localhost_and_plain_host():
    from services.server_runtime import port_from_url

    assert port_from_url("http://127.0.0.1:8000") == 8000
    assert port_from_url("localhost:9000") == 9000
    assert port_from_url("bad-url") == 8000
