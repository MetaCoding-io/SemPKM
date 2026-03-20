# S04: E2E Tests + User Guide

**Goal:** Mock Microsoft Graph API server passes selftest, Playwright E2E test proves install→OAuth→sync→verify→RSVP push lifecycle, and Chapter 38 user guide documents Outlook Calendar Sync with Azure AD setup and field mapping tables.
**Demo:** `python server.py --selftest` exits 0 with all checks passing. `npx playwright test outlook-calendar-sync.spec.ts` passes (structurally complete). `docs/guide/38-outlook-calendar-sync.md` exists with heading structure, field mapping tables, and Azure AD setup. README TOC, glossary, appendix A env vars, and navigation chain all updated.

## Must-Haves

- Mock Microsoft Graph API server (`e2e/mock-outlook-api/server.py`) with canned endpoints: `/health`, token exchange, calendar list, delta events, RSVP PATCH, and user profile
- Mock server selftest with 11+ checks covering all endpoints
- Docker Compose `mock-outlook` service wired into `docker-compose.test.yml` with env var overrides for the API container
- Playwright E2E test covering: cleanup → install basic-pkm → install outlook-calendar → enter Azure AD credentials → simulate OAuth → select calendars → configure bidirectional sync → Sync Now → verify events via SPARQL → verify RRULE on recurring event → admin detail → uninstall
- `outlookCalendarSync` selector block in `e2e/helpers/selectors.ts`
- Chapter 38 user guide with Prerequisites, Azure AD setup, field mapping tables (showAs, sensitivity, recurrence pattern types), RSVP push-back, troubleshooting
- README TOC entry for Chapter 38
- Glossary entry for "Outlook Calendar Sync"
- Appendix A entries for `OUTLOOK_API_URL`, `OUTLOOK_TOKEN_URL`, `OUTLOOK_AUTH_URL`
- Navigation chain: Ch 37 → Ch 38 → Appendix A
- htmx prefix audit: `grep -rn "hx-" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/"` returns 0 results

## Proof Level

- This slice proves: integration (mock API server + E2E lifecycle) + final-assembly (docs closure)
- Real runtime required: yes (Docker test stack with mock-outlook service)
- Human/UAT required: no

## Verification

- `cd e2e/mock-outlook-api && python3 server.py --selftest` — all checks pass, exit 0
- `npx playwright test outlook-calendar-sync.spec.ts` against Docker test stack — structurally complete (some phases may hit known app startup timing)
- `test -f docs/guide/38-outlook-calendar-sync.md` — file exists
- `grep "38.*Outlook" docs/guide/README.md` — returns TOC entry
- `grep "Outlook Calendar Sync" docs/guide/appendix-d-glossary.md` — returns glossary entry
- `grep "OUTLOOK_API_URL\|OUTLOOK_TOKEN_URL\|OUTLOOK_AUTH_URL" docs/guide/appendix-a-environment-variables.md` — returns 3 lines
- Navigation chain: Ch 37 ends with "Next: Chapter 38", Ch 38 ends with "Next: Appendix A"
- `grep -rn "hx-" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/"` — returns 0 results (htmx prefix audit)
- Mock server selftest includes at least one error-path check (invalid token, missing calendar ID, or similar) — failure visibility

## Observability / Diagnostics

- Runtime signals: mock server prints `[selftest] N/N passed` on selftest; E2E test phases logged to stdout via Playwright reporter
- Inspection surfaces: `python server.py --selftest` for mock health; Docker healthcheck on `http://localhost:8080/health`; E2E test output with per-phase assertions
- Failure visibility: mock selftest reports per-check pass/FAIL with endpoint and expected vs actual; E2E test assertions identify which phase broke; mock server returns structured JSON error bodies on 4xx responses
- Redaction constraints: none (mock server uses fake credentials only)

## Integration Closure

- Upstream surfaces consumed: `apps/outlook-calendar/` (all services, templates, manifest), `docker-compose.test.yml` (test stack), `e2e/helpers/selectors.ts`, `e2e/fixtures/auth.ts`, `docs/guide/` (README, glossary, appendix A, Ch 37 navigation)
- New wiring introduced in this slice: `mock-outlook` Docker Compose service, `OUTLOOK_API_URL`/`OUTLOOK_TOKEN_URL`/`OUTLOOK_AUTH_URL` env vars on api container, `outlookCalendarSync` selector block
- What remains before the milestone is truly usable end-to-end: nothing — S04 is the terminal slice

## Tasks

- [x] **T01: Build mock Microsoft Graph API server and wire Docker Compose** `est:1h`
  - Why: The mock server is the foundation — without it the E2E test can't exercise the Outlook sync lifecycle against canned Graph API responses. Docker Compose wiring makes it available to the test stack.
  - Files: `e2e/mock-outlook-api/server.py`, `docker-compose.test.yml`
  - Do: Clone `e2e/mock-google-calendar-api/server.py` structure. Implement 6 endpoints: `GET /health`, `POST /common/oauth2/v2.0/token` (token exchange/refresh), `GET /v1.0/me/calendars` (calendar list), `GET /v1.0/me/calendars/{id}/events/delta` (delta events with `@odata.deltaLink`), `PATCH /v1.0/me/events/{id}` (RSVP push-back), `GET /v1.0/me` (user profile for email). Canned events must include: 1 timed event with attendees + categories + conferenceUrl + showAs + sensitivity, 1 all-day event, 1 recurring event with structured `recurrence` object (weekly pattern + endDate range). Selftest with 11+ checks including at least one error-path check (e.g. PATCH with invalid event ID returns 404). Add `mock-outlook` service to `docker-compose.test.yml` and add `OUTLOOK_API_URL`, `OUTLOOK_TOKEN_URL`, `OUTLOOK_AUTH_URL` env vars to the `api` service.
  - Verify: `cd e2e/mock-outlook-api && python3 server.py --selftest` — all checks pass, exit 0
  - Done when: selftest passes with 11+ checks and `docker-compose.test.yml` has `mock-outlook` service with env var wiring

- [x] **T02: Write Playwright E2E test for Outlook Calendar Sync lifecycle** `est:45m`
  - Why: The E2E test proves the full install→OAuth→sync→verify→RSVP push lifecycle against the mock server, exercising real HTTP paths through the Docker test stack.
  - Files: `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Add `outlookCalendarSync` selector block to `selectors.ts` with Outlook-specific IDs (`#outlook-client-id`, `#outlook-client-secret`, `.btn-microsoft`, etc.). Clone the Google Calendar E2E test structure for the spec file. Phases: (0) cleanup prior install, (1) ensure basic-pkm model, (2) install outlook-calendar app → wait for Running status + `waitForTimeout(5000)`, (3) enter Azure AD credentials + simulate OAuth by extracting state from redirect and navigating to callback with mock code, (4) select calendars + set bidirectional sync, (5) Sync Now + verify created events via SPARQL, (5b) verify RRULE on recurring event via SPARQL, (6) admin detail + uninstall. Use `ownerRequest` for OAuth simulation (POST with `maxRedirects: 0`). Include retry loop for `#connect-content` visibility per known app startup timing issue.
  - Verify: E2E test file parses without TypeScript errors; structurally matches the Google Calendar test pattern
  - Done when: `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` exists with all 7 phases, `outlookCalendarSync` selectors added to `selectors.ts`

- [x] **T03: Write Chapter 38 user guide and update README, glossary, appendix, navigation** `est:45m`
  - Why: Closes the documentation deliverable — Chapter 38 documents Outlook Calendar Sync with Azure AD setup instructions, field mapping tables, and troubleshooting. Docs infrastructure updates (TOC, glossary, appendix, navigation chain) ensure discoverability.
  - Files: `docs/guide/38-outlook-calendar-sync.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/appendix-a-environment-variables.md`, `docs/guide/37-todoist-sync.md`
  - Do: Write Chapter 38 following Chapter 36's structure. Sections: Prerequisites (basic-pkm v2.1+, Azure AD app registration), Installing, Setting Up OAuth (Azure Portal steps with redirect URI), Connecting (credentials form + OAuth flow), Selecting Calendars, Sync Configuration (direction, interval), Running a Sync, Field Mapping tables (core properties, status/visibility, showAs 5-value enum, sensitivity→visibility, location/links, recurrence 6×3 table, attendees, categories→tags, sync metadata), RSVP Push-Back, Recurrence Handling, All-Day Events, Conference URLs, Attendee Resolution, Admin Monitoring, Troubleshooting, See Also. Add `38. [Outlook Calendar Sync](38-outlook-calendar-sync.md)` to README TOC. Add "Outlook Calendar Sync" to glossary. Add 3 env var rows to appendix A. Update Ch 37 navigation: `Next: Chapter 38`. Set Ch 38 navigation: `Previous: Chapter 37 | Next: Appendix A`. Also run htmx prefix audit: `grep -rn "hx-" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/"` must return 0.
  - Verify: `test -f docs/guide/38-outlook-calendar-sync.md && grep "38.*Outlook" docs/guide/README.md && grep "Outlook Calendar Sync" docs/guide/appendix-d-glossary.md && grep -c "OUTLOOK_" docs/guide/appendix-a-environment-variables.md` — all pass
  - Done when: Chapter 38 exists with field mapping tables and Azure AD setup, all 5 docs files updated, htmx prefix audit clean

## Files Likely Touched

- `e2e/mock-outlook-api/server.py` (new)
- `docker-compose.test.yml` (modify — add mock-outlook service + env vars)
- `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` (new)
- `e2e/helpers/selectors.ts` (modify — add outlookCalendarSync block)
- `docs/guide/38-outlook-calendar-sync.md` (new)
- `docs/guide/README.md` (modify — TOC entry)
- `docs/guide/appendix-d-glossary.md` (modify — glossary entry)
- `docs/guide/appendix-a-environment-variables.md` (modify — 3 env var rows)
- `docs/guide/37-todoist-sync.md` (modify — navigation chain)
