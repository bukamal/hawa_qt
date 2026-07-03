# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Hawaa Windows build.
# Run from project root:
#   pyinstaller build/windows/hawaa_windows.spec --clean --noconfirm

from pathlib import Path

ROOT = Path.cwd()
BRANDING = ROOT / "resources" / "branding"

block_cipher = None

added_files = [
    (str(ROOT / "resources"), "resources"),
    (str(ROOT / "printing"), "printing"),
]

hiddenimports = [
    "PyQt5.QtPrintSupport",
    "PyQt5.QtSvg",
    "PyQt5.QtMultimedia",
    "qtawesome",
    "requests",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Hawaa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(BRANDING / "app.ico"),
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Hawaa",
)
