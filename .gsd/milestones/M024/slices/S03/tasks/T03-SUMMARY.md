---
id: T03
parent: S03
milestone: M024
provides:
  - "Full push_sync() pipeline: auth → direction check → SPARQL change detection → per-task mutation → LoopGuard mark → lastSyncedAt update"
  - "parse_external_url() helper for Monday.com URL → (board_id, item_id) extraction"
  - "_find_changed_tasks() SPARQL query for Monday-synced tasks with local modifications"
  - "_get_task_body() SPARQL query for task body text"
  - "Module-level _loop_guard singleton shared between push and pull sync"
  - "LoopGuard echo check in pull_sync() item and subitem loops"
key_files:
  - apps/monday-sync/services/sync_engine.py
  - backend/tests/test_monday_sync_engine.py
key_decisions:
  - "push_sync() accepts optional monday_client parameter for test injection rather than patching constructors"
  - "LoopGuard marks use item_id from URL (not task IRI) with wildcard column_id for broad echo prevention"
  - "Push sync inverts label_mapping_{board_id} dicts at runtime for reverse status/priority mapping"
patterns_established:
  - "Push sync test context: _build_push_sync_context() returns (ctx, MockMondayClient) with configurable changed_tasks, board mappings, and label mappings"
  - "MockGraphClient now supports changed_tasks and task_bodies for push-sync SPARQL query routing"
  - "LoopGuard cleanup via pytest fixture (autouse) to prevent test pollution across push/pull integration tests"
observability_surfaces:
  - "last_push_result state key (JSON): status, pushed, skipped, errors, timestamp"
  - "monday_sync.sync logger: INFO for push phase transitions, WARNING for per-task errors"
  - "errors list in push result: per-task {iri, error} details"
  - "Push auth skip / direction skip stored with reason key"
duration: 25min
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: Implement push sync pipeline with LoopGuard integration

**Replaced push_sync() stub with full pipeline (auth → direction → SPARQL → per-task mutation → LoopGuard → lastSyncedAt) and wired LoopGuard echo prevention into pull_sync item/subitem loops; 53 new tests, 607 total Monday tests passing**

## What Happened

Implemented the complete push sync pipeline in `sync_engine.py` following the Jira push sync pattern:

1. **Added `parse_external_url()`** — extracts `(board_id, item_id)` from Monday.com URLs like `https://monday.com/boards/{id}/pulses/{id}`. Handles edge cases (None, empty, wrong format, extra segments, trailing slashes).

2. **Added `_find_changed_tasks()`** — SPARQL query finding Monday-synced tasks where `dcterms:modified > bpkm:lastSyncedAt`. Returns task IRI, external URL, status, priority, title, dueDate, lastSynced.

3. **Added `_get_task_body()`** — simple SPARQL query reading `<iri> <urn:sempkm:body> ?body`.

4. **Created module-level `_loop_guard = LoopGuard(ttl_seconds=30)` singleton** — shared between push and pull sync. Added LoopGuard import alongside other service imports.

5. **Replaced `push_sync()` stub** with full pipeline: auth check → sync direction check → find changed tasks → per-task loop (parse URL → load column mapping → load label mapping → invert label dicts → build reverse column values → mutate via Monday.com API → mark LoopGuard → update lastSyncedAt) → store result. Per-task error isolation ensures one failure doesn't stop others.

6. **Wired LoopGuard echo check into `pull_sync()`** — added `_loop_guard.is_echo()` check in both the item processing loop and subitem processing loop, right after computing `item_id`/`sub_id`. Marked items increment `skipped_count` and `continue`.

7. **Extended test infrastructure** — added `mutations` tracking and `change_multiple_column_values()` to MockMondayClient. Extended MockGraphClient with `changed_tasks` and `task_bodies` parameters for push-sync SPARQL query routing. Added `_build_push_sync_context()` helper. Added `_loop_guard` module to test load order.

8. **Added 53 new tests** across 7 test classes: TestParseExternalUrl (10), TestFindChangedTasks (5), TestGetTaskBody (4), TestPushSyncPipeline (16), TestLoopGuardIntegrationPull (8), TestPushPullLoopGuardRoundTrip (3), TestPushSyncErrorIsolation (2), plus 5 in updated TestPushSync and TestPushSyncExtended.

## Verification

- `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py -v` — **180 passed** (127 existing + 53 new)
- `cd backend && uv run python -m pytest tests/test_monday_*.py -v` — **607 passed** (exceeds 590 target)
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` — valid syntax
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read())"` — valid syntax
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"` — valid syntax
- `grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py` — zero results
- LoopGuard smoke test (mark → echo round-trip) — prints "LoopGuard smoke OK"

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run python -m pytest tests/test_monday_sync_engine.py -v` | 0 | ✅ pass | 0.31s |
| 2 | `uv run python -m pytest tests/test_monday_*.py -v` | 0 | ✅ pass | 0.49s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <0.1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read())"` | 0 | ✅ pass | <0.1s |
| 5 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | <0.1s |
| 6 | `grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py` | 1 (no matches) | ✅ pass | <0.1s |
| 7 | LoopGuard smoke test (importlib round-trip) | 0 | ✅ pass | <0.1s |

## Diagnostics

- **`last_push_result` state key**: JSON with `status` (success/partial/error/skipped), `pushed`, `skipped`, `errors` (list of `{iri, error}`), `timestamp` (ISO 8601). Auth skip and direction skip include `reason` key.
- **Logger**: `monday_sync.sync` at INFO for push phase transitions ("found N changed tasks", "Push sync complete"), WARNING for per-task errors.
- **LoopGuard**: `monday_sync.loop_guard` at DEBUG for mark/echo events. `len(_loop_guard)` for active mark count.
- **Runtime inspection**: `_loop_guard._marks` dict for debugging mark state. `_loop_guard.cleanup()` to remove expired entries.

## Deviations

- Plan step 8 suggested either patching MondayClient constructor or adding optional parameter. Chose the optional `monday_client` parameter approach — cleaner than monkey-patching for tests and consistent with how the test infrastructure already works.
- `_get_task_body()` was implemented but not called in the push pipeline since Monday.com doesn't have a body/description column push path in the current column mapping. It's available for future use if a text/long_text column mapping is added.

## Known Issues

None.

## Files Created/Modified

- `apps/monday-sync/services/sync_engine.py` — MODIFIED: Added `parse_external_url()`, `_find_changed_tasks()`, `_get_task_body()`, LoopGuard import + singleton, full `push_sync()` implementation, LoopGuard echo checks in `pull_sync()` item and subitem loops
- `backend/tests/test_monday_sync_engine.py` — MODIFIED: 53 new tests across 7 test classes, MockMondayClient extended with mutations tracking + `change_multiple_column_values()`, MockGraphClient extended with `changed_tasks`/`task_bodies`, `_build_push_sync_context()` helper, loop_guard added to module load order
