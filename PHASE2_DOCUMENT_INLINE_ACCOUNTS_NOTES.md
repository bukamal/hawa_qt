# Phase 2 - Document Shell + Inline Accounts

## Scope
This phase makes the accounting area use the new Document Shell in practice instead of keeping it as a detached prototype.

## Implemented
- Added `ui/shell/accounting_shell.py` and wired it into `views/main_window.py` as the Accounts page.
- Added `ui/documents/company_document.py` as an inline company ledger document.
- Reworked `ui/documents/accounts_document.py` to route company opening and global add-entry actions through the shell.
- Expanded `ui/editors/expense_editor_panel.py` into a full inline financial entry editor.
- Added document-mode signals to `views/widgets/accounts_widget.py`:
  - `company_open_requested(str)`
  - `add_record_requested()`
- Kept old dialogs as fallbacks for legacy usage, but the Accounts page now uses document navigation and inline editing.

## Currency/accounting rule preserved
- New entries snapshot current `exchange_rate_to_usd` on save.
- Editing an entry with the same `currency_original` preserves the historical rate.
- Changing the entry currency creates a new snapshot.
- Company ledger still displays original entry amounts in لنا/له and uses the selected display currency for cumulative balance when required.

## Tested
- Python syntax compile passed.
- Repository currency snapshot test passed:
  - Added `14000 SYP` at rate `14000` => `1 USD` base.
  - Changed rate to `15000`.
  - Edited same entry to `28000 SYP`.
  - Historical rate remained `14000`, base amount became `2 USD`.

## Remaining recommended work
- Move report HTML generation from legacy `CompanyDetailsDialog` into a dedicated `PrintService`.
- Convert Users/Settings/Audit to documents.
- Add a central permission service instead of scattered role checks.
- Add unit tests for inline editor payload validation and API permissions.
