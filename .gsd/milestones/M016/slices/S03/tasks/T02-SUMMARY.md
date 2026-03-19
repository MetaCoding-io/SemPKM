---
id: T02
parent: S03
milestone: M016
provides:
  - push_sync(ctx) orchestrator — detects changed tasks, reverse-maps properties, executes issueUpdate mutations, updates lastSyncedAt
  - _find_changed_tasks() SPARQL query for tasks with modified > lastSyncedAt
  - _resolve_workflow_states() builds (team_id, state_type) → state_id lookup
  - Loop prevention in pull_sync() — skips issues where updatedAt ≤ lastSyncedAt
  - _find_existing_task() now returns lastSyncedAt in result dict
  - pull_sync() stores last_pull_result JSON in state (parallels push_sync's last_push_result)
  - 25 new unit tests for push sync orchestration, change detection, loop prevention
key_files:
  - apps/linear-sync/services/sync_engine.py
  - backend/tests/test_push_sync.py
key_decisions:
  - "push_sync uses first team_id from sync_teams for workflow state lookup (v1 simplification — single-team push)"
  - "_find_changed_tasks SPARQL filters with FILTER(!BOUND(?syncDir) || ?syncDir != 'pull-only') and FILTER(!BOUND(?lastSynced) || !BOUND(?modified) || STR(?modified) > STR(?lastSynced)) for change detection"
  - "Loop prevention uses string comparison on ISO-8601 timestamps — works because both Linear updatedAt and bpkm:lastSyncedAt are in the same format"
patterns_established:
  - "push_sync follows same auth-check → state-read → process → store-result pattern as pull_sync"
  - "Per-task error isolation: try/except around each task, errors accumulated in list, processing continues"
observability_surfaces:
  - "StateClient key last_push_result — JSON with {status, pushed, skipped, errors}"
  - "StateClient key last_pull_result — JSON with {status, created, updated, unchanged, errors}"
  - "Logger linear_sync.sync at INFO for push sync start/complete with counts; WARNING for per-task failures"
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Push sync engine with loop prevention and unit tests

**Added push_sync() orchestrator with SPARQL change detection, issueUpdate mutations, lastSyncedAt updates, and loop prevention in pull_sync() — 25 new tests, 150 total passing**

## What Happened

Built the complete push sync pipeline in `sync_engine.py`:

1. `_find_changed_tasks()` — SPARQL query that finds Linear-synced tasks with `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt), excluding pull-only tasks.

2. `_resolve_workflow_states()` — Fetches workflow states for each synced team via LinearClient, builds a `(team_id, state_type) → state_id` lookup dict. First match wins for duplicate state types.

3. `push_sync(ctx)` — Full orchestrator: auth check → read sync state (direction, teams) → find changed tasks → fetch workflow states → for each task: build properties dict → `build_issue_update_input()` → `client.update_issue()` → update lastSyncedAt via `object.patch` → store `last_push_result` in state. Per-task errors are isolated and accumulated.

4. Loop prevention in `pull_sync()` — After finding an existing task, if the task has a `lastSyncedAt` and the issue's `updatedAt ≤ lastSyncedAt`, the issue is skipped (change originated from our push). Modified `_find_existing_task()` to also return `lastSyncedAt` from SPARQL.

5. Added `last_pull_result` storage in `pull_sync()` — parallels the `last_push_result` in `push_sync()`, giving T03's settings page both result sets.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v` — 69 tests pass (44 T01 + 25 T02)
- `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v` — all 150 tests pass
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"` — syntax valid
- `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v -k "error or unknown or missing"` — 6 failure-path tests pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_push_sync.py -v` | 0 | ✅ pass | 0.12s |
| 2 | `pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v` | 0 | ✅ pass | 0.14s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read())"` | 0 | ✅ pass | <1s |
| 6 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 7 | `pytest tests/test_push_sync.py -v -k "error or unknown or missing"` | 0 | ✅ pass | 0.03s |

## Diagnostics

- `last_push_result` state key contains JSON `{status, pushed, skipped, errors}` — inspect via StateClient or settings page (T03)
- `last_pull_result` state key contains JSON `{status, created, updated, unchanged, errors}` — same inspection path
- Per-task push errors include `{iri, error}` entries in the errors list
- Logger `linear_sync.sync` at INFO shows push sync start/complete with counts; WARNING for per-task failures
- Empty `build_issue_update_input()` return (no pushable changes) causes task skip — visible in `skipped` count

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/linear-sync/services/sync_engine.py` — Added `_find_changed_tasks()`, `_resolve_workflow_states()`, `push_sync()`, loop prevention in `pull_sync()`, `last_pull_result` storage, `lastSyncedAt` in `_find_existing_task()`, `build_issue_update_input` import
- `backend/tests/test_push_sync.py` — Added 25 unit tests covering push sync orchestration (skips, execution, error isolation, workflow state fetching), `_find_changed_tasks()` shape, `_resolve_workflow_states()` lookup, loop prevention (4 scenarios), `_find_existing_task()` lastSyncedAt, and `pull_sync()` last_pull_result storage
