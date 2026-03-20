---
id: T01
parent: S02
milestone: M019
provides:
  - push_sync() engine with close/reopen branching for Todoist status changes
  - _find_changed_tasks() SPARQL query for locally modified Todoist tasks
  - Loop prevention in pull_sync via lastSyncedAt comparison
key_files:
  - apps/todoist-sync/services/sync_engine.py
  - backend/tests/test_todoist_push_sync.py
key_decisions:
  - Used externalId (not externalUuid) in _find_changed_tasks since Todoist pull_sync sets externalId via field_mapper
patterns_established:
  - Todoist close/reopen endpoints called before update_task for same-task status+field changes
observability_surfaces:
  - last_push_result state key — JSON with status, pushed, skipped, closed, reopened, updated, errors, timestamp
  - todoist.sync logger — INFO per push cycle, WARNING per task failure
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Implement push_sync engine with close/reopen branching and unit tests

**Added push_sync() with close/reopen branching, _find_changed_tasks() SPARQL, pull_sync loop prevention, and 46 unit tests**

## What Happened

Implemented the complete push sync pipeline for Todoist:

1. Added `_find_changed_tasks()` — SPARQL query that finds `bpkm:Task` objects with `externalProvider="todoist"` where `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt). Includes `syncDirection` filter to exclude pull-only tasks. Uses the same `STR()` comparison pattern as github-sync.

2. Added `push_sync()` — Main pipeline that: checks auth, reads sync_direction from settings (skips if "pull-only"), finds changed tasks, then for each task: detects status → calls `close_task()` or `reopen_task()` via dedicated endpoints, builds reverse-mapped update body → calls `update_task()` for non-status fields, then updates `lastSyncedAt` via `object.patch`. Status change is processed before field update. Results stored in `last_push_result` state key.

3. Added loop prevention to `pull_sync()` — After finding an existing task, checks if `lastSyncedAt` is set and compares against the remote `updated_at`. If remote isn't newer, skips the task (increments `unchanged_count`).

4. Imported `BPKM_TO_TODOIST_STATUS` and `build_todoist_task_data` from field_mapper following the existing try/except import pattern.

Deviation from plan: Used `externalId` instead of `externalUuid` in `_find_changed_tasks()` because the Todoist pull sync (via `build_task_properties`) only sets `externalId`, not `externalUuid`. The plan referenced the github-sync pattern which uses `externalUuid`, but that doesn't apply to Todoist.

## Verification

- 46 push sync tests pass covering all pipeline paths
- 214 total Todoist tests pass (168 existing + 46 new) with no regressions
- All tests complete in 0.25s
- Error isolation tests confirm per-task failure doesn't block others

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest backend/tests/test_todoist_push_sync.py -v` | 0 | ✅ pass | 0.11s |
| 2 | `python -m pytest backend/tests/test_todoist_*.py -v` | 0 | ✅ pass | 0.25s |
| 3 | `python -m pytest backend/tests/test_todoist_push_sync.py -v -k "error"` | 0 | ✅ pass | 0.03s |

## Diagnostics

- **Push results:** `await ctx.state.get("last_push_result")` → JSON with status, pushed, skipped, closed, reopened, updated, errors, timestamp
- **Per-task errors:** `last_push_result.errors` array, each entry has `{iri, error}`
- **Logger:** `todoist.sync` — INFO with aggregate counts, WARNING per task failure
- **Loop prevention:** `unchanged_count` in pull result tracks tasks skipped by lastSyncedAt comparison

## Deviations

Used `externalId` instead of `externalUuid` in `_find_changed_tasks()` — the Todoist pull sync only populates `externalId`, not `externalUuid`. This is the correct field for Todoist tasks.

## Known Issues

None.

## Files Created/Modified

- `apps/todoist-sync/services/sync_engine.py` — Added `_find_changed_tasks()`, `push_sync()`, loop prevention in `pull_sync()`, new imports for `BPKM_TO_TODOIST_STATUS` and `build_todoist_task_data`
- `backend/tests/test_todoist_push_sync.py` — New test file with 46 tests covering push pipeline, close/reopen branching, field-only updates, ordering, lastSyncedAt updates, error isolation, loop prevention, result structure, and MockResponse pattern
