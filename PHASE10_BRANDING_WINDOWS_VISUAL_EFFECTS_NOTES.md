# Phase 10 — Branding, Windows Icons, and Visual Effects

## Scope

This phase adds a project-specific visual identity and prepares the Windows build assets without changing the accounting rules.

## Added

### Branding assets

New folder:

```text
resources/branding/
```

Key files:

```text
app.ico
installer.ico
project_file.ico
backup_file.ico
app_icon_16.png ... app_icon_256.png
app_logo.png
app_logo.svg
app_symbol.svg
BRAND_MANIFEST.md
```

The icon concept is a simple accounting ledger card with a financial trend mark. The identity uses deep teal as the primary color with a controlled amber accent.

### Branding helper

New file:

```text
branding.py
```

It provides PyInstaller-safe resource resolution and app identity constants.

### Runtime integration

Updated:

```text
main.py
views/main_window.py
views/splash_screen.py
ui/shell/app_shell.py
theme_manager.py
```

The application now sets a runtime window/application icon and uses the logo in the splash screen, title bar, sidebar, and Document Shell command bar.

### Visual effects

New file:

```text
ui/effects.py
```

Updated:

```text
ui/shell/inline_panel.py
ui/shell/document_workspace.py
views/toast.py
```

Effects added:

- light fade between documents
- inline panel slide open/close
- animated toast fade/slide
- refined hover/active styles through `ThemeManager`

Effects are intentionally short and low-cost to preserve data-entry speed.

### Windows build assets

New files:

```text
build/windows/hawaa_windows.spec
build/windows/hawaa_installer.iss
```

The PyInstaller spec uses `resources/branding/app.ico` for the executable.
The Inno Setup script uses `resources/branding/installer.ico` and includes optional `.hawa` file association using `project_file.ico`.

### Readiness checks

Updated:

```text
scripts/check_project_readiness.py
tests/test_phase9_readiness.py
```

The readiness check now validates the required branding assets and checks basic PNG/ICO/SVG signatures.

## Notes

- No accounting logic was changed.
- Historical exchange-rate behavior remains unchanged.
- `display_currency` remains presentation-only.
- The `.hawa` file association is optional and only activated by the installer script.

## Manual Windows checks

After building, confirm:

1. EXE icon appears in Explorer.
2. Taskbar icon appears correctly after launching.
3. Window icon appears in Alt+Tab.
4. Installer icon appears in Inno Setup output.
5. Desktop shortcut icon appears correctly.
6. Splash logo renders cleanly.
7. Sidebar logo does not overflow when collapsed/expanded.
8. Inline panel animation does not cause transparency or layout gaps.
9. Toast animation appears in the top-right without covering critical buttons.
