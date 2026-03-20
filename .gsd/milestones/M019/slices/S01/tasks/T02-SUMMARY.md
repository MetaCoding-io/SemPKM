---
id: T02
parent: S01
milestone: M019
provides:
  - TodoistClient REST client with get_tasks/get_projects/get_labels + task mutations
  - Field mapper with bidirectional priority/status mapping, due date extraction, property builder
key_files:
  - apps/todoist-sync/services/todoist_client.py
  - apps/todoist-sync/services/field_mapper.py
  - backend/tests/test_todoist_client.py
  - backend/tests/test_todoist_field_mapper.py
key_decisions:
  - "TodoistClient uses simple request() wrapper without pagination — Todoist REST v2 returns all items in one response for personal accounts"
  - "Field mapper treats REST v2 labels as name strings (not IDs) — labels_lookup kept for API compat but not needed in practice"
patterns_established:
  - "Client follows github_client.py pattern: _get_token → _request → convenience methods, with typed exceptions from auth.py"
  - "Field mapper uses BPKM IRI prefix constant for property keys, strips None/empty values, always includes lastSyncedAt"
  - "importlib test loading: create pseudo-package with types.ModuleType to resolve relative imports; exception classes must come from the same module namespace the client imports from"
observability_surfaces:
  - "todoist.sync.client logger — DEBUG for each request (method + URL)"
  - "TodoistAuthError (401/403) and TodoistAPIError (other 4xx/5xx) carry .status_code for structured error inspection"
  - "get_projects() doubles as health check — successful return means client + token work"
duration: 14m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: TodoistClient + field mapper

**Built TodoistClient REST wrapper (get_tasks/get_projects/get_labels/close/reopen/create/update) and bidirectional field mapper with priority inversion, due date extraction, and property builder — 87 tests pass.**

## What Happened

Created two service modules following the github-sync pattern:

1. **TodoistClient** (`services/todoist_client.py`) — thin wrapper around SDK HttpClient with Bearer token auth from state store. Methods: `get_tasks(project_id=None)`, `get_projects()`, `get_labels()`, `close_task()`, `reopen_task()`, `create_task()`, `update_task()`. No pagination needed (Todoist REST v2 returns all items). Typed exceptions (`TodoistAuthError`, `TodoistAPIError`) imported from `auth.py`.

2. **Field mapper** (`services/field_mapper.py`) — pure functions for bidirectional mapping:
   - Priority: Todoist 1→low, 2→medium, 3→high, 4→critical (and reverse)
   - Status: `is_completed` bool ↔ bpkm taskStatus string
   - Due date: handles None, date-only, datetime with time-stripping
   - Labels: direct passthrough (REST v2 returns name strings)
   - `build_task_properties()` assembles full bpkm property dict with external ID/URL/provider
   - `build_todoist_task_data()` reverse-maps bpkm props to Todoist create/update body

3. **Tests** — 22 client tests + 65 mapper tests = 87 total. Client tests cover auth header, no-token errors, HTTP error codes (401/403/404/429/500/502), all CRUD operations. Mapper tests cover all 4 priority levels bidirectionally, status mapping, 9 due date edge cases, label handling, slug generation, full property builder with all field combinations, and reverse mapping.

Key implementation detail: the importlib test loading needed a pseudo-package (`types.ModuleType`) to make the client's relative import (`from .auth import ...`) resolve correctly. Exception classes must be referenced from the same module namespace the client uses to avoid `except` identity mismatches.

## Verification

- Task-level: `pytest backend/tests/test_todoist_client.py backend/tests/test_todoist_field_mapper.py -v` — 87 passed
- Slice-level: `pytest backend/tests/test_todoist_*.py -v` — 112 passed (25 auth + 22 client + 65 mapper)
- Sync engine tests (T03/T04) not yet written — expected partial pass at this task stage

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest backend/tests/test_todoist_client.py backend/tests/test_todoist_field_mapper.py -v` | 0 | ✅ pass | 0.10s |
| 2 | `pytest backend/tests/test_todoist_*.py -v` (slice-level) | 0 | ✅ pass | 0.12s |

## Diagnostics

- **Client health:** `TodoistClient.get_projects()` succeeds → client + token are working
- **Logger:** `todoist.sync.client` at DEBUG level for each request (method + URL)
- **Errors:** `TodoistAuthError` (401/403) and `TodoistAPIError` (other HTTP codes) — both carry `.status_code`
- **Field mapper:** Pure functions — no runtime signals. Test coverage is the inspection surface.

## Deviations

- Added `close_task()`, `reopen_task()`, `create_task()`, `update_task()` methods to the client beyond what the plan explicitly listed (get_tasks/get_projects/get_labels). These are needed for push sync (T04) and were straightforward additions.
- Had to comment out `LINEAR_API_KEY` in worktree `.env` — the Settings model has `extra='forbid'` and the env var from a prior milestone was causing conftest import failure.

## Known Issues

- DeprecationWarning from Python 3.14: `__package__ != __spec__.parent` on the client's relative import. Cosmetic only — the import works correctly. This is an artifact of the importlib pseudo-package approach used for test loading.

## Files Created/Modified

- `apps/todoist-sync/services/todoist_client.py` — REST client with auth, error handling, and all CRUD methods
- `apps/todoist-sync/services/field_mapper.py` — Bidirectional field mapping (priority, status, due date, labels, properties)
- `backend/tests/test_todoist_client.py` — 22 unit tests for client methods, auth, and error handling
- `backend/tests/test_todoist_field_mapper.py` — 65 unit tests for all mapping functions and edge cases
- `.gsd/milestones/M019/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section
