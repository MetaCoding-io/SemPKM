---
id: S01
parent: M050
milestone: M050
provides:
  - Renderer-filtered type lists in all view templates via get_compatible_types()
  - JSON endpoint GET /browser/views/compatible-types?renderer=X for frontend lazy-loading
  - type_filter_dropdown.html partial with scope_query preservation and localStorage persistence
requires:
  []
affects:
  - S02
  - S03
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/tests/test_compatible_types.py
  - backend/app/templates/browser/type_filter_dropdown.html
  - backend/app/templates/browser/view_toolbar.html
  - frontend/static/css/views.css
key_decisions:
  - D389: Remove View Variants dropdown entirely — confusing UX with no data model impact
  - D390: Reuse existing SHACL introspection methods for renderer-filtered type lists
patterns_established:
  - Renderer compatibility filtering via SHACL shape introspection — kanban checks _detect_status_field, calendar/timeline check _detect_date_fields, map checks _detect_geo_fields, all others return unfiltered
  - type_filter_dropdown.html partial with select onchange → htmx swap preserving scope_query — replaces the pill bar pattern
observability_surfaces:
  - get_compatible_types() logs 'compatible_types: renderer=%s total=%d compatible=%d' at INFO level
drill_down_paths:
  - .gsd/milestones/M050/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M050/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T21:35:44.285Z
blocker_discovered: false
---

# S01: Smart Type Dropdown

**Replaced the 37-pill type bar with a renderer-filtered select dropdown and removed the View Variants dropdown from the toolbar.**

## What Happened

Two tasks delivered the slice goal cleanly. T01 added `get_compatible_types(renderer, exclude_iris)` to ViewSpecService, reusing existing SHACL introspection methods (`_detect_status_field`, `_detect_date_fields`, `_detect_geo_fields`) to filter types by renderer compatibility. A new JSON endpoint `GET /browser/views/compatible-types?renderer=X` was added. `generic_view()` now passes renderer-filtered types to templates instead of all types. 10 unit tests cover all filter paths including edge cases (unknown renderer, no shapes service, exclude_iris).

T02 created `type_filter_dropdown.html` with a `<select>` element that loops over the filtered types. The onchange handler preserves scope_query from the nearest `.view-scope-select`, persists selection to localStorage, and fires an htmx swap. All 11 view templates (7 core + 4 specialized) were updated from pills to dropdown. The View Variants dropdown was removed from `view_toolbar.html` per D389. CSS rules for pills and variants were removed; new dropdown styles added. `type_filter_pills.html` kept as empty stub to prevent include errors from stale references.

## Verification

All slice-level checks pass:
- `grep -r 'type_filter_pills' backend/app/templates/browser/ | grep -v type_filter_pills.html | wc -l` → 0 (no templates reference old pills)
- All 11 view templates include `type_filter_dropdown` (1 match each confirmed)
- `grep -c 'view-variant-select' backend/app/templates/browser/view_toolbar.html` → 0 (View Variants removed)
- `cd backend && .venv/bin/python -m pytest tests/test_compatible_types.py -v` → 10/10 passed (all renderer filter paths, edge cases)

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 updated all 11 view templates instead of the planned 7 — the 4 specialized views (okr, bmc, quadrant, decision-matrix) also included the pills template and needed updating.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/views/service.py` — Added get_compatible_types() method using SHACL introspection to filter types by renderer
- `backend/app/views/router.py` — Added GET /browser/views/compatible-types endpoint; updated generic_view() to use filtered types
- `backend/tests/test_compatible_types.py` — New: 10 unit tests for all renderer filter paths and edge cases
- `backend/app/templates/browser/type_filter_dropdown.html` — New: select dropdown partial with onchange htmx swap and localStorage persistence
- `backend/app/templates/browser/type_filter_pills.html` — Emptied to stub (prevents include errors from stale references)
- `backend/app/templates/browser/view_toolbar.html` — Removed View Variants dropdown block
- `backend/app/templates/browser/table_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/cards_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/kanban_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/graph_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/calendar_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/timeline_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/map_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/okr_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/bmc_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/quadrant_view.html` — Changed pills include to dropdown include
- `backend/app/templates/browser/decision_matrix_view.html` — Changed pills include to dropdown include
- `frontend/static/css/views.css` — Removed pill/variant CSS rules; added .type-filter-dropdown and .type-filter-select styles
