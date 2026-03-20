---
id: T02
parent: S02
milestone: M024
provides:
  - sync_engine.py with pull_sync() and push_sync() — complete Monday.com pull sync pipeline
  - _find_existing_task(), _find_all_tasks_for_board() SPARQL helpers
  - _build_create_command(), _build_update_commands(), _submit_commands_batched() command builders
  - _has_changes() change detection (always-process for now, idempotent)
  - _compute_status(), _make_result() result helpers
  - 56 unit tests in test_monday_sync_engine.py
key_files:
  - apps/monday-sync/services/sync_engine.py
  - backend/tests/test_monday_sync_engine.py
key_decisions:
  - Change detection (_has_changes) always returns True for initial implementation — correctness over performance since two-phase bulk is idempotent; future optimization can compare status/priority/title
  - Group title sourced from item["group"]["title"] not column_values — groups are structural in Monday.com, not user-configurable columns
patterns_established:
  - Per-board iteration with per-board column_mapping_{board_id} and label_mapping_{board_id} settings keys
  - Three-phase bulk: Phase 1 object.create, Phase 2 body.set + edge.create for new tasks, Phase 3 subitem→parentTask edges
  - Mock pattern for sync engine tests: _MonkeyPatchedHttpForAuth for auth flow, monkey-patch MondayClient methods for item/subitem data
observability_surfaces:
  - monday_sync.sync logger: INFO for phase transitions and counts, WARNING for per-item errors
  - last_sync_at state key: ISO timestamp of last sync
  - last_pull_result state key: JSON with status, created, updated, skipped, errors, duration_ms, failed_items, parent_links
duration: 18m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Pull sync engine with group and subitem support

**Created sync_engine.py with full Monday.com pull sync pipeline — per-board iteration, column mapping config, group→taskGroup from item.group, subitems→parentTask edges, two-phase bulk create, per-item error isolation, plus 56 unit tests**

## What Happened

Created `apps/monday-sync/services/sync_engine.py` (683 lines) by cloning the Jira sync engine structure and adapting for Monday.com specifics. The key differences from Jira: per-board iteration with per-board column/label mapping config from settings, group titles from `item["group"]["title"]` (not column values), subitem→parentTask edge creation in Phase 3, and no delta query (always-process change detection since Monday.com has no `updatedAt` filter).

The pull_sync pipeline follows these phases:
1. Auth check → skip if not connected
2. Read selected boards → skip if none
3. Per-board: read column_mapping_{board_id} and label_mapping_{board_id} from settings
4. Fetch all items via paginated get_all_board_items, process each with build_task_properties using stored mapping
5. Phase 1: submit object.create commands for new tasks
6. Phase 2: discover minted IRIs, submit body.set + edge.create
7. Phase 3: create parentTask edges for subitems
8. Store last_sync_at and last_pull_result in state

Also created `backend/tests/test_monday_sync_engine.py` with 56 tests covering: SPARQL helpers, command builders, result helpers, push stub, auth checks, board iteration, item processing, label mappings, subitems, two-phase bulk, state persistence, group handling edge cases, and error isolation.

## Verification

- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` — passes
- All 6 grep checks from the task plan pass (pull_sync, push_sync, monday-sync, parentTask, group title)
- 56 sync engine tests pass
- 345 total Monday tests pass (S01 + S02 combined)
- 5 service modules present: auth, monday_client, field_mapper, person_matcher, sync_engine
- Both syntax checks pass (sync_engine.py and app.py)
- 2 template files present (configure_columns.html, configure_labels.html)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `grep "async def pull_sync" apps/monday-sync/services/sync_engine.py` | 0 | ✅ pass | <1s |
| 3 | `grep "async def push_sync" apps/monday-sync/services/sync_engine.py` | 0 | ✅ pass | <1s |
| 4 | `grep "monday-sync" apps/monday-sync/services/sync_engine.py` | 0 | ✅ pass | <1s |
| 5 | `grep "parentTask" apps/monday-sync/services/sync_engine.py` | 0 | ✅ pass | <1s |
| 6 | `grep "group.*title" apps/monday-sync/services/sync_engine.py` | 0 | ✅ pass | <1s |
| 7 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_sync_engine.py -v` | 0 | ✅ pass (56 tests) | 3.1s |
| 8 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_*.py -v` | 0 | ✅ pass (345 tests) | 0.3s |
| 9 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 10 | `ls apps/monday-sync/services/*.py` (5 modules) | 0 | ✅ pass | <1s |
| 11 | `ls apps/monday-sync/frontend/templates/configure_*.html` (2 files) | 0 | ✅ pass | <1s |

### Slice-level verification status (T02 is intermediate, not final task)

| Slice Check | Status | Notes |
|---|---|---|
| test_monday_column_mapping.py — 50+ tests | ✅ 12 pass | T01 created 12 type compatibility tests; T03 will add the remaining 38+ route tests |
| test_monday_sync_engine.py — 100+ tests | ⏳ 56 pass | T04 will add 44+ more tests to reach 100+ |
| test_monday_*.py — 427+ total | ⏳ 345 pass | Will reach 427+ after T03 and T04 |
| sync_engine.py syntax | ✅ pass | |
| app.py syntax | ✅ pass | |
| 5 service modules | ✅ pass | |
| 2 template files | ✅ pass | |
| error-path tests | ⏳ pending | T03 will add these |

## Diagnostics

- **Logger:** `monday_sync.sync` — INFO for "Board N: fetched M items", phase transitions, "Pull sync complete: {result}"; WARNING for per-item errors, assignee resolution failures, subitem fetch failures
- **State inspection:** Read `last_pull_result` from state for JSON with status/created/updated/skipped/errors/duration_ms/failed_items/parent_links. Read `last_sync_at` for ISO timestamp.
- **Failed items:** `result["failed_items"]` is a list of Monday.com item ID strings that failed with per-item error isolation

## Deviations

- File ended up at 683 lines vs estimated ~450 — due to comprehensive docstrings and the full `_find_all_tasks_for_board` helper from the plan
- Created 56 sync engine tests alongside the implementation (plan had tests as T04) — gives earlier verification coverage; T04 can expand to 100+

## Known Issues

- `_has_changes()` always returns True — every existing task gets patched on every sync. This is correct (idempotent) but not efficient. A future optimization can compare key properties to skip no-op updates.
- The error-path column mapping tests (`-k "error or malformed or missing"`) selected 0 tests — those will be added in T03.

## Files Created/Modified

- `apps/monday-sync/services/sync_engine.py` — NEW: 683 lines, complete pull sync engine with group/subitem support + push stub
- `backend/tests/test_monday_sync_engine.py` — NEW: 56 unit tests covering all sync engine functions and pull_sync pipeline paths
- `.gsd/milestones/M024/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
