---
id: T01
parent: S05
milestone: M018
provides:
  - Mock Google Calendar API server with health, OAuth token, calendar list, events list (syncToken), event PATCH endpoints
  - Docker service definition for mock-google-calendar in test stack
  - GCAL_API_URL and GOOGLE_TOKEN_URL env vars wired to api service
key_files:
  - e2e/mock-google-calendar-api/server.py
  - docker-compose.test.yml
key_decisions:
  - Selftest uses real HTTP via urllib (background thread server) instead of fake handler injection — more realistic, tests actual HTTP parsing
patterns_established:
  - Mock Google Calendar server follows same structure as mock-github-api (http.server, canned data, --selftest, Docker service)
observability_surfaces:
  - "[mock-gcal] METHOD /path → STATUS" stderr logs in Docker
  - "GET /health" → 200 health probe for Docker healthcheck
  - "--selftest" mode for local verification without Docker
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build mock Google Calendar API server + Docker wiring

**Mock Google Calendar API server (488 lines) handles 6 endpoint patterns with 11 selftest checks; Docker service wired with GCAL_API_URL and GOOGLE_TOKEN_URL env vars**

## What Happened

Built `e2e/mock-google-calendar-api/server.py` following the mock-github-api pattern. The server handles:

- `GET /health` — Docker healthcheck
- `POST /oauth/token` — code exchange and token refresh (validates grant_type, returns 400 on invalid)
- `GET /calendar/v3/users/me/calendarList` — returns 2 calendars (primary + secondary)
- `GET /calendar/v3/calendars/{id}/events` — syncToken pagination: no token → 3 canned events + nextSyncToken, valid token → empty incremental, invalid token → 410 Gone
- `PATCH /calendar/v3/calendars/{id}/events/{eventId}` — merges JSON body with canned event for RSVP echo-back

Canned events include: timed event (attendees, conferenceData with Meet URI, location), all-day event (date-only), recurring master (RRULE:FREQ=WEEKLY;BYDAY=FR). All match Google Calendar API v3 response format.

Added `mock-google-calendar` service to `docker-compose.test.yml` and wired `GCAL_API_URL` + `GOOGLE_TOKEN_URL` env vars on the api service with `depends_on` healthy condition.

## Verification

- `python3 e2e/mock-google-calendar-api/server.py --selftest` — 11/11 checks pass, exit 0
- `grep 'mock-google-calendar' docker-compose.test.yml` — service defined, env vars present, depends_on entry present
- `grep 'GCAL_API_URL' docker-compose.test.yml` — env var present
- `grep 'GOOGLE_TOKEN_URL' docker-compose.test.yml` — env var present

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 e2e/mock-google-calendar-api/server.py --selftest` | 0 | ✅ pass | 3.1s |
| 2 | `grep 'mock-google-calendar' docker-compose.test.yml` | 0 | ✅ pass | <1s |
| 3 | `grep 'GCAL_API_URL' docker-compose.test.yml` | 0 | ✅ pass | <1s |
| 4 | `grep 'GOOGLE_TOKEN_URL' docker-compose.test.yml` | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T01 is task 1 of 3)

| # | Slice Check | Status |
|---|------------|--------|
| 1 | Mock selftest ≥8 checks, exit 0 | ✅ 11/11 pass |
| 2 | Playwright E2E test | ⬜ T02 |
| 3 | Chapter 36 user guide ≥200 lines | ⬜ T03 |
| 4 | README TOC entry | ⬜ T03 |
| 5 | Glossary entry | ⬜ T03 |
| 6 | Appendix-a env var entry | ⬜ T03 |
| 7 | Navigation chain | ⬜ T03 |
| 8 | GCAL-05,06,09 validated | ⬜ T03 |

## Diagnostics

- **Docker logs:** `docker compose -f docker-compose.test.yml logs mock-google-calendar` — shows all request/response log lines
- **Health probe:** `curl http://localhost:8080/health` (inside container or via port mapping)
- **Selftest:** `python3 e2e/mock-google-calendar-api/server.py --selftest` — exercises all endpoints locally, no Docker needed
- **Env var check:** `docker compose -f docker-compose.test.yml exec api env | grep -E 'GCAL|GOOGLE_TOKEN'`

## Deviations

- Selftest uses real HTTP via background thread + `urllib.request` instead of the fake handler injection pattern from mock-github. More realistic — tests actual HTTP request/response cycle including URL encoding and form parsing.
- Added 3 extra selftest checks beyond the required 8 (bad grant_type → 400, PATCH unknown event → 404, unknown path → 404) for better coverage.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-google-calendar-api/server.py` — new, 488 lines, mock Google Calendar API + OAuth token server with --selftest mode
- `docker-compose.test.yml` — added mock-google-calendar service, GCAL_API_URL + GOOGLE_TOKEN_URL env vars, depends_on entry
