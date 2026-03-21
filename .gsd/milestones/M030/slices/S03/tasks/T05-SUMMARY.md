---
id: T05
parent: S03
milestone: M030
provides:
  - Lint settings management section accessible from dashboard sidebar
  - Individual remove and bulk clear actions for suppressions and dismissals
  - Preset management (apply, rename, delete) in settings view
  - Back navigation from settings to dashboard
key_files:
  - backend/app/templates/browser/lint_settings.html
  - backend/app/browser/pages.py
  - backend/app/templates/browser/lint_dashboard.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
key_decisions:
  - Rule labels always use _local_name() extraction (e.g. EmptyBodyValidationShape) rather than LabelService resolve, since SHACL shapes have no rdfs:label in the store — the QName fallback from LabelService was too verbose
patterns_established:
  - Settings actions use fetch() + htmx.ajax() refresh pattern with refreshLintSettings() targeting the settings container
  - Destructive bulk actions (Clear All) use confirm() dialog before executing
observability_surfaces:
  - Settings section shows count badges in section headers: Suppressions (N), Dismissals (N), Presets (N)
  - JS error diagnostics prefixed with function names: removeSuppression error, clearAllSuppressions error, etc.
  - All CRUD goes through existing T02 API endpoints — no new API routes
duration: 35m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T05: Lint settings management section

**Added lint settings management section with three collapsible sections for viewing/removing suppressions, dismissals, and presets — accessible from "Manage Filters" link in dashboard sidebar.**

## What Happened

Created `lint_settings.html` template with three `<details>` sections (Suppressions, Dismissals, Presets). Each section shows items with remove buttons and optional bulk clear. Presets also show apply/rename/delete actions. The template swaps into the dashboard container via htmx when clicking "Manage Filters" in the sidebar.

Added `GET /browser/lint-settings` route in pages.py that fetches all filter data via LintFilterService, resolves object labels via LabelService batch resolve, and renders the template. Rule labels use `_local_name()` for clean display (e.g. "EmptyBodyValidationShape" instead of the full IRI or QName).

Added "Manage Filters" link at the bottom of the lint dashboard sidebar with settings icon. Added six JS handler functions (removeSuppression, clearAllSuppressions, removeDismissal, clearAllDismissals, deleteLintPreset, renameLintPreset) all using the fetch→refresh pattern. Added CSS for the settings section layout.

## Verification

- `grep "lint-settings" backend/app/browser/pages.py` — route exists ✅
- `ls backend/app/templates/browser/lint_settings.html` — template exists ✅
- `cd backend && python -m pytest tests/test_lint_filter_service.py -v` — 30/30 passed ✅
- `cd backend && python -m pytest tests/test_lint_filtering.py -v` — 11/11 passed ✅
- `cd backend && python -m pytest tests/test_lint_filter_api.py -v` — 18/18 passed ✅
- Docker: dashboard → "Manage Filters" → settings section with all three sections ✅
- Remove suppression → count updates to (0), empty state shows ✅
- "← Back to Dashboard" → returns to normal dashboard ✅
- All three sections render with correct data, labels, dates, and action buttons ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_lint_filter_service.py -v` | 0 | ✅ pass | 1.65s |
| 2 | `cd backend && python -m pytest tests/test_lint_filtering.py -v` | 0 | ✅ pass | 0.23s |
| 3 | `cd backend && python -m pytest tests/test_lint_filter_api.py -v` | 0 | ✅ pass | 2.42s |
| 4 | `grep "lint-settings" backend/app/browser/pages.py` | 0 | ✅ pass | <1s |
| 5 | `ls backend/app/templates/browser/lint_settings.html` | 0 | ✅ pass | <1s |
| 6 | Docker: Manage Filters → settings section visible | - | ✅ pass | manual |
| 7 | Docker: remove suppression → count updates | - | ✅ pass | manual |
| 8 | Docker: back to dashboard navigation | - | ✅ pass | manual |

## Diagnostics

- **Inspect settings section:** Open workspace → LINT tab in bottom panel → scroll sidebar down → click "Manage Filters"
- **Verify empty state:** Remove all items → sections show "No rules suppressed." / "No results dismissed."
- **JS errors:** Browser console → filter for `removeSuppression`, `clearAllSuppressions`, `deleteLintPreset`, `renameLintPreset`
- **Network:** DevTools Network tab shows fetch calls to existing `/api/lint/suppress/`, `/api/lint/dismiss/`, `/api/lint/presets/` endpoints

## Deviations

- Rule labels always use `_local_name()` instead of `labels.get()` fallback — LabelService returns verbose QNames for SHACL shape IRIs (e.g. `sempkm:model:basic-pkm:EmptyBodyValidationShape`) while `_local_name()` returns clean `EmptyBodyValidationShape`

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/lint_settings.html` — new template with three management sections
- `backend/app/browser/pages.py` — added lint-settings route with label resolution
- `backend/app/templates/browser/lint_dashboard.html` — added "Manage Filters" link in sidebar
- `frontend/static/js/workspace.js` — added 6 settings action handlers + refreshLintSettings()
- `frontend/static/css/workspace.css` — added lint-settings styling (~230 lines)
