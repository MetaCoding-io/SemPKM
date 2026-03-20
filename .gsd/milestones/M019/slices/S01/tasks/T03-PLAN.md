# T03: PersonMatcher + sync engine + pull routes

**Slice:** S01 — Auth + Client + Pull Sync
**Milestone:** M019

## Description

Person resolution, sync engine orchestration with pull_sync(), project selection routes, and connect_status template completion.

## Steps

1. Copy `services/person_matcher.py` from github-sync — email-based SPARQL lookup, creation on miss, LRU cache. Minimal adaptation (import paths).
2. Write `services/sync_engine.py`:
   - pull_sync(ctx, state_client) — fetch tasks from selected projects, fetch labels for lookup, build properties via field_mapper, two-phase bulk create (object.create → SPARQL discover IRI → body.set + edge.create for assignee), existing task detection by bpkm:externalId SPARQL, per-task error isolation, structured result dict with created/updated/unchanged/error counts
   - X-Request-Id header on create operations for idempotency
3. Wire route handlers in app.py:
   - POST /_fragments/sync-now — call pull_sync, return status
   - GET /_fragments/projects — fetch projects via client, render checkboxes
   - POST /_fragments/projects — save selected project IDs to state
   - poll-tasks task handler — call pull_sync
4. Update connect_status.html — add project selection checkboxes section (loaded via htmx from /_fragments/projects), Sync Now button, sync stats display
5. Write `backend/tests/test_todoist_person_matcher.py` — 10+ tests
6. Write `backend/tests/test_todoist_sync_engine.py` — 40+ tests: pull_sync creates correct commands, handles existing tasks, per-task error isolation, structured results, label lookup integration

## Must-Haves

- [ ] pull_sync creates bpkm:Task objects with all mapped fields
- [ ] Existing tasks detected by externalId and updated (not duplicated)
- [ ] Per-task error isolation (one bad task doesn't kill the batch)
- [ ] 50+ combined tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_todoist_person_matcher.py tests/test_todoist_sync_engine.py -v`
- `cd backend && .venv/bin/python -m pytest tests/test_todoist_*.py -v` — all 100+ S01 tests pass

## Inputs

- T01 outputs: app scaffold, auth module, route handlers
- T02 outputs: TodoistClient, field_mapper
- `apps/github-sync/services/person_matcher.py` — copy source
- `apps/github-sync/services/sync_engine.py` — sync pattern

## Expected Output

- `apps/todoist-sync/services/person_matcher.py`, `services/sync_engine.py`
- Updated `app.py` with pull routes and task handlers
- Updated `connect_status.html` with project selection and sync UI
- `backend/tests/test_todoist_person_matcher.py`, `test_todoist_sync_engine.py` — 50+ passing tests

## Observability Impact

- **New logger:** `todoist.sync` — INFO per pull_sync (created/updated/unchanged counts), WARNING on per-task failures
- **New logger:** `todoist.sync.person` — DEBUG for cache hits and person creation
- **State key:** `last_pull_result` — JSON with status, counts, error_details, duration_ms, timestamp. Query via `ctx.state.get("last_pull_result")`.
- **State key:** `selected_projects` — JSON array of Todoist project IDs selected for sync
- **Error visibility:** `error_details` array in pull result contains per-task `{task_id, error}` dicts for diagnosis
- **Failure state:** When sync fails, `last_pull_result` shows `status: "error"` or `"partial"` with non-zero error count
