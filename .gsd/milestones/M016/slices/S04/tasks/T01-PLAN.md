---
estimated_steps: 8
estimated_files: 7
---

# T01: E2E test with mock Linear API server

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M016

## Description

Build the E2E integration test proving the Linear sync app works end-to-end within the Docker test stack. This requires three layers of work:

1. **App code testability** — Make `LINEAR_GRAPHQL_URL` and `LINEAR_TOKEN_URL` configurable via environment variables so the app subprocess calls the mock server instead of the real Linear API. Add `mock-linear` to the manifest's network domain list so the SDK's HttpClient domain check passes.

2. **Mock Linear API server** — A lightweight Python HTTP server (`http.server` stdlib) returning canned GraphQL responses. It receives POST requests with a JSON body containing a `query` string, matches by substring to determine which canned response to return. Covers: `viewer` (profile), `organization` (workspace info), `teams` (team list), `issues` (paginated issues with various statuses/priorities), `states` (workflow states), and `issueUpdate` (mutation success).

3. **Playwright E2E spec** — Following the app-platform test pattern (`e2e/tests/30-app-platform/app-platform.spec.ts`), a serial test with phases: cleanup → install basic-pkm → install linear-sync → connect API key → select team → configure sync → Sync Now → verify tasks via SPARQL → check admin detail → cleanup.

**Relevant skills:** Load the `test` skill for E2E test patterns.

**Key knowledge from KNOWLEDGE.md:**
- "Workspace explorer sections start collapsed" — APPS section must be expanded before clicking.
- "E2E tests: Docker stack must run from main tree for auth fixture" — run from main tree.
- The `/api/sparql` endpoint scopes to `urn:sempkm:current` graph — use it to verify task creation.
- HttpClient domain enforcement reads from manifest's `network` list at install time.

## Steps

1. **Make API URLs configurable via env vars.** In `apps/linear-sync/services/linear_client.py`, change:
   ```python
   LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
   LINEAR_TOKEN_URL = "https://api.linear.app/oauth/token"
   ```
   to:
   ```python
   import os
   LINEAR_GRAPHQL_URL = os.environ.get("LINEAR_API_URL", "https://api.linear.app/graphql")
   LINEAR_TOKEN_URL = os.environ.get("LINEAR_TOKEN_URL", "https://api.linear.app/oauth/token")
   ```
   Similarly in `apps/linear-sync/services/auth.py`, change `LINEAR_TOKEN_URL` to read from env var:
   ```python
   import os
   LINEAR_TOKEN_URL = os.environ.get("LINEAR_TOKEN_URL", "https://api.linear.app/oauth/token")
   ```

2. **Add `mock-linear` to manifest network domains.** In `apps/linear-sync/manifest.yaml`, add `"mock-linear"` to the `permissions.network` list:
   ```yaml
   network:
     - "api.linear.app"
     - "linear.app"
     - "mock-linear"
   ```
   This is harmless in production (DNS won't resolve `mock-linear` outside Docker) and allows the mock server calls to pass domain enforcement.

3. **Create mock Linear API server** at `e2e/mock-linear-api/server.py`. Use Python stdlib `http.server`. The server:
   - Listens on port 8080
   - Handles POST to `/graphql` — reads JSON body, extracts `query` string
   - Uses substring matching to return canned responses:
     - `"viewer"` in query → `{ "data": { "viewer": { "id": "user-1", "name": "Test User", "email": "test@example.com" } } }`
     - `"organization"` in query → `{ "data": { "organization": { "id": "org-1", "name": "Test Workspace", "urlKey": "test-ws" } } }`
     - `"teams"` in query → 2 teams with ids, names, keys
     - `"states"` in query → workflow states covering triage/backlog/unstarted/started/completed/canceled types
     - `"issues"` in query → 3 mock issues with varied statuses, priorities, assignees, labels, dates. Include `pageInfo` with `hasNextPage: false`. Each issue needs: `id`, `identifier`, `title`, `description`, `priority` (1-4), `dueDate`, `url`, `createdAt`, `updatedAt`, `state` (with `type` field), `assignee` (with `name`/`email`), `labels` (nodes array), `team` (with `id`/`name`/`key`)
     - `"issueUpdate"` in query → `{ "data": { "issueUpdate": { "success": true, "issue": { "id": "...", "updatedAt": "..." } } } }`
   - Returns `Content-Type: application/json`
   - Logs each matched query type to stdout for debugging

4. **Add `mock-linear` service to `docker-compose.test.yml`.** Add a service that runs the mock server:
   ```yaml
   mock-linear:
     image: python:3.12-slim
     volumes:
       - ./e2e/mock-linear-api:/app:ro
     working_dir: /app
     command: ["python", "server.py"]
     networks:
       - sempkm-test
     healthcheck:
       test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/graphql')"]
       interval: 3s
       timeout: 3s
       retries: 5
   ```
   Add `LINEAR_API_URL: http://mock-linear:8080/graphql` and `LINEAR_TOKEN_URL: http://mock-linear:8080/oauth/token` to the `api` service's environment. Add `mock-linear` to the api service's `depends_on` (with `condition: service_healthy`).

   Note: The healthcheck for mock-linear needs to handle the POST-only /graphql endpoint. The simplest approach is to also handle GET requests on `/graphql` returning a simple `{"status":"ok"}` JSON, or use a different path like `/health`. Alternatively, use a Python `-c` snippet that does a POST. Simplest: have the mock server respond to GET on `/` or `/health` with 200.

5. **Add linear-sync selectors to `e2e/helpers/selectors.ts`.** Add a `linearSync` section to the SEL object with selectors for key elements:
   ```typescript
   linearSync: {
     apiKeyInput: '#linear-api-key',
     connectBtn: '.api-key-form button[type="submit"]',
     connectStatus: '.connection-status',
     workspaceName: '.workspace-name',
     teamCheckbox: '.team-checkbox-item input[type="checkbox"]',
     saveTeamsBtn: '.teams-section button[type="submit"]',
     syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
     saveConfigBtn: '.sync-config-form button[type="submit"]',
     syncNowBtn: '#sync-now-btn',
     syncStats: '.sync-stats',
     statValue: '.stat-value',
   },
   ```

6. **Write the Playwright E2E spec** at `e2e/tests/31-linear-sync/linear-sync.spec.ts`. Follow the app-platform test pattern:
   - Import `test, expect, BASE_URL` from auth fixture, SEL from selectors, wait helpers
   - Single `test.describe('Linear Sync')` with single serial `test()` 
   - `test.setTimeout(240_000)` for generous timeout
   - Accept dialog events for hx-confirm on uninstall
   
   **Phases:**
   
   **Phase 0 — Cleanup:** Navigate to `/admin/apps`. If linear-sync card exists, go to detail page and uninstall it. Wait for reload.
   
   **Phase 1 — Prerequisite: basic-pkm model.** Navigate to `/admin/models`. Check if basic-pkm is already installed (look for card with "basic-pkm"). If not installed, install it using the install form at `/admin/models` with path `/app/models/basic-pkm`. Wait for model status to show installed/active. This is needed because linear-sync creates `bpkm:Task` objects.
   
   **Phase 2 — Install linear-sync app.** Navigate to `/admin/apps`. Fill install form with `/app/apps/linear-sync`. Click install. Poll admin list until linear-sync shows "Running" status badge (same polling pattern as app-platform test, up to 120s).
   
   **Phase 3 — Open app settings page.** Navigate to `/browser/`. Wait for workspace to load. Expand the APPS section in the sidebar by clicking its header. Click the "Linear Sync" leaf entry to open the app page. Wait for the connect fragment to load (look for `#connect-content`). Verify the API key form is visible.
   
   **Phase 4 — Connect via API key.** Fill the API key input (`#linear-api-key`) with `lin_api_test_mock_key`. Click the Connect button. Wait for the page to show connected status — look for `.connection-status` containing "Connected" and `.workspace-name` containing "Test Workspace" (from mock response).
   
   **Phase 5 — Select team.** The connected view should show team checkboxes. Check the first team checkbox. Click "Save Teams". Wait for the htmx swap to complete. Verify the checkbox is still checked after re-render.
   
   **Phase 6 — Configure sync.** Select "bidirectional" radio for sync direction. Select poll interval. Click "Save Config". Wait for htmx swap.
   
   **Phase 7 — Sync Now.** Click the "Sync Now" button (`#sync-now-btn`). Wait for sync to complete — watch for `.sync-stats` section to show sync results. Look for `.stat-value` containing a number (created count). This is the key proof moment: the mock API returns 3 issues, so we expect "3" in the created count (or at least > 0).
   
   **Phase 8 — Verify tasks via SPARQL.** Use `ownerRequest.post()` to query the SPARQL endpoint for `bpkm:Task` instances. Send a SPARQL query like:
   ```sparql
   PREFIX bpkm: <https://test.example.org/data/vocab/bpkm/>
   PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
   SELECT (COUNT(?s) AS ?count) WHERE { ?s rdf:type bpkm:Task }
   ```
   Verify the count is ≥ 3 (the number of mock issues). Note: use `BASE_URL` for the API request. The SPARQL endpoint is at `/api/sparql`.
   
   **Phase 9 — Admin detail.** Navigate to `/admin/apps/linear-sync`. Verify the app detail page loads showing "Linear Sync" in the title. Look for task history entries if available.
   
   **Phase 10 — Cleanup.** Click uninstall button on the detail page. Wait for redirect back to apps list. Verify linear-sync no longer appears.

7. **Verify all modified Python files pass syntax check:**
   ```bash
   python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read())"
   python3 -c "import ast; ast.parse(open('apps/linear-sync/services/auth.py').read())"
   python3 -c "import ast; ast.parse(open('e2e/mock-linear-api/server.py').read())"
   ```

8. **Run existing unit tests to confirm no regressions:**
   ```bash
   cd backend && python -m pytest tests/test_field_mapper.py tests/test_sync_engine.py tests/test_push_sync.py tests/test_person_matcher.py -x -q
   ```
   All 189 existing tests should still pass (the env var change uses defaults identical to the old hardcoded values).

## Must-Haves

- [ ] `LINEAR_GRAPHQL_URL` and `LINEAR_TOKEN_URL` in `linear_client.py` read from env vars with existing values as defaults
- [ ] `LINEAR_TOKEN_URL` in `auth.py` reads from env var with existing value as default
- [ ] `mock-linear` added to manifest.yaml network permissions
- [ ] Mock server at `e2e/mock-linear-api/server.py` returns valid canned responses for all query types
- [ ] `mock-linear` service in `docker-compose.test.yml` with `LINEAR_API_URL` env var on api service
- [ ] Playwright spec at `e2e/tests/31-linear-sync/linear-sync.spec.ts` covers install → connect → sync → verify → cleanup
- [ ] Existing unit tests (189) still pass

## Verification

- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/linear_client.py').read())"` — no error
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/auth.py').read())"` — no error
- `python3 -c "import ast; ast.parse(open('e2e/mock-linear-api/server.py').read())"` — no error
- `cd backend && python -m pytest tests/test_field_mapper.py tests/test_sync_engine.py tests/test_push_sync.py tests/test_person_matcher.py -x -q` — 189 pass
- `npx playwright test e2e/tests/31-linear-sync/linear-sync.spec.ts` — all phases pass (requires Docker test stack running with `docker compose -f docker-compose.test.yml up -d --build`)

## Observability Impact

- Mock server logs query type matches to stdout — visible via `docker compose -f docker-compose.test.yml logs mock-linear`
- E2E test phases use descriptive `expect()` assertions so failures identify which phase broke
- No production runtime changes — env var defaults preserve existing behavior

## Inputs

- `apps/linear-sync/services/linear_client.py` — has hardcoded `LINEAR_GRAPHQL_URL` and `LINEAR_TOKEN_URL` at lines 16-17
- `apps/linear-sync/services/auth.py` — has hardcoded `LINEAR_TOKEN_URL` at line 16
- `apps/linear-sync/manifest.yaml` — has `network: ["api.linear.app", "linear.app"]`
- `docker-compose.test.yml` — existing test stack with api, frontend, triplestore services
- `e2e/tests/30-app-platform/app-platform.spec.ts` — reference pattern for app lifecycle E2E test
- `e2e/helpers/selectors.ts` — existing selector constants (apps section at line 157)
- `apps/linear-sync/frontend/templates/connect.html` — API key form with `#linear-api-key` input
- `apps/linear-sync/frontend/templates/connect_status.html` — Connected status page with team checkboxes, sync config, sync now, sync stats
- S03 summary — 150 unit tests passing, sync state keys documented, all routes documented

## Expected Output

- `apps/linear-sync/services/linear_client.py` — `LINEAR_GRAPHQL_URL` and `LINEAR_TOKEN_URL` read from env vars
- `apps/linear-sync/services/auth.py` — `LINEAR_TOKEN_URL` reads from env var
- `apps/linear-sync/manifest.yaml` — `mock-linear` in network permissions
- `e2e/mock-linear-api/server.py` — complete mock server with canned responses
- `docker-compose.test.yml` — `mock-linear` service added, `LINEAR_API_URL`/`LINEAR_TOKEN_URL` env vars on api service
- `e2e/helpers/selectors.ts` — `linearSync` selector section added
- `e2e/tests/31-linear-sync/linear-sync.spec.ts` — complete E2E test spec
