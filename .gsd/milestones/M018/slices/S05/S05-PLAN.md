# S05: E2E tests + user guide

**Goal:** Mock Google Calendar API server passes selftest. Playwright E2E test proves install → OAuth → sync → verify → RSVP push lifecycle. Chapter 36 user guide documents full workflow. All GCAL/EVENT requirements validated.
**Demo:** `python e2e/mock-google-calendar-api/server.py --selftest` passes. `npx playwright test e2e/tests/36-google-calendar-sync/` passes against Docker stack. `docs/guide/36-google-calendar-sync.md` exists with field mapping tables, OAuth setup, RSVP, recurrence docs.

## Must-Haves

- Mock Google Calendar API server with canned responses for: health check, OAuth token exchange, token refresh, calendar list, events list (with syncToken), event PATCH (RSVP echo-back)
- Mock selftest mode (`--selftest`) verifying all endpoints
- Docker service `mock-google-calendar` in `docker-compose.test.yml` with `GCAL_API_URL` and `GOOGLE_TOKEN_URL` env vars on the API container
- Playwright E2E test covering: cleanup → install basic-pkm → install google-calendar → enter credentials → simulate OAuth callback → select calendars → Sync Now → verify Events via SPARQL → verify sync stats UI → admin detail → cleanup
- Chapter 36 user guide with prerequisites, OAuth setup, calendar selection, sync config, field mapping tables, RSVP push-back, recurrence handling, troubleshooting
- README TOC, glossary, appendix-a env vars, navigation chain (Ch 35 → Ch 36 → Appendix A) updated
- GCAL-05, GCAL-06, GCAL-09 requirements moved to validated in REQUIREMENTS.md
- `googleCalendarSync` selector block added to `e2e/helpers/selectors.ts`

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker stack with mock API)
- Human/UAT required: no

## Verification

- `python e2e/mock-google-calendar-api/server.py --selftest` — must pass ≥8 endpoint checks, exit 0
- `npx playwright test e2e/tests/36-google-calendar-sync/ --project chromium` — must pass against Docker stack with mock-google-calendar service
- `docs/guide/36-google-calendar-sync.md` exists at correct path with ≥200 lines
- `rg 'Chapter 36|36-google-calendar' docs/guide/README.md` — returns TOC entry
- `rg 'Google Calendar Sync' docs/guide/appendix-d-glossary.md` — returns glossary entry
- `rg 'GCAL_API_URL' docs/guide/appendix-a-environment-variables.md` — returns env var entry
- Navigation chain: Ch 35 "Next" links to Ch 36, Ch 36 "Next" links to Appendix A
- GCAL-05, GCAL-06, GCAL-09 in REQUIREMENTS.md have `Status: validated`

## Observability / Diagnostics

- **Mock server logs:** `[mock-gcal] METHOD /path → STATUS` on stderr (same pattern as mock-github). Filter in Docker: `docker compose -f docker-compose.test.yml logs mock-google-calendar`.
- **Health check surface:** `GET /health` returns `{"status": "ok"}` — used by Docker healthcheck and selftest.
- **Selftest mode:** `python server.py --selftest` runs all endpoint checks locally, prints per-check pass/fail, exits 0/1. No Docker required.
- **API env vars:** `GCAL_API_URL` and `GOOGLE_TOKEN_URL` on the `api` service. Inspect with `docker compose -f docker-compose.test.yml exec api env | grep -E 'GCAL|GOOGLE_TOKEN'`.
- **Failure visibility:** Mock returns 410 Gone for invalid syncToken (triggers full resync path in client). Token endpoint validates grant_type — returns 400 on invalid type.
- **Redaction:** No real secrets — all tokens are `mock-*` constants. No redaction constraints.

## Integration Closure

- Upstream surfaces consumed: Complete google-calendar app (S02+S03+S04), bpkm:Event type (S01), `connect.html` / `connect_status.html` templates, auth.py OAuth flow, sync_engine.py pull_sync/push_sync
- New wiring introduced in this slice: `mock-google-calendar` Docker service, `GCAL_API_URL` + `GOOGLE_TOKEN_URL` env vars in docker-compose.test.yml
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Build mock Google Calendar API server + Docker wiring** `est:45m`
  - Why: E2E test needs a mock Google Calendar API that the containerized app can call. Must handle token exchange, calendar list, events list with syncToken, and RSVP PATCH echo-back. Docker service definition wires it into the test stack.
  - Files: `e2e/mock-google-calendar-api/server.py`, `docker-compose.test.yml`
  - Do: Build Python HTTP server following `e2e/mock-github-api/server.py` pattern. Implement endpoints: `GET /health`, `POST /oauth/token` (code exchange + refresh), `GET /calendar/v3/users/me/calendarList`, `GET /calendar/v3/calendars/{id}/events` (syncToken pagination, canned events including timed, all-day, recurring master), `PATCH /calendar/v3/calendars/{id}/events/{id}` (echo-back merged data). Add `--selftest` flag. Add `mock-google-calendar` service to docker-compose.test.yml, add `GCAL_API_URL` and `GOOGLE_TOKEN_URL` env vars to api service, add to depends_on.
  - Verify: `python e2e/mock-google-calendar-api/server.py --selftest` passes ≥8 checks
  - Done when: selftest passes, docker-compose.test.yml has the new service and env vars

- [x] **T02: Playwright E2E test for Google Calendar sync lifecycle** `est:1h`
  - Why: Proves the full install → OAuth → sync → verify → RSVP push lifecycle against real Docker stack with mock API. Validates GCAL-09 requirement. Also adds googleCalendarSync selector block to selectors.ts.
  - Files: `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Follow `e2e/tests/32-github-sync/github-sync.spec.ts` pattern. Phases: (0) cleanup existing app, (1) install basic-pkm, (2) install google-calendar + wait 5s for subprocess, (3) navigate to app page + fill credentials form, (4) simulate OAuth by POSTing to `/_fragments/connect/google` to get redirect URL + extracting state param + navigating to callback URL with `?code=mock-auth-code&state={state}`, (5) select calendars + save, (6) configure sync direction bidirectional, (7) click Sync Now, (8) verify Events via SPARQL query, (9) verify sync stats in UI, (10) admin app detail page, (11) cleanup. Key constraint: `GOOGLE_AUTHORIZE_URL` is hardcoded to Google — the OAuth simulation must use the callback URL directly, relying on the mock `GOOGLE_TOKEN_URL` for code exchange.
  - Verify: `npx playwright test e2e/tests/36-google-calendar-sync/ --project chromium` passes
  - Done when: E2E test passes against Docker test stack with mock-google-calendar service

- [x] **T03: Chapter 36 user guide + docs updates + requirement validation** `est:45m`
  - Why: Completes the user-facing documentation for Google Calendar sync and validates remaining GCAL requirements. Updates navigation chain, TOC, glossary, and env var appendix.
  - Files: `docs/guide/36-google-calendar-sync.md`, `docs/guide/README.md`, `docs/guide/35-github-sync.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/appendix-a-environment-variables.md`, `.gsd/REQUIREMENTS.md`
  - Do: Write chapter 36 following chapter 35 structure: prerequisites, installation, OAuth setup (Google Cloud Console instructions), calendar selection, sync configuration, field mapping tables (Google → bpkm:Event for all ~22 properties), RSVP push-back workflow, recurrence handling (master + exceptions), admin monitoring, troubleshooting. Update README.md TOC with Ch 36, update Ch 35 "Next" link to Ch 36, add "Google Calendar Sync" glossary entry, add `GCAL_API_URL` and `GOOGLE_TOKEN_URL` to appendix-a. Move GCAL-05, GCAL-06, GCAL-09 to validated in REQUIREMENTS.md with proof references.
  - Verify: File exists at correct path with ≥200 lines. README TOC, glossary, appendix-a, navigation chain all updated. Requirements moved to validated.
  - Done when: All doc files updated, navigation chain intact (Ch 35 → Ch 36 → Appendix A), three requirements validated

## Files Likely Touched

- `e2e/mock-google-calendar-api/server.py` — new
- `docker-compose.test.yml` — modified
- `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` — new
- `e2e/helpers/selectors.ts` — modified
- `docs/guide/36-google-calendar-sync.md` — new
- `docs/guide/README.md` — modified
- `docs/guide/35-github-sync.md` — modified
- `docs/guide/appendix-d-glossary.md` — modified
- `docs/guide/appendix-a-environment-variables.md` — modified
- `.gsd/REQUIREMENTS.md` — modified
