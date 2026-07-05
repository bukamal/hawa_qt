# Phase 34 — Windows Server Stop Fix

## Problem
The Network Settings "Stop Server" button only stopped the in-memory `subprocess.Popen` handle stored in `ServerService`. When the server had been started during application startup (`main.py` spawning `main.py --server`) or from an older session, the settings page could lose that handle while the Waitress server kept listening on port `8000`.

Symptoms:
- `OSError: [Errno 98] Address already in use` when starting again.
- Network Settings showed the server alive, but "Stop Server" did not actually stop it.
- Resource warnings appeared after startup failures because the server process failed midway.

## Fixes
- Added `services/server_runtime.py`.
- The server process now writes a persistent PID file under the writable config directory:
  - Windows: `%APPDATA%/Hawaa/config/hawaa_server.pid`
  - Linux/macOS: `~/.hawaa/config/hawaa_server.pid`
  - Portable mode: `data/config/hawaa_server.pid`
- `main.py --server` writes/removes the PID file and closes DB resources in `finally`.
- `run_server.py` writes/removes the PID file and closes DB resources in `finally`.
- `ServerService.stop()` now attempts, in order:
  1. Stop the in-memory `Popen` process.
  2. Stop the PID found in `hawaa_server.pid`.
  3. If `/health` is still alive, find and stop the Hawaa process listening on the configured port.
- Settings > Network now passes the relevant URL/port to `ServerService.stop()` and displays details.
- `ServerService.command()` now uses an absolute `run_server.py` path in source mode.

## Safety
The port-kill fallback only stops listeners that look like Hawaa server processes by command line (`hawaa`, `main.py --server`, `run_server.py`, `flask_server.py`, `waitress`). It does not blindly kill arbitrary programs on port 8000.

## Validation
Commands run:

```bash
python3 scripts/check_project_readiness.py
python3 -m compileall -q .
PYTHONPATH=. pytest -q
```

Result:

```text
OK: no readiness issues detected.
59 passed
```
