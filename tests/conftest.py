# -*- coding: utf-8 -*-
"""Test-time PyQt stub.

The CI/container used by the coding assistant may not have PyQt installed. DatabaseConnection
only needs QSettings for these service-level tests, so we provide the smallest compatible stub.
"""
import sys
import types
from pathlib import Path

import pytest


if 'PyQt5' not in sys.modules:
    pyqt5 = types.ModuleType('PyQt5')
    qtcore = types.ModuleType('PyQt5.QtCore')

    class QSettings:
        _store = {}

        def __init__(self, *_args, **_kwargs):
            pass

        def value(self, key, default=None, **_kwargs):
            return self._store.get(key, default)

        def setValue(self, key, value):
            self._store[key] = value

    qtcore.QSettings = QSettings
    pyqt5.QtCore = qtcore
    sys.modules['PyQt5'] = pyqt5
    sys.modules['PyQt5.QtCore'] = qtcore


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parents[1]
