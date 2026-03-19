---
estimated_steps: 6
estimated_files: 2
---

# T01: Build mock Google Calendar API server + Docker wiring

**Slice:** S05 — E2E tests + user guide
**Milestone:** M018

## Description

Build a Python HTTP mock server that simulates the Google Calendar API and Google OAuth token endpoint, following the same `http.server` pattern used by `e2e/mock-github-api/server.py`. The mock handles the endpoints that the google-calendar app's `auth.py` and `gcal_client.py` call: token exchange, token refresh, calendar list, events list (with syncToken pagination), and event PATCH (for RSVP). Wire it into `docker-compose.test.yml` as a new service.

The canned event data must include:
- One timed event with attendees + conference URL (Meet link)
- One all-day event
- One recurring master event with RRULE

Return `nextSyncToken` on events list responses. PATCH echoes back merged data for RSVP verification.

## Steps

1. **Create `e2e/mock-google-calendar-api/server.py`** following `e2e/mock-github-api/server.py` as a structural reference (~426 lines). Use `http.server.HTTPServer` + `BaseHTTPRequestHandler`.

2. **Implement canned response data constants** at the top of the file:
   - `TOKEN_RESPONSE` — `{"access_token": "mock-access-token", "refresh_token": "mock-refresh-token", "expires_in": 3600, "token_type": "Bearer"}`
   - `CALENDAR_LIST_RESPONSE` — `{"kind": "calendar#calendarList", "items": [...]}` with 2 calendars: one primary (`test@example.com`), one secondary (`team-calendar-id`)
   - `EVENTS_RESPONSE` — `{"kind": "calendar#events", "items": [...], "nextSyncToken": "mock-sync-token-1"}` with 3 events:
     - Timed event: `id: "event-timed-001"`, title "Team Standup", start/end with dateTime + timeZone, 2 attendees (one self), conferenceData with Meet URI, location "Conference Room A"
     - All-day event: `id: "event-allday-001"`, title "Company Holiday", start/end with `date` (not `dateTime`), no attendees
     - Recurring master: `id: "event-recurring-001"`, title "Weekly Review", start/end with dateTime, `recurrence: ["RRULE:FREQ=WEEKLY;BYDAY=FR"]`
   - `INCREMENTAL_EVENTS_RESPONSE` — `{"kind": "calendar#events", "items": [], "nextSyncToken": "mock-sync-token-2"}` — empty events for second sync (incremental, nothing changed)

3. **Implement request handler** with routing:
   - `GET /health` → 200 `{"status": "ok"}`
   - `POST /oauth/token` → parse form body, check `grant_type` is `authorization_code` or `refresh_token`, return `TOKEN_RESPONSE`
   - `GET /calendar/v3/users/me/calendarList` → return `CALENDAR_LIST_RESPONSE`
   - `GET /calendar/v3/calendars/{calendarId}/events` → check query param `syncToken`: if absent return `EVENTS_RESPONSE`, if `"mock-sync-token-1"` return `INCREMENTAL_EVENTS_RESPONSE`, if unrecognized return 410 Gone (triggers full resync)
   - `PATCH /calendar/v3/calendars/{calendarId}/events/{eventId}` → parse JSON body, merge with matching canned event, return merged result (for RSVP echo-back)
   - Default → 404

4. **Implement `--selftest` mode**: when `sys.argv` contains `--selftest`, start the server in a background thread, run HTTP requests against each endpoint, assert expected status codes and response shapes, print results, exit 0 on all pass / exit 1 on any failure. Target ≥8 checks:
   - Health endpoint returns 200
   - Token exchange (authorization_code) returns 200 with access_token
   - Token refresh (refresh_token) returns 200 with access_token
   - Calendar list returns 200 with items array
   - Events list (no syncToken) returns 200 with 3 items and nextSyncToken
   - Events list (with syncToken) returns 200 with 0 items
   - Events list (invalid syncToken) returns 410
   - Event PATCH returns 200 with merged data

5. **Add `mock-google-calendar` service to `docker-compose.test.yml`**: Same pattern as `mock-github`. Python 3.12-slim image, volume mount `./e2e/mock-google-calendar-api:/app:ro`, health check against `/health`.

6. **Add env vars to `api` service in `docker-compose.test.yml`**: `GCAL_API_URL: http://mock-google-calendar:8080/calendar/v3` and `GOOGLE_TOKEN_URL: http://mock-google-calendar:8080/oauth/token`. Add `mock-google-calendar` to `depends_on` with `condition: service_healthy`.

## Must-Haves

- [ ] Mock server handles all 6 endpoint patterns (health, token exchange, token refresh, calendar list, events list, event PATCH)
- [ ] Canned events include timed (with attendees + conferenceData), all-day, and recurring master (with RRULE)
- [ ] syncToken pagination: first request returns events + nextSyncToken, subsequent request with syncToken returns empty + new token, invalid syncToken returns 410
- [ ] `--selftest` passes ≥8 checks and exits 0
- [ ] `docker-compose.test.yml` has mock-google-calendar service, GCAL_API_URL, GOOGLE_TOKEN_URL env vars, and depends_on entry

## Verification

- `python e2e/mock-google-calendar-api/server.py --selftest` — all checks pass, exit 0
- `grep 'mock-google-calendar' docker-compose.test.yml` — service defined
- `grep 'GCAL_API_URL' docker-compose.test.yml` — env var present
- `grep 'GOOGLE_TOKEN_URL' docker-compose.test.yml` — env var present

## Inputs

- `e2e/mock-github-api/server.py` — reference mock server pattern (426 lines, HTTP handler, --selftest)
- `apps/google-calendar/services/auth.py` — `GOOGLE_TOKEN_URL` env var override (line 18), token exchange/refresh POST format
- `apps/google-calendar/services/gcal_client.py` — `GCAL_BASE_URL` env var override (line 17), API paths for calendarList, events, events.patch
- `docker-compose.test.yml` — existing test stack definition with mock-github and mock-linear services
- S05 Research — canned event structure must match Google Calendar API v3 response format (`kind`, `items`, `nextSyncToken`, `nextPageToken`)

## Observability Impact

- **New log stream:** Mock server emits `[mock-gcal] METHOD /path → STATUS` on stderr in Docker. Inspect via `docker compose -f docker-compose.test.yml logs mock-google-calendar`.
- **Selftest inspection:** `python e2e/mock-google-calendar-api/server.py --selftest` — runs ≥8 checks, prints per-check `✓`/`✗`, exits 0/1. No external dependencies.
- **Docker health probe:** `GET /health` on port 8080 inside the container. `docker compose -f docker-compose.test.yml ps` shows health status.
- **Failure state visible:** Invalid syncToken → 410 response (logged). Bad grant_type → 400 response (logged). 404 for unrecognized paths (logged).
- **Env var wiring:** `GCAL_API_URL` and `GOOGLE_TOKEN_URL` added to api service. Verify: `docker compose -f docker-compose.test.yml exec api env | grep -E 'GCAL|GOOGLE_TOKEN'`.

## Expected Output

- `e2e/mock-google-calendar-api/server.py` — new, ~350-450 lines, self-contained mock server
- `docker-compose.test.yml` — modified with new service + env vars
