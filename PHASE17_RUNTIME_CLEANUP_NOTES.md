# Phase 17 — Runtime Warning Cleanup

This phase addresses warnings observed during `python3 main.py` startup in root/Linux test environments.

## Fixed

- Added Linux/root Qt runtime environment setup before creating `QApplication`:
  - creates `XDG_RUNTIME_DIR` if missing
  - disables QtWebEngine sandbox when running as root
  - adds Chromium flags: `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`

- Removed Python 3.12+ deprecation warnings in `auth/activation.py`:
  - replaced `datetime.utcnow()`
  - replaced `datetime.utcfromtimestamp()`
  - preserves UTC-naive datetime compatibility for existing license data

- Prevented SQLite `ResourceWarning` at shutdown:
  - added `DatabaseConnection.close_global()`
  - registered close handler with `atexit`
  - explicitly closes runtime DB connection on normal/early app exit

## Notes

The `--shm-helper` message is a Qt/Chromium helper warning typically seen in root/container Linux sessions. It is not a business-logic error, but it pollutes logs and can indicate sandbox configuration problems. The new environment guard makes this more stable in test environments.

## Validation

- `python -m compileall -q .`
- `PYTHONPATH=. pytest -q`
- Result: 46 passed
