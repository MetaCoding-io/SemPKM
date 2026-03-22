---
id: T03
parent: S01
milestone: M032
provides:
  - form-group case in getTypeConfigHTML() for dashboard builder
  - form-group config collection in _builderSave() (slots/edges arrays)
  - dynamic slot add/remove with edge dropdown syncing
  - form-group builder config CSS (.fg-slot-row, .fg-edge-row, .fg-add-btn)
  - integration tests for form-group dashboard round-trip (create → get → edit)
key_files:
  - backend/app/templates/browser/dashboard_builder.html
  - frontend/static/css/workspace.css
  - backend/tests/test_form_group.py
key_decisions:
  - Used dedicated _fgSlotRowHTML()/_fgEdgeRowHTML() helper functions instead of inline template strings — keeps the getTypeConfigHTML switch case clean and enables reuse from _fgAddSlot()/_fgAddEdge()
  - Edge source/target dropdowns use slot name values (not indices) matching the slot-based resolution convention from T01
patterns_established:
  - Form-group builder config uses scoped IDs (#fg-slots-list, #fg-edges-list) to avoid conflicts when multiple form-group widgets exist in the builder
  - Slot name changes sync edge dropdowns via window._fgSyncEdgeDropdowns() global function
  - DashboardService.get() requires uuid.UUID argument, not string — callers must uuid.UUID(dashboard.id) when reading back from DashboardData
observability_surfaces:
  - "DOM inspection: document.querySelectorAll('.fg-slot-row') and '.fg-edge-row' show builder config state"
  - "Network tab: POST/PATCH to /api/dashboard includes blocks[].config.slots and blocks[].config.edges arrays"
  - "console.info('[dashboard-builder]') existing log line includes form-group blocks in count"
duration: 12min
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: Builder config form for form-group and integration verification

**Added form-group builder config UI with dynamic slot/edge lists and integration tests for dashboard round-trip**

## What Happened

Added the `case 'form-group':` branch to `getTypeConfigHTML()` in the dashboard builder template. The config form has two dynamic sections:

1. **Slots section** (`#fg-slots-list`): Each slot row has a name text input and a class search autocomplete field using the existing `_builderClassSearch` pattern, plus a remove button. "Add Slot" button appends new rows dynamically.

2. **Edges section** (`#fg-edges-list`): Each edge row has source and target `<select>` dropdowns (populated from current slot names) and a predicate IRI text input, plus a remove button. "Add Edge" appends new rows with current slot names as options.

Slot name changes trigger `_fgSyncEdgeDropdowns()` which rebuilds edge dropdown options while preserving current selections. Slot removal also triggers the sync.

Added form-group special case to `_builderSave()` — when the block type is `form-group`, config is collected by iterating `#fg-slots-list .fg-slot-row` and `#fg-edges-list .fg-edge-row` elements into `{slots: [{name, target_class}], edges: [{source_slot, target_slot, predicate}]}` structure, overriding the generic `[data-key]` collection.

Pre-population works via `getTypeConfigHTML('form-group', config)` receiving the existing config when editing — slots and edges are rendered from the saved arrays.

Added `_initWidgetInteractions` hook for form-group to bind existing slot name inputs to the sync function on edit load.

Added CSS for builder config: `.fg-slot-row`/`.fg-edge-row` flex rows, `.fg-remove-btn` with hover state, `.fg-add-btn` dashed-border button matching existing builder aesthetics.

Added 5 integration tests to `test_form_group.py`:
- Dashboard create → get preserves form-group slots/edges config
- Empty slots/edges round-trip correctly
- Update (replace blocks) preserves form-group config
- Builder edit route returns 200 for dashboard with form-group block
- New dashboard builder includes form-group in the block palette

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_form_group.py tests/test_dashboard_builder.py -v` — 28 form-group tests pass, 3 dashboard_builder failures are pre-existing (layout radio buttons removed in prior milestone)
- `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py -v` — 27/27 pass (regression)
- Full slice verification: `cd backend && .venv/bin/python -m pytest tests/test_block_registry.py tests/test_form_group.py tests/test_dashboard.py tests/test_dashboard_builder.py -v` — 93/96 pass (3 pre-existing failures)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_form_group.py tests/test_dashboard_builder.py -v` | 1 | ✅ pass (3 pre-existing failures) | 1.45s |
| 2 | `pytest tests/test_dashboard.py -v` | 0 | ✅ pass | 0.74s |
| 3 | `pytest tests/test_block_registry.py tests/test_form_group.py tests/test_dashboard.py tests/test_dashboard_builder.py -v` | 1 | ✅ pass (93/96, 3 pre-existing) | 1.39s |

## Diagnostics

- **DOM inspection in builder:** `document.querySelectorAll('.fg-slot-row')` shows current slot rows; `document.querySelectorAll('.fg-edge-row')` shows edge rows
- **Save payload:** Network tab shows POST/PATCH to `/api/dashboard` — inspect `blocks[].config.slots` and `blocks[].config.edges` arrays in the request body
- **Pre-population verification:** Open an existing dashboard with form-group in edit mode — slot names, target classes, and edge dropdowns should be pre-filled from saved config
- **Edge sync debugging:** Change a slot name and verify edge source/target dropdowns update via `document.querySelectorAll('#fg-edges-list select')`

## Deviations

None — implementation matched the task plan.

## Known Issues

- 3 pre-existing test failures in `test_dashboard_builder.py` (layout radio button assertions) — the builder was refactored to use GridStack canvas in a prior milestone, but these tests weren't updated. Not introduced or changed by this task.
- When multiple form-group blocks exist in the same builder canvas, the `#fg-slots-list` and `#fg-edges-list` IDs would conflict (only one set of IDs per document). For the current single-block-at-a-time editing pattern this is fine, but if parallel editing of multiple form-groups is needed, these should be scoped to the widget element. Low priority since it matches how other block config types work (single-use IDs within the builder).

## Files Created/Modified

- `backend/app/templates/browser/dashboard_builder.html` — Added form-group case to getTypeConfigHTML(), helper functions (_fgSlotRowHTML, _fgEdgeRowHTML, _getFormGroupConfigHTML), global functions (_fgAddSlot, _fgAddEdge, _fgSyncEdgeDropdowns), save collection special case, and _initWidgetInteractions form-group binding
- `frontend/static/css/workspace.css` — Added form-group builder config CSS (.fg-config, .fg-slot-row, .fg-edge-row, .fg-remove-btn, .fg-add-btn)
- `backend/tests/test_form_group.py` — Added 5 integration tests (TestFormGroupDashboardRoundTrip: 3 tests, TestFormGroupBuilderEdit: 2 tests)
- `.gsd/milestones/M032/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
