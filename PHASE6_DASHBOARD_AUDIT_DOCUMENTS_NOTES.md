# Phase 6 — Dashboard + Audit Documents

## Scope

This phase continues the migration away from legacy Widget/Dialog workflows toward the Document Shell + Inline model.

Implemented:

- `services/dashboard_service.py`
- `services/audit_service.py`
- `ui/shell/dashboard_shell.py`
- `ui/documents/dashboard_document.py`
- `ui/shell/audit_shell.py`
- `ui/documents/audit_document.py`
- `tests/test_dashboard_service.py`
- `tests/test_audit_service.py`

Updated:

- `views/main_window.py` now uses `DashboardShell` and `AuditShell` instead of legacy `DashboardWidget` and `AuditLogWidget`.
- `services/permission_service.py` now includes audit-view and audit-admin permissions.

## Accounting invariant preserved

Dashboard totals are calculated from `amount_base` in USD and converted only for display using the selected display currency.

Historical rows keep their own `exchange_rate_to_usd` snapshot. Changing the current exchange rate later does not alter old entries.

The dashboard now displays historical-rate labels in the same accounting convention used elsewhere:

`1 USD = <historical_rate> <currency_original>`

## Permissions

Audit Log access is now service-level, not just UI-level:

- `admin`: can view and clean old audit logs.
- `auditor`: can view/export/preview audit logs, but cannot delete old logs.
- `viewer`: denied at service level.

The main sidebar now exposes Audit Log to `admin` and `auditor` roles.

## Dashboard changes

The legacy dashboard calculation logic was moved into `DashboardService`.

The new `DashboardDocument` renders:

- summary cards,
- last-six-month trend table,
- latest five entries,
- current display-currency context,
- historical-rate column for recent entries.

This intentionally avoids keeping dashboard arithmetic inside PyQt UI code.

## Audit changes

The new `AuditDocument` supports:

- user/action/table/date filters,
- inline print preview,
- inline statistics preview,
- Excel export,
- admin-only cleanup of logs older than 90 days.

## Validation

Commands run:

```bash
python -m compileall -q .
PYTHONPATH=. pytest -q
```

Result:

```text
13 passed
```

## Still legacy / next work

Legacy files still exist for fallback and gradual migration:

- `views/widgets/dashboard_widget.py`
- `views/widgets/audit_log_widget.py`

Next recommended phases:

1. Remove or isolate converted legacy widgets.
2. Convert table models from `GenericTableModel` to specialized models.
3. Convert remaining legacy dialogs to inline panels or mark as compatibility-only.
4. Add visual Windows testing for RTL, inline panels, shell sizing, print previews, and side navigation.
