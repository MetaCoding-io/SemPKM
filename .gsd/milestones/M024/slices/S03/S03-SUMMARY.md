---
id: S03
parent: M024
milestone: M024
provides:
  - "LoopGuard TTL cache module (loop_guard.py) with mark_pushed/is_echo/cleanup API"
  - "Full push_sync() pipeline: auth → direction check → SPARQL change detection → per-task reverse column mapping → change_multiple_column_values mutation → LoopGuard mark → lastSyncedAt update"
  - "parse_external_url() for Monday.com URL → (board_id, item_id) extraction"
  - "_find_changed_tasks() SPARQL query for Monday-synced tasks with local modifications"
  - "LoopGuard echo check in pull_sync() item and subitem processing loops"
  - "_extract_dependency() for Monday.com dependency column parsing with _dependency_item_ids temp key"
  - "_process_dependencies() creating bpkm:dependsOn edge.create commands from dependency columns"
  - "Tag ID → name batch resolution via MondayClient.get_tags() in pull_sync"
  - "dependency_edges count in _make_result() and last_pull_result state key"
  - "Module-level _loop_guard singleton shared between push and pull sync"
requires:
  - slice: S01
    provides: "MondayClient.change_multiple_column_values(), MondayClient.get_tags(), field_mapper.build_reverse_column_values()"
  - slice: S02
    provides: "sync_engine.pull_sync() with two-phase bulk create, column mapping storage keys, push task handler stub in app.py"
affects:
  - S04
key_files:
  - apps/monday-sync/services/loop_guard.py
  - apps/monday-sync/services/sync_engine.py
  - apps/monday-sync/services/field_mapper.py
  - backend/tests/test_monday_loop_guard.py
  - backend/tests/test_monday_sync_engine.py
  - backend/tests/test_monday_field_mapper.py
key_decisions:
  - "D241 confirmed: LoopGuard as in-memory TTL dict with 30s default, wildcard column_id for broad echo prevention"
  - "push_sync accepts optional monday_client parameter for test injection (cleaner than constructor patching)"
  - "Label mapping dicts inverted at runtime for reverse status/priority mapping during push"
  - "Dependency temp key pattern: _dependency_item_ids stored as underscore-prefixed key, popped before command creation"
  - "Tag resolution per-board (one get_tags call per board) matching per-board loop structure"
patterns_established:
  - "Push sync test context: _build_push_sync_context() returns (ctx, MockMondayClient) with configurable changed_tasks, board mappings, and label mappings"
  - "Dependency temp key pattern: store non-graph data as underscore-prefixed keys (_dependency_item_ids) in properties dict, pop before command creation"
  - "Tag resolution pattern: collect tag IDs during per-item processing, batch-resolve after board loop, substitute names into properties before commands are submitted"
  - "Slug-based deferred dependency resolution: new items store __slug__{slug} as source reference, resolved to IRI after Phase 1 creates"
  - "time.time() mocking via patch.object on the module's time import for deterministic TTL tests"
observability_surfaces:
  - "last_push_result state key (JSON): status, pushed, skipped, errors, timestamp — readable via ctx.state.get('last_push_result')"
  - "last_pull_result now includes dependency_edges count"
  - "monday_sync.sync logger: INFO for push phase transitions, WARNING for per-task push errors"
  - "monday_sync.loop_guard logger: DEBUG events for mark_pushed and is_echo hits"
  - "errors list in push result: per-task {iri, error} details"
  - "Push auth skip / direction skip stored with reason key"
drill_down_paths:
  - .gsd/milestones/M024/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M024/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M024/slices/S03/tasks/T03-SUMMARY.md
duration: 62m
verification_result: passed
completed_at: 2026-03-20
---

# S03: Push sync + LoopGuard + dependency edges

**Bidirectional Monday.com sync is now complete — push sync mutates column values, LoopGuard prevents echo loops, dependency columns create bpkm:dependsOn edges, and tag IDs resolve to names. 117 new tests bring the total to 607 across all Monday.com test files.**

## What Happened

This slice completed the Monday.com sync pipeline's write side and enriched the pull side with dependency edges and tag resolution, delivering three tasks in sequence:

**T01 — LoopGuard module** (12 min): Created `loop_guard.py` — a 65-line pure Python class implementing an in-memory `dict[str, float]` TTL cache per D241. Keys are `"{item_id}:{column_id}"` mapped to `time.time()` timestamps. `mark_pushed()` records a push event, `is_echo()` checks TTL (strict `<` so boundary = expired), `cleanup()` sweeps expired entries, and `__len__()` reports active marks. Created 25 dedicated tests covering basic operations, TTL expiry (via `time.time()` monkeypatch), cleanup, and edge cases (None/empty/numeric/large/special-char IDs, 500 concurrent marks).

**T02 — Dependency extraction, tag resolution, dependency edges** (25 min): Extended the pull-side pipeline with three features. (1) Added `_extract_dependency()` to `field_mapper.py` parsing Monday.com's `{"linkedPulseIds": [{"linkedPulseId": 123}]}` column shape, registered as `"dependency"` in `_EXTRACTORS`, storing extracted IDs in a `_dependency_item_ids` temp key that's popped before command creation. (2) Added tag resolution in `pull_sync` — tag IDs collected during per-item processing are batch-resolved via `client.get_tags()` per board, with API failure falling back to string IDs. (3) Added `_process_dependencies()` with `_find_task_by_monday_item_id()` SPARQL helper — creates `bpkm:dependsOn` edge.create commands with per-dependency error isolation. Wired as Phase 4 in pull_sync. Extended `_make_result()` with `dependency_edges` count. Added 44 new tests (25 field_mapper + 19 sync_engine).

**T03 — Push sync pipeline with LoopGuard integration** (25 min): Replaced the `push_sync()` stub with the full pipeline: auth check → sync direction check → `_find_changed_tasks()` SPARQL query (Monday-synced tasks where `dcterms:modified > bpkm:lastSyncedAt`) → per-task loop (parse URL via `parse_external_url()` → load board's column mapping + label mapping → invert label dicts for reverse mapping → `build_reverse_column_values()` → `change_multiple_column_values()` mutation → mark LoopGuard → update lastSyncedAt) → store `last_push_result`. Created module-level `_loop_guard = LoopGuard(ttl_seconds=30)` singleton shared between push and pull sync. Wired `_loop_guard.is_echo()` checks into `pull_sync()` for both items and subitems — marked items increment `skipped_count` and continue. Added 53 new tests across 7 test classes covering the full push pipeline, LoopGuard pull integration, push→pull round-trip, and error isolation.

## Verification

All slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `uv run python -m pytest tests/test_monday_loop_guard.py -v` | 25/25 passed (0.04s) |
| 2 | `uv run python -m pytest tests/test_monday_sync_engine.py -v` | 180/180 passed (0.20s) |
| 3 | `uv run python -m pytest tests/test_monday_field_mapper.py -v` | 173/173 passed (0.12s) |
| 4 | `uv run python -m pytest tests/test_monday_*.py -v` | **607/607 passed** (0.55s) |
| 5 | Syntax validation (loop_guard.py, sync_engine.py, field_mapper.py) | All OK |
| 6 | Conflict markers grep | Zero results |
| 7 | LoopGuard smoke test (importlib mark→echo round-trip) | "LoopGuard smoke OK" |

The 607 total exceeds the plan's 590 target by 17 tests.

## Requirements Advanced

- MON-09 (push sync) — push_sync() now executes `change_multiple_column_values` mutations with per-column-type JSON format derived from reverse column mapping. Auth check, direction check, SPARQL change detection, per-task error isolation, and result storage all implemented.
- MON-10 (LoopGuard) — LoopGuard prevents push→poll echo loops. Module-level singleton shared between push and pull. Push marks items after mutation; pull checks and skips echoed items. TTL-based expiry ensures marks don't persist indefinitely.
- MON-11 (dependency edges) — Dependency column values parsed via `_extract_dependency()`, targets resolved via SPARQL lookup, `bpkm:dependsOn` edge.create commands generated with per-dependency error isolation.
- MON-12 (tags mapping) — Tag IDs batch-resolved to names via `MondayClient.get_tags()` per board. Names substituted into task properties as comma-separated string. API failure falls back to string IDs.

## Requirements Validated

- None promoted to validated this slice — MON-09/10/11/12 are advanced to "proven by unit tests" but full validation requires E2E testing in S04.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T02: Implementation uses `(source_iri, dependency_item_ids)` tuples instead of planned `(item_slug, dep_ids)` — IRIs are resolved in Phase 4 after Phase 1 creates. Cleaner because `_process_dependencies()` works directly with IRIs.
- T02: Tag resolution is per-board (after each board's items are processed) rather than globally — matches the per-board loop structure and allows one API call per board.
- T03: Chose optional `monday_client` parameter for test injection over constructor patching — cleaner for tests and consistent with existing infrastructure.
- T03: `_get_task_body()` was implemented but not called in the push pipeline — Monday.com doesn't have a body/description column push path in the current column mapping. Available for future text/long_text column mapping support.

## Known Limitations

- LoopGuard is in-memory only — marks are lost on process restart. This is acceptable for v1 polling where push→poll echo occurs within same process lifetime.
- Push sync currently doesn't push body/description content — no reverse mapping for text/long_text column types in the current implementation (the helper `_get_task_body()` exists but is unused).
- No delta query optimization — Monday.com has no `updatedAt` filter for items. Each poll still fetches all items from selected boards. Change detection relies on content comparison.

## Follow-ups

- S04 will exercise the complete bidirectional pipeline via E2E testing with the mock Monday.com GraphQL server.
- S04 will document the push sync, LoopGuard, and dependency features in Chapter 37 user guide.

## Files Created/Modified

- `apps/monday-sync/services/loop_guard.py` — NEW: LoopGuard TTL cache class with mark_pushed/is_echo/cleanup/len API
- `apps/monday-sync/services/sync_engine.py` — MODIFIED: Full push_sync() pipeline, parse_external_url(), _find_changed_tasks(), _get_task_body(), _find_task_by_monday_item_id(), _process_dependencies(), LoopGuard singleton + echo checks in pull_sync, tag resolution, dependency Phase 4
- `apps/monday-sync/services/field_mapper.py` — MODIFIED: _extract_dependency() + "dependency" in _EXTRACTORS + dependency branch in build_task_properties()
- `backend/tests/test_monday_loop_guard.py` — NEW: 25 tests covering basic, TTL, and edge-case behavior
- `backend/tests/test_monday_sync_engine.py` — MODIFIED: 72 new tests (19 T02 + 53 T03) covering dependency edges, tag resolution, push sync pipeline, LoopGuard integration, and error isolation. MockMondayClient extended with mutations tracking + change_multiple_column_values() + get_tags(). MockGraphClient extended with item_id_to_iri, changed_tasks, task_bodies.
- `backend/tests/test_monday_field_mapper.py` — MODIFIED: 25 new tests covering _extract_dependency (13 tests), build_task_properties dependency branch (5 tests), extractors registration (7 tests)

## Forward Intelligence

### What the next slice should know
- The bidirectional sync pipeline is fully functional at the unit test level. S04 needs to wire it up with the mock GraphQL server and prove the full lifecycle via Playwright E2E.
- The mock server needs to handle `change_multiple_column_values` mutations (currently only tested via MockMondayClient in unit tests).
- The push task handler in `app.py` calls `push_sync()` which is now fully implemented — S04 E2E tests should trigger it via the Sync Now button or task scheduler.
- Chapter 37 user guide should document the column mapping → sync → push → LoopGuard lifecycle with a worked example showing a status change round-trip.

### What's fragile
- `_loop_guard` is a module-level singleton in `sync_engine.py` — tests must clear it between runs. The test suite uses an autouse fixture for this. If a new test file imports sync_engine and runs push/pull, it needs the same cleanup.
- `parse_external_url()` uses a regex that expects `monday.com/boards/{id}/pulses/{id}` — Monday.com occasionally uses different URL formats for enterprise workspaces. The current regex handles extra path segments but not domain variants.

### Authoritative diagnostics
- `last_push_result` state key — JSON with status/pushed/skipped/errors/timestamp. This is the primary signal for push health.
- `last_pull_result` now includes `dependency_edges` count alongside existing `created`/`updated`/`skipped`/`errors`.
- `monday_sync.sync` logger at INFO level for push phase transitions (found N changed tasks, push complete).

### What assumptions changed
- Original plan estimated 100+ new tests; actual delivery was 117 new tests (25 LoopGuard + 44 T02 + 53 T03 = 122, minus 5 counted differently in totals).
- The plan assumed dependency processing would use slug-based references throughout; the implementation uses IRI-based references for existing items and slug-based for new items, resolving after Phase 1 creates.
