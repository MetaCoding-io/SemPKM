---
id: T01
parent: S04
milestone: M020
provides:
  - Mock Microsoft Graph API server for E2E testing
  - Docker Compose mock-outlook service with env var wiring
key_files:
  - e2e/mock-outlook-api/server.py
  - docker-compose.test.yml
key_decisions:
  - "Used /v1.0/me/calendars/{calId}/events/{eventId} for PATCH path (matches real OutlookClient, not the plan's shorthand /me/events/{id})"
patterns_established:
  - "Mock Outlook server follows same structure as mock-google-calendar: http.server + canned data + selftest + Docker healthcheck"
observability_surfaces:
  - "python3 server.py --selftest prints per-check ✓/✗ with [selftest] N/N passed summary"
  - "Docker healthcheck on GET /health returns {status: ok}"
  - "Selftest reports endpoint, expected vs actual status, and response body snippet on FAIL"
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build mock Microsoft Graph API server and wire Docker Compose

**Mock Outlook Graph API server with 13 selftest checks and Docker Compose wiring for E2E testing**

## What Happened

Created `e2e/mock-outlook-api/server.py` (~480 lines) cloning the pattern from `mock-google-calendar-api/server.py`. Implemented 6 endpoints covering the full Microsoft Graph API surface used by the Outlook Calendar Sync app: health check, OAuth token exchange, user profile, calendar list, delta events query, and RSVP PATCH. Canned event data includes a timed event with attendees/categories/showAs/sensitivity/onlineMeeting, an all-day event, and a recurring event with structured weekly recurrence pattern. The `@odata.deltaLink` returns full URLs with `$deltatoken` parameter. Selftest runs 13 checks including error-path validation (PATCH unknown event → 404).

Wired `mock-outlook` service into `docker-compose.test.yml` with the same `python:3.12-slim` + volume mount + healthcheck pattern as other mock services. Added `OUTLOOK_API_URL`, `OUTLOOK_TOKEN_URL`, and `OUTLOOK_AUTH_URL` env vars to the `api` service pointing to the mock, plus `mock-outlook` as a healthy dependency.

## Verification

- `python3 server.py --selftest` — 13/13 passed, exit 0
- `grep "mock-outlook" docker-compose.test.yml` — 6 matches (service, depends_on, env vars, volume mount)
- `grep "OUTLOOK_API_URL" docker-compose.test.yml` — env var present pointing to `http://mock-outlook:8080/v1.0`
- Error-path check: PATCH unknown event ID returns 404 with `ErrorItemNotFound` error code

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e/mock-outlook-api && python3 server.py --selftest` | 0 | ✅ pass | 1s |
| 2 | `grep "mock-outlook" docker-compose.test.yml` | 0 | ✅ pass | <1s |
| 3 | `grep "OUTLOOK_API_URL" docker-compose.test.yml` | 0 | ✅ pass | <1s |

### Slice-Level Checks (partial — T01 of 3)

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Mock selftest passes | ✅ | 13/13 checks, exit 0 |
| 2 | mock-outlook in docker-compose.test.yml | ✅ | Service entry + healthcheck + depends_on |
| 3 | OUTLOOK env vars wired | ✅ | 3 env vars on api service |
| 4 | E2E Playwright test | ⬜ | T02 |
| 5 | Chapter 38 user guide | ⬜ | T03 |
| 6 | README/glossary/appendix updates | ⬜ | T03 |
| 7 | Navigation chain | ⬜ | T03 |
| 8 | htmx prefix audit | ⬜ | T03 |

## Diagnostics

- Quick health: `python3 e2e/mock-outlook-api/server.py --selftest` — exercises all endpoints
- Docker health: container healthcheck probes `GET /health` every 3s
- Runtime logs: mock server prints `[mock-outlook] METHOD /path → STATUS` to stderr
- Failure visibility: selftest reports per-check pass/FAIL with endpoint URL, expected vs actual status, and response body snippet (first 200 chars)

## Deviations

- PATCH endpoint uses `/v1.0/me/calendars/{calId}/events/{eventId}` path (matching the real `OutlookClient.patch_event()` implementation) rather than the plan's shorthand `/me/events/{id}`. No functional difference — the mock correctly routes both the selftest and the real client.
- Selftest has 13 checks (exceeding the 11+ requirement) — added separate checks for deltaLink URL format, timed event field richness, all-day flag, and recurrence pattern structure.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-outlook-api/server.py` — new: Mock Microsoft Graph API server (~480 lines) with 6 endpoints + 13-check selftest
- `docker-compose.test.yml` — modified: added `mock-outlook` service entry, 3 `OUTLOOK_*` env vars on api service, `mock-outlook` in api.depends_on
