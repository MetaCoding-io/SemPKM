---
id: T02
parent: S03
milestone: M024
provides:
  - "_extract_dependency() function for Monday.com dependency column parsing"
  - "dependency type registered in _EXTRACTORS dispatcher"
  - "_dependency_item_ids temp key in build_task_properties() output"
  - "_find_task_by_monday_item_id() SPARQL helper for dependency target lookup"
  - "_process_dependencies() creating bpkm:dependsOn edge.create commands"
  - "Tag ID → name batch resolution via MondayClient.get_tags() in pull_sync"
  - "dependency_edges count in _make_result() and last_pull_result"
  - "44 new tests (25 field_mapper + 19 sync_engine)"
key_files:
  - apps/monday-sync/services/field_mapper.py
  - apps/monday-sync/services/sync_engine.py
  - backend/tests/test_monday_field_mapper.py
  - backend/tests/test_monday_sync_engine.py
key_decisions: []
patterns_established:
  - "Dependency temp key pattern: store non-graph data as underscore-prefixed keys (_dependency_item_ids) in properties dict, pop before command creation"
  - "Tag resolution pattern: collect tag IDs during per-item processing, batch-resolve after board loop, substitute names into properties before commands are submitted"
  - "Slug-based deferred dependency resolution: new items store __slug__{slug} as source reference, resolved to IRI after Phase 1 creates"
observability_surfaces:
  - "dependency_edges count in last_pull_result JSON state key"
  - "_process_dependencies logs per-dependency errors at WARNING level"
  - "Tag resolution failure logged at WARNING with fallback to string IDs"
duration: 25m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Add dependency extraction, tag resolution, and dependency edge processing

**Added dependency column extraction, tag ID→name batch resolution, and bpkm:dependsOn edge processing to the Monday.com pull sync pipeline with 44 new tests**

## What Happened

Implemented three features extending the pull-side sync pipeline:

1. **Dependency extraction** (`field_mapper.py`): Added `_extract_dependency()` that parses Monday.com's dependency column shape (`{"linkedPulseIds": [{"linkedPulseId": 123}]}`), returning a list of integer item IDs. Registered `"dependency"` in the `_EXTRACTORS` dispatcher. Added a `bpkm_prop == "dependency"` branch in `build_task_properties()` that stores extracted IDs in a `_dependency_item_ids` temp key (not under the BPKM namespace, popped before command creation).

2. **Tag resolution** (`sync_engine.py`): During per-item processing, tag IDs (integer lists from `_extract_tags()`) are collected into a set. After the per-board item loop, all tag IDs are batch-resolved via `client.get_tags()` — one API call per board. An `id→name` lookup dict substitutes names into properties as a comma-separated string. On API failure, falls back to string IDs.

3. **Dependency edge processing** (`sync_engine.py`): Added `_find_task_by_monday_item_id()` SPARQL helper that looks up tasks by `externalUrl` containing `/pulses/{item_id}`. Added `_process_dependencies()` that iterates dependency pairs, looks up target IRIs, and creates `edge.create` commands with `bpkm:dependsOn` predicate. Per-dependency error isolation ensures one failure doesn't block others. Wired as Phase 4 in `pull_sync()` between Phase 3 (parent links) and follow-up submission.

4. **Result extension**: `_make_result()` now accepts and includes `dependency_edges` count (default 0).

## Verification

- 173 field mapper tests pass (148 existing + 25 new)
- 127 sync engine tests pass (108 existing + 19 new)  
- 25 loop guard tests pass (from T01)
- 554 total Monday.com tests pass — zero regressions
- All three source files pass syntax validation
- No conflict markers in modified files

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && uv run python -m pytest tests/test_monday_field_mapper.py -v` | 0 | ✅ pass | 0.27s |
| 2 | `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py -v` | 0 | ✅ pass | 0.30s |
| 3 | `cd backend && uv run python -m pytest tests/test_monday_loop_guard.py -v` | 0 | ✅ pass | 0.29s |
| 4 | `cd backend && uv run python -m pytest tests/test_monday_*.py -q` | 0 | ✅ pass (554) | 0.48s |
| 5 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | <1s |
| 6 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |
| 7 | `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read())"` | 0 | ✅ pass | <1s |
| 8 | `grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py` | 1 | ✅ pass (no markers) | <1s |
| 9 | LoopGuard smoke test | 0 | ✅ pass | <1s |

## Diagnostics

- **dependency_edges** count in `last_pull_result` state key — read via `ctx.state.get("last_pull_result")` and parse JSON
- **Tag resolution failures** logged at WARNING on `monday_sync.sync` logger — includes board ID and exception
- **Per-dependency errors** logged at WARNING with source IRI and dependency item ID
- **MockGraphClient.item_id_to_iri** dict added to test infrastructure for dependency lookup testing

## Deviations

- The plan suggested collecting `(item_slug, dependency_item_ids)` tuples, but the implementation uses `(source_iri, dependency_item_ids)` for existing items and `(__slug__{slug}, dep_ids)` for new items — IRIs are resolved in Phase 4 after Phase 1 creates the objects. This is cleaner because `_process_dependencies()` works directly with IRIs.
- Tag resolution is done per-board (after each board's items are processed) rather than globally — this matches the per-board loop structure and allows one API call per board.

## Known Issues

None.

## Files Created/Modified

- `apps/monday-sync/services/field_mapper.py` — Added `_extract_dependency()`, registered `"dependency"` in `_EXTRACTORS`, added dependency branch in `build_task_properties()`
- `apps/monday-sync/services/sync_engine.py` — Added `_find_task_by_monday_item_id()`, `_process_dependencies()`, tag resolution in pull_sync per-board loop, Phase 4 dependency wiring, `dependency_edges` in `_make_result()`
- `backend/tests/test_monday_field_mapper.py` — 25 new tests: 13 `_extract_dependency` + 5 `build_task_properties` dependency + 7 total covering extractors/registration
- `backend/tests/test_monday_sync_engine.py` — 19 new tests: 5 `_find_task_by_monday_item_id` + 6 `_process_dependencies` + 2 tag resolution + 2 dependency edges in pull_sync + 3 `_make_result` dependency_edges + 3 MockMondayClient.get_tags; MockGraphClient extended with `item_id_to_iri`; MockMondayClient extended with `tags` param and `get_tags()` method
