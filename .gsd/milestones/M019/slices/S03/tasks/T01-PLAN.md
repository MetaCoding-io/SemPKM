---
estimated_steps: 7
estimated_files: 4
---

# T01: Build mock Todoist API server, add env var override, and wire Docker service

**Slice:** S03 — E2E Tests + User Guide
**Milestone:** M019

## Description

Create the mock Todoist API server for E2E testing, add `TODOIST_API_URL` env var override to the app's client and auth modules so Docker can redirect API calls to the mock, and wire the `mock-todoist` service into `docker-compose.test.yml`.

The mock server follows the exact pattern established by `e2e/mock-github-api/server.py` — stdlib `http.server`, canned JSON responses, auth header validation, selftest via `--selftest` flag.

## Steps

1. **Create `e2e/mock-todoist-api/server.py`** following `e2e/mock-github-api/server.py` structure:
   - Canned data constants: `PROJECTS_RESPONSE` (2 projects: "Work" id "100001", "Personal" id "100002"), `TASKS_RESPONSE` (2 tasks: "Review quarterly report" with priority 4, labels ["urgent","finance"], due date "2026-03-25", project_id "100001"; "Buy groceries" with priority 1, no labels, no due date, project_id "100002"), `LABELS_RESPONSE` (2 labels: "urgent", "finance")
   - `MockTodoistHandler(BaseHTTPRequestHandler)` with:
     - `_check_auth()` — validates `Authorization: Bearer <token>` header, returns 401 if missing/invalid
     - `_json_response(status, body)` — writes JSON response with Content-Type header
     - `_log_request(method, path, status)` — logs to stderr
     - `do_GET()` routes: `/health` (200 no auth), `/rest/v2/projects` (200 + auth), `/rest/v2/tasks` (200 + auth), `/rest/v2/labels` (200 + auth)
     - `do_POST()` routes: `/rest/v2/tasks/{id}/close` (204 + auth), `/rest/v2/tasks/{id}/reopen` (204 + auth), `/rest/v2/tasks/{id}` (200 + merged task + auth), `/rest/v2/tasks` (200 + created task + auth)
   - **Important**: Close and reopen return 204 with empty body (not JSON). The mock must use `self.send_response(204)` + `self.end_headers()` with no body write.
   - `selftest()` function with ~10 checks: health, projects (200), tasks (200), labels (200), tasks without auth (401), close (204), reopen (204), task update (200), task create (200), projects response content validation. Print `[selftest] N passed, M failed` and `sys.exit(1)` if any fail.
   - `_make_test_request(method, path, body=None)` helper for selftest that constructs a handler without real socket (same pattern as github mock).
   - Entrypoint: `--selftest` flag runs selftest; otherwise starts HTTPServer on port 8080.

2. **Add `TODOIST_API_URL` env var override to `todoist_client.py`**:
   - Add `import os` at the top of the file (module level, outside the try/except block)
   - Change line `TODOIST_API_URL = "https://api.todoist.com/rest/v2"` to `TODOIST_API_URL = os.environ.get("TODOIST_API_URL", "https://api.todoist.com/rest/v2")`

3. **Add `TODOIST_API_URL` env var override to `auth.py`**:
   - Add `import os` at the top
   - Change the hardcoded URL in `verify_token()` from `"https://api.todoist.com/rest/v2/projects"` to `f"{os.environ.get('TODOIST_API_URL', 'https://api.todoist.com/rest/v2')}/projects"`

4. **Wire Docker service in `docker-compose.test.yml`**:
   - Add `TODOIST_API_URL: http://mock-todoist:8080/rest/v2` to the `api` service `environment` block (after the GCAL entries)
   - Add `mock-todoist` to the `api` service `depends_on` with `condition: service_healthy`
   - Add `mock-todoist` service block (after `mock-google-calendar`):
     ```yaml
     mock-todoist:
       image: python:3.12-slim
       volumes:
         - ./e2e/mock-todoist-api:/app:ro
       working_dir: /app
       command: ["python", "server.py"]
       healthcheck:
         test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
         interval: 3s
         timeout: 3s
         retries: 5
       networks:
         - sempkm-test
     ```

5. **Run selftest**: `python e2e/mock-todoist-api/server.py --selftest`

6. **Verify existing unit tests still pass**: `python -m pytest backend/tests/test_todoist_*.py -v` — all 239 tests should pass (the env var change defaults to the original URL)

7. **Validate Docker compose**: `docker compose -f docker-compose.test.yml config --quiet`

## Must-Haves

- [ ] Mock server responds correctly to all Todoist REST v2 endpoints (projects, tasks, labels, close, reopen, update, create)
- [ ] Close/reopen endpoints return 204 with empty body (not 200 with JSON)
- [ ] Auth header validation returns 401 for missing/invalid tokens
- [ ] Selftest exercises all endpoints and validates responses including error path (unauthorized request → 401)
- [ ] `TODOIST_API_URL` env var in todoist_client.py and auth.py defaults to production URL when not set
- [ ] `import os` is at module level in both files (not inside try/except)
- [ ] Docker compose validates with new mock-todoist service

## Verification

- `python e2e/mock-todoist-api/server.py --selftest` exits 0 with all checks passed
- `python -m pytest backend/tests/test_todoist_*.py -v` — 239 tests pass (no regressions)
- `docker compose -f docker-compose.test.yml config --quiet` — validates without error
- `rg "os.environ" apps/todoist-sync/services/todoist_client.py apps/todoist-sync/services/auth.py` — both files use env var

## Observability Impact

- Signals added/changed: Mock server logs each request method+path+status to stderr for Docker log inspection
- How a future agent inspects this: `docker compose -f docker-compose.test.yml logs mock-todoist` or `python e2e/mock-todoist-api/server.py --selftest`
- Failure state exposed: Selftest prints `[selftest] FAIL: {endpoint}` with expected vs actual, exits non-zero on any failure

## Inputs

- `e2e/mock-github-api/server.py` — Reference implementation for mock server structure, selftest pattern, and `_make_test_request` helper
- `apps/todoist-sync/services/todoist_client.py` — Has hardcoded `TODOIST_API_URL` constant at line 27
- `apps/todoist-sync/services/auth.py` — Has hardcoded `"https://api.todoist.com/rest/v2/projects"` in `verify_token()` at line 72
- `docker-compose.test.yml` — Existing mock-github and mock-google-calendar service blocks as pattern
- S03-RESEARCH.md canned data section — Exact JSON for projects, tasks, labels responses

## Expected Output

- `e2e/mock-todoist-api/server.py` — ~250-line mock server with canned responses and selftest
- `apps/todoist-sync/services/todoist_client.py` — `TODOIST_API_URL` reads from env var with production default
- `apps/todoist-sync/services/auth.py` — `verify_token()` uses env var for API URL
- `docker-compose.test.yml` — `mock-todoist` service added, `TODOIST_API_URL` env var on api service
