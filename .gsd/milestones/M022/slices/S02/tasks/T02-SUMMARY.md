---
id: T02
parent: S02
milestone: M022
provides:
  - Pull sync engine with two-phase bulk create, subtask recursion up to 5 levels, and configurable field mapping from StateClient
  - poll_tasks handler wired to pull_sync, sync_now POST route for on-demand sync
key_files:
  - apps/asana-sync/services/sync_engine.py
  - apps/asana-sync/app.py
  - backend/tests/test_asana_sync_engine.py
key_decisions:
  - Used _PatchedPullSync context manager to monkeypatch AsanaClient in tests rather than fighting the HTTP layer — keeps tests focused on sync logic
  - get_connection_status takes only state_client (no http_client) — adapted from plan which mentioned passing http_client
patterns_established:
  - Subtask recursion via _fetch_subtasks_recursive with _parent_gid annotation on each subtask dict for edge creation
  - Phase-2 slug→IRI discovery for body.set + edge.create after object.create commands
observability_surfaces:
  - asana.sync.engine logger with pull_sync start/complete events
  - last_pull_result StateClient key (JSON with status, created, updated, errors, duration_ms, timestamp)
  - last_sync_at cursor for incremental sync
  - Per-task error_details list with task_gid, project_gid, error message
duration: 25m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Build sync engine, wire app.py poll handler, and add sync-now route

**Built pull sync engine with two-phase bulk create, subtask recursion bounded at 5 levels, and wired poll_tasks + sync_now route — 58 tests passing, 168 total across all S02 tests.**

## What Happened

Built `sync_engine.py` following the established Todoist/Linear two-phase bulk pattern. The engine reads field mapping configuration from StateClient via `_read_field_config()` and passes it to `build_task_properties()` for configurable status/priority extraction. Novel pieces vs prior sync engines:

1. **Subtask recursion**: `_fetch_subtasks_recursive()` walks the Asana subtask tree up to `MAX_SUBTASK_DEPTH=5` levels. Each subtask is annotated with `_parent_gid` so the engine creates `dcterms:isPartOf` edge.create commands linking children to parents.

2. **Field config from StateClient**: The engine reads `status_source`, `status_field_gid`, `status_mapping`, `priority_field_gid`, `priority_mapping`, and `story_points_field_gid` from the state store and passes them as a dict to the field mapper.

3. **Milestone detection**: Tasks with `resource_subtype: "milestone"` get `bpkm:Milestone` type instead of `bpkm:Task` in the object.create command.

Wired `poll_tasks` handler to call `pull_sync(ctx)` and added `/_fragments/sync-now` POST route that triggers pull sync and returns an HTML result summary.

## Verification

- 58 sync engine tests passing with `--noconftest`
- 168 total tests across field_mapper (91), person_matcher (19), sync_engine (58) — all passing
- Syntax valid on both sync_engine.py and app.py
- `test_last_pull_result_stored` explicitly asserts `created`, `errors`, `duration_ms`, `timestamp` keys in last_pull_result

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `pytest backend/tests/test_asana_sync_engine.py -v --noconftest` | 0 | ✅ pass (58 tests) | 0.12s |
| 4 | `pytest backend/tests/test_asana_field_mapper.py backend/tests/test_asana_person_matcher.py backend/tests/test_asana_sync_engine.py -v --noconftest` | 0 | ✅ pass (168 tests) | 0.15s |

## Diagnostics

- **Runtime inspection**: `ctx.state.get("last_pull_result")` returns JSON with full sync stats (status, created, updated, unchanged, errors, error_details, duration_ms, timestamp)
- **Incremental cursor**: `ctx.state.get("last_sync_at")` shows last sync timestamp for modified_since filtering
- **Error details**: `error_details` list in result dict contains per-task failures with task_gid, project_gid, and error message
- **Logger**: `asana.sync.engine` emits pull_sync start (project count), completion (all counts), and per-task error warnings

## Deviations

- `get_connection_status` in asana auth.py takes only `state_client`, not `(state_client, http_client)` as the plan suggested — adapted accordingly
- sync_now route returns HTML (consistent with htmx fragment pattern) rather than raw JSON — the result dict is still stored in StateClient as JSON for programmatic access
- Test count is 58 (exceeds the 40+ requirement)

## Known Issues

None.

## Files Created/Modified

- `apps/asana-sync/services/sync_engine.py` — new, ~450 lines, pull sync pipeline with subtask recursion
- `apps/asana-sync/app.py` — modified: poll_tasks calls pull_sync, sync_now route added, sync_engine import added
- `backend/tests/test_asana_sync_engine.py` — new, ~900 lines, 58 tests covering all sync paths
