---
estimated_steps: 7
estimated_files: 2
---

# T01: Build mock Microsoft Graph API server and wire Docker Compose

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M020

## Description

Create a mock Microsoft Graph API server that returns canned REST responses for all endpoints the Outlook Calendar Sync app consumes. This server runs inside Docker alongside the test stack, replacing the real Microsoft Graph API during E2E testing. Clone the structure from `e2e/mock-google-calendar-api/server.py` (488 lines, Python `http.server`) and adapt all endpoints to Microsoft Graph API paths. Wire the `mock-outlook` service into `docker-compose.test.yml` with env var overrides so the API container talks to the mock.

## Steps

1. **Create `e2e/mock-outlook-api/server.py`** — clone the structure from `e2e/mock-google-calendar-api/server.py`. Use Python `http.server.HTTPServer` + `BaseHTTPRequestHandler`. Set `PORT = 8080`.

2. **Implement canned response data.** Define constants for:
   - `TOKEN_RESPONSE` — `access_token`, `refresh_token`, `expires_in`, `token_type`
   - `USER_PROFILE` — `displayName`, `mail` (e.g. `test@example.com`), `userPrincipalName`
   - `CALENDAR_LIST_RESPONSE` — `value` array with 2 calendars (primary + secondary), each with `id`, `name`, `isDefaultCalendar`, `color`, `canEdit`
   - `EVENTS_RESPONSE` — `value` array with 3 events + `@odata.deltaLink`:
     - **Timed event**: `id: "event-timed-001"`, `subject: "Team Standup"`, `body: {contentType: "html", content: "<p>Daily standup</p>"}`, `start/end` with `dateTime` + `timeZone`, `attendees` array (2 entries with `emailAddress` + `status.response`), `categories: ["Work", "Important"]`, `showAs: "busy"`, `sensitivity: "normal"`, `location: {displayName: "Conference Room A"}`, `onlineMeeting: {joinUrl: "https://teams.microsoft.com/meet/123"}`, `isAllDay: false`, `organizer` with email
     - **All-day event**: `id: "event-allday-002"`, `isAllDay: true`, `start/end` with date-only strings, `showAs: "free"`, `sensitivity: "private"`
     - **Recurring event**: `id: "event-recurring-003"`, `recurrence` object with `pattern: {type: "weekly", interval: 1, daysOfWeek: ["monday", "wednesday", "friday"]}` and `range: {type: "endDate", startDate: "2026-01-01", endDate: "2026-06-30"}`
   - `@odata.deltaLink` must be a full URL: `http://localhost:8080/v1.0/me/calendars/{id}/events/delta?$deltatoken=mock-delta-1`

3. **Implement request handler** (`MockOutlookHandler`). Route by path:
   - `GET /health` → 200 `{"status": "ok"}`
   - `POST /common/oauth2/v2.0/token` → 200 `TOKEN_RESPONSE`
   - `GET /v1.0/me/calendars` → 200 `CALENDAR_LIST_RESPONSE`
   - `GET /v1.0/me/calendars/{id}/events/delta` → 200 `EVENTS_RESPONSE` (initial) or `{"value": [], "@odata.deltaLink": ...}` (delta token present)
   - `PATCH /v1.0/me/events/{id}` → 200 echo-back with merged attendee status from request body; return 404 for unknown event IDs (error path)
   - `GET /v1.0/me` → 200 `USER_PROFILE`
   - Anything else → 404

4. **Implement selftest function** with 11+ checks:
   - Health check (GET /health → 200)
   - Token exchange (POST /token → 200 with access_token)
   - Calendar list (GET /calendars → 200 with 2 items)
   - Events delta initial (GET /events/delta → 200 with 3 events)
   - Events delta incremental (GET with deltatoken → 200 with empty value)
   - Event fields: timed event has attendees, categories, showAs, onlineMeeting
   - All-day event has isAllDay=true
   - Recurring event has recurrence.pattern.type = "weekly"
   - RSVP PATCH (PATCH /events/{id} → 200)
   - RSVP PATCH invalid ID → 404 (error path check)
   - User profile (GET /me → 200 with mail field)
   - `@odata.deltaLink` in initial response is a full URL containing `$deltatoken`

5. **Add `__main__` block** — `--selftest` flag runs selftest, otherwise starts server on port 8080.

6. **Wire into `docker-compose.test.yml`:**
   - Add `mock-outlook` service entry (copy pattern from `mock-google-calendar`): `image: python:3.12-slim`, volume mount `./e2e/mock-outlook-api:/app:ro`, `working_dir: /app`, `command: ["python", "server.py"]`, healthcheck on `/health`, network `sempkm-test`
   - Add env vars to `api` service:
     ```
     OUTLOOK_API_URL: http://mock-outlook:8080/v1.0
     OUTLOOK_TOKEN_URL: http://mock-outlook:8080/common/oauth2/v2.0/token
     OUTLOOK_AUTH_URL: http://mock-outlook:8080/common/oauth2/v2.0/authorize
     ```
   - Add `mock-outlook` to `api.depends_on` (with `condition: service_healthy`)

7. **Run selftest** to verify: `cd e2e/mock-outlook-api && python3 server.py --selftest`

## Must-Haves

- [ ] 6 endpoints covering the full Graph API surface used by the Outlook app
- [ ] Canned events include: timed event with attendees+categories+showAs+sensitivity+conferenceUrl, all-day event, recurring event with structured recurrence pattern
- [ ] `@odata.deltaLink` returns a full URL (not relative) so the client can follow it directly
- [ ] Selftest with 11+ checks including at least one error-path check (PATCH with unknown event ID → 404)
- [ ] Docker Compose `mock-outlook` service with healthcheck
- [ ] API container env vars: `OUTLOOK_API_URL`, `OUTLOOK_TOKEN_URL`, `OUTLOOK_AUTH_URL` pointing to mock-outlook
- [ ] Selftest passes: `python3 server.py --selftest` exits 0

## Verification

- `cd e2e/mock-outlook-api && python3 server.py --selftest` — all checks pass, exit 0
- `grep "mock-outlook" docker-compose.test.yml` — service entry exists
- `grep "OUTLOOK_API_URL" docker-compose.test.yml` — env var wired to api service

## Observability Impact

- Signals added/changed: selftest prints `[selftest] N/N passed, 0 failed` with per-check PASS/FAIL
- How a future agent inspects this: `python3 server.py --selftest` for quick health; Docker healthcheck on `/health`
- Failure state exposed: selftest reports exact endpoint, expected status vs actual, and response body snippet on FAIL

## Inputs

- `e2e/mock-google-calendar-api/server.py` — reference implementation (488 lines, 11 selftest checks)
- `docker-compose.test.yml` — existing test stack configuration with `mock-google-calendar` service pattern
- `apps/outlook-calendar/services/auth.py` — env var names: `OUTLOOK_AUTH_URL` (default `https://login.microsoftonline.com/common/oauth2/v2.0/authorize`), `OUTLOOK_TOKEN_URL` (default `https://login.microsoftonline.com/common/oauth2/v2.0/token`)
- `apps/outlook-calendar/services/outlook_client.py` — env var `OUTLOOK_API_URL` (default `https://graph.microsoft.com/v1.0`); client calls: `GET /me/calendars`, `GET /me/calendars/{id}/events/delta`, `PATCH /me/events/{id}`
- `apps/outlook-calendar/services/field_mapper.py` — field names consumed from events: `showAs`, `sensitivity`, `categories`, `recurrence` (pattern+range), `onlineMeeting.joinUrl`, `attendees`, `body.contentType`, `body.content`, `isAllDay`, `organizer`

## Expected Output

- `e2e/mock-outlook-api/server.py` — new file, ~500 lines, standalone Python mock server with 6 endpoints + selftest
- `docker-compose.test.yml` — modified with `mock-outlook` service entry and 3 env vars on api service
