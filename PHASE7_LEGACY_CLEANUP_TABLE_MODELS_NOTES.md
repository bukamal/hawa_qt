# Phase 7 - Legacy Isolation + Specialized Table Models

## Scope

This phase continues from Phase 6 and focuses on removing hidden coupling between the new Document Shell and legacy widgets/dialogs.

## Implemented

- Added `services/accounts_service.py` as the canonical company-summary provider.
- Rebuilt `ui/documents/accounts_document.py` so the new Accounts Document no longer embeds `views.widgets.accounts_widget.AccountsWidget`.
- Added inline print preview for account summaries through `AccountsService + PrintPreviewPanel`.
- Added explicit Document Shell table models in `models/table_models.py`:
  - `StructuredTableModel`
  - `CompanySummaryTableModel`
  - `CompanyLedgerTableModel`
  - `UserTableModel`
  - `AuditLogTableModel`
  - `DashboardTrendTableModel`
  - `DashboardRecentTableModel`
  - `ReportTableModel`
- Updated Document Shell pages to use specialized models instead of `GenericTableModel`:
  - Accounts
  - Company Ledger
  - Users
  - Reports
  - Dashboard
  - Audit Log
- Kept `GenericTableModel` only for legacy widgets.
- Made `views.widgets.__init__` lazy so old widgets are isolated and not imported unless explicitly requested.

## Accounting invariant preserved

- `amount_base` remains the canonical USD accounting amount.
- `display_currency` remains presentation-only.
- Historical `exchange_rate_to_usd` snapshots are not recomputed when the current rate changes.
- Waiting-payment rows do not affect balances until they become approved financial rows.

## Tests

- `python -m compileall -q .`
- `PYTHONPATH=. pytest -q`
- Result: 16 passed.

## Remaining

- Full visual test on Windows/PyQt.
- Decide whether to delete or archive legacy widgets/dialogs after one stable UI pass.
- Convert remaining OS-dialog dependent actions where practical, except native save/open dialogs.
- Add dedicated PyQt UI smoke tests when a Qt-capable CI/runtime is available.
