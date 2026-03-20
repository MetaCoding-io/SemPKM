# S02: Column mapping configuration UI + pull sync — UAT

**Milestone:** M024
**Written:** 2026-03-20

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All column mapping routes and sync engine logic are tested via 213 offline unit tests with mocked clients. Live runtime UAT deferred to S04 E2E test which exercises the full install → auth → column mapping → sync → verify lifecycle against Docker stack.

## Preconditions

- Backend venv available at `/home/james/Code/SemPKM/backend/.venv/`
- All tests run from `backend/` directory with PYTHONPATH pointing to worktree
- No Docker stack required (offline tests only)

## Smoke Test

Run all Monday.com tests and confirm 490+ pass:
```bash
cd /home/james/Code/SemPKM/backend && \
PYTHONPATH=/home/james/Code/SemPKM/.gsd/worktrees/M024/backend:/home/james/Code/SemPKM/.gsd/worktrees/M024 \
.venv/bin/python3 -m pytest /home/james/Code/SemPKM/.gsd/worktrees/M024/backend/tests/test_monday_*.py -v --tb=short
```
**Expected:** 490 passed, 0 failed, 0 errors.

## Test Cases

### 1. Column type compatibility filtering

1. Run: `pytest tests/test_monday_column_mapping.py -v -k "TestColumnTypeCompatibility"`
2. **Expected:** 19 tests pass. Status property only shows status-type columns. Due date only shows date-type columns. Assignee only shows people-type columns.

### 2. Column mapping save and load round-trip

1. Run: `pytest tests/test_monday_column_mapping.py -v -k "TestColumnMappingSaveLoad"`
2. **Expected:** 15 tests pass. Mapping saved as JSON at `column_mapping_{board_id}`. Per-board independence verified. Overwrite replaces old mapping. Empty/blank values handled.

### 3. Settings_str label discovery

1. Run: `pytest tests/test_monday_column_mapping.py -v -k "TestLabelDiscovery"`
2. **Expected:** 14 tests pass. Labels parsed from `settings_str` JSON. Malformed JSON returns empty list gracefully. Missing keys, None values, unicode strings all handled.

### 4. Label mapping save with nested structure

1. Run: `pytest tests/test_monday_column_mapping.py -v -k "TestLabelMappingSaveLoad"`
2. **Expected:** 8 tests pass. Label mapping stored with `status_label_mapping` and `priority_label_mapping` sub-dicts. Per-board independence. Enum value validation.

### 5. MondayClient group field in items query

1. Run: `pytest tests/test_monday_column_mapping.py -v -k "TestMondayClientGetBoardItems"`
2. **Expected:** 8 tests pass. GraphQL query includes `group { id title }`. Cursor pagination works. Empty board returns empty list.

### 6. MondayClient get_subitems with parent_item_id

1. Run: `pytest tests/test_monday_column_mapping.py -v -k "TestMondayClientGetSubitems"`
2. **Expected:** 9 tests pass. Subitems augmented with `parent_item_id`. Empty item_ids returns empty list. Multiple parents handled.

### 7. Pull sync pipeline — new task creation

1. Run: `pytest tests/test_monday_sync_engine.py -v -k "test_single_board_creates_task"`
2. **Expected:** Passes. Pull sync creates object.create command with correct slug, title, type (bpkm:Task), provider (monday), external URL/ID/UUID.

### 8. Pull sync pipeline — group → taskGroup mapping

1. Run: `pytest tests/test_monday_sync_engine.py -v -k "group"`
2. **Expected:** All group-related tests pass. Group title from `item["group"]["title"]` becomes bpkm:taskGroup property value.

### 9. Pull sync pipeline — subitem → parentTask edge

1. Run: `pytest tests/test_monday_sync_engine.py -v -k "subitem"`
2. **Expected:** Tests pass. Subitems create separate Task objects. Phase 3 creates bpkm:parentTask edges linking subitems to parent tasks.

### 10. Push sync stub returns skipped

1. Run: `pytest tests/test_monday_sync_engine.py -v -k "push"`
2. **Expected:** All push sync tests pass. Returns `{"status": "skipped", "reason": "not implemented"}`. Is an async function. Does not interact with state or graph.

### 11. Per-item error isolation

1. Run: `pytest tests/test_monday_sync_engine.py -v -k "Fail"`
2. **Expected:** AlwaysFailGraph → "error" status with all items in failed_items. FailOnSecondItem → "partial" status with first item succeeded and second in failed_items.

### 12. Assignee resolution

1. Run: `pytest tests/test_monday_sync_engine.py -v -k "Assignee"`
2. **Expected:** Assignee present triggers PersonMatcher.resolve(). Assignee resolution failure doesn't crash the item — it proceeds without assignee.

## Edge Cases

### Malformed settings_str parsing

1. Run: `pytest tests/test_monday_column_mapping.py -v -k "malformed"`
2. **Expected:** 2 tests pass. Invalid JSON in settings_str returns empty labels gracefully. No exception propagated.

### Error paths (missing board_id, no token, API errors)

1. Run: `pytest tests/test_monday_column_mapping.py -v -k "error or malformed or missing"`
2. **Expected:** 14 tests pass. Missing board_id, no column mapping for labels, malformed settings, API errors, auth errors, no token — all handled with appropriate error responses.

### MockResponse falsy data correctness

1. Run: `pytest tests/test_monday_sync_engine.py -v -k "MockResponseFalsy"`
2. **Expected:** 5 tests pass. Empty list `[]` preserved (not converted to `{}`). Zero and False preserved. None → empty dict. This validates KNOWLEDGE.md Pattern #2 compliance.

### Empty sync results

1. Run: `pytest tests/test_monday_sync_engine.py -v -k "Empty"`
2. **Expected:** 2 tests pass. Zero items returns success with zero counts. Timestamp still stored even for empty results.

## Failure Signals

- Any test failure in `test_monday_column_mapping.py` indicates broken column mapping logic
- Any test failure in `test_monday_sync_engine.py` indicates broken sync pipeline
- `_extract_constants()` KeyError at import time means COLUMN_TYPE_COMPATIBILITY was renamed/moved in app.py
- `ModuleNotFoundError: sempkm_app_sdk` means tests are being run from the wrong PYTHONPATH
- Running pytest from the worktree root (not `backend/`) may cause conftest.py import failures

## Requirements Proved By This UAT

- MON-03 (column mapping) — 107 column mapping tests prove type filtering, save/load, and UI logic
- MON-04 (status label mapping) — Label discovery from settings_str + mapping to bpkm:taskStatus enum
- MON-05 (priority label mapping) — Label discovery + mapping to bpkm:taskPriority enum
- MON-06 (pull sync) — 106 sync engine tests prove create/update/skip/error paths
- MON-07 (groups as taskGroup) — Group title from item.group verified in dedicated tests
- MON-08 (subitems→parentTask) — Subitem edge creation verified in sync engine tests

## Not Proven By This UAT

- Live UI rendering of column mapping forms (no Docker/browser verification)
- htmx form submission flow (routes tested via logic replication, not Starlette request objects)
- Visual correctness of configure_columns.html and configure_labels.html templates
- End-to-end sync against a real or mocked Monday.com API over HTTP
- Push sync (stub only — deferred to S03)
- Dependency column → bpkm:dependsOn edges (deferred to S03)

## Notes for Tester

- All tests must be run from the `backend/` directory with PYTHONPATH including the worktree path
- The column mapping tests use a constants extraction pattern (parsing app.py source) — if this fails, check that COLUMN_TYPE_COMPATIBILITY still exists in app.py
- The `_has_changes()` function always returns True — this is intentional for v1 (idempotent updates), not a bug
- 490 total tests = 277 (S01) + 107 (column mapping) + 106 (sync engine)
