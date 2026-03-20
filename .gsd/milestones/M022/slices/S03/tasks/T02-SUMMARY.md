---
id: T02
parent: S03
milestone: M022
provides:
  - push_sync(ctx) — full push pipeline orchestrating PATCH + section moves for locally-changed Asana tasks
  - _find_changed_tasks(graph_client) — SPARQL discovery of tasks with externalProvider "asana" modified since last sync
key_files:
  - apps/asana-sync/services/sync_engine.py
  - backend/tests/test_asana_sync_engine.py
key_decisions:
  - Two-path push dispatch: build_asana_patch for custom fields/completed → patch_task; resolve_section_gid_for_status → add_task_to_section. Both can fire on same task when section status + priority change.
  - Skip (not error) when task is detected as changed but nothing reverse-maps — prevents false error noise
patterns_established:
  - _PatchedPushSync context manager patches both AsanaClient and _find_changed_tasks for isolated push tests
  - Push result schema: {status, pushed, skipped, errors, error_details} — stored in last_push_result StateClient key
observability_surfaces:
  - last_push_result StateClient key — JSON with status/pushed/skipped/errors/error_details
  - Logger "asana.sync.engine" — push_sync start, per-task push, section move, per-task errors
duration: 25min
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Build push_sync pipeline in sync_engine.py

**Added push_sync pipeline with two-path dispatch (custom field PATCH + section move) and 26 tests covering all push paths, guards, error isolation, and result storage.**

## What Happened

Added `_find_changed_tasks(graph_client)` — SPARQL query filtering for `externalProvider = "asana"` with `externalUuid` required, excluding pull-only tasks, and including only tasks where `dcterms:modified > bpkm:lastSyncedAt`. Cloned from Linear's pattern with provider filter changed to "asana".

Added `push_sync(ctx)` — the main push orchestrator with this flow:
1. Guard: check auth (skip if not connected)
2. Guard: check sync_direction (skip if pull-only)
3. Read field_config, discovered_enum_fields, discovered_sections from StateClient
4. Find changed tasks via `_find_changed_tasks`
5. For each task: build bpkm properties → `build_asana_patch()` for custom field PATCH → `resolve_section_gid_for_status()` for section moves → update `lastSyncedAt` via `_submit_commands_batched`
6. Per-task try/except for error isolation
7. Store `last_push_result` in StateClient

The two-path dispatch works: when `status_source == "section"` and status changed, the engine calls `add_task_to_section()` for the section move. When there's also a priority change, it additionally calls `patch_task()` with the priority custom field — both paths can fire on the same task.

Added push-sync imports (`build_asana_patch`, `resolve_section_gid_for_status`) to the sync_engine import block.

## Verification

- `uv run pytest tests/test_asana_sync_engine.py -q` — 84 tests pass (58 existing + 26 new)
- `uv run pytest tests/test_asana_field_mapper.py tests/test_asana_sync_engine.py -q` — 209 tests pass
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"` — no SyntaxError

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run pytest tests/test_asana_sync_engine.py -q` | 0 | ✅ pass | 0.18s |
| 2 | `uv run pytest tests/test_asana_field_mapper.py tests/test_asana_sync_engine.py -q` | 0 | ✅ pass | 0.16s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |

## Diagnostics

- `last_push_result` StateClient key → JSON `{status, pushed, skipped, errors, error_details}` — inspect via app state API
- Logger `asana.sync.engine` emits: `push_sync: found %d changed tasks`, `push_sync: pushed task %s via PATCH`, `push_sync: section move for task %s → section %s`, per-task error warnings with task GID
- Error details list includes `{iri, task_gid, error}` per failed task

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/asana-sync/services/sync_engine.py` — Added `_find_changed_tasks()` and `push_sync()` (~170 new lines), plus push-sync imports
- `backend/tests/test_asana_sync_engine.py` — Added `TestFindChangedTasks` (5 tests), `TestPushSync` (21 tests), mock infrastructure (`MockPushAsanaClient`, `_PatchedPushSync`, `_push_state`, `_changed_task`)
