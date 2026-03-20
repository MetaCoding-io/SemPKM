# S02: Push Sync + Settings UI — UAT

**Milestone:** M019
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Push sync logic and settings wiring are comprehensively tested by 71 dedicated unit tests covering all pipeline paths, branching, error isolation, and template context. No live runtime needed — the mock patterns prove correctness without Docker.

## Preconditions

- Python 3.12+ available with uv for running pytest
- Working directory is the M018 worktree at `.gsd/worktrees/M018`
- S01 code in place (auth, client, field_mapper, person_matcher, pull_sync)

## Smoke Test

Run `cd backend && uv run python -m pytest tests/test_todoist_push_sync.py -v` — all 71 tests pass in <1s. This confirms push_sync, settings routes, and template context are all wired correctly.

## Test Cases

### 1. Push sync closes a completed task

1. A Todoist task pulled into SemPKM has status "todo" and lastSyncedAt set
2. User marks task as "done" in SemPKM (dcterms:modified advances past lastSyncedAt)
3. push_sync() detects status change via `_find_changed_tasks()` SPARQL
4. **Expected:** `close_task()` is called on the TodoistClient (POST /tasks/{id}/close). The task's lastSyncedAt is updated to prevent re-import loop. `last_push_result` has `closed: 1`.

**Proven by:** `TestPushSyncClose::test_close_task_called_for_done_status`, `TestPushSyncClose::test_close_called_for_cancelled_status`

### 2. Push sync reopens a task

1. A Todoist task pulled into SemPKM has status "done" (was completed)
2. User changes status back to "todo" in SemPKM
3. push_sync() detects status change from done→todo
4. **Expected:** `reopen_task()` is called (POST /tasks/{id}/reopen). `last_push_result` has `reopened: 1`.

**Proven by:** `TestPushSyncReopen::test_reopen_task_called_for_todo_status`, `TestPushSyncReopen::test_reopen_called_for_in_progress`, `TestPushSyncReopen::test_reopen_called_for_blocked`

### 3. Close/reopen executes before field update

1. A task has both status change (todo→done) and title change in the same push cycle
2. push_sync() processes the task
3. **Expected:** `close_task()` is called BEFORE `update_task()`. This ordering prevents Todoist API issues where updating a closed task might reopen it.

**Proven by:** `TestPushSyncOrdering::test_close_before_update`, `TestPushSyncOrdering::test_reopen_before_update`

### 4. Field-only update (no status change)

1. User changes only the title/labels/due date of a synced Todoist task, status unchanged
2. push_sync() detects the modification
3. **Expected:** Neither `close_task()` nor `reopen_task()` is called. Only `update_task()` with the reverse-mapped fields (title→content, priority→integer, tags→labels, dueDate→due_date).

**Proven by:** `TestPushSyncFieldOnly::test_update_task_called_for_title_change`, `TestPushSyncFieldOnly::test_update_sends_content_field`, `TestPushSyncFieldOnly::test_update_with_tags`

### 5. Push skipped for empty field updates

1. Task's dcterms:modified advanced (triggering change detection) but no actual field values differ
2. push_sync() detects the task but `build_todoist_task_data()` returns empty dict
3. **Expected:** No `update_task()` call. Task counted as pushed but with no API mutation.

**Proven by:** `TestPushSyncFieldOnly::test_skipped_when_no_fields_to_update`

### 6. Loop prevention in pull_sync

1. push_sync() updates a task in Todoist and sets lastSyncedAt
2. Next poll via pull_sync() sees the same task with remote `updated_at` ≤ `lastSyncedAt`
3. **Expected:** pull_sync() skips the task (no re-import). Increments `unchanged_count` in result.

**Proven by:** `TestPullSyncLoopPrevention::test_skips_task_with_stale_updated_at`, `TestPullSyncLoopPrevention::test_processes_task_with_newer_updated_at`

### 7. Push skipped when not connected

1. No Todoist token stored (auth not configured)
2. push_sync() is called
3. **Expected:** Returns immediately with `status: "skipped"`, `reason: "not_connected"`. No API calls made.

**Proven by:** `TestPushSyncSkipped::test_skipped_when_not_connected`

### 8. Push skipped when direction is pull-only

1. User has set sync_direction to "pull-only" in settings
2. push_sync() is called
3. **Expected:** Returns immediately with `status: "skipped"`, `reason: "pull_only"`. No API calls made.

**Proven by:** `TestPushSyncSkipped::test_skipped_when_pull_only_direction`

### 9. Sync config route saves settings

1. POST to `/_fragments/settings/sync-config` with `sync_direction=bidirectional&poll_interval=30m`
2. **Expected:** `ctx.settings.set("sync_direction", "bidirectional")` and `ctx.settings.set("poll_interval", "30m")` are called. Returns HTML response (re-rendered connect_status).

**Proven by:** `TestSyncConfigRoute::test_saves_sync_direction`, `TestSyncConfigRoute::test_saves_poll_interval`, `TestSyncConfigRoute::test_returns_html_response`

### 10. Bidirectional sync_now runs both pull and push

1. sync_direction is set to "bidirectional"
2. User clicks Sync Now
3. **Expected:** pull_sync() runs first, then push_sync() runs. Both results recorded. `last_sync_at` updated.

**Proven by:** `TestSyncNowBidirectional::test_calls_push_sync_when_bidirectional`, `TestSyncNowBidirectional::test_updates_last_sync_at`

### 11. Template context includes all settings and push result

1. `_render_connect_status()` is called after a push has occurred
2. **Expected:** Template receives `sync_direction`, `poll_interval`, `last_push_result`, and `last_sync_at` variables. Defaults are "pull-only", "15m", None, and "" respectively.

**Proven by:** `TestRenderConnectStatus` (9 tests covering all variables and defaults)

### 12. All htmx URLs use app proxy prefix

1. Scan all `hx-post=` and `hx-get=` attributes in Todoist templates
2. **Expected:** Every URL starts with `/app/todoist-sync/`. No bare `/_fragments/` paths.

**Proven by:** `TestHtmxPrefixVerification` (3 tests) + `rg "hx-(post|get)=" | grep -v "/app/todoist-sync/"` returns empty

## Edge Cases

### Per-task error isolation

1. Push sync processes 3 tasks. Task 2 throws an exception during close_task()
2. **Expected:** Tasks 1 and 3 still process successfully. `last_push_result.errors` contains one entry with task 2's IRI and error message. Overall status is "ok" (not "error") because some succeeded.

**Proven by:** `TestPushSyncErrorIsolation::test_one_task_error_doesnt_block_others`

### All tasks error

1. Push sync processes 2 tasks, both throw exceptions
2. **Expected:** `last_push_result.status` is "error". `errors` array has 2 entries.

**Proven by:** `TestPushSyncErrorIsolation::test_all_tasks_error_gives_error_status`

### Push error doesn't crash sync_now

1. Bidirectional sync_now: pull_sync succeeds, push_sync throws an unhandled exception
2. **Expected:** sync_now still returns successfully (pull results preserved). Push failure logged but not propagated.

**Proven by:** `TestSyncNowBidirectional::test_push_error_isolated_from_pull`

### Unknown status value in push

1. A task has an unexpected status value not in BPKM_TO_TODOIST_STATUS mapping
2. **Expected:** No close or reopen call made. Only field update proceeds if fields changed.

**Proven by:** `TestPushSyncStatusMapping::test_unknown_status_no_close_or_reopen`

### MockResponse empty list preservation

1. Mock returns `MockResponse(200, [])` for tasks endpoint
2. **Expected:** Response `.json()` returns `[]`, not `{}`. (K002 lesson — Python `[] or {}` is `{}`).

**Proven by:** `TestMockResponsePattern::test_empty_list_data_not_coerced_to_dict`

## Failure Signals

- Any of the 71 tests in `test_todoist_push_sync.py` failing
- `rg "hx-(post|get)=" apps/todoist-sync/frontend/templates/ | grep -v "/app/todoist-sync/"` returning results (htmx URLs missing prefix)
- `last_push_result` state key missing expected keys (status, pushed, skipped, closed, reopened, updated, errors, timestamp)
- push_sync calling update_task before close_task/reopen_task (ordering violation)

## Requirements Proved By This UAT

- TD-03 (push sync) — push_sync correctly branches close/reopen/update with error isolation and loop prevention
- TD-07 (settings UI) — direction radios, poll interval dropdown, push stats, bidirectional sync_now

## Not Proven By This UAT

- TD-08 (E2E + user guide) — no live runtime test or documentation; deferred to S03
- Real Todoist API interaction — all tests use mocks; E2E with mock server is S03 scope
- Template rendering fidelity — tests verify template context variables but not actual HTML output in a browser

## Notes for Tester

- All 71 tests are deterministic and fast (<1s). No flaky tests.
- The `externalId` (not `externalUuid`) divergence from github-sync is intentional — Todoist pull_sync only sets `externalId`.
- The push_changes task handler is wired but only exercised via unit test — the platform scheduler integration is S03 scope.
