---
id: S03
parent: M046
milestone: M046
provides:
  - 5 mock API Docker services (todoist, asana, caldav, google-calendar, outlook) in test compose
  - 7 API URL env vars pointing to mock services
  - 6 E2E selector groups for sync app tests
  - 4 apps selectors (installDetails, installPathInput, sidebarAppsSection, appsTree)
  - Fixed scheduler datetime crash for app subprocess lifecycle
  - APP_BASE_URL configured for test container
requires:
  []
affects:
  - S06
key_files:
  - backend/app/apps/scheduler.py
  - docker-compose.test.yml
  - e2e/helpers/selectors.ts
  - backend/app/templates/admin/apps/list.html
key_decisions:
  - (none)
patterns_established:
  - Mock API Docker service pattern: python:3.12-slim, volume mount from e2e/mock-*-api/:ro, python server.py entrypoint, health check via urllib, sempkm-test network, depends_on with service_healthy
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M046/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M046/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M046/slices/S03/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T02:18:44.538Z
blocker_discovered: false
---

# S03: App Platform — Subprocess Lifecycle in Test Container

**Fixed backend bugs, added 5 mock API Docker services, added 6 E2E selector groups + 4 apps selectors, and fixed admin install form template — unblocking all sync app E2E tests.**

## What Happened

This slice addressed the infrastructure preventing sync app E2E tests from passing. Three tasks covered four distinct problems:

**T01 — Backend bug fixes.** Two bugs prevented app subprocesses from starting in the test container: (1) `scheduler.py` crashed with `TypeError: can't subtract offset-naive and offset-aware datetimes` because SQLite returns naive datetimes while the scheduler uses `datetime.now(timezone.utc)`. Applied the established project pattern (Knowledge entry about SQLite naive datetimes) — normalize `started_at` with `replace(tzinfo=timezone.utc)` before subtraction. (2) `docker-compose.test.yml` lacked `APP_BASE_URL`, so the default `http://localhost:4000` was used when the test API listens on port 8000. Added `APP_BASE_URL: http://localhost:8000`.

**T02 — Mock API services.** Added 5 Docker service definitions (mock-todoist, mock-asana, mock-caldav, mock-google-calendar, mock-outlook) to `docker-compose.test.yml`, following the exact pattern of existing mock-linear/mock-github/mock-jira/mock-monday services: `python:3.12-slim` image, read-only volume mount from `e2e/mock-*-api/`, health check via urllib, `sempkm-test` network. Added 7 environment variables to the api service pointing to these mock services. Added `depends_on` with `service_healthy` condition for all 5 new services.

**T03 — E2E selectors and admin template fix.** Added 6 selector groups to `e2e/helpers/selectors.ts` (todoistSync, asanaSync, caldavCalendarSync, googleCalendarSync, outlookCalendarSync, rss) with selectors derived from each app's actual HTML templates. Added 4 missing `apps` selectors (installDetails, installPathInput, sidebarAppsSection, appsTree). Fixed the admin apps list template by wrapping the install form in a `<details class="install-details">` element with a `<summary>`, matching the E2E test expectation.

All three tasks completed without deviations or blockers.

## Verification

All three task verification checks pass:
- T01: `python3 -c "import ast; ast.parse(...)"` passes for scheduler.py; `grep -q APP_BASE_URL docker-compose.test.yml` confirms env var present.
- T02: `docker compose -f docker-compose.test.yml config` validates YAML; grep confirms all 7 env vars (TODOIST_API_URL, ASANA_API_URL, ASANA_TOKEN_URL, GCAL_API_URL, GOOGLE_TOKEN_URL, OUTLOOK_API_URL, OUTLOOK_TOKEN_URL) and all 5 mock service definitions.
- T03: `npx tsc --noEmit` reports zero errors for all 6 new selector groups; grep confirms `details.install-details` wrapper in admin template.

## Requirements Advanced

- APP-02 — Fixed scheduler datetime crash that prevented app subprocess lifecycle from working in test container
- APP-06 — Fixed naive/aware datetime bug in AppScheduler that crashed on interval check
- APP-14 — Added APP_BASE_URL and 5 mock service dependencies to docker-compose.test.yml

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

Mock API servers for todoist, asana, caldav, google-calendar, and outlook must exist at e2e/mock-*-api/ with server.py entrypoints for the Docker services to start. If any mock server directory is missing, the corresponding Docker service will fail to start. CalDAV has no API URL env var — the server URL is user-supplied via the connect form, so tests must configure it directly.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/apps/scheduler.py` — Added timezone normalization for naive SQLite datetimes before subtraction
- `docker-compose.test.yml` — Added APP_BASE_URL, 5 mock API services, 7 env vars, 5 depends_on entries
- `e2e/helpers/selectors.ts` — Added 6 selector groups (todoistSync, asanaSync, caldavCalendarSync, googleCalendarSync, outlookCalendarSync, rss) and 4 apps selectors
- `backend/app/templates/admin/apps/list.html` — Wrapped install form in details.install-details element with summary
