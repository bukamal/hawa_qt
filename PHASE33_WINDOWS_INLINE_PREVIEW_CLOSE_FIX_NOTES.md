# Phase 33 — Windows Inline Preview Close Fix

## Problem

In the Windows accounts document, the `PrintPreviewPanel` close button emitted its
`closed` signal, but `AccountsDocument.open_summary_preview()` did not connect that
signal to `shell.close_inline()`.  Therefore the close button worked in some preview
flows, such as company ledgers where the signal was connected manually, but not in the
accounts-summary preview.

## Fix

`AppShell.open_inline()` now centrally wires any inline content exposing a `closed`
signal to `AppShell.close_inline()`.  This makes inline previews and future inline
panels consistent without requiring every document to remember the connection.

`PrintPreviewPanel` now routes its close button through `request_close()`, which emits
`closed` and includes a standalone debug fallback.

## Impact

- Fixes the accounts summary preview close button.
- Prevents the same bug in reports and audit previews.
- Keeps existing editor `cancelled`/`saved` behavior unchanged.

## Verification

Added source-level regression tests:

- `tests/test_phase33_inline_preview_close.py`
