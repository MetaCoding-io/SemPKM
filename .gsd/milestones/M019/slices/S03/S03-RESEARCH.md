# S03: E2E Tests + User Guide — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

S03 is the final slice — mock Todoist API server, Playwright E2E test, and Chapter 37 user guide. All app code (auth, client, pull sync, push sync, settings UI) is done from S01+S02. This is a copy-and-adapt job from the GitHub sync (M017) equivalents, which are the closest match (REST API, PAT auth, similar E2E flow). One code change is needed: the Todoist client and auth module hardcode `https://api.todoist.com/rest/v2` — they need an env var override (`TODOIST_API_URL`) so the Docker test stack can redirect to the mock server.

## Recommendation

Three tasks, each independent enough to parallelize but natural to do sequentially:

1. **Mock server + env var fix** — build `e2e/mock-todoist-api/server.py` (canned responses for `/projects`, `/tasks`, `/labels`, `/tasks/{id}/close`, `/tasks/{id}/reopen`, plus health and selftest), add `TODOIST_API_URL` env var to `todoist_client.py` and `auth.py`, wire Docker service in `docker-compose.test.yml`.
2. **E2E Playwright test** — `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` following the github-sync.spec.ts phase structure. Add `todoistSync` selectors to `e2e/helpers/selectors.ts`.
3. **Chapter 37 user guide** — `docs/guide/37-todoist-sync.md` with field mapping tables, priority inversion docs, close/reopen pattern, troubleshooting. Update README TOC, glossary, appendix A env vars, navigation chain (Ch 36 → Ch 37 → Appendix A).

## Implementation Landscape

### Key Files

**Mock server (new):**
- `e2e/mock-todoist-api/server.py` — Clone from `e2e/mock-github-api/server.py` (426 lines). Todoist is simpler — fewer endpoints, no pagination, no timeline. Needs: `GET /health`, `GET /projects`, `GET /tasks`, `GET /labels`, `POST /tasks/{id}/close`, `POST /tasks/{id}/reopen`, `POST /tasks/{id}` (update), `POST /tasks` (create). Selftest with 8-10 checks.

**Env var override (modify):**
- `apps/todoist-sync/services/todoist_client.py` — Line 27: change `TODOIST_API_URL = "https://api.todoist.com/rest/v2"` to `TODOIST_API_URL = os.environ.get("TODOIST_API_URL", "https://api.todoist.com/rest/v2")`. Add `import os`. This matches the github-sync pattern (`GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")`).
- `apps/todoist-sync/services/auth.py` — `verify_token()` hardcodes `"https://api.todoist.com/rest/v2/projects"`. Needs to import and use `TODOIST_API_URL` from `todoist_client` (or duplicate the env var read). Cleanest approach: add `import os` and construct URL from env var inline, e.g. `os.environ.get("TODOIST_API_URL", "https://api.todoist.com/rest/v2") + "/projects"`.

**Docker wiring (modify):**
- `docker-compose.test.yml` — Add `TODOIST_API_URL: http://mock-todoist:8080` env var to the `api` service. Add `mock-todoist` service block (same pattern as `mock-github`). Add `mock-todoist` to api's `depends_on` with `condition: service_healthy`.

**E2E test (new):**
- `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` — Clone from `e2e/tests/32-github-sync/github-sync.spec.ts`. Phases: cleanup → install basic-pkm → install todoist-sync → open app settings → connect PAT → select projects → configure sync → Sync Now → verify tasks via SPARQL → verify admin → cleanup. Known limitation: may hit pre-existing subprocess 500 error at Phase 2 (app startup).

**Selectors (modify):**
- `e2e/helpers/selectors.ts` — Add `todoistSync` block. Based on template IDs in `connect.html`/`connect_status.html`: `patInput: '#todoist-token'`, `connectBtn: '.api-key-form button[type="submit"]'`, `connectStatus: '.connection-status'`, `tokenPreview: '.token-preview'`, `projectCheckbox: '.project-checkbox input[type="checkbox"]'`, `saveProjectsBtn: '.projects-form button[type="submit"]'`, `syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]'`, `saveConfigBtn: '.sync-config-form button[type="submit"]'`, `syncNowBtn: '#sync-now-btn'`, `syncStats: '.sync-stats'`.

**User guide (new):**
- `docs/guide/37-todoist-sync.md` — Chapter 37. Follow structure from Ch. 35 (GitHub Sync, 309 lines). Sections: Prerequisites, Installing, Connecting (PAT), Selecting Projects, Sync Configuration (direction, interval), Manual Sync, Sync Stats, Field Mapping (priority inversion table, status, due dates, labels, external link), Push Sync (close/reopen pattern, supported fields, loop prevention), Admin Monitoring, Troubleshooting, See Also.
- `docs/guide/README.md` — Add line `37. [Todoist Sync](37-todoist-sync.md)` after line 36.
- `docs/guide/appendix-d-glossary.md` — Add **Todoist Sync** entry.
- `docs/guide/appendix-a-environment-variables.md` — Add `TODOIST_API_URL` row.
- `docs/guide/36-google-calendar-sync.md` — Update navigation footer: Next → Chapter 37.
- `docs/guide/37-todoist-sync.md` — Navigation footer: Previous Ch 36, Next Appendix A.

### Canned Mock Data

The mock server needs these canned responses:

**Projects** (`GET /projects`):
```json
[
  {"id": "100001", "name": "Work", "color": "berry_red"},
  {"id": "100002", "name": "Personal", "color": "blue"}
]
```

**Tasks** (`GET /tasks`):
```json
[
  {
    "id": "200001", "content": "Review quarterly report",
    "description": "Check all figures before the board meeting",
    "project_id": "100001", "priority": 4, "is_completed": false,
    "labels": ["urgent", "finance"],
    "due": {"date": "2026-03-25", "is_recurring": false, "string": "Mar 25"},
    "url": "https://todoist.com/showTask?id=200001",
    "created_at": "2026-03-01T10:00:00Z", "creator_id": "12345"
  },
  {
    "id": "200002", "content": "Buy groceries",
    "description": "", "project_id": "100002", "priority": 1,
    "is_completed": false, "labels": [],
    "due": null,
    "url": "https://todoist.com/showTask?id=200002",
    "created_at": "2026-03-10T08:00:00Z", "creator_id": "12345"
  }
]
```

**Labels** (`GET /labels`):
```json
[
  {"id": "300001", "name": "urgent", "color": "red"},
  {"id": "300002", "name": "finance", "color": "yellow"}
]
```

**Close/reopen** (`POST /tasks/{id}/close`, `POST /tasks/{id}/reopen`): Return 204 No Content.

**Update** (`POST /tasks/{id}`): Read body, merge with base task, return merged.

### Build Order

1. **Mock server + env var fix** — This must be done first because the E2E test depends on the mock server in Docker and the env var override in the app code. Selftest verifies the mock in isolation.
2. **E2E test** — Depends on mock server + docker-compose wiring. Can be structurally complete even if the subprocess startup issue blocks execution past Phase 2.
3. **User guide** — Independent of the other two but logically last (documents the finished feature). Includes README TOC, glossary, appendix updates, and navigation chain fixes.

### Verification Approach

| Check | Command / Method |
|-------|-----------------|
| Mock server selftest | `python e2e/mock-todoist-api/server.py --selftest` |
| Env var override works | `rg "os.environ" apps/todoist-sync/services/todoist_client.py apps/todoist-sync/services/auth.py` — both files use env var |
| Existing unit tests still pass | `python -m pytest backend/tests/test_todoist_*.py -v` — 239 tests pass |
| htmx URLs prefixed | `rg "hx-(post\|get)=" apps/todoist-sync/frontend/templates/ \| grep -v "/app/todoist-sync/"` — empty |
| Docker service valid | `docker compose -f docker-compose.test.yml config --quiet` |
| E2E test runs | `npx playwright test e2e/tests/37-todoist-sync/` (may hit pre-existing subprocess issue) |
| User guide navigation chain | `rg "37-todoist" docs/guide/` — appears in README, glossary, appendix, ch. 36 footer |
| Glossary entry exists | `rg "Todoist Sync" docs/guide/appendix-d-glossary.md` |
| Appendix A env var | `rg "TODOIST_API_URL" docs/guide/appendix-a-environment-variables.md` |

## Constraints

- `todoist_client.py` uses try/except import pattern (not relative imports) for importlib test loading — the `os` import must be at module level, not inside the try/except block.
- Auth's `verify_token()` calls `http_client.get()` with a full URL string — the env var override must construct the full URL, not a path-only route.
- The E2E test will likely hit the pre-existing subprocess 500 error at the "install app" phase. This is documented across M016-M018 and is not Todoist-specific. The test should be structurally complete regardless.
- The mock server uses `http.server` stdlib (no dependencies) — same as all prior mocks. No Dockerfile needed; the `python:3.12-slim` image runs it directly.

## Common Pitfalls

- **Priority values in mock data** — Todoist priority 4 is "urgent" (highest), not lowest. The mock task with `"priority": 4` should appear as `bpkm:priority = "critical"` after sync. The SPARQL verification in the E2E test should check for this.
- **Close endpoint returns 204 not JSON** — `POST /tasks/{id}/close` returns empty body with 204. The mock server must return 204, not 200 with JSON. Same for reopen. The TodoistClient's `close_task()` and `reopen_task()` methods don't read the response body.
- **Project checkbox selector** — The Todoist template uses class `project-checkbox` (not `repo-checkbox-item` like GitHub). The selector in `selectors.ts` must match: `.project-checkbox input[type="checkbox"]`.

## Open Risks

- **Pre-existing subprocess startup bug** — Same as M016/M017/M018 E2E tests. The E2E test is structurally complete but may fail after the app install phase. Document this in the test file comments.
