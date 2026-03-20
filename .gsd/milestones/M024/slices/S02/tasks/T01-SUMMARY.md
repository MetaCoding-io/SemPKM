---
id: T01
parent: S02
milestone: M024
provides:
  - COLUMN_TYPE_COMPATIBILITY and BPKM_PROPERTY_LABELS constants
  - 4 column/label mapping routes (configure-columns GET, save-column-mapping POST, configure-labels GET, save-label-mapping POST)
  - configure_columns.html and configure_labels.html templates
  - connect_status.html updated with column mapping section and configured_boards indicator
  - MondayClient.get_board_items includes group { id title }
  - MondayClient.get_subitems() method for subitem fetching
  - Initial test_monday_column_mapping.py with 12 constant validation tests
key_files:
  - apps/monday-sync/app.py
  - apps/monday-sync/services/monday_client.py
  - apps/monday-sync/frontend/templates/configure_columns.html
  - apps/monday-sync/frontend/templates/configure_labels.html
  - apps/monday-sync/frontend/templates/connect_status.html
  - apps/monday-sync/frontend/static/styles.css
  - backend/tests/test_monday_column_mapping.py
key_decisions:
  - Label mapping stored as nested dict under label_mapping_{board_id} with status_label_mapping and priority_label_mapping sub-keys
  - settings_str parsing uses json.loads with try/except for graceful handling of malformed data
patterns_established:
  - Column mapping per-board storage pattern: column_mapping_{board_id} and label_mapping_{board_id} as JSON in settings
  - Type-filtered dropdown pattern: COLUMN_TYPE_COMPATIBILITY filters Monday.com columns per bpkm property
observability_surfaces:
  - Settings keys column_mapping_{board_id} and label_mapping_{board_id} inspectable via SDK state client
  - INFO logging on all save operations with board_id and count of mapped fields
  - WARNING logging on malformed settings_str parsing failures
  - connect_status.html shows configured/not-configured status per board
duration: 18m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Column mapping configuration routes, templates, and client extension

**Added 4 column/label mapping routes with type-filtered UI, extended MondayClient with group and subitem queries, and created mapping configuration templates**

## What Happened

Implemented the complete column mapping configuration UI for the Monday.com Sync app. Added `COLUMN_TYPE_COMPATIBILITY`, `BPKM_PROPERTY_LABELS`, `BPKM_STATUS_VALUES`, and `BPKM_PRIORITY_VALUES` constants to `app.py`. Built 4 new routes: `configure-columns` GET (fetches board columns, filters by type compatibility, renders dropdown form), `save-column-mapping` POST (persists per-board mapping as JSON), `configure-labels` GET (parses `settings_str` JSON to discover Monday.com status/priority labels, renders label→bpkm enum mapping form), and `save-label-mapping` POST (persists label mappings). Created `configure_columns.html` and `configure_labels.html` Jinja2 templates with htmx-driven forms. Updated `connect_status.html` to show per-board "Configure Columns" and "Configure Labels" buttons with ✓ Configured / Not configured indicators. Updated `_render_connect_status()` to compute `configured_boards` set.

Extended `MondayClient.get_board_items()` to include `group { id title }` in both paginated and non-paginated GraphQL query variants (needed by T02's sync engine for taskGroup mapping). Added `get_subitems(item_ids)` method that returns a flat list of subitem dicts augmented with `parent_item_id`.

Added CSS for mapping forms (`.mapping-row`, `.mapping-fieldset`, `.board-mapping-row`, `.mapping-status`, `.btn-sm`, `.btn-link`). Created initial `test_monday_column_mapping.py` with 12 constant validation tests (T03 will expand to 50+).

## Verification

- Both Python files pass `ast.parse()` syntax check
- Both template files exist
- `group {` appears 3 times in monday_client.py (paginated, non-paginated, and subitems)
- `get_subitems` method present in monday_client.py
- `configure-columns` appears 2+ times in app.py
- `COLUMN_TYPE_COMPATIBILITY` constant present in app.py
- All 277 S01 tests pass (zero regressions)
- 12 new column mapping constant tests pass
- 289 total Monday tests pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` | 0 | ✅ pass | 0.3s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/monday_client.py').read())"` | 0 | ✅ pass | 0.3s |
| 3 | `ls apps/monday-sync/frontend/templates/configure_columns.html configure_labels.html` | 0 | ✅ pass | 0.1s |
| 4 | `grep -c "group {" apps/monday-sync/services/monday_client.py` → 3 | 0 | ✅ pass | 0.1s |
| 5 | `grep -c "get_subitems" apps/monday-sync/services/monday_client.py` → 1 | 0 | ✅ pass | 0.1s |
| 6 | `grep -c "configure-columns" apps/monday-sync/app.py` → 2 | 0 | ✅ pass | 0.1s |
| 7 | `grep "COLUMN_TYPE_COMPATIBILITY" apps/monday-sync/app.py` | 0 | ✅ pass | 0.1s |
| 8 | `pytest tests/test_monday_auth.py tests/test_monday_client.py tests/test_monday_field_mapper.py tests/test_monday_person_matcher.py -v` → 277 passed | 0 | ✅ pass | 0.2s |
| 9 | `pytest tests/test_monday_column_mapping.py -v` → 12 passed | 0 | ✅ pass | 0.1s |

## Slice-Level Verification (partial — T01 of 4)

| Check | Status | Notes |
|-------|--------|-------|
| `pytest tests/test_monday_column_mapping.py -v` | ✅ 12 pass | Foundational tests; T03 expands to 50+ |
| `pytest tests/test_monday_sync_engine.py -v` | ⬜ pending | T02 creates sync_engine.py, T04 creates tests |
| `pytest tests/test_monday_*.py -v` — 427+ total | ⬜ pending | 289 so far (277 S01 + 12 T01) |
| `ast.parse` apps/monday-sync/services/sync_engine.py | ⬜ pending | T02 creates this file |
| `ast.parse` apps/monday-sync/app.py | ✅ pass | |
| 5 service modules exist | ⬜ 4 of 5 | sync_engine.py created in T02 |
| 2 new templates exist | ✅ pass | configure_columns.html, configure_labels.html |

## Diagnostics

- **Settings inspection:** Column mappings stored at `column_mapping_{board_id}` key — JSON dict of bpkm property → Monday column ID. Label mappings at `label_mapping_{board_id}` — JSON dict with `status_label_mapping` and `priority_label_mapping` sub-dicts.
- **Logging:** `monday_sync` logger at INFO for save operations (board_id + field count), WARNING for malformed `settings_str`.
- **UI indicators:** `connect_status.html` shows "✓ Configured" / "Not configured" per board, computed from `configured_boards` set.

## Deviations

None — all steps implemented as planned.

## Known Issues

None.

## Files Created/Modified

- `apps/monday-sync/app.py` — Added constants (COLUMN_TYPE_COMPATIBILITY, BPKM_PROPERTY_LABELS, BPKM_STATUS_VALUES, BPKM_PRIORITY_VALUES), 4 new routes, updated _render_connect_status with configured_boards
- `apps/monday-sync/services/monday_client.py` — Added `group { id title }` to get_board_items queries, added get_subitems() method
- `apps/monday-sync/frontend/templates/configure_columns.html` — NEW: column mapping form with type-filtered dropdowns
- `apps/monday-sync/frontend/templates/configure_labels.html` — NEW: status/priority label mapping form
- `apps/monday-sync/frontend/templates/connect_status.html` — Added column mapping section with per-board configure buttons
- `apps/monday-sync/frontend/static/styles.css` — Added column mapping CSS (mapping-row, mapping-fieldset, board-mapping-row, etc.)
- `backend/tests/test_monday_column_mapping.py` — NEW: 12 initial constant validation tests
