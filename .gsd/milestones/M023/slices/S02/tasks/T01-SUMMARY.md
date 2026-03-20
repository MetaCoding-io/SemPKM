---
id: T01
parent: S02
milestone: M023
provides:
  - pull_sync(ctx) — complete Jira→bpkm:Task/Milestone pull pipeline
  - push_sync(ctx) — stub returning skipped status for S03
  - app.py sync_now/poll-tasks/push-changes handlers wired to real sync functions
key_files:
  - apps/jira-sync/services/sync_engine.py
  - apps/jira-sync/app.py
key_decisions:
  - Result dict uses "success"/"partial"/"error" (not "ok") to match connect_status.html template
  - Epic parent detection checks both next-gen parent.key and classic customfield_10014
patterns_established:
  - Two-phase bulk create with Phase 3 epic→child linking (extends Linear/GCal pattern)
  - _build_jql() with project keys, user filter, and ISO→JQL date conversion for delta sync
observability_surfaces:
  - ctx.state "last_pull_result" — JSON with status/created/updated/skipped/errors/failed_issues/duration_ms
  - ctx.state "last_push_result" — JSON with status/reason
  - Structured logging at INFO for all sync phases, WARNING for per-issue errors
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build sync_engine.py and wire app.py handlers

**Built Jira pull sync engine with two-phase bulk create, Epic→Milestone mapping, ADF→Markdown conversion, JQL construction, and wired all 3 app.py handlers**

## What Happened

Created `sync_engine.py` (~380 lines) following the proven two-phase bulk create pattern from Linear/GCal sync engines, with Jira-specific additions:

1. **SPARQL helpers** — `_find_existing_task()` and `_find_existing_milestone()` lookup by slug with `STRENDS` and `externalProvider = "jira"`.

2. **Command builders** — `_build_create_command()` accepts an `obj_type` parameter (Task or Milestone), `_build_update_commands()` generates patch + body.set + assignedTo edge.

3. **JQL builder** — `_build_jql()` constructs JQL from project keys + optional user filter + optional delta timestamp (ISO→Jira date format conversion via `_iso_to_jql_date()`).

4. **`pull_sync(ctx)`** — Full pipeline with 12 steps: auth check → settings read → JQL build → issue fetch → Epic/task classification → PersonMatcher(graph, commands, client) → process Epics to Milestones → process tasks with loop prevention → Phase 1 create → Phase 2 body/edge → Phase 3 epic→child linking → store state. Per-issue error isolation via try/except.

5. **`push_sync(ctx)`** stub — checks auth + sync_direction, returns `{status: "skipped", reason: "Push sync not yet implemented (S03)"}`.

6. **app.py wiring** — All 3 handlers updated with lazy imports: `sync_now` calls pull_sync + conditionally push_sync, `poll-tasks` calls pull_sync, `push-changes` calls push_sync. Uses `ctx.settings` for sync_direction (not ctx.state).

## Verification

- Both files parse as valid Python (ast.parse)
- 3 lazy imports of `from services.sync_engine import` in app.py (sync_now, poll-tasks, push-changes)
- 7 occurrences of `pull_sync`/`push_sync` in app.py (3 imports + 4 calls)
- All 237 S01 Jira tests still pass (no regressions)
- Failure-path signals verified present in sync_engine.py (status error/partial, failed_issues, WARNING logging)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/jira-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep -c "from services.sync_engine import" apps/jira-sync/app.py` → 3 | 0 | ✅ pass | <1s |
| 4 | `grep "pull_sync\|push_sync" apps/jira-sync/app.py \| wc -l` → 7 | 0 | ✅ pass | <1s |
| 5 | `pytest tests/test_jira_*.py -v` → 237 passed | 0 | ✅ pass | 9.5s |
| 6 | `grep -n "status.*error\|status.*partial\|failed_issues" sync_engine.py` → 10 matches | 0 | ✅ pass | <1s |

## Diagnostics

- **Pull sync results:** `ctx.state.get("last_pull_result")` returns JSON with `status`, `created`, `updated`, `skipped`, `errors`, `failed_issues`, `duration_ms`. Rendered in `connect_status.html` sync stats section.
- **Push sync results:** `ctx.state.get("last_push_result")` returns JSON with `status`, `reason`.
- **Sync phases logged at INFO:** auth check, JQL string, issue count, epic/task classification, Phase 1/2/3 command counts, final result summary.
- **Per-issue errors logged at WARNING:** with issue key and exception message.
- **Result status values:** `success` (all ok), `partial` (some failed), `error` (all failed), `skipped` (precondition not met).

## Deviations

None — implementation matches plan exactly.

## Known Issues

None.

## Files Created/Modified

- `apps/jira-sync/services/sync_engine.py` — new, ~380 lines: pull_sync, push_sync stub, SPARQL helpers, command builders, JQL builder, batch submission
- `apps/jira-sync/app.py` — modified 3 handlers (sync_now, poll-tasks, push-changes) with lazy imports and real sync calls
- `.gsd/milestones/M023/slices/S02/S02-PLAN.md` — added failure-path verification check (pre-flight fix)
