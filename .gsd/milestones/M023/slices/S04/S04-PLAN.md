# S04: E2E Tests + User Guide

**Goal:** Mock Jira REST API server passes selftest, Playwright E2E test exercises the full install → configure → sync → verify lifecycle, and Chapter 36 user guide documents Jira sync with field mapping tables.
**Demo:** `python e2e/mock-jira-api/server.py --selftest` exits 0. Playwright E2E test against Docker test stack completes all phases. Chapter 36 exists at `docs/guide/36-jira-sync.md` with prerequisites, installation, connection, field mapping, statusCategory explanation, and ADF conversion notes.

## Must-Haves

- Mock Jira REST API server at `e2e/mock-jira-api/server.py` with 7 endpoints (health, myself, projects, search, user, issue update, issue get) and `--selftest` mode
- Canned data includes: 2 projects (PROJ/DESIGN), 3 issues (1 in-progress with assignee, 1 todo unassigned, 1 done epic), issue links with Blocks inward entry for dependsOn verification
- Docker integration: `mock-jira` service in `docker-compose.test.yml` with `JIRA_API_URL` env var
- `jiraSync` selector block in `e2e/helpers/selectors.ts`
- Playwright E2E test at `e2e/tests/41-jira-sync/jira-sync.spec.ts` following the 12-phase pattern
- User guide Chapter 36 at `docs/guide/36-jira-sync.md` with field mapping tables, statusCategory explanation, ADF conversion notes, JQL filter documentation
- README TOC, glossary, appendix-a, and navigation chain (Ch 35 ↔ Ch 36 ↔ Appendix A) updated

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker Compose stack with mock API)
- Human/UAT required: no

## Verification

- `python e2e/mock-jira-api/server.py --selftest` exits 0 with all endpoint checks passing
- `jiraSync` block present in `e2e/helpers/selectors.ts` with all expected selectors
- `docker-compose.test.yml` has `mock-jira` service and `JIRA_API_URL` env var on api container
- `e2e/tests/41-jira-sync/jira-sync.spec.ts` exists with all 12 phases (cleanup → install → connect → select projects → configure → sync → verify tasks via SPARQL → verify epic/milestone → verify dependsOn → admin → cleanup)
- `docs/guide/36-jira-sync.md` exists with sections: Prerequisites, Installing, Connecting, Project Selection, JQL Filter, Sync Configuration, Field Mapping (status + priority tables), Push Sync, Epic→Milestone, Issue Links, Troubleshooting
- `docs/guide/README.md` has Chapter 36 entry
- `docs/guide/appendix-d-glossary.md` has Jira Sync + statusCategory + ADF entries
- Navigation chain: Ch 35 → Ch 36 → Appendix A

## Integration Closure

- Upstream surfaces consumed: S01–S03 complete Jira sync app (all services, routes, templates, CSS), `apps/jira-sync/services/jira_client.py` (JIRA_API_URL override), `apps/jira-sync/frontend/templates/connect.html` + `connect_status.html` (form selectors)
- New wiring introduced in this slice: `mock-jira` Docker service, `JIRA_API_URL` env var on api container, `jiraSync` selectors
- What remains before the milestone is truly usable end-to-end: nothing — S04 is the final slice

## Tasks

- [x] **T01: Build mock Jira REST API server with selftest** `est:1h`
  - Why: The E2E test needs a canned Jira API server running in Docker. Building and verifying it standalone first (via `--selftest`) ensures the mock is correct before Docker integration.
  - Files: `e2e/mock-jira-api/server.py`
  - Do: Clone the `e2e/mock-github-api/server.py` pattern. Implement 7 endpoints: GET `/health`, GET `/rest/api/3/myself`, GET `/rest/api/3/project`, POST `/rest/api/3/search` (JSON body with jql/startAt/maxResults/fields), GET `/rest/api/3/user` (accountId query param), GET `/rest/api/3/issue/{key}`, PUT `/rest/api/3/issue/{key}` (fields body, echo-back). Canned data: 2 projects (PROJ key="PROJ" name="Test Project", DESIGN key="DESIGN" name="Design Team"), 3 issues in PROJ (PROJ-1 in-progress with assignee accountId "user-abc-123" and issue link Blocks inward from PROJ-3, PROJ-2 todo unassigned, PROJ-3 done Epic type). User response for accountId "user-abc-123" returns email "test@example.com" and displayName "Test User". Search response returns all 3 issues with nested `fields` structure matching Jira REST API format (statusCategory.key, issuetype.name, priority.name, assignee.accountId, labels array, components array, sprint object, issuelinks). Implement `--selftest` mode verifying all endpoints with expect_check lambdas. Key constraints: (1) POST search must parse JSON body, (2) PUT update must read fields from body and echo merged result, (3) issue links must use correct Jira format with type.name="Blocks" and inwardIssue key, (4) Epic must have issuetype.name="Epic" (capitalized), (5) user endpoint must parse accountId from query string.
  - Verify: `python e2e/mock-jira-api/server.py --selftest` exits 0
  - Done when: All selftest checks pass (health, myself, projects, search, user, issue get, issue update, 404 unknown)

- [x] **T02: Wire Docker integration, add selectors, and write Playwright E2E test** `est:1h30m`
  - Why: The E2E test proves the full Jira sync lifecycle against the Docker test stack. Docker integration connects the mock to the API container, selectors provide stable element references, and the test exercises install → connect → sync → verify.
  - Files: `docker-compose.test.yml`, `e2e/helpers/selectors.ts`, `e2e/tests/41-jira-sync/jira-sync.spec.ts`
  - Do: (1) Add `mock-jira` service to docker-compose.test.yml following the mock-github pattern (python:3.12-slim, volume mount `./e2e/mock-jira-api:/app:ro`, healthcheck on `/health`, sempkm-test network). Add `JIRA_API_URL: http://mock-jira:8080` to api environment. Add `mock-jira: condition: service_healthy` to api depends_on. (2) Add `jiraSync` block to selectors.ts: emailInput `#jira-email`, tokenInput `#jira-token`, siteUrlInput `#jira-site-url`, connectBtn `.credentials-form button[type="submit"]`, connectStatus `.connection-status`, siteUrl `.site-url`, projectCheckbox `.project-checkbox-item input[type="checkbox"]`, saveProjectsBtn `.projects-section button[type="submit"]`, syncDirectionBidirectional `input[name="sync_direction"][value="bidirectional"]`, saveConfigBtn `.sync-config-form button[type="submit"]`, syncNowBtn `#sync-now-btn`, syncStats `.sync-stats`. (3) Write E2E test following github-sync.spec.ts 12-phase pattern. Key differences from GitHub test: Phase 0 cleanup uses app ID `jira-sync`, Phase 4 connect fills 3 fields (email, token, site_url) not 1, Phase 5 selects project checkboxes, Phase 8 SPARQL uses `bpkm:Task` count query, Phase 9 uses ASK query for Epic→Milestone (`bpkm:Milestone` type), Phase 9b uses ASK query for dependsOn edges, Phase 10 admin check. KNOWLEDGE.md constraints: APPS section starts collapsed (must expand before clicking leaf), htmx URLs already have proxy prefix in templates. Test timeout 240s.
  - Verify: `e2e/tests/41-jira-sync/jira-sync.spec.ts` exists with all phases. `grep -c "jiraSync" e2e/helpers/selectors.ts` returns 1. `grep "mock-jira" docker-compose.test.yml` shows service and env var.
  - Done when: E2E test file has all 12 phases, selectors block has all 12 entries, docker-compose.test.yml has mock-jira service + JIRA_API_URL env var + depends_on entry

- [x] **T03: Write user guide Chapter 36 and update cross-references** `est:1h`
  - Why: The user guide documents the Jira sync feature for end users. Chapter 36 follows the established pattern from Chapter 35 (GitHub Sync) with Jira-specific content.
  - Files: `docs/guide/36-jira-sync.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/appendix-a-environment-variables.md`, `docs/guide/35-github-sync.md`
  - Do: (1) Write Chapter 36 following Chapter 35's structure. Sections: title, intro paragraph, Prerequisites (basic-pkm model + Jira Cloud API token + site URL), Installing the App (path `/app/apps/jira-sync`), Connecting to Jira (3-field form: email + token + site URL, auth method table showing API token only), Project Selection (checkbox list), JQL Filter (optional JQL clause with examples), Sync Configuration (direction: pull-only/bidirectional, poll interval), Field Mapping section with two tables (Status Mapping: statusCategory.key new→todo, indeterminate→in-progress, done→done; Priority Mapping: Highest/Critical/Blocker→critical, High→high, Medium→medium, Low/Lowest/Trivial→low), Jira-specific fields (labels+components→tags, sprint→taskGroup, assignee via accountId resolution), Status Names paragraph explaining statusCategory vs status.name and bpkm:externalStatus, ADF Conversion Notes (Atlassian Document Format→Markdown, supported node types list, unsupported placeholder), Push Sync (title/description/priority only, no status transitions per D237, Markdown→ADF reverse), Epic→Milestone Mapping (Epic issuetype creates bpkm:Milestone, child issues linked), Issue Links (Blocks→dependsOn edges, inward-only dedup per D240), Troubleshooting (common issues), navigation footer. (2) Update README.md TOC: add `36. [Jira Sync](36-jira-sync.md)` after line 64. (3) Add glossary entries: Jira Sync, Atlassian Document Format (ADF), statusCategory. (4) Add `JIRA_API_URL` to appendix-a. (5) Update Ch 35 navigation footer: Next → Chapter 36. (6) Ch 36 footer: Previous Ch 35, Next Appendix A.
  - Verify: `test -f docs/guide/36-jira-sync.md && grep "36.*Jira" docs/guide/README.md && grep -i "jira sync" docs/guide/appendix-d-glossary.md && grep "JIRA_API_URL" docs/guide/appendix-a-environment-variables.md`
  - Done when: Chapter 36 exists with all sections, README TOC has entry, glossary has 3 entries, appendix-a has JIRA_API_URL, navigation chain Ch 35 → Ch 36 → Appendix A is correct

## Observability / Diagnostics

- **Mock server logs:** All mock-jira HTTP requests are logged to stderr with `[mock-jira]` prefix — visible in Docker container logs via `docker compose logs mock-jira`.
- **Selftest output:** `python server.py --selftest` prints pass/fail per endpoint with `✓`/`✗` markers and a summary line. Exit code 0 = all passed.
- **Health endpoint:** `GET /health` returns `{"status": "ok"}` — used by Docker healthcheck and manual inspection (`curl http://mock-jira:8080/health`).
- **Docker service status:** `docker compose ps mock-jira` shows container health. Service won't start the API container until mock-jira is healthy (depends_on condition).
- **E2E test diagnostics:** Playwright test phases emit `console.log` at phase boundaries. Sync stats are verified via DOM selectors after sync completes.
- **Failure visibility:** Mock returns 404 with `{"message": "Not Found"}` for unrecognized paths — distinguishable from network errors. PUT/POST parse errors return 400 with `{"message": "Invalid JSON"}`.
- **Redaction:** No real credentials are used — mock ignores Authorization headers entirely. Canned data uses synthetic identifiers (`user-abc-123`, `test@example.com`).

## Files Likely Touched

- `e2e/mock-jira-api/server.py` (new)
- `docker-compose.test.yml`
- `e2e/helpers/selectors.ts`
- `e2e/tests/41-jira-sync/jira-sync.spec.ts` (new)
- `docs/guide/36-jira-sync.md` (new)
- `docs/guide/README.md`
- `docs/guide/appendix-d-glossary.md`
- `docs/guide/appendix-a-environment-variables.md`
- `docs/guide/35-github-sync.md`
