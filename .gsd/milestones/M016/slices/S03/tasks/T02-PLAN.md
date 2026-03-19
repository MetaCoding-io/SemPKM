---
estimated_steps: 8
estimated_files: 2
---

# T02: Push sync engine with loop prevention and unit tests

**Slice:** S03 — Push Sync + Settings Polish + Admin Detail
**Milestone:** M016

## Description

Build the `push_sync(ctx)` orchestrator that detects changes to Linear-synced tasks in SemPKM, reverse-maps their properties back to Linear's GraphQL mutation format, and executes `issueUpdate` mutations. Also add loop prevention to `pull_sync()` so pushed changes aren't re-imported on the next poll.

The push sync pipeline: auth check → read sync state → SPARQL query for changed tasks → for each task: load workflow states (cached) → reverse map properties → execute issueUpdate → update lastSyncedAt → persist result summary.

Loop prevention strategy: after push_sync updates a task in Linear, it bumps that task's `bpkm:lastSyncedAt` to the current time. On next pull_sync, for each issue fetched from Linear, compare `issue.updatedAt` against the task's existing `lastSyncedAt` — if `updatedAt <= lastSyncedAt`, the change originated from our push, so skip the update (count as unchanged).

## Steps

1. **Add `_find_changed_tasks()` to `sync_engine.py`:**
   - SPARQL query: SELECT tasks WHERE `externalProvider = "linear"`, `bpkm:externalUuid` exists (has a Linear UUID), and `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt — treat as changed).
   - Also check `bpkm:syncDirection != "pull-only"` (respect per-task sync direction setting).
   - Return list of dicts: `{iri, externalUuid, status, priority, title, dueDate, teamId, lastSyncedAt}`.
   - Note: `teamId` isn't stored on the task — derive it from the sync_teams state. For v1, use the first team ID from sync_teams (push sync operates on all synced teams).

2. **Add `_resolve_workflow_states()` to `sync_engine.py`:**
   - Accepts LinearClient and list of team_ids.
   - For each team, calls `client.get_workflow_states(team_id)`.
   - Builds a `{state_type: state_id}` lookup dict (first match wins if multiple states of same type).
   - Returns the combined lookup dict. (For v1, workflow states are fetched fresh on each push run — simple and avoids stale cache issues.)

3. **Add `push_sync(ctx)` to `sync_engine.py`:**
   - Auth check (reuse `get_connection_status()`).
   - Read sync_teams from state. Check sync_direction state key — if "pull-only", return skipped.
   - Build LinearClient.
   - Call `_find_changed_tasks()` via `ctx.graph.query()`.
   - Call `_resolve_workflow_states()` for the synced teams.
   - For each changed task:
     - Call `build_issue_update_input()` from field_mapper with the task's current properties and workflow states.
     - If input_dict is empty (no pushable changes), skip.
     - Call `client.update_issue(task.externalUuid, input_dict)`.
     - Update the task's `lastSyncedAt` to current time via `object.patch` command (using `_submit_commands_batched`).
     - On per-task error: log warning, record in errors list, continue to next task.
   - Store `last_push_result` in state as JSON (for settings page display).
   - Return `{status, pushed, skipped, errors}`.

4. **Add loop prevention to `pull_sync()`:**
   - In the per-issue processing loop, after computing the slug and finding the existing task, check: if `existing` has a `lastSyncedAt` and the issue's `updatedAt` is ≤ `lastSyncedAt`, skip this issue (increment `unchanged_count`, continue).
   - Modify `_find_existing_task()` to also return `lastSyncedAt` in the SPARQL result.
   - Parse dates for comparison: `updatedAt` is ISO-8601 from Linear, `lastSyncedAt` is ISO-8601 stored during sync. String comparison works for ISO-8601 dates in the same timezone.

5. **Write ~25 unit tests in `test_push_sync.py` (appending to the file created in T01):**
   - `push_sync()` skips when not connected.
   - `push_sync()` skips when sync_direction is "pull-only".
   - `push_sync()` skips when no changed tasks found.
   - `push_sync()` detects changed tasks via SPARQL query.
   - `push_sync()` calls `update_issue()` with correct issue UUID and input dict.
   - `push_sync()` updates `lastSyncedAt` on pushed tasks via object.patch.
   - `push_sync()` stores `last_push_result` in state.
   - `push_sync()` isolates per-task errors (one failure doesn't abort others).
   - `push_sync()` result contains pushed/skipped/errors counts.
   - `push_sync()` fetches workflow states for each team.
   - `push_sync()` skips tasks with no pushable changes (empty update input).
   - Loop prevention: `pull_sync()` skips issue when `updatedAt <= lastSyncedAt`.
   - Loop prevention: `pull_sync()` processes issue when `updatedAt > lastSyncedAt`.
   - Loop prevention: `pull_sync()` processes issue when no `lastSyncedAt` on existing task.
   - `_find_changed_tasks()` returns correct dict shape from SPARQL bindings.
   - `_resolve_workflow_states()` builds correct lookup dict from LinearClient response.

6. **Store `last_pull_result` in `pull_sync()`:**
   - At the end of `pull_sync()`, add `await ctx.state.set("last_pull_result", json.dumps(result))` before returning. This parallels the `last_push_result` storage in `push_sync()` and gives T03's settings page both result sets.

7. **Run full test suite to confirm integration:**
   - `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v`

8. **Syntax-check modified files and verify logger output patterns match S02 convention** (logger name `linear_sync.sync`, INFO for start/complete with counts, WARNING for per-task failures).

## Must-Haves

- [ ] `_find_changed_tasks()` SPARQL query finds tasks with modified > lastSyncedAt
- [ ] `_resolve_workflow_states()` fetches and builds state_type → state_id lookup
- [ ] `push_sync(ctx)` orchestrates full push pipeline with per-task error isolation
- [ ] `push_sync()` updates lastSyncedAt on each pushed task
- [ ] `push_sync()` stores last_push_result JSON in state
- [ ] Loop prevention in pull_sync: skip issues where updatedAt ≤ lastSyncedAt
- [ ] `_find_existing_task()` also returns lastSyncedAt
- [ ] `pull_sync()` stores last_pull_result JSON in state (parallel to push_sync's last_push_result)
- [ ] ~25 unit tests covering all push sync and loop prevention logic
- [ ] All existing 81+ tests still pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_push_sync.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v` — full suite passes (81 existing + all new)
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"` — syntax valid

## Observability Impact

- Signals added: Logger `linear_sync.sync` at INFO for push sync start/complete with `{pushed, skipped, errors}` counts; WARNING for per-task push failures
- How a future agent inspects this: StateClient key `last_push_result` (JSON with status/counts/errors), `last_sync_at` (ISO timestamp)
- Failure state exposed: Per-task errors in push_sync return dict `errors` list with `{iri, error}` entries

## Inputs

- `apps/linear-sync/services/field_mapper.py` — T01's reverse mapping functions: `reverse_status()`, `reverse_priority()`, `build_issue_update_input()`, BPKM prefix, and externalUuid storage in `build_task_properties()`
- `apps/linear-sync/services/linear_client.py` — T01's `get_workflow_states()` and `update_issue()` methods
- `apps/linear-sync/services/sync_engine.py` — existing `pull_sync()`, `_find_existing_task()`, `_submit_commands_batched()`, `BATCH_SIZE`
- `backend/tests/test_push_sync.py` — T01's test file with importlib loading setup and mock classes
- `apps/linear-sync/services/auth.py` — `get_connection_status()` for auth check
- S02 Forward Intelligence: `_submit_commands_batched()` reusable for push sync bulk mutations; full IRI keys for bpkm properties

## Expected Output

- `apps/linear-sync/services/sync_engine.py` — extended with `_find_changed_tasks()`, `_resolve_workflow_states()`, `push_sync(ctx)`, and loop prevention in `pull_sync()`
- `backend/tests/test_push_sync.py` — extended with ~25 additional unit tests for push sync and loop prevention
