---
id: T02
parent: S01
milestone: M050
key_files:
  - backend/app/templates/browser/type_filter_dropdown.html
  - backend/app/templates/browser/view_toolbar.html
  - frontend/static/css/views.css
  - backend/app/templates/browser/type_filter_pills.html
key_decisions:
  - Kept type_filter_pills.html as empty stub rather than deleting to prevent include errors from stale references
  - Dropdown onchange discovers scope_query from nearest .view-scope-select element for live accuracy
duration: 
verification_result: passed
completed_at: 2026-04-05T21:34:06.907Z
blocker_discovered: false
---

# T02: Replace 37-pill type bar with compact select dropdown across all 11 view templates and remove View Variants dropdown

**Replace 37-pill type bar with compact select dropdown across all 11 view templates and remove View Variants dropdown**

## What Happened

Created type_filter_dropdown.html with a select element that loops over renderer-filtered types from T01's backend. The onchange handler preserves scope_query from the nearest .view-scope-select, persists selection to localStorage, and fires htmx swap. Updated all 11 view templates from pills include to dropdown include. Removed View Variants dropdown from view_toolbar.html per D389. Updated views.css: removed pill/variant CSS rules, added dropdown styles. Emptied type_filter_pills.html to a stub.

## Verification

All task-level grep checks pass: 0 templates reference old pills, all 11 templates include dropdown (1 match each), 0 view-variant-select in toolbar, 0 pill CSS classes in views.css, 2 dropdown CSS rules present. T01 backend tests: 10/10 passed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -r 'type_filter_pills' backend/app/templates/browser/ | grep -v type_filter_pills.html | wc -l` | 0 | ✅ pass | 50ms |
| 2 | `grep -c 'type_filter_dropdown' backend/app/templates/browser/{table,kanban}_view.html` | 0 | ✅ pass | 50ms |
| 3 | `grep -c 'view-variant-select' backend/app/templates/browser/view_toolbar.html` | 1 | ✅ pass (0 matches expected) | 50ms |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_compatible_types.py -v` | 0 | ✅ pass | 700ms |

## Deviations

Updated all 11 view templates instead of just 7 — the 4 specialized views (okr, bmc, quadrant, decision-matrix) also included the pills template.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/type_filter_dropdown.html`
- `backend/app/templates/browser/view_toolbar.html`
- `frontend/static/css/views.css`
- `backend/app/templates/browser/type_filter_pills.html`
