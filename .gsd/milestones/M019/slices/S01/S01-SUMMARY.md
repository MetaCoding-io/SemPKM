---
id: S01
parent: M019
milestone: M019
provides:
  - Todoist PAT auth with store/verify/status/disconnect and error classes
  - TodoistClient REST wrapper (get_tasks/projects/labels, close/reopen/create/update)
  - Bidirectional field mapper (priority inversion, status, due dates, labels, property builder)
  - PersonMatcher with email/name SPARQL lookup and LRU cache
  - pull_sync() engine with two-phase bulk create, existing task detection, per-task error isolation
  - Route handlers for connect, disconnect, project selection, sync-now, poll-tasks
  - Connect/status templates with project checkboxes, sync button, sync stats
requires:
  - slice: none
    provides: first slice — no dependencies
affects:
  - S02
key_files:
  - apps/todoist-sync/manifest.yaml
  - apps/todoist-sync/app.py
  - apps/todoist-sync/services/auth.py
  - apps/todoist-sync/services/todoist_client.py
  - apps/todoist-sync/services/field_mapper.py
  - apps/todoist-sync/services/person_matcher.py
  - apps/todoist-sync/services/sync_engine.py
  - apps/todoist-sync/frontend/templates/connect.html
  - apps/todoist-sync/frontend/templates/connect_status.html
  - apps/todoist-sync/frontend/templates/projects.html
  - backend/tests/test_todoist_auth.py
  - backend/tests/test_todoist_client.py
  - backend/tests/test_todoist_field_mapper.py
  - backend/tests/test_todoist_person_matcher.py
  - backend/tests/test_todoist_sync_engine.py
key_decisions:
  - "Auth verifies via GET /rest/v2/projects (returns project count) — Todoist REST v2 has no /user endpoint"
  - "TodoistClient uses simple request() wrapper without pagination — Todoist REST v2 returns all items in one response for personal accounts"
  - "Field mapper treats REST v2 labels as name strings (not IDs) — labels_lookup kept for API compat but unused in practice"
  - "Existing task detection uses bpkm:externalId + externalProvider='todoist' SPARQL lookup — more precise than slug-based STRENDS"
patterns_established:
  - "Todoist auth follows github-sync pattern: store_token/get_stored_token/verify_token/get_connection_status/clear_credentials/_mask_token"
  - "Client uses try/except import pattern (not relative imports) for importlib test loading compatibility"
  - "pull_sync follows github-sync pattern: auth check → fetch → classify create/update → two-phase bulk submit → store result"
  - "State keys: selected_projects (JSON array), last_pull_result (JSON with status/counts/error_details)"
observability_surfaces:
  - "todoist.sync.auth logger — INFO on token store/verify/clear, WARNING on verification failures"
  - "todoist.sync.client logger — DEBUG for each request (method + URL)"
  - "todoist.sync logger — INFO per sync with created/updated/unchanged/errors counts"
  - "todoist.sync.person logger — DEBUG for cache hits, person creation"
  - "get_connection_status() returns {connected, auth_method, projects_count, token_preview}"
  - "last_pull_result state key — JSON with status, counts, error_details array, duration_ms"
drill_down_paths:
  - .gsd/milestones/M019/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M019/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M019/slices/S01/tasks/T03-SUMMARY.md
duration: 61m
verification_result: passed
completed_at: 2026-03-19
---

# S01: Auth + Client + Pull Sync

**Todoist Sync app scaffold with PAT auth, REST client, bidirectional field mapper, person matcher, and pull sync engine — 168 unit tests pass in 0.18s.**

## What Happened

Built the fourth sync app (after Linear, GitHub, Google Calendar) following the established pattern. Three tasks executed sequentially:

**T01 (12m):** Created app scaffold — manifest, auth module (store/verify/status/disconnect with `TodoistAuthError`/`TodoistAPIError`), route handlers, connect/status templates. Auth verification uses `GET /rest/v2/projects` since Todoist REST v2 has no dedicated user endpoint. 25 tests.

**T02 (14m):** Built TodoistClient REST wrapper and field mapper. Client covers all CRUD operations (get_tasks/projects/labels, close/reopen/create/update) — no pagination needed since Todoist returns all items in one response. Field mapper handles bidirectional priority inversion (1→low, 2→medium, 3→high, 4→critical and reverse), status mapping (is_completed ↔ taskStatus), due date extraction (None/date-only/datetime), labels passthrough, and full property builder with external ID/URL/provider. 87 tests.

**T03 (35m):** Adapted PersonMatcher from github-sync for email/name-based SPARQL resolution with LRU cache. Built sync engine with `pull_sync()` orchestrating: auth check → selected projects → fetch tasks per project → classify create/update via externalId SPARQL lookup → two-phase bulk command submission (Phase 1: object.create, Phase 2: discover IRI → body.set + edge.create for assignees). Per-task error isolation. Wired project selection routes (GET/POST), sync-now handler, poll-tasks task handler. Updated templates with project checkboxes, sync button, and stats display. 56 tests.

Key implementation detail: changed todoist_client.py from relative imports to try/except pattern matching github-sync convention — necessary for importlib-based test loading without breaking module namespace resolution for exception classes.

## Verification

- `pytest tests/test_todoist_*.py -v` — **168 passed in 0.18s**
  - 25 auth tests (storage, verification, masking, status, disconnect)
  - 22 client tests (auth header, error codes, all CRUD operations)
  - 65 field mapper tests (4 priority levels both directions, status, 9 due date edge cases, labels, slug, property builder, reverse mapping)
  - 18 person matcher tests (email/name lookup, cache, creation, slugify)
  - 38 sync engine tests (existing task detection, create/update classification, two-phase bulk, error isolation, result structure, labels, priority, idempotency)
- Manifest validates against `AppManifestSchema`
- All htmx URLs use `/app/todoist-sync/` prefix (grep-verified)

## Requirements Advanced

- TD-01 (PAT auth) — token storage, verification via /rest/v2/projects, connection status with project count, disconnect, masking. Ready for validation once E2E confirms.
- TD-02 (pull sync) — pull_sync creates bpkm:Task objects with all mapped fields. Ready for validation once E2E confirms.
- TD-05 (priority mapping) — all 4 levels tested bidirectionally (Todoist 1→low, 2→medium, 3→high, 4→critical and reverse). Unit test proven.
- TD-06 (label→tag mapping) — labels passed through directly as bpkm:tags array. Unit test proven.

## Requirements Validated

- None yet — requirements need E2E confirmation in S03 for full validation.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

- None.

## Deviations

- T02 added close_task(), reopen_task(), create_task(), update_task() to the client beyond plan scope — these are needed for push sync (S02) and were trivial additions.
- T03 changed todoist_client.py from relative imports to try/except pattern — unplanned but necessary for importlib test loading.

## Known Limitations

- Pull sync only — push sync (close/reopen/update) deferred to S02.
- No settings UI for sync direction or poll interval yet — S02 delivers those controls.
- Project selection saves to state but doesn't filter by sync direction (all projects are pull-only for now).

## Follow-ups

- S02: Wire push_sync() with close/reopen endpoint pattern, add sync direction and poll interval settings.
- S03: Mock Todoist API server, E2E Playwright test, Chapter 37 user guide.

## Files Created/Modified

- `apps/todoist-sync/manifest.yaml` — App manifest with identity, permissions, two background tasks
- `apps/todoist-sync/app.py` — Route handlers for connect/disconnect/projects/sync-now/poll-tasks
- `apps/todoist-sync/services/__init__.py` — Package init
- `apps/todoist-sync/services/auth.py` — Token storage, verification, connection status, masking, error classes
- `apps/todoist-sync/services/todoist_client.py` — REST client with Bearer auth, error handling, all CRUD methods
- `apps/todoist-sync/services/field_mapper.py` — Bidirectional field mapping (priority, status, due date, labels, properties)
- `apps/todoist-sync/services/person_matcher.py` — Email/name SPARQL person resolution with LRU cache
- `apps/todoist-sync/services/sync_engine.py` — pull_sync engine with two-phase bulk create, error isolation
- `apps/todoist-sync/frontend/templates/connect.html` — PAT input form with htmx
- `apps/todoist-sync/frontend/templates/connect_status.html` — Connected status with project selection, sync button, stats
- `apps/todoist-sync/frontend/templates/projects.html` — Project checkbox form
- `apps/todoist-sync/frontend/static/styles.css` — Minimal app-specific styles
- `backend/tests/test_todoist_auth.py` — 25 unit tests for auth functions
- `backend/tests/test_todoist_client.py` — 22 unit tests for client methods and error handling
- `backend/tests/test_todoist_field_mapper.py` — 65 unit tests for all mapping functions
- `backend/tests/test_todoist_person_matcher.py` — 18 unit tests for person matching
- `backend/tests/test_todoist_sync_engine.py` — 38 unit tests for sync engine

## Forward Intelligence

### What the next slice should know
- All S01 modules follow the github-sync pattern almost exactly — S02 push_sync can be adapted from github-sync's push_sync with minimal changes. The key novelty is the close/reopen endpoint pattern: Todoist uses `POST /rest/v2/tasks/{id}/close` and `POST /rest/v2/tasks/{id}/reopen` instead of PATCH for status changes.
- TodoistClient already has close_task() and reopen_task() methods wired and tested — S02 just needs to call them from push_sync based on status change direction.
- Field mapper already has `build_todoist_task_data()` for reverse mapping — S02 needs to use it for non-status field updates.

### What's fragile
- The importlib test loading with types.ModuleType pseudo-packages generates a DeprecationWarning on Python 3.14 (`__package__ != __spec__.parent`). Works correctly but may need revision if Python tightens this check.

### Authoritative diagnostics
- `last_pull_result` state key — JSON with status/created/updated/unchanged/errors/error_details/duration_ms/timestamp. This is the single source of truth for sync health.
- `get_connection_status()` — returns connected flag, auth_method, projects_count, token_preview. Quick health check.

### What assumptions changed
- Original plan assumed 100+ tests — delivered 168 (68% over target). The field mapper alone needed 65 tests to cover all priority/status/due-date edge cases bidirectionally.
