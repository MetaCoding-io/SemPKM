---
id: T01
parent: S03
milestone: M023
provides:
  - Real push_sync implementation replacing stub — SPARQL change detection, reverse field mapping, Jira API update, lastSyncedAt loop prevention
  - _find_changed_tasks() SPARQL function for Jira-provider task change detection
  - _get_task_body() SPARQL helper for reading task body text by IRI
  - build_issue_patch() extended with description_adf parameter for ADF description push
  - markdown_to_adf integration for push sync description conversion
key_files:
  - apps/jira-sync/services/sync_engine.py
  - apps/jira-sync/services/field_mapper.py
  - backend/tests/test_jira_sync_engine.py
key_decisions:
  - Push sync result uses "success" status (not "ok") for consistency with connect_status.html template
  - Push result includes "timestamp" field alongside pushed/skipped/errors for diagnostics
  - Per-task error isolation: each task wrapped in try/except, errors collected in list, status computed from counts
patterns_established:
  - MockGraphClient extended with body_map and changed_tasks for push sync testing — downstream tests can reuse
  - MockJiraClient tracks update_issue calls via update_issue_calls list for assertion
observability_surfaces:
  - ctx.state "last_push_result" — JSON with status/pushed/skipped/errors/timestamp
  - Structured logging at INFO for push phases, WARNING for per-task errors
  - errors list with per-task {iri, error} dicts in push result
duration: 25m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Implement real push sync with SPARQL change detection and ADF description conversion

**Replaced push_sync stub with real bidirectional push pipeline: SPARQL change detection → reverse field mapping → ADF description conversion → Jira API update → lastSyncedAt loop prevention**

## What Happened

Implemented the full push sync pipeline in sync_engine.py following the proven Linear/GitHub push pattern:

1. Added `_find_changed_tasks()` — SPARQL query that finds Jira-provider tasks where `dcterms:modified > bpkm:lastSyncedAt` (or no lastSyncedAt), filtering out pull-only tasks. Returns list of dicts with iri, externalId, status, priority, title, lastSyncedAt.

2. Added `_get_task_body()` — SPARQL helper that reads body text via `urn:sempkm:body` predicate for a given task IRI. Returns the body string or None.

3. Extended `build_issue_patch()` in field_mapper.py to accept optional `description_adf: dict | None` parameter. When provided and non-empty, includes the ADF document as the `description` field in the Jira update payload.

4. Replaced the `push_sync()` stub with the real implementation: auth check → direction check → find changed tasks → for each task: read body via SPARQL, convert to ADF via `markdown_to_adf()`, build issue patch with title/priority/description, call `client.update_issue(externalId, fields)`, update lastSyncedAt. Per-task error isolation wraps each task in try/except.

5. Added `markdown_to_adf` and `build_issue_patch` to the import block in sync_engine.py.

6. Wrote 32 new tests across 4 test classes (TestFindChangedTasks: 6, TestGetTaskBody: 4, TestBuildIssuePatchWithDescription: 5, TestPushSyncReal: 17). Updated 3 existing stub tests to match new behavior. Extended MockGraphClient with `body_map` and `changed_tasks` support. Extended MockJiraClient with `update_issue` call tracking.

## Verification

- All 127 tests pass (95 existing + 32 new) — `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -v --noconftest`
- Python syntax validation passes for both sync_engine.py and field_mapper.py
- Error isolation tests pass — push errors list, per-task isolation, partial/error status
- sync_engine.py grew from ~666 to 839 lines; test file from ~2328 to 3130 lines

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -v --noconftest` | 0 | ✅ pass | 0.35s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read()); ast.parse(open('apps/jira-sync/services/field_mapper.py').read()); print('VALID')"` | 0 | ✅ pass | <1s |
| 3 | `grep -c "push_sync\|_find_changed_tasks" apps/jira-sync/services/sync_engine.py` → 6 | 0 | ✅ pass | <1s |
| 4 | `./backend/.venv/bin/pytest backend/tests/test_jira_sync_engine.py -k "error" -v --noconftest` → 11 passed | 0 | ✅ pass | 0.11s |

## Diagnostics

- **Push result inspection:** `ctx.state.get("last_push_result")` returns JSON with `{status, pushed, skipped, errors, timestamp}`
- **Error details:** `errors` list contains `{iri, error}` dicts for each failed task push
- **Status values:** `"success"` (all ok), `"partial"` (some failed), `"error"` (all failed), `"skipped"` (not connected or pull-only)
- **Logging:** INFO-level logs for push phase transitions ("found N changed tasks", "Push sync complete"), WARNING for per-task errors

## Deviations

- Test file requires `--noconftest` flag due to a pre-existing conftest.py import error (pydantic Settings validation) unrelated to this task. The conftest is for the main backend app, not the Jira sync tests.
- Added 32 new tests instead of the planned ~30 — slightly more coverage for edge cases.

## Known Issues

- `_process_issue_links` not yet present (T02 scope) — slice-level grep for all three functions will only fully pass after T02.
- conftest.py has a pre-existing `linear_api_key` extra field error in Settings — affects `pytest` without `--noconftest` but doesn't impact Jira sync tests.

## Files Created/Modified

- `apps/jira-sync/services/sync_engine.py` — Added `_find_changed_tasks()`, `_get_task_body()`, replaced `push_sync()` stub with real implementation. Added `markdown_to_adf` and `build_issue_patch` imports. (666→839 lines)
- `apps/jira-sync/services/field_mapper.py` — Extended `build_issue_patch()` with `description_adf` parameter. (403→413 lines)
- `backend/tests/test_jira_sync_engine.py` — Added 4 new test classes (32 tests), updated 3 existing stub tests, extended MockGraphClient and MockJiraClient. (2328→3130 lines)
