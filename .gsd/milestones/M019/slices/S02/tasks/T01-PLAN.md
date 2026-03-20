---
estimated_steps: 6
estimated_files: 2
---

# T01: Implement push_sync engine with close/reopen branching and unit tests

**Slice:** S02 — Push Sync + Settings UI
**Milestone:** M019

## Description

Build the push sync engine that detects locally changed Todoist tasks, branches on status change direction (close vs reopen), updates non-status fields, and prevents sync loops. The key novelty vs github-sync is that Todoist uses separate `POST /tasks/{id}/close` and `POST /tasks/{id}/reopen` endpoints for status changes instead of PATCH. Status changes must be processed before field updates (close/reopen first, then update_task for other fields).

Also add loop prevention to the existing `pull_sync()` — skip tasks whose remote `updated_at` isn't newer than the task's `lastSyncedAt` timestamp (set by push_sync). This prevents re-importing changes we just pushed.

## Steps

1. **Add `_find_changed_tasks()` to `sync_engine.py`** — SPARQL query that finds bpkm:Task objects with `externalProvider = "todoist"` and `externalUuid` set, where `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt). Returns list of dicts with iri, externalId, externalUuid, status, title, tags, lastSyncedAt. Use `STR(?modified) > STR(?lastSynced)` for string comparison (same pattern as github-sync). Add `syncDirection` filter to exclude pull-only tasks.

2. **Add `push_sync()` to `sync_engine.py`** — Main push pipeline:
   - Auth check via `get_connection_status()` — skip if not connected
   - Read `sync_direction` from `ctx.settings` — skip if "pull-only"
   - Call `_find_changed_tasks(ctx.graph)` — skip if empty
   - For each changed task:
     - Build `task_props` dict from SPARQL result fields (title, status, tags)
     - Check if status changed: compare `task["status"]` against `BPKM_TO_TODOIST_STATUS` — if it maps to `True` (is_completed), call `client.close_task(task["externalId"])`; if `False`, call `client.reopen_task(task["externalId"])`
     - Build reverse-mapped update body via `build_todoist_task_data(task_props)` — call `client.update_task(task["externalId"], update_data)` for non-status field changes
     - Update `lastSyncedAt` on the task via `object.patch` command through `_submit_commands_batched`
   - Store `last_push_result` in state (JSON with status, pushed, skipped, closed, reopened, updated, errors, timestamp)
   - TodoistClient is constructed as: `TodoistClient(http_client=ctx.http, state_client=ctx.state)`

3. **Add loop prevention to `pull_sync()`** — In the existing task processing loop, after fetching an existing task via `_find_existing_task()`, check if `existing.get("lastSyncedAt")` is set. If so, compare the Todoist task's `updated_at` (from the API response, keyed as "updated_at" — note: this field is returned by Todoist REST v2 in ISO 8601 format, but may not be present on all tasks). If `updated_at` is not newer than `lastSyncedAt`, skip the task (increment `unchanged_count`, continue). This prevents re-importing changes we just pushed.

4. **Add necessary imports** — Import `BPKM_TO_TODOIST_STATUS` and `build_todoist_task_data` from `services.field_mapper` (following the existing try/except import pattern). Import `TodoistClient` if not already imported.

5. **Write comprehensive unit tests in `test_todoist_push_sync.py`** — Create a new test file following the pattern from `backend/tests/test_todoist_sync_engine.py` (same MockResponse, MockCtx, MockGraphClient, MockStateClient, MockSettingsClient fixtures). Cover:
   - `_find_changed_tasks`: SPARQL query structure (contains "todoist", correct FILTER clauses), result parsing (multiple tasks, empty results)
   - `push_sync` pipeline: not connected → skipped, pull-only direction → skipped, no changed tasks → ok with 0 counts, successful close (status "done" → close_task called), successful reopen (status "todo" → reopen_task called), field-only update (no status change → update_task only, no close/reopen), combined status+field (close first, then update), push error isolation (one task fails, others succeed), result structure validation
   - Loop prevention in pull_sync: task with lastSyncedAt newer than updated_at → skipped, task without lastSyncedAt → processed normally
   - `lastSyncedAt` update after push (object.patch command submitted with push timestamp)
   - **Important pattern**: Use `data if data is not None else {}` (not `data or {}`) in MockResponse per KNOWLEDGE.md pattern #2

6. **Run all Todoist tests together** to verify no regressions: `python -m pytest backend/tests/test_todoist_*.py -v`

## Must-Haves

- [ ] `_find_changed_tasks()` returns tasks with externalProvider="todoist" and modified > lastSyncedAt
- [ ] `push_sync()` calls `close_task()` when status maps to is_completed=True
- [ ] `push_sync()` calls `reopen_task()` when status maps to is_completed=False
- [ ] `push_sync()` calls `update_task()` for non-status field changes
- [ ] Status change processed before field update in the same task
- [ ] `lastSyncedAt` updated on each pushed task via object.patch
- [ ] Loop prevention in pull_sync skips tasks where updated_at ≤ lastSyncedAt
- [ ] `last_push_result` stored in state with correct structure
- [ ] 35+ unit tests covering all push paths

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_todoist_push_sync.py -v` — 35+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_todoist_*.py -v` — all Todoist tests (168 + 35+ = 203+) pass in <3s

## Inputs

- `apps/todoist-sync/services/sync_engine.py` — existing pull_sync, _find_existing_task, _submit_commands_batched, _make_result functions
- `apps/todoist-sync/services/field_mapper.py` — BPKM_TO_TODOIST_STATUS dict (maps "done"→True, "todo"→False, etc.), build_todoist_task_data() reverse mapper
- `apps/todoist-sync/services/todoist_client.py` — close_task(task_id), reopen_task(task_id), update_task(task_id, data) methods
- `apps/todoist-sync/services/auth.py` — get_connection_status(state_client, http_client)
- `backend/tests/test_todoist_sync_engine.py` — reference test patterns (MockResponse, MockCtx, MockGraphClient, MockStateClient, MockCommandsClient)
- `apps/github-sync/services/sync_engine.py` lines 181-380 — reference implementation for _find_changed_tasks SPARQL and push_sync pipeline structure

## Observability Impact

- **New state key:** `last_push_result` — JSON with `{status, pushed, skipped, closed, reopened, updated, errors, timestamp}`. Inspect via `ctx.state.get("last_push_result")`.
- **Logger:** `todoist.sync` — INFO per push cycle with aggregate counts, WARNING per individual task push failure.
- **Failure state:** `last_push_result.errors` array — each entry has `{iri, error}` for per-task diagnosis. Status field is "error" when all tasks fail, "partial" when some succeed.
- **Loop prevention signal:** `lastSyncedAt` property on each task — set after successful push. `pull_sync` skips tasks where remote `updated_at ≤ lastSyncedAt`, logging to `unchanged_count`.

## Expected Output

- `apps/todoist-sync/services/sync_engine.py` — extended with `_find_changed_tasks()` and `push_sync()` functions, pull_sync updated with loop prevention
- `backend/tests/test_todoist_push_sync.py` — new test file with 35+ tests covering push sync pipeline, close/reopen branching, loop prevention, and result structure
