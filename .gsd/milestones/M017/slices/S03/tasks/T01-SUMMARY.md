---
id: T01
parent: S03
milestone: M017
provides:
  - push_sync() engine with SPARQL change detection and GitHub PATCH
  - parse_external_url() for issue/PR URL decomposition
  - _find_changed_tasks() SPARQL query with modified > lastSyncedAt filter
  - Loop prevention in pull_sync via lastSyncedAt comparison
  - lastSyncedAt field in build_task_properties and _find_existing_task
key_files:
  - apps/github-sync/services/sync_engine.py
  - apps/github-sync/services/field_mapper.py
  - backend/tests/test_github_sync_engine.py
  - backend/tests/test_github_field_mapper.py
key_decisions:
  - sync_direction read from ctx.settings (not ctx.state) matching GitHub app's settings pattern
  - Tags from SPARQL come as single strings; push_sync wraps in list for build_issue_patch
  - parse_external_url accepts both github.com and www.github.com hostnames
patterns_established:
  - Push sync follows linear-sync pattern: auth check → direction check → find changed → per-task push → update lastSyncedAt → store result
  - Loop prevention via string comparison of ISO timestamps (updated_at <= lastSyncedAt)
observability_surfaces:
  - last_push_result StateClient key — JSON with status/pushed/skipped/errors/timestamp
  - Per-task errors in errors list with IRI and error message
  - Logger github_sync.sync at INFO for push start/complete, WARNING for per-task errors
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Push sync engine with loop prevention and field mapper extensions

**Implemented push_sync() pipeline, _find_changed_tasks() SPARQL query, parse_external_url(), lastSyncedAt tracking in build_task_properties/_find_existing_task, and loop prevention in pull_sync — 33 new tests all passing.**

## What Happened

Added the core push sync engine to the GitHub sync app, following the linear-sync pattern:

1. **field_mapper.py**: Added `parse_external_url()` that decomposes GitHub issue/PR URLs into (owner, repo, number) tuples. Extended `build_task_properties()` with a `sync_time` parameter and always-present `bpkm:lastSyncedAt` in the output (survives the None/empty stripping).

2. **sync_engine.py**: Added `_find_changed_tasks()` SPARQL query that finds tasks with `externalProvider "github"` where `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt). Added `push_sync(ctx)` that: checks auth → checks sync_direction from settings → finds changed tasks → for each: builds issue patch via reverse mapping → parses external URL → calls `github_client.patch_issue()` → updates lastSyncedAt via bulk command → stores `last_push_result` in StateClient.

3. Extended `_find_existing_task()` to return `lastSyncedAt` via an OPTIONAL SPARQL clause.

4. Added loop prevention to `pull_sync()`: after finding an existing task, compares `issue["updated_at"] <= existing["lastSyncedAt"]` and skips the issue if true, preventing re-import of changes we just pushed.

5. Updated the MockGraphClient in tests to support rich task data (dict values in slug_map with optional lastSyncedAt).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py -v` — 127 tests pass (94 existing + 33 new)
- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py tests/test_github_client.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` — all 189 tests pass
- New test count: 33 (≥25 required)
- `test_last_push_result_structure` confirms status/pushed/errors/timestamp in last_push_result

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py -v` | 0 | ✅ pass | 0.12s |
| 2 | `pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py tests/test_github_client.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` | 0 | ✅ pass | 0.20s |

## Diagnostics

- **last_push_result** in StateClient: JSON with `{status, pushed, skipped, errors, timestamp}`. Read via `ctx.state.get("last_push_result")`.
- **errors** list contains per-task dicts with `{iri, error}` for failed pushes.
- Logger `github_sync.sync` emits INFO on push start/complete with counts, WARNING for per-task failures.
- PAT is never included in push result or error messages.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/github-sync/services/field_mapper.py` — Added `parse_external_url()`, extended `build_task_properties()` with sync_time/lastSyncedAt
- `apps/github-sync/services/sync_engine.py` — Added `_find_changed_tasks()`, `push_sync()`, extended `_find_existing_task()` with lastSyncedAt, loop prevention in `pull_sync()`, new imports for `build_issue_patch` and `parse_external_url`
- `backend/tests/test_github_field_mapper.py` — 13 new tests (TestParseExternalUrl: 10, TestBuildTaskPropertiesLastSyncedAt: 3)
- `backend/tests/test_github_sync_engine.py` — 20 new tests (TestFindExistingTaskLastSyncedAt: 2, TestFindChangedTasks: 3, TestPushSync: 8, TestLoopPrevention: 4, TestPushSyncDiagnostics: 3), updated MockGraphClient to support dict slug_map values
