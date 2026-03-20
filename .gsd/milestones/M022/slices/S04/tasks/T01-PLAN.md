---
estimated_steps: 8
estimated_files: 1
---

# T01: Build mock Asana REST API server with selftest

**Slice:** S04 — E2E tests + mock server + user guide
**Milestone:** M022

## Description

Create a mock Asana REST API server using Python stdlib (`http.server`, `json`, `re`) that returns canned responses for all endpoints the Asana Sync app calls. The server must wrap all responses in Asana's `{"data": ..., "next_page": null}` envelope, enforce Bearer token auth, and pass a `--selftest` that exercises all endpoints.

This is the foundational piece for the E2E test — the mock server runs in Docker alongside the SemPKM test stack, and the Asana Sync app's `AsanaClient` is pointed here via `ASANA_API_URL` env var override.

**Reference:** `e2e/mock-caldav-api/server.py` (677 lines) and `e2e/mock-todoist-api/server.py` (383 lines) for the established pattern. Read either one to understand the server structure, auth checking, selftest pattern, and response formatting conventions.

## Steps

1. **Read a reference mock server** (e.g., `e2e/mock-todoist-api/server.py`) to understand the pattern: `BaseHTTPRequestHandler` subclass, `do_GET`/`do_POST`/`do_PATCH` methods, `_send_json()` helper, `_check_auth()` returning 401, `--selftest` mode using `urllib.request`.

2. **Create `e2e/mock-asana-api/server.py`** with these constants:
   - `PORT = 8080`
   - `VALID_TOKEN = "test-asana-pat-token-abc123"` (matches E2E test convention)
   - Canned data for: 1 user, 1 workspace (`gid: "ws-001"`), 2 projects (`gid: "proj-001"`, `gid: "proj-002"`), 3 sections per project (To Do, In Progress, Done), custom field settings on each project (Status enum, Priority enum, Story Points number), 2-3 tasks with custom_fields + memberships + tags + assignee, 1 subtask for one task.

3. **Implement endpoints** (all require Bearer auth except `/health`):
   - `GET /health` → `{"status": "ok"}` (no auth, no envelope)
   - `GET /api/1.0/users/me` → `{"data": {"gid": "user-001", "name": "Test User", "email": "test@example.com"}}`
   - `GET /api/1.0/workspaces` → `{"data": [workspace], "next_page": null}`
   - `GET /api/1.0/workspaces/{gid}/projects` → `{"data": [project1, project2], "next_page": null}` (filter `archived=false` if present in query params)
   - `GET /api/1.0/projects/{gid}` → `{"data": {project with custom_field_settings}}` — The `custom_field_settings` array must contain objects with `custom_field` sub-object having `gid`, `name`, `resource_subtype` ("enum" or "number"), and for enums: `enum_options: [{gid, name}]`.
   - `GET /api/1.0/projects/{gid}/sections` → `{"data": [3 sections], "next_page": null}` — Each section has `gid` and `name`.
   - `GET /api/1.0/projects/{gid}/tasks` → `{"data": [tasks], "next_page": null}` — Each task has: `gid`, `name`, `completed`, `resource_subtype` ("default_task"), `notes` (plain text), `html_notes`, `due_on`, `custom_fields` array (with matching GIDs for Status/Priority enums, each having `enum_value: {gid, name}`), `memberships` array (`[{section: {gid, name}}]`), `tags` array (`[{gid, name}]`), `assignee` object (`{gid, email, name}`), `created_at`, `modified_at`, `permalink_url`.
   - `GET /api/1.0/tasks/{gid}/subtasks` → `{"data": [subtask], "next_page": null}` — Return 1 subtask for one specific task, empty for others.
   - `PATCH /api/1.0/tasks/{gid}` → Read JSON body, merge with existing task, return `{"data": merged_task}`.
   - `POST /api/1.0/sections/{gid}/addTask` → Read JSON body (expects `task` GID), return `{"data": {}}`.

4. **Implement auth checking**: `_check_auth()` extracts `Authorization: Bearer {token}`, compares to `VALID_TOKEN`. Returns `True` if valid, sends `401 {"errors": [{"message": "Not Authorized"}]}` and returns `False` if invalid.

5. **Implement `_send_json(data, status=200)`** helper that sets `Content-Type: application/json` and writes the JSON response.

6. **Implement URL routing** in `do_GET`, `do_PATCH`, `do_POST` using `re.match()` patterns against `self.path`.

7. **Implement `--selftest`** mode: start server in a thread, run ~12 `urllib.request` checks covering each endpoint + one auth rejection test, print results, `sys.exit(0)` on all pass / `sys.exit(1)` on any failure. Follow the exact selftest pattern from reference mock servers.

8. **Verify**: Run `python e2e/mock-asana-api/server.py --selftest` — all checks must pass.

## Must-Haves

- [ ] All responses (except /health) use `{"data": ..., "next_page": null}` Asana envelope
- [ ] Bearer token auth enforced on all endpoints except /health
- [ ] Task data includes `custom_fields` array with enum Status/Priority GIDs matching the project's `custom_field_settings`
- [ ] Task data includes `memberships` array with section `{gid, name}` for section-based status mapping
- [ ] Selftest covers all endpoints + auth rejection (12+ checks)
- [ ] Only Python stdlib — no external dependencies

## Verification

- `python e2e/mock-asana-api/server.py --selftest` — all 12+ checks pass
- `python3 -c "import ast; ast.parse(open('e2e/mock-asana-api/server.py').read())"` — syntax OK

## Inputs

- `e2e/mock-todoist-api/server.py` or `e2e/mock-caldav-api/server.py` — reference pattern for server structure, auth, selftest
- `apps/asana-sync/services/asana_client.py` — shows which endpoints the client calls and what `opt_fields` it expects
- `apps/asana-sync/services/field_mapper.py` — shows how task data is consumed (custom_fields, memberships, tags, assignee structure)
- S04 research doc (inlined in slice plan context) — lists all endpoints with response structures

## Expected Output

- `e2e/mock-asana-api/server.py` — ~500-600 line mock server, selftest passing with 12+ checks

## Observability Impact

- **New signals:** Every request logged to stderr as `[mock-asana] METHOD /path → STATUS`. Selftest prints per-check ✓/FAIL with final pass/fail count.
- **Inspection:** `--selftest` flag provides zero-dependency verification. `/health` endpoint enables Docker healthcheck and manual readiness probing.
- **Failure state:** Non-zero exit from selftest indicates which specific checks failed. Missing auth returns structured 401 JSON. Unknown routes return 404 with JSON body.
