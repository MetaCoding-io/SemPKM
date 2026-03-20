---
id: S02
parent: M024
milestone: M024
provides:
  - Column mapping configuration UI — 4 routes (configure-columns GET, save-column-mapping POST, configure-labels GET, save-label-mapping POST) with type-filtered dropdowns per bpkm property
  - Status/priority label mapping — settings_str JSON parsing discovers Monday.com labels, maps to bpkm enum values
  - Per-board mapping storage — column_mapping_{board_id} and label_mapping_{board_id} settings keys
  - connect_status.html shows per-board "Configure Columns" / "Configure Labels" buttons with configured/not-configured indicators
  - MondayClient.get_board_items extended with group { id title } in GraphQL queries
  - MondayClient.get_subitems(item_ids) method for subitem fetching with parent_item_id augmentation
  - sync_engine.py with pull_sync() — full two-phase bulk pipeline following Jira pattern
  - push_sync() stub returning {"status": "skipped", "reason": "not implemented"}
  - Group title → bpkm:taskGroup from item.group (not column_values)
  - Subitems → separate Task objects with bpkm:parentTask edge to parent
  - Per-item error isolation with failed_items diagnostic list
  - Content comparison framework (_has_changes, always-process for v1)
  - 213 new unit tests (107 column mapping + 106 sync engine)
requires:
  - slice: S01
    provides: auth.py, monday_client.py, field_mapper.py, person_matcher.py, app.py scaffold, manifest, templates, CSS, 277 unit tests
affects:
  - S03
key_files:
  - apps/monday-sync/app.py
  - apps/monday-sync/services/monday_client.py
  - apps/monday-sync/services/sync_engine.py
  - apps/monday-sync/frontend/templates/configure_columns.html
  - apps/monday-sync/frontend/templates/configure_labels.html
  - apps/monday-sync/frontend/templates/connect_status.html
  - apps/monday-sync/frontend/static/styles.css
  - backend/tests/test_monday_column_mapping.py
  - backend/tests/test_monday_sync_engine.py
key_decisions:
  - D242 — Per-board column mapping storage (column_mapping_{board_id} and label_mapping_{board_id} as JSON in settings)
  - D243 — Group title from item.group, not column_values (groups are structural, not user-configurable columns)
  - _has_changes() always returns True for v1 — idempotent but not efficient; optimization deferred
patterns_established:
  - Column mapping per-board storage pattern reusable by any future provider with custom fields
  - Type-filtered dropdown pattern — COLUMN_TYPE_COMPATIBILITY maps bpkm properties to compatible Monday.com column types
  - Constants extraction pattern for testing app modules that depend on unavailable SDK imports (parse source lines, exec constant blocks)
  - AlwaysFailGraph / FailOnSecondItem mock patterns for testing per-item error isolation and partial-failure status
observability_surfaces:
  - Settings keys column_mapping_{board_id} and label_mapping_{board_id} inspectable via SDK state client
  - last_sync_at state key — ISO timestamp of last sync
  - last_pull_result state key — JSON with status, created, updated, skipped, errors, duration_ms, failed_items, parent_links
  - monday_sync.sync logger — INFO for phase transitions and counts, WARNING for per-item errors
  - connect_status.html shows configured/not-configured status per board
drill_down_paths:
  - .gsd/milestones/M024/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M024/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M024/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M024/slices/S02/tasks/T04-SUMMARY.md
duration: 71m
verification_result: passed
completed_at: 2026-03-20
---

# S02: Column mapping configuration UI + pull sync

**Built the Monday.com column mapping configuration UI with type-filtered dropdowns and label mapping, extended GraphQL queries for groups and subitems, and implemented the full pull sync engine producing correctly-mapped bpkm:Task objects — 490 total Monday.com tests passing.**

## What Happened

This slice delivered two major capabilities: the column mapping configuration UI (the highest-risk feature in M024) and the pull sync engine.

**T01 — Column mapping configuration routes and client extensions.** Added `COLUMN_TYPE_COMPATIBILITY` and `BPKM_PROPERTY_LABELS` constants to `app.py`, enabling type-filtered dropdowns where each bpkm property (status, priority, due date, assignee, etc.) only shows compatible Monday.com column types. Built 4 new routes: `configure-columns` GET (discovers board columns, renders type-filtered dropdown form), `save-column-mapping` POST (persists per-board mapping), `configure-labels` GET (parses `settings_str` JSON to discover status/priority labels), and `save-label-mapping` POST (saves label→bpkm enum mappings). Created `configure_columns.html` and `configure_labels.html` templates. Updated `connect_status.html` with per-board "Configure Columns" and "Configure Labels" buttons showing ✓ Configured / Not configured indicators. Extended `MondayClient.get_board_items()` to include `group { id title }` in GraphQL queries and added `get_subitems(item_ids)` returning subitem dicts augmented with `parent_item_id`.

**T02 — Pull sync engine.** Created `sync_engine.py` (683 lines) following the established Jira sync engine pattern. The pull pipeline: auth check → read selected boards → per-board column mapping config from settings → paginated item fetch → build properties via `build_task_properties()` with stored mapping → resolve assignee via PersonMatcher → set taskGroup from `item["group"]["title"]` → classify create/update → Phase 1 bulk create → Phase 2 body.set + edge.create → Phase 3 subitem→parentTask edges → store sync timestamp and result. Push sync returns a skipped stub for S03.

**T03 — Column mapping route tests.** Created 107 tests across 9 test classes covering type compatibility filtering, column/label mapping save/load, settings_str label discovery (including malformed JSON, missing keys, unicode), MondayClient group and subitem extensions, route handler logic, error paths (14 tests), and end-to-end mapping flows. Constants extracted from `app.py` via source parsing + exec to avoid importing the full module with SDK dependencies.

**T04 — Sync engine tests.** Extended sync engine tests to 106 covering SPARQL lookup helpers, command builders, result helpers, push stub, auth checks, assignee resolution, all-fail/partial status, empty results, timestamp format, column mapping flow, MockResponse falsy-data correctness (KNOWLEDGE.md Pattern #2), batch boundary, and slug integration.

## Verification

| Check | Status | Evidence |
|-------|--------|----------|
| `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` | ✅ pass | Syntax valid |
| `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` | ✅ pass | Syntax valid |
| `pytest tests/test_monday_column_mapping.py -v` | ✅ 107 pass | 0.10s |
| `pytest tests/test_monday_sync_engine.py -v` | ✅ 106 pass | 0.13s |
| `pytest tests/test_monday_*.py -v` | ✅ **490 pass** | Exceeds 427+ target |
| `pytest tests/test_monday_column_mapping.py -v -k "error or malformed or missing"` | ✅ 14 pass | Error paths verified |
| 5 service modules exist in services/ | ✅ pass | auth, monday_client, field_mapper, person_matcher, sync_engine (+ __init__) |
| 2 new templates exist | ✅ pass | configure_columns.html, configure_labels.html |

## Requirements Advanced

- MON-03 (column mapping) — Column mapping UI routes, type-filtered dropdowns, and per-board mapping storage implemented and tested
- MON-04 (status label mapping) — Status label discovery from settings_str and mapping to bpkm:taskStatus enum values
- MON-05 (priority label mapping) — Priority label discovery and mapping to bpkm:taskPriority enum values
- MON-06 (pull sync) — Pull sync engine creates bpkm:Task objects with correct field values from stored column mapping
- MON-07 (groups as taskGroup) — Group title from item.group mapped to bpkm:taskGroup property
- MON-08 (subitems→parentTask) — Subitems create separate Task objects with bpkm:parentTask edge to parent

## Requirements Validated

- None — MON requirements not yet registered in REQUIREMENTS.md; validation deferred to S04 E2E

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T02 delivered 56 initial sync engine tests alongside the implementation rather than deferring all tests to T04. T04 then expanded to 106 total (adding 50 more tests). Net result exceeds the planned 100+.
- T03 delivered 107 tests (planned 50+) due to more thorough edge case coverage including unicode labels, many entries, whitespace handling, and integration-style flow tests.
- sync_engine.py is 683 lines (estimated ~450) due to comprehensive docstrings and the `_find_all_tasks_for_board` helper.

## Known Limitations

- `_has_changes()` always returns True — every existing task gets patched on every sync. This is correct (idempotent via two-phase bulk) but not efficient. A future optimization can compare key property values to skip no-op updates.
- Column mapping route tests extract constants via source parsing + exec rather than importing the full module, since `app.py` depends on `sempkm_app_sdk` which is unavailable in the test context. If constants are refactored out of `app.py`, the extraction pattern will need updating.
- Push sync is a stub returning `{"status": "skipped"}` — implementation deferred to S03.
- No live/E2E testing of the column mapping UI — deferred to S04.

## Follow-ups

- S03 must implement push_sync() using `build_reverse_column_values()` from field_mapper.py, LoopGuard echo prevention, and dependency column → bpkm:dependsOn edge creation. The sync engine's `push_sync()` stub is the hook point.
- S03 should consider optimizing `_has_changes()` to compare status/priority/title before issuing update commands.
- S04 E2E test should exercise the column mapping UI flow end-to-end: board selection → configure columns → configure labels → sync → verify task properties.

## Files Created/Modified

- `apps/monday-sync/app.py` — Added COLUMN_TYPE_COMPATIBILITY, BPKM_PROPERTY_LABELS, BPKM_STATUS_VALUES, BPKM_PRIORITY_VALUES constants; 4 new routes; updated _render_connect_status with configured_boards
- `apps/monday-sync/services/monday_client.py` — Added `group { id title }` to get_board_items queries; added get_subitems() method
- `apps/monday-sync/services/sync_engine.py` — NEW: 683 lines, complete pull sync engine with group/subitem support + push stub
- `apps/monday-sync/frontend/templates/configure_columns.html` — NEW: column mapping form with type-filtered dropdowns
- `apps/monday-sync/frontend/templates/configure_labels.html` — NEW: status/priority label mapping form
- `apps/monday-sync/frontend/templates/connect_status.html` — Added column mapping section with per-board configure buttons and status indicators
- `apps/monday-sync/frontend/static/styles.css` — Added column mapping CSS (mapping-row, mapping-fieldset, board-mapping-row, etc.)
- `backend/tests/test_monday_column_mapping.py` — NEW: 107 tests across 9 test classes
- `backend/tests/test_monday_sync_engine.py` — NEW: 106 tests covering all sync engine paths

## Forward Intelligence

### What the next slice should know
- The sync engine's `push_sync()` is an async function stub returning `{"status": "skipped", "reason": "not implemented"}`. S03 replaces this with real implementation.
- Column mapping config is stored at `column_mapping_{board_id}` as JSON dict mapping bpkm property → Monday column ID. Label mappings at `label_mapping_{board_id}` with `status_label_mapping` and `priority_label_mapping` sub-dicts. S03's push sync needs to read these same keys and reverse-map.
- `field_mapper.build_reverse_column_values()` already exists from S01 — S03 should use it directly for push mutations.
- `MondayClient.change_multiple_column_values()` already exists from S01 — S03 should use it for push mutations.

### What's fragile
- Constants extraction pattern in test_monday_column_mapping.py — if COLUMN_TYPE_COMPATIBILITY or other constants are renamed or moved out of app.py, the `_extract_constants()` function will fail with a KeyError at import time. The error message is clear but the fix requires updating the extraction regex.
- `_has_changes()` always returns True — this means every sync run creates update commands for every existing task. Not a correctness issue (idempotent) but will be noticeable on large boards.

### Authoritative diagnostics
- `last_pull_result` state key contains JSON with `status`, `created`, `updated`, `skipped`, `errors`, `duration_ms`, `failed_items`, `parent_links` — this is the single best diagnostic for sync health
- `monday_sync.sync` logger at INFO level shows per-board item counts, phase transitions, and final results
- `failed_items` list in the pull result identifies exactly which Monday.com item IDs failed and why

### What assumptions changed
- sync_engine.py ended up larger than estimated (683 vs ~450 lines) due to comprehensive docstrings and the `_find_all_tasks_for_board` helper, but the structure exactly follows the Jira pattern
- Test count significantly exceeded plan: 213 new tests vs 150+ planned, driven by thorough edge case coverage
