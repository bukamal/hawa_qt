# Phase 12 — Printing / Export Finalization

## Goal

Finalize the report pipeline so inline previews, printing, PDF, Excel, CSV, and HTML exports use the same canonical report data.

## Main changes

- Added `services/export_service.py`.
- Added HTML templates under `printing/templates/`:
  - `base.html`
  - `table_report.html`
  - `company_ledger.html`
- Refactored `services/print_service.py` to render reports from templates.
- Added company-ledger report payloads with `headers`, `rows`, `html`, `subtitle`, and `default_filename`.
- Extended `PrintPreviewPanel` with Excel and CSV export buttons.
- Updated Reports, Accounts, Company, and Audit documents to pass report metadata to the preview panel.
- Updated Audit export to use `ExportService` instead of hand-written openpyxl logic.
- Updated PyInstaller spec to include the whole `printing/` folder.
- Extended readiness checks to verify print/export files and templates.

## Accounting invariant

Exports do not recalculate balances. They export the exact same rows shown in the inline preview.

The accounting source of truth remains:

```text
amount_base = USD accounting value
amount_original + currency_original = user-entered amount
exchange_rate_to_usd = historical snapshot
```

## Tests

Added export-service tests and report-payload tests.

Result:

```text
33 passed
```
