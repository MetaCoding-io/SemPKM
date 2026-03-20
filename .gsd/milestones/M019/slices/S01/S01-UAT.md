# S01: Auth + Client + Pull Sync — UAT

**Milestone:** M019
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All S01 deliverables are backend services tested by 168 unit tests. No live runtime needed — the sync engine, field mapper, and auth module are pure functions with injected dependencies. Templates are verified by htmx URL grep.

## Preconditions

- Backend venv available at `/home/james/Code/SemPKM/backend/.venv/`
- Test files exist in worktree at `backend/tests/test_todoist_*.py`
- App source exists at `apps/todoist-sync/`

## Smoke Test

```bash
cd backend && /path/to/.venv/bin/python -m pytest tests/test_todoist_*.py -v --tb=short
```
Expected: 168 tests pass in <1s.

## Test Cases

### 1. Auth module — token storage and verification

1. Run `pytest tests/test_todoist_auth.py -v`
2. **Expected:** 25 tests pass covering:
   - `store_token` saves token via StateClient
   - `verify_token` calls GET /rest/v2/projects with Bearer header, returns project count on success
   - `verify_token` raises TodoistAuthError on 401/403
   - `get_connection_status` returns `{connected: true, auth_method: "pat", projects_count: N, token_preview: "tok_***xyz"}`
   - `clear_credentials` removes stored token
   - `_mask_token` shows first 4 + last 3 chars with `***` in between
   - Disconnect route clears credentials and returns connect form

### 2. REST client — all CRUD operations and error handling

1. Run `pytest tests/test_todoist_client.py -v`
2. **Expected:** 22 tests pass covering:
   - `get_tasks()` fetches from `/rest/v2/tasks` with optional `project_id` param
   - `get_projects()` fetches from `/rest/v2/projects`
   - `get_labels()` fetches from `/rest/v2/labels`
   - `close_task(id)` POSTs to `/rest/v2/tasks/{id}/close`
   - `reopen_task(id)` POSTs to `/rest/v2/tasks/{id}/reopen`
   - `create_task(data)` POSTs to `/rest/v2/tasks`
   - `update_task(id, data)` POSTs to `/rest/v2/tasks/{id}`
   - Auth header is `Authorization: Bearer <token>`
   - 401/403 → TodoistAuthError, 404/429/500/502 → TodoistAPIError
   - No token stored → raises TodoistAuthError

### 3. Field mapper — priority inversion (all 4 levels, both directions)

1. Run `pytest tests/test_todoist_field_mapper.py -k "priority" -v`
2. **Expected:** Tests pass proving:
   - Todoist 1 → bpkm "low"
   - Todoist 2 → bpkm "medium"
   - Todoist 3 → bpkm "high"
   - Todoist 4 → bpkm "critical"
   - bpkm "low" → Todoist 1
   - bpkm "medium" → Todoist 2
   - bpkm "high" → Todoist 3
   - bpkm "critical" → Todoist 4
   - Unknown priority → "medium" default

### 4. Field mapper — status mapping

1. Run `pytest tests/test_todoist_field_mapper.py -k "status" -v`
2. **Expected:** Tests pass proving:
   - `is_completed: false` → "todo"
   - `is_completed: true` → "done"
   - Missing `is_completed` → "todo" default

### 5. Field mapper — due date edge cases

1. Run `pytest tests/test_todoist_field_mapper.py -k "due" -v`
2. **Expected:** Tests pass proving:
   - No due field → None
   - `due.date` = "2024-03-15" → "2024-03-15" (date-only)
   - `due.datetime` = "2024-03-15T10:00:00Z" → "2024-03-15" (time stripped)
   - `due.date` only, no datetime → uses date

### 6. Field mapper — full property builder

1. Run `pytest tests/test_todoist_field_mapper.py -k "build_task_properties" -v`
2. **Expected:** Tests pass proving `build_task_properties()` produces a dict with:
   - `bpkm:externalId` = task ID string
   - `bpkm:externalUrl` = `https://todoist.com/app/task/{id}`
   - `bpkm:externalProvider` = "todoist"
   - `bpkm:taskStatus` from status mapping
   - `bpkm:priority` from priority mapping
   - `bpkm:dueDate` from due date extraction
   - `bpkm:tags` from labels array
   - `bpkm:lastSyncedAt` always present (ISO 8601)
   - None/empty values stripped

### 7. Person matcher — email and name lookup

1. Run `pytest tests/test_todoist_person_matcher.py -v`
2. **Expected:** 18 tests pass covering:
   - Email match via foaf:mbox/crm:email SPARQL → returns existing IRI
   - Name fallback when email has no match
   - Creates new Person when no match found (with email or name-derived slug)
   - LRU cache hit on second call for same person
   - None/empty input → returns None

### 8. Sync engine — pull_sync creates tasks

1. Run `pytest tests/test_todoist_sync_engine.py -k "PullSyncCreates" -v`
2. **Expected:** Tests pass proving:
   - Single task → object.create command submitted
   - Multiple tasks → all created in one batch
   - Properties include `externalProvider: "todoist"`
   - Slug is deterministic from task content
   - Task with description → body.set command generated
   - Task without description → no body.set

### 9. Sync engine — existing task detection and updates

1. Run `pytest tests/test_todoist_sync_engine.py -k "Updates or FindExisting" -v`
2. **Expected:** Tests pass proving:
   - Existing task found by externalId SPARQL lookup → object.patch (not create)
   - Mix of new and existing → creates + patches in same batch
   - Update includes body.set when description present

### 10. Sync engine — error isolation

1. Run `pytest tests/test_todoist_sync_engine.py -k "ErrorIsolation" -v`
2. **Expected:** Tests pass proving:
   - One bad task doesn't kill the entire batch — other tasks still sync
   - Project fetch failure isolated — other projects still sync
   - All tasks failing → result status = "error"

### 11. Sync engine — skip conditions

1. Run `pytest tests/test_todoist_sync_engine.py -k "Skipped" -v`
2. **Expected:** Tests pass proving:
   - Not connected → skipped with reason
   - No projects selected → skipped with reason
   - Empty projects list → skipped with reason

### 12. Manifest validation

1. Run: `python -c "from backend.app.apps.manifest import parse_app_manifest; m = parse_app_manifest('apps/todoist-sync/manifest.yaml'); print(m.app_id, m.name)"`
2. **Expected:** Prints `todoist-sync Todoist Sync`

### 13. htmx URL prefix check

1. Run: `rg "hx-post|hx-get" apps/todoist-sync/frontend/templates/`
2. **Expected:** All URLs start with `/app/todoist-sync/` — no bare `/_fragments/` paths

## Edge Cases

### Priority out-of-range

1. Run `pytest tests/test_todoist_field_mapper.py -k "unknown_priority" -v`
2. **Expected:** Unknown Todoist priority values default to "medium", unknown bpkm values default to Todoist 1

### Task with no assignee

1. Run `pytest tests/test_todoist_sync_engine.py -k "without_assignee" -v`
2. **Expected:** No edge.create command generated for unassigned tasks

### Empty sync (no tasks returned)

1. Verify via test_todoist_sync_engine.py that pull_sync with zero tasks returns `{status: "success", created: 0, updated: 0}`

## Failure Signals

- Any test in `test_todoist_*.py` fails → regression in auth, client, mapping, or sync logic
- Manifest parse fails → manifest.yaml has schema violation
- htmx URLs without `/app/todoist-sync/` prefix → template routing will break through app proxy
- `TodoistAuthError` or `TodoistAPIError` without `.status_code` → error class contract broken

## Requirements Proved By This UAT

- TD-01 (PAT auth) — test cases 1, 12 prove token storage, verification, status, disconnect
- TD-02 (pull sync) — test cases 8, 9, 10, 11 prove task creation, update detection, error isolation
- TD-05 (priority mapping) — test case 3 proves all 4 levels bidirectionally
- TD-06 (label→tag mapping) — test case 6 proves labels passthrough as bpkm:tags

## Not Proven By This UAT

- Live Todoist API connectivity (mocked in all tests)
- Push sync / close / reopen (S02 scope)
- Settings UI for sync direction and poll interval (S02 scope)
- E2E lifecycle through Docker stack (S03 scope)
- User guide documentation (S03 scope)

## Notes for Tester

- All tests use mocked HTTP responses — no Todoist account or API token needed
- Run from `backend/` directory using the project venv: `/home/james/Code/SemPKM/backend/.venv/bin/python -m pytest tests/test_todoist_*.py -v`
- The DeprecationWarning about `__package__ != __spec__.parent` on Python 3.14 is cosmetic — importlib pseudo-package pattern works correctly
