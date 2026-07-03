# Windows Packaging

Run from the project root on Windows:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller pytest
python scripts/check_project_readiness.py
python scripts/build_windows.py
```

Outputs:

```text
dist/Hawaa/Hawaa.exe
dist/installer/Hawaa_Setup.exe   # when Inno Setup is installed
```

Runtime data is not stored inside `Program Files`. By default, it is stored in:

```text
%APPDATA%/Hawaa/
  hawaa_data.db
  backups/
  logs/
  config/
```

Portable mode: place a file named `portable.flag` beside `Hawaa.exe`; runtime data will then be created in `Hawaa/data/` beside the executable.

Support bundle:

```powershell
python scripts/collect_support_bundle.py
```

The support bundle excludes the database unless `--include-db` is explicitly passed.
