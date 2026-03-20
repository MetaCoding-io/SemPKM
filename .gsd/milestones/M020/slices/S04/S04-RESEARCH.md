# S04: E2E Tests + User Guide — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

S04 is a direct structural clone of M018/S05 (Google Calendar E2E + User Guide). The three deliverables — mock Microsoft Graph API server, Playwright E2E test, and Chapter 38 user guide — all follow established patterns with no new technology or architectural risk. The mock server is a single Python file using `http.server`, the E2E test mirrors `google-calendar-sync.spec.ts` with Outlook-specific selectors and OAuth simulation, and the user guide follows Chapter 36's structure with Outlook field mapping tables and Azure AD setup instructions.

The Outlook app's auth/client modules already have env var overrides (`OUTLOOK_API_URL`, `OUTLOOK_TOKEN_URL`, `OUTLOOK_AUTH_URL`) matching the Google Calendar pattern, so Docker Compose integration is straightforward. 193 unit tests already pass for the Outlook services layer — S04 adds integration-level verification on top.

## Recommendation

Three sequential tasks: (1) mock server + Docker Compose wiring, (2) Playwright E2E test, (3) user guide + README/glossary/appendix/navigation updates. Build the mock server first because the E2E test depends on it. The user guide is independent of both and can be written last.

## Implementation Landscape

### Key Files

**Mock server (new):**
- `e2e/mock-outlook-api/server.py` — Clone from `e2e/mock-google-calendar-api/server.py` (488 lines). Adapt endpoints to Microsoft Graph API: `POST /common/oauth2/v2.0/token` (token exchange), `GET /v1.0/me/calendars` (calendar list), `GET /v1.0/me/calendars/{id}/events/delta` (delta events with `@odata.deltaLink`), `PATCH /v1.0/me/events/{id}` (RSVP push-back), `GET /v1.0/me` (profile for email). Canned data needs: 1 timed event with attendees+categories+conferenceUrl, 1 all-day event, 1 recurring event with structured recurrence pattern. Must include selftest with 11+ checks.

**Docker Compose (modify):**
- `docker-compose.test.yml` — Add `mock-outlook` service (same `python:3.12-slim` pattern as mock-google-calendar). Add env vars to `api` service: `OUTLOOK_API_URL: http://mock-outlook:8080/v1.0`, `OUTLOOK_TOKEN_URL: http://mock-outlook:8080/common/oauth2/v2.0/token`, `OUTLOOK_AUTH_URL: http://mock-outlook:8080/common/oauth2/v2.0/authorize`. Add `mock-outlook` to `api.depends_on`.

**E2E test (new):**
- `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` — Clone from `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts`. Phases: (0) cleanup prior install, (1) ensure basic-pkm model, (2) install outlook-calendar app → wait for Running, (3) enter Azure AD credentials + simulate OAuth, (4) select calendars + set bidirectional, (5) Sync Now + verify created events via SPARQL, (5b) verify RRULE on recurring event, (6) admin detail + uninstall.
- `e2e/helpers/selectors.ts` — Add `outlookCalendarSync` selector block mirroring `googleCalendarSync` but with Outlook-specific IDs: `#outlook-client-id`, `#outlook-client-secret`, `.btn-microsoft`, etc.

**User guide (new):**
- `docs/guide/38-outlook-calendar-sync.md` — Chapter 38, following Chapter 36's structure. Sections: Prerequisites, Installing, Setting Up OAuth (Azure AD app registration), Connecting, Selecting Calendars, Sync Configuration, Running a Sync, Field Mapping (core, status/visibility, showAs, sensitivity, location/links, recurrence, attendees, categories/tags, sync metadata), RSVP Push-Back, Recurrence Handling (6 pattern types × 3 range types table), All-Day Events, Conference URLs, Attendee Resolution, Admin Monitoring, Troubleshooting, See Also.

**README/glossary/appendix updates (modify):**
- `docs/guide/README.md` — Add line 67: `38. [Outlook Calendar Sync](38-outlook-calendar-sync.md)`
- `docs/guide/appendix-d-glossary.md` — Add "Outlook Calendar Sync" entry
- `docs/guide/appendix-a-environment-variables.md` — Add `OUTLOOK_API_URL`, `OUTLOOK_TOKEN_URL`, `OUTLOOK_AUTH_URL` rows
- `docs/guide/37-todoist-sync.md` — Update navigation: **Next:** → Chapter 38 (was Appendix A)
- `docs/guide/38-outlook-calendar-sync.md` — Navigation: **Previous:** Chapter 37, **Next:** Appendix A

### Build Order

1. **Mock server + Docker Compose** — T01. The mock server is the foundation — without it the E2E test can't run. Write `e2e/mock-outlook-api/server.py` with canned Graph API responses, add `mock-outlook` service to `docker-compose.test.yml`, verify via `python server.py --selftest`. This is the only dependency — unblocks T02.

2. **Playwright E2E test** — T02. Depends on T01 (mock server running in Docker). Clone and adapt the Google Calendar E2E test for Outlook selectors. Add `outlookCalendarSync` to `e2e/helpers/selectors.ts`. The test exercises the full install→OAuth→sync→verify→cleanup lifecycle against the mock. Verification: `npx playwright test outlook-calendar-sync.spec.ts` passes (structurally complete — some phases may hit the known app startup timing issue).

3. **User guide + docs updates** — T03. Independent of T01/T02. Write Chapter 38, update README TOC, glossary, appendix A env vars, and navigation chain (Ch 37 ↔ Ch 38 ↔ Appendix A).

### Verification Approach

- Mock server: `cd e2e/mock-outlook-api && python3 server.py --selftest` — all checks pass, exit 0
- E2E test: `npx playwright test outlook-calendar-sync.spec.ts` against Docker test stack
- User guide: verify file exists, check heading structure, confirm navigation chain is consistent
- README TOC: `grep "38.*Outlook" docs/guide/README.md` — returns the entry
- Glossary: `grep "Outlook Calendar Sync" docs/guide/appendix-d-glossary.md`
- Appendix A: `grep "OUTLOOK_" docs/guide/appendix-a-environment-variables.md`
- htmx prefix: `grep -rn "hx-" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/"` — must return 0 results

## Constraints

- The mock server must use Python `http.server` (same as all other mocks) — no Express.js despite the roadmap mentioning it. All existing mocks are Python.
- Outlook app env var names are `OUTLOOK_API_URL`, `OUTLOOK_TOKEN_URL`, `OUTLOOK_AUTH_URL` (checked in services/auth.py and services/outlook_client.py).
- The `OUTLOOK_AUTH_URL` env var exists but the authorize URL is only used in `build_authorize_url()` — the E2E test simulates OAuth by extracting the state param from the redirect and navigating directly to the callback, same as the Google Calendar E2E pattern.
- Canned event data must include: `categories` (string array) for tags mapping, `showAs` for the 5-value enum, `sensitivity` for visibility mapping, a structured `recurrence` object (pattern + range) for the RRULE converter, `onlineMeeting.joinUrl` for conference URL, and `attendees` array for person matching.
- The `@odata.deltaLink` response must use a full URL (e.g., `http://mock-outlook:8080/v1.0/me/calendars/{id}/events/delta?$deltatoken=mock-delta-1`) because the client follows the link directly (no URL construction).

## Common Pitfalls

- **Mock delta query URL must be a full URL** — Outlook's delta API returns `@odata.deltaLink` as a full URL that the client follows verbatim. The mock must return `http://localhost:8080/v1.0/...?$deltatoken=...` in selftest mode but the Docker hostname doesn't matter because the E2E test hits the API container which uses the `OUTLOOK_API_URL` env var.
- **OAuth simulation state extraction** — The E2E test POSTs to `/app/outlook-calendar/_fragments/connect/microsoft` with `maxRedirects: 0`, extracts the `state` param from the redirect Location header, then navigates the browser to the callback URL. This pattern works identically to the Google Calendar E2E.
- **App startup timing** — Per KNOWLEDGE.md, the app subprocess needs time to start and open its UDS socket. The E2E test must include `waitForTimeout(5000)` after confirming "Running" status, same as the Google Calendar test. The retry loop for `#connect-content` visibility handles cases where the first load fails.
- **Selectors must match actual template IDs** — The connect form uses `#outlook-client-id` and `#outlook-client-secret` (verified in `connect.html`), not the `#gcal-*` IDs from Google Calendar.

## Sources

- Mock server reference: `e2e/mock-google-calendar-api/server.py` (488 lines, 11 selftest checks)
- E2E test reference: `e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` (full lifecycle test)
- User guide reference: `docs/guide/36-google-calendar-sync.md` (377 lines, 12 sections)
- Outlook app templates: `apps/outlook-calendar/frontend/templates/connect.html`, `connect_status.html`
- Field mapper constants: `apps/outlook-calendar/services/field_mapper.py` (SHOW_AS_MAP, SENSITIVITY_MAP, RESPONSE_STATUS_MAP, recurrence converter)
- Docker Compose: `docker-compose.test.yml` (mock service pattern)
- Selector reference: `e2e/helpers/selectors.ts` (googleCalendarSync block at line 217)
