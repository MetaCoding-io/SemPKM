# S03: Push sync + LoopGuard + dependency edges

**Goal:** User edits a task in SemPKM and changes push to Monday.com via column value mutations. Dependency columns create bpkm:dependsOn edges. LoopGuard prevents push→poll echo loops. Tag columns resolve to named bpkm:tags values.
**Demo:** Run push sync after modifying a Monday-synced task — the change mutation fires against the Monday.com API. Run pull sync immediately after — LoopGuard skips the just-pushed item, preventing an echo update. Dependency columns in pull sync produce bpkm:dependsOn edges. Tag IDs resolve to tag names.

## Must-Haves

- `loop_guard.py` module with `LoopGuard` class — `mark_pushed(item_id, column_id)`, `is_echo(item_id, column_id)`, `cleanup()`, configurable TTL (default 30s)
- Push sync pipeline: auth check → sync direction check → SPARQL change detection → per-task reverse column mapping → `change_multiple_column_values` mutation → LoopGuard mark → `lastSyncedAt` update → store `last_push_result`
- `parse_external_url(url)` helper extracting `(board_id, item_id)` from Monday.com URLs
- `_find_changed_tasks()` SPARQL query finding Monday-synced tasks where modified > lastSyncedAt
- LoopGuard echo check integrated into pull_sync — skip items that were just pushed
- `_extract_dependency()` function in field_mapper for dependency column values
- Dependency edge processing in pull_sync — `bpkm:dependsOn` edges from dependency columns
- Tag ID → name resolution in pull_sync via `MondayClient.get_tags()` batch call
- 100+ new unit tests across `test_monday_loop_guard.py` (new), `test_monday_sync_engine.py` (extended), `test_monday_field_mapper.py` (extended)

## Proof Level

- This slice proves: contract (all tests run offline via importlib, no live API calls)
- Real runtime required: no (E2E testing deferred to S04)
- Human/UAT required: no

## Verification

- `cd backend && uv run python -m pytest tests/test_monday_loop_guard.py -v` — all pass (25+ tests)
- `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py -v` — all pass (160+ tests including 50+ new push tests)
- `cd backend && uv run python -m pytest tests/test_monday_field_mapper.py -v` — all pass (extended with dependency extraction tests)
- `cd backend && uv run python -m pytest tests/test_monday_*.py -v` — 590+ total pass (490 existing + 100+ new)
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read())"` — valid syntax
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` — valid syntax
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"` — valid syntax
- `grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py` — zero results
- `python3 -c "from pathlib import Path; import importlib.util, sys; spec=importlib.util.spec_from_file_location('lg', Path('apps/monday-sync/services/loop_guard.py')); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); lg=mod.LoopGuard(); lg.mark_pushed('test','*'); assert lg.is_echo('test','*'), 'echo check failed'; print('LoopGuard smoke OK')"` — prints "LoopGuard smoke OK" (diagnostic: confirms mark→echo round-trip works outside pytest)

## Observability / Diagnostics

- Runtime signals: `monday_sync.sync` logger at INFO for push phase transitions, WARNING for per-task push errors; `monday_sync.loop_guard` logger for mark/echo events
- Inspection surfaces: `last_push_result` state key — JSON with status, pushed, skipped, errors, timestamp; `last_pull_result` now includes `dependency_edges` count
- Failure visibility: `errors` list in push result with per-task `{iri, error}` details; push auth/direction skip stored with `reason` key
- Redaction constraints: none (no secrets in sync data)

## Integration Closure

- Upstream surfaces consumed: `field_mapper.build_reverse_column_values()` (S01), `MondayClient.change_multiple_column_values()` (S01), `MondayClient.get_tags()` (S01), `sync_engine.pull_sync()` (S02), column mapping storage keys (S02), `_find_existing_task()` (S02), `_submit_commands_batched()` (S02), `_build_update_commands()` (S02), `_compute_status()` / `_make_result()` (S02), push task handler in `app.py` (S02)
- New wiring introduced in this slice: module-level `_loop_guard` singleton in `sync_engine.py`; `push_sync()` replaces stub; LoopGuard echo check wired into `pull_sync()` item loop; dependency edge processing added as Phase 4 in pull_sync
- What remains before the milestone is truly usable end-to-end: S04 (E2E tests + mock server + user guide)

## Tasks

- [x] **T01: Create LoopGuard module and dedicated test file** `est:25m`
  - Why: LoopGuard (D241) is the foundation for echo prevention — push sync marks items, pull sync checks them. Must exist before T03 can wire it in.
  - Files: `apps/monday-sync/services/loop_guard.py`, `backend/tests/test_monday_loop_guard.py`
  - Do: Create `LoopGuard` class with in-memory `dict[str, float]` mapping `"{item_id}:{column_id}"` → timestamp. Implement `mark_pushed()`, `is_echo()` (checks TTL), `cleanup()` (removes expired). Configurable `ttl_seconds` (default 30). Create comprehensive test file with 25+ tests covering mark+check, TTL expiry (via `time.time()` monkeypatch), cleanup, concurrent marks, repeated marks, None/empty edge cases, wildcard column_id.
  - Verify: `cd backend && uv run python -m pytest tests/test_monday_loop_guard.py -v` — all pass
  - Done when: 25+ tests pass and `loop_guard.py` syntax validates

- [x] **T02: Add dependency extraction, tag resolution, and dependency edge processing** `est:40m`
  - Why: Completes the pull-side pipeline for MON-11 (dependency edges) and MON-12 (tags mapping). Dependency extraction goes in field_mapper, edge processing and tag resolution go in sync_engine.
  - Files: `apps/monday-sync/services/field_mapper.py`, `apps/monday-sync/services/sync_engine.py`, `backend/tests/test_monday_field_mapper.py`, `backend/tests/test_monday_sync_engine.py`
  - Do: (1) Add `_extract_dependency()` to field_mapper — extracts `linkedPulseId` values from dependency column shape `{"linkedPulseIds": [{"linkedPulseId": 123}]}`. Register `"dependency"` in `_EXTRACTORS`. Handle `build_task_properties()` branch for `bpkm_prop == "dependency"` storing extracted IDs in a non-BPKM temp key (e.g. `_dependency_ids`). (2) Add `_process_dependencies()` to sync_engine — analogous to Jira's `_process_issue_links()`: for each item with dependency IDs, compute target slugs, look up Task IRIs, create `edge.create` commands with `bpkm:dependsOn`. (3) Add tag resolution in pull_sync: collect all tag ID lists across items, batch-resolve via `MondayClient.get_tags()`, substitute names for IDs in task properties before command creation. (4) Wire dependency processing as Phase 4 in pull_sync between Phase 3 and follow-up submission. (5) Add tests to both test files (~25-30 tests).
  - Verify: `cd backend && uv run python -m pytest tests/test_monday_field_mapper.py tests/test_monday_sync_engine.py -v` — all pass including new tests
  - Done when: Dependency extraction tests pass, dependency edge commands generated correctly in sync engine tests, tag resolution tests pass, `_make_result` includes `dependency_edges` count

- [x] **T03: Implement push sync pipeline with LoopGuard integration** `est:50m`
  - Why: Replaces the push_sync stub with the real pipeline (MON-09) and wires LoopGuard echo prevention into both push and pull (MON-10). The biggest deliverable of the slice.
  - Files: `apps/monday-sync/services/sync_engine.py`, `backend/tests/test_monday_sync_engine.py`
  - Do: (1) Add `parse_external_url(url)` helper — regex parse `https://monday.com/boards/{board_id}/pulses/{item_id}` returning `(board_id, item_id)` tuple, None on parse failure. (2) Add `_find_changed_tasks(graph_client)` SPARQL query — find Monday-synced tasks where `dcterms:modified > bpkm:lastSyncedAt` (clone from Jira pattern, change provider to "monday"). Also fetch `externalUrl` in the query for board/item extraction. (3) Create module-level `_loop_guard = LoopGuard(ttl_seconds=30)` singleton with `import` of LoopGuard from loop_guard module. (4) Replace `push_sync()` stub with full pipeline: auth check → direction check → find changed tasks → per-task loop (parse URL → load board's column mapping → build reverse column values → call `change_multiple_column_values` → mark in LoopGuard → update lastSyncedAt) → store `last_push_result`. (5) Add LoopGuard echo check in `pull_sync()` item processing loop — before processing each item, check `_loop_guard.is_echo(item_id, "*")` and skip if True. (6) Add `MockMondayClient.change_multiple_column_values()` and `get_tags()` methods to test infrastructure. (7) Add 50+ push sync tests: auth skip, direction skip, no changed tasks, parse_external_url (valid/invalid/missing), changed task detection, reverse mapping, mutation call verification, LoopGuard mark after push, lastSyncedAt update, error per-task isolation, partial success status, LoopGuard echo skip in pull_sync.
  - Verify: `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py -v` — all pass (160+ total); `cd backend && uv run python -m pytest tests/test_monday_*.py -v` — 590+ total
  - Done when: push_sync pipeline works end-to-end in tests, LoopGuard prevents echo in pull_sync tests, 590+ total Monday.com tests pass

## Files Likely Touched

- `apps/monday-sync/services/loop_guard.py` — NEW: LoopGuard TTL cache module
- `apps/monday-sync/services/field_mapper.py` — Add `_extract_dependency()`, register in `_EXTRACTORS`, handle dependency branch in `build_task_properties()`
- `apps/monday-sync/services/sync_engine.py` — Replace push_sync stub, add `_find_changed_tasks()`, `parse_external_url()`, `_process_dependencies()`, LoopGuard singleton, tag resolution, LoopGuard echo check in pull_sync
- `backend/tests/test_monday_loop_guard.py` — NEW: 25+ LoopGuard-focused tests
- `backend/tests/test_monday_sync_engine.py` — Extend with 50+ push sync tests, dependency edge tests, tag resolution tests, LoopGuard integration tests
- `backend/tests/test_monday_field_mapper.py` — Extend with dependency extraction tests
