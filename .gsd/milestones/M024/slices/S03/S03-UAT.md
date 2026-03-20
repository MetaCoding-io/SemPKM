# S03: Push sync + LoopGuard + dependency edges — UAT

**Milestone:** M024
**Written:** 2026-03-20

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All deliverables are backend service modules with no UI changes. 607 unit tests exercise the full push pipeline, LoopGuard TTL, dependency edge creation, and tag resolution. Runtime E2E testing deferred to S04.

## Preconditions

- Working directory: `/home/james/Code/SemPKM/.gsd/worktrees/M024`
- Python environment: `cd backend && uv sync` has been run
- No Docker stack needed — all tests run offline via importlib module loading

## Smoke Test

```bash
cd backend && uv run python -m pytest tests/test_monday_*.py -q
```
Expected: `607 passed` with zero failures.

## Test Cases

### 1. LoopGuard mark→echo round-trip
1. Run: `python3 -c "from pathlib import Path; import importlib.util; spec=importlib.util.spec_from_file_location('lg', Path('apps/monday-sync/services/loop_guard.py')); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); lg=mod.LoopGuard(); lg.mark_pushed('12345','*'); assert lg.is_echo('12345','*'); assert not lg.is_echo('99999','*'); print('OK')"`
2. **Expected:** Prints "OK" with exit code 0.

### 2. LoopGuard TTL expiry
1. Run: `cd backend && uv run python -m pytest tests/test_monday_loop_guard.py::TestLoopGuardTTL -v`
2. **Expected:** 8/8 passed — within-TTL, beyond-TTL, exact-boundary, custom TTL, zero TTL, cleanup.

### 3. Push sync pipeline
1. Run: `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py::TestPushSyncPipeline -v`
2. **Expected:** 16/16 passed — mutation calls, reverse column values, lastSyncedAt, LoopGuard mark, error isolation, multi-board.

### 4. Push sync auth/direction checks
1. Run: `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py::TestPushSync -v`
2. **Expected:** 5/5 passed — skip-not-connected, skip-pull-only, bidirectional-proceeds.

### 5. LoopGuard integration in pull sync
1. Run: `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py::TestLoopGuardIntegrationPull -v`
2. **Expected:** 8/8 passed — marked-item-skipped, unmarked-processed, expired-processed, subitem-skipped.

### 6. Push→pull round-trip echo prevention
1. Run: `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py::TestPushPullLoopGuardRoundTrip -v`
2. **Expected:** 3/3 passed — pushed-item-skipped-on-next-pull, unpushed-not-skipped, correct-item-id.

### 7. Dependency extraction
1. Run: `cd backend && uv run python -m pytest tests/test_monday_field_mapper.py::TestExtractDependency -v`
2. **Expected:** 13/13 passed — normal, multiple, empty, None, malformed, mixed, registered in extractors.

### 8. Dependency edge processing
1. Run: `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py::TestProcessDependencies -v`
2. **Expected:** 6/6 passed — edge creation, missing-target-skipped, error-isolation.

### 9. Tag resolution
1. Run: `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py::TestPullSyncTagResolution -v`
2. **Expected:** 2/2 passed — tag-ids-resolved-to-names, fallback-on-error.

### 10. parse_external_url
1. Run: `cd backend && uv run python -m pytest tests/test_monday_sync_engine.py::TestParseExternalUrl -v`
2. **Expected:** 10/10 passed — valid URL, None, empty, wrong format, trailing slash, numeric IDs.

### 11. Syntax validation
1. Run: `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/loop_guard.py').read()); ast.parse(open('apps/monday-sync/services/sync_engine.py').read()); ast.parse(open('apps/monday-sync/services/field_mapper.py').read()); print('All OK')"`
2. **Expected:** Prints "All OK".

### 12. No conflict markers
1. Run: `grep -rn "^<<<<<<< " apps/monday-sync/ backend/tests/test_monday_*.py`
2. **Expected:** No output (exit code 1).

## Edge Cases

### LoopGuard with empty/None/special IDs
1. Run: `cd backend && uv run python -m pytest tests/test_monday_loop_guard.py::TestLoopGuardEdgeCases -v`
2. **Expected:** 9/9 passed — None coercion, special chars, 500 concurrent marks, cleanup on empty.

### Dependency column with malformed data
1. TestExtractDependency covers malformed entries, mixed valid/invalid, non-dict linkedPulseIds.
2. **Expected:** Graceful degradation — partial extraction, empty list, no exceptions.

## Failure Signals

- Any test failure in `test_monday_*.py`
- SyntaxError on any service module
- Conflict markers in source files
- ImportError when loading loop_guard from sync_engine

## Requirements Proved By This UAT

- MON-09 (push sync) — TestPushSyncPipeline proves mutation, reverse mapping, lastSyncedAt, error isolation
- MON-10 (LoopGuard) — TestLoopGuardIntegrationPull + TestPushPullLoopGuardRoundTrip prove echo prevention
- MON-11 (dependency edges) — TestProcessDependencies + TestPullSyncDependencyEdges prove bpkm:dependsOn creation
- MON-12 (tags mapping) — TestPullSyncTagResolution proves tag ID → name resolution with fallback

## Not Proven By This UAT

- Runtime behavior against real/mock Monday.com API (S04 E2E)
- UI for triggering push sync (S04 Playwright)
- LoopGuard behavior across process restarts (by design, in-memory only)

## Notes for Tester

- All tests run in <1 second. No Docker needed.
- Use `_build_push_sync_context()` helper for new push-related tests.
- The `_loop_guard` singleton requires cleanup between test classes — check autouse fixture.
