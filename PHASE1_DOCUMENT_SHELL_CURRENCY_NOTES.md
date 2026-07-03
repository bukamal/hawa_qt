# Phase 1 - Document Shell + Currency Ledger Fixes

## Accounting currency invariants

Every financial row now follows this invariant:

- `amount_original`: the exact amount entered by the user.
- `currency_original`: the currency selected by the user when entering the row.
- `exchange_rate_to_usd`: the historical rate snapshot stored on the row.
- `amount_base`: the canonical USD value calculated from the historical snapshot.
- `display_currency`: presentation setting only. It must not rewrite old rows.

When editing an existing row with the same original currency, the old historical exchange rate is preserved. This prevents silent repricing after exchange-rate updates.

## New modules

- `services/currency_ledger_service.py`: single source of truth for currency snapshots, display conversion, original amount formatting, and company summary math.
- `services/backup_service.py`: SQLite backup/restore using the SQLite backup API instead of `shutil.copy2`, safe for WAL mode.
- `ui/shell/*`: first Document Shell scaffold: workspace, navigation, inline panel.
- `ui/documents/accounts_document.py`: wrapper to migrate Accounts into a document gradually.
- `ui/editors/expense_editor_panel.py`: first inline editor scaffold.

## Fixed in this phase

- Preserved historical exchange rate on expense edits.
- Server-side API now recalculates trusted currency snapshots instead of trusting client-submitted `amount_base`.
- Viewer/auditor-like roles can no longer write expenses through API; write routes require admin/user/accountant/manager.
- Exchange-rate changes are logged into `exchange_rate_history`.
- Settings backup/export/import now use SQLite backup API and integrity verification.
- Periodic backup and migration backup no longer copy only the `.db` file in WAL mode.
- License checks now reject expired licenses.
- Server stop button condition fixed.
- Broken report/table HTML fragments fixed.
- Company details table now shows the historical row rate and no longer hides the visible serial column by mistake.

## Migration note

Schema version is now `4`. Existing databases will get `exchange_rate_history` automatically.
