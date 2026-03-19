---
estimated_steps: 8
estimated_files: 2
---

# T01: Mock GitHub REST API server + docker-compose integration

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M017

## Description

Build a mock GitHub REST API server for E2E testing and wire it into the Docker test stack. The mock server provides canned responses for 6 endpoints that `GitHubClient` calls, enabling the Playwright E2E test (T02) to run without a real GitHub account.

Clone the pattern from `e2e/mock-linear-api/server.py` — same Python `http.server` structure, same `--selftest` flag, same Docker healthcheck pattern — but replace GraphQL substring matching with REST path-based routing using `do_GET` and `do_PATCH`.

## Steps

1. **Create `e2e/mock-github-api/server.py`** — Clone `e2e/mock-linear-api/server.py` as the skeleton. Replace `do_POST` with `do_GET` and `do_PATCH` methods. Use `self.path` for route matching.

2. **Implement canned response data** — Define these constants:
   - `USER_RESPONSE`: `{"login": "test-user", "id": 12345, "name": "Test User", "email": "test@example.com"}`
   - `REPOS_RESPONSE`: Array of 2 repos — `{"full_name": "test-owner/test-repo", "name": "test-repo", "private": false, "has_issues": true}` and `{"full_name": "test-owner/empty-repo", "name": "empty-repo", "private": true, "has_issues": true}`
   - `ISSUES_RESPONSE`: Array of 3 items:
     - Issue #1: open, with labels `["bug", "priority-high"]` and assignee (login `test-user`, email `test@example.com`), has body text, has milestone `{"title": "v1.0"}`
     - Issue #2: closed (state_reason: `completed`), no assignee, no labels
     - Item #3: open PR (has `"pull_request": {"html_url": "..."}` key), with label `["enhancement"]`
   - `TIMELINE_RESPONSE`: Array with 1 `cross-referenced` event — `{"event": "cross-referenced", "source": {"issue": {"number": 3, "pull_request": {"html_url": "..."}, "repository": {"full_name": "test-owner/test-repo"}}}}`
   - `PATCH_RESPONSE_TEMPLATE`: Function that echoes back patched fields (title/state) merged with base issue data

3. **Implement `do_GET` routing** — Match paths:
   - `/user` → `USER_RESPONSE`
   - `/user/repos` → `REPOS_RESPONSE`
   - `/repos/test-owner/test-repo/issues` → `ISSUES_RESPONSE` (filter by `state=all` if present in query params)
   - `/repos/test-owner/test-repo/issues/1/timeline` → `TIMELINE_RESPONSE`
   - `/repos/test-owner/test-repo/issues/2/timeline` → `[]` (empty)
   - `/repos/test-owner/test-repo/issues/3/timeline` → `[]` (empty)
   - `/health` → `{"status": "ok"}`
   - Default → 404

4. **Implement `do_PATCH` routing** — Match `/repos/test-owner/test-repo/issues/{n}`. Read JSON body, merge with base issue data for that number, return the merged result. This validates push sync.

5. **Add rate-limit headers to every response** — Include `X-RateLimit-Remaining: 4999` and `X-RateLimit-Reset: {future_epoch}` on ALL responses to prevent the client's `_check_rate_limit()` from sleeping.

6. **Add `--selftest` mode** — When `sys.argv` contains `--selftest`, simulate GET requests to all endpoints and PATCH to issue #1, verify response codes and data shapes, print results, exit with code 0 on success / 1 on failure. Follow the mock-linear pattern exactly.

7. **Wire into docker-compose.test.yml**:
   - Add `mock-github` service block (copy `mock-linear` structure, change volume to `./e2e/mock-github-api:/app:ro`)
   - Add `GITHUB_API_URL: http://mock-github:8080` to `api.environment`
   - Add `mock-github: condition: service_healthy` to `api.depends_on`

8. **Validate** — Run selftest, check docker-compose config.

## Must-Haves

- [ ] Mock server handles all 6 GET endpoints and PATCH endpoint with correct response formats
- [ ] Canned issues include: open issue with labels/assignee, closed issue, PR (with `pull_request` key)
- [ ] Timeline endpoint returns cross-referenced event linking PR #3 to issue #1
- [ ] Rate-limit headers on every response (prevent client sleep)
- [ ] `--selftest` exits 0 with all endpoints validated
- [ ] docker-compose.test.yml has mock-github service with GITHUB_API_URL wired to api

## Verification

- `python e2e/mock-github-api/server.py --selftest` exits 0
- `docker compose -f docker-compose.test.yml config --services` lists `mock-github`
- `docker compose -f docker-compose.test.yml config` shows `GITHUB_API_URL: http://mock-github:8080` in api environment

## Observability Impact

- Signals added/changed: Mock server logs each request to stderr as `{method} {path} → {status}` for debugging failed E2E runs
- How a future agent inspects this: `docker compose -f docker-compose.test.yml logs mock-github` shows request log
- Failure state exposed: Selftest prints per-endpoint PASS/FAIL with expected vs actual status codes

## Inputs

- `e2e/mock-linear-api/server.py` — Reference pattern to clone (252 lines, Python http.server, --selftest, canned responses)
- `docker-compose.test.yml` — Existing test stack to extend with mock-github service
- `apps/github-sync/services/github_client.py` — Line 19: `GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")` — the env var that redirects the client to the mock
- S04-RESEARCH.md mock server endpoints table — authoritative spec for required endpoints and response shapes
- S01 forward intelligence: `MockExternalHttpClient` response queue ordering matters — the mock server must return items in the order the client expects (repos → issues → timeline)

## Expected Output

- `e2e/mock-github-api/server.py` — Complete mock server (~250-300 lines) with 6 GET routes, 1 PATCH route, --selftest, rate-limit headers, health endpoint
- `docker-compose.test.yml` — Updated with mock-github service block and GITHUB_API_URL env var on api container
