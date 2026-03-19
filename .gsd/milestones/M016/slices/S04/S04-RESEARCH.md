# S04: E2E Tests + User Guide — Research

**Date:** 2026-03-18

## Summary

S04 is the terminal slice: write a Playwright E2E test proving the Linear sync app works end-to-end within the Docker test stack, and write user guide Chapter 34 documenting the full workflow. The app code is complete (S01–S03), with 189 unit tests covering all pure logic. The E2E test adds integration proof; the guide adds user-facing documentation.

The main challenge is mocking the Linear API for the E2E test. The linear-sync app's Python subprocess makes direct HTTP calls via httpx to `https://api.linear.app/graphql` — Playwright's network interception operates at the browser level and can't intercept server-side HTTP calls. The solution is a lightweight mock HTTP server added to the Docker test stack, plus a small code change to make `LINEAR_GRAPHQL_URL` configurable via environment variable so the app subprocess calls the mock instead of the real Linear API. The HttpClient domain enforcement in the SDK also needs the mock hostname added to the manifest's allowed domains (or use a wildcard for test mode).

The user guide follows the established pattern: Chapter 33 → Chapter 34 → Appendix A navigation chain. Content covers installation, API key configuration, team selection, sync behavior, push sync, admin monitoring, and troubleshooting.

## Recommendation

Split into two tasks: T01 builds the E2E test infrastructure (mock server, URL override, test spec), T02 writes the user guide chapter. These are independent — the guide documents existing behavior, the test proves it. T01 is more complex and should go first because it may surface integration issues that inform the guide's troubleshooting section.

For the mock server, use a minimal Python HTTP handler (stdlib `http.server` or a 30-line FastAPI app) that returns canned GraphQL responses for viewer, organization, teams, and issues queries. This avoids adding any new dependencies to the Docker stack — just a new service with the existing Python image.

## Implementation Landscape

### Key Files

**E2E test infrastructure:**
- `e2e/tests/31-linear-sync/linear-sync.spec.ts` — new Playwright E2E test (directory 31, next available number after 30-app-platform)
- `e2e/helpers/selectors.ts` — add selectors for linear-sync settings page elements
- `e2e/helpers/wait-for.ts` — existing helpers (no changes needed)
- `e2e/fixtures/auth.ts` — existing auth fixture (no changes needed)

**Mock Linear API:**
- `e2e/mock-linear-api/server.py` — new lightweight Python HTTP server returning canned GraphQL responses
- `docker-compose.test.yml` — add `mock-linear` service running the mock server

**App code changes for testability:**
- `apps/linear-sync/services/linear_client.py` — make `LINEAR_GRAPHQL_URL` configurable via `LINEAR_API_URL` env var
- `apps/linear-sync/services/auth.py` — make `LINEAR_TOKEN_URL` configurable via env var (if needed for OAuth test)
- `apps/linear-sync/manifest.yaml` — the domain enforcement needs to allow the mock server hostname. Options: (a) add `mock-linear` to network domains in test mode, or (b) the mock server uses a hostname that matches `*.linear.app` glob. Simplest: override via env var isn't possible for manifest. Instead, the mock server should be named `api.linear.app` in the Docker network — Docker DNS will resolve it to the mock container, and the domain check passes.

**User guide:**
- `docs/guide/34-linear-sync.md` — new Chapter 34
- `docs/guide/README.md` — add Chapter 34 to TOC
- `docs/guide/33-context-overlay.md` — update navigation footer (Next → Ch 34)
- `docs/guide/appendix-a-environment-variables.md` — update navigation footer if needed
- `docs/guide/appendix-d-glossary.md` — add glossary entries (Linear Sync, Bidirectional Sync, Pull Sync, Push Sync)

**Existing reference files (read-only):**
- `e2e/tests/30-app-platform/app-platform.spec.ts` — reference pattern for app install → configure → verify lifecycle
- `docs/guide/29-app-platform.md` — reference pattern for app-related user guide chapter
- `apps/linear-sync/frontend/templates/connect.html` — API key form selectors
- `apps/linear-sync/frontend/templates/connect_status.html` — settings page selectors (teams, sync config, sync now, stats)

### Build Order

**T01: E2E Test** — build first because it validates the integration and may reveal issues.

1. Create mock Linear API server (`e2e/mock-linear-api/server.py`) — returns canned responses for:
   - `{ viewer { id name email } }` — viewer profile
   - `{ organization { id name urlKey } }` — workspace info
   - `{ teams { nodes { ... } } }` — team list (1–2 teams)
   - `issues(filter: ...)` — paginated issues (3–5 mock issues with various states/priorities)
   - `team(id) { states { nodes { ... } } }` — workflow states
   - `issueUpdate(...)` mutation — success response

2. Make `LINEAR_GRAPHQL_URL` configurable: read from `os.environ.get("LINEAR_API_URL", "https://api.linear.app/graphql")` in `linear_client.py`. Same for `LINEAR_TOKEN_URL` in both files.

3. Add `mock-linear` service to `docker-compose.test.yml`:
   - Simple Python container running `server.py` on port 8080
   - Network alias `mock-linear` on `sempkm-test` network
   - API container gets `LINEAR_API_URL=http://mock-linear:8080/graphql` env var
   - **Domain enforcement workaround:** Either (a) add `mock-linear` to the manifest network domains list during test, or (b) set the env var to `http://mock-linear:8080/graphql` and add `mock-linear` to allowed domains. The HttpClient checks the hostname against the manifest's allowed domains list. Since the manifest allows `api.linear.app`, and we're calling `mock-linear:8080`, the domain check will fail. **Best approach:** The `HttpClient` is instantiated by the SDK `AppContext` with domains from the manifest. The simplest fix is to also allow `mock-linear` in the manifest's network list — it's harmless in production (no DNS resolution) and makes tests work. Alternatively, update the app to make the domain list configurable via env var, but that's a bigger change. Pragmatic: just add `"mock-linear"` to the manifest network list.

4. Write `linear-sync.spec.ts` following the app-platform test pattern:
   - Phase 0: Cleanup — uninstall linear-sync if already present
   - Phase 1: Install basic-pkm model (prerequisite for bpkm:Task type) — skip if already installed
   - Phase 2: Install linear-sync app → wait for Running status
   - Phase 3: Open app settings page in workspace → verify connect form visible
   - Phase 4: Enter API key → submit → verify connected status with workspace name
   - Phase 5: Select a team checkbox → save teams → verify selection persisted
   - Phase 6: Configure sync direction (bidirectional) and interval → save → verify
   - Phase 7: Click Sync Now → wait for sync stats to appear → verify task creation counts
   - Phase 8: Verify synced tasks appear in object browser (SPARQL query or UI check)
   - Phase 9: Admin detail page shows sync task history
   - Phase 10: Cleanup — uninstall app

**T02: User Guide Chapter 34** — write after E2E test, referencing actual UI behavior.

1. Write `docs/guide/34-linear-sync.md` covering:
   - What the Linear Sync app does
   - Prerequisites (basic-pkm model installed)
   - Installation from Admin > Applications
   - Connecting via API key (with screenshot reference)
   - OAuth connection (brief, since not fully implemented)
   - Selecting teams to sync
   - Sync direction and poll interval configuration
   - Manual sync (Sync Now)
   - Understanding sync status and stats
   - How field mapping works (status, priority, assignee, etc.)
   - Push sync and bidirectional mode
   - Troubleshooting common issues
   - See Also references

2. Update `docs/guide/README.md` — add line `34. [Linear Sync](34-linear-sync.md)`

3. Update navigation chain: Ch 33 footer → Ch 34, Ch 34 footer → Appendix A

4. Add glossary entries to `appendix-d-glossary.md`

### Verification Approach

**E2E test verification:**
- `npx playwright test e2e/tests/31-linear-sync/linear-sync.spec.ts` against Docker test stack
- Mock server returns predictable data → assertions on specific task counts, team names, workspace name
- SPARQL query via `ownerRequest.post()` to verify tasks created with correct properties

**User guide verification:**
- All internal links resolve (no broken `[text](path)` references)
- README TOC includes Chapter 34
- Navigation chain: Ch 33 → Ch 34 → Appendix A (check footer links)
- Glossary entries exist

## Constraints

- `LINEAR_GRAPHQL_URL` and `LINEAR_TOKEN_URL` are module-level constants in `linear_client.py` and `auth.py` — must be changed to env-var-configurable for mock server to work. This is a small but necessary code change.
- The HttpClient domain enforcement reads from the manifest at app install time. Adding `"mock-linear"` to the manifest's network list is the simplest way to allow mock API calls. This is safe in production (DNS won't resolve `mock-linear` outside Docker).
- The app install process includes venv creation and SDK install, which takes 30-60 seconds in Docker. The E2E test needs generous timeouts (matching the app-platform test's 240s pattern).
- The basic-pkm model must be installed before linear-sync can create bpkm:Task objects. The test needs a prerequisite step.
- Knowledge: "Workspace explorer sections start collapsed" — the APPS section must be expanded before clicking the app leaf.
- Knowledge: "E2E tests: Docker stack must run from main tree for auth fixture" — ensure the test runs from the main tree.

## Common Pitfalls

- **Mock server query matching** — GraphQL queries arrive as POST bodies with a `query` string. The mock must parse the query string to determine which canned response to return. Use simple substring matching (`"viewer"` → viewer response, `"issues"` → issues response) rather than full GraphQL parsing.
- **Sync timing** — After clicking "Sync Now", the htmx request may take several seconds while the app fetches from the mock API and processes issues. Use `waitForIdle` plus check for sync stats content rather than fixed timeouts.
- **Phase 2 IRI discovery** — Pull sync creates tasks in phase 1, then needs to SPARQL-discover the minted IRIs for phase 2 (body.set/edge.create). The mock must return issue data that includes description and assignee so both phases execute.
- **API key form is inside the app fragment** — The app page loads via htmx from `/_fragments/connect`. The API key input is inside this fragment, not on the main page. Tests need to wait for the fragment to load before interacting.

## Open Risks

- **Mock server reliability in CI** — The mock server is a new component. If it fails to start or returns unexpected responses, the E2E test fails in ways that look like app bugs. Mitigation: keep the mock dead simple (single file, no dependencies beyond stdlib).
- **App install timing** — The linear-sync app has `requirements.txt` (httpx dependency). Venv creation + pip install adds time to the install step. If the Docker test stack has no internet (offline CI), this fails. Mitigation: the test stack already has `./apps:/app/apps:ro` volume mount and the `backend/sdk` mount, but httpx needs to be pip-installable. The base Docker image already includes httpx (it's in the platform's dependencies), so the app's venv may inherit it or need a --system-site-packages flag. Check during execution.
