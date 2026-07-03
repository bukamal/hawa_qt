# Phase 8 - Inline Editor UX + Validation Stabilization

## Scope
This phase stabilizes the main accounting-entry workflow after the Document Shell migration.
The focus is the inline financial-entry editor, validation rules, unsaved-change protection,
and visible historical-currency behavior.

## Added

### `services/validation_service.py`
Central, testable validation layer for financial entries.

Rules implemented:
- company name is required;
- operation type must be `incoming` or `outgoing`;
- currency must be one of the supported currencies;
- negative amounts are rejected;
- zero amount becomes `waiting_payment` and requires a payment due date;
- dates must be ISO `YYYY-MM-DD` at service boundary;
- notes and payment reminder notes have length limits;
- currency preview is generated without writing to the database.

### Expense preview
The validation service now exposes `expense_preview()` showing:
- original amount and currency;
- historical or current exchange rate mode;
- `amount_base` in USD;
- current display-currency value;
- warnings when a currency change creates a new historical snapshot.

## Updated

### `services/expense_service.py`
Expense add/update now validates through `ValidationService` before repository writes.
This prevents UI, desktop service and later API paths from bypassing business validation.

### `ui/editors/expense_editor_panel.py`
The inline editor now includes:
- inline error banner;
- field-level validation labels;
- dirty-state indicator;
- unsaved-change confirmation;
- `Ctrl+S` to save;
- `Esc` to cancel;
- visible accounting preview before saving;
- explicit warning when editing uses the preserved historical rate;
- explicit warning when changing currency will create a new snapshot.

### `ui/shell/inline_panel.py`
Closing the inline panel now respects editor discard confirmation when the content implements
`confirm_discard_changes()`.

### `ui/shell/app_shell.py`
`close_inline()` returns the close result from the inline panel.

## Tests
Added `tests/test_validation_service.py`.

Current result:

```text
21 passed
```

## Accounting invariant preserved
- `amount_original` and `currency_original` remain the user-entered value.
- `exchange_rate_to_usd` remains the historical snapshot for the row.
- `amount_base` remains the canonical USD accounting value.
- `display_currency` is presentation only and does not reprice historical rows.
