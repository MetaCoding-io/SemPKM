# S03: App Platform — Subprocess Lifecycle in Test Container — UAT

**Milestone:** M046
**Written:** 2026-03-29T02:18:44.538Z

# S03 UAT — App Platform Subprocess Lifecycle in Test Container

## Preconditions
- Docker test stack can be built from `docker-compose.test.yml`
- E2E test project compiles (`cd e2e && npx tsc --noEmit` exits 0)
- Mock API server directories exist at `e2e/mock-{todoist,asana,caldav,google-calendar,outlook}-api/`

---

## TC-01: Scheduler datetime crash fix
**Goal:** Verify the scheduler no longer crashes when checking app run intervals.

1. Open `backend/app/apps/scheduler.py` line ~257-260.
2. Confirm the pattern: `if started.tzinfo is None: started = started.replace(tzinfo=timezone.utc)` exists before the `now - started` subtraction.
3. Run `cd backend && python3 -c "import ast; ast.parse(open('app/apps/scheduler.py').read())"` — expect exit 0.

**Expected:** No TypeError when scheduler compares timezone-aware `now` against naive SQLite `started_at`.

---

## TC-02: APP_BASE_URL in test compose
**Goal:** App subprocesses use the correct base URL inside the test container.

1. Run `grep 'APP_BASE_URL' docker-compose.test.yml`.
2. Confirm value is `http://localhost:8000` (not 4000).

**Expected:** `APP_BASE_URL: http://localhost:8000` present in api service environment.

---

## TC-03: Mock API services defined
**Goal:** All 5 new mock services are correctly defined in docker-compose.test.yml.

1. Run `grep -E '^  mock-(todoist|asana|caldav|google-calendar|outlook):' docker-compose.test.yml | wc -l` — expect 5.
2. For each service, verify: image is `python:3.12-slim`, volume mount points to `./e2e/mock-*-api:/app:ro`, command is `python /app/server.py`, healthcheck exists, network is `sempkm-test`.
3. Run `docker compose -f docker-compose.test.yml config > /dev/null` — expect exit 0 (valid YAML).

**Expected:** 5 service definitions, all valid, following existing mock service pattern.

---

## TC-04: API URL environment variables
**Goal:** The api service has all mock API URL env vars.

1. Run `grep -E 'TODOIST_API_URL|ASANA_API_URL|ASANA_TOKEN_URL|GCAL_API_URL|GOOGLE_TOKEN_URL|OUTLOOK_API_URL|OUTLOOK_TOKEN_URL' docker-compose.test.yml | wc -l` — expect 7.
2. Verify each URL points to the corresponding mock service on port 8080.

**Expected:** 7 environment variables, each pointing to `http://mock-<service>:8080` (or sub-path for token URLs).

---

## TC-05: depends_on entries
**Goal:** The api service waits for all mock services to be healthy before starting.

1. In `docker-compose.test.yml`, find the api service's `depends_on` block.
2. Confirm entries for mock-todoist, mock-asana, mock-caldav, mock-google-calendar, mock-outlook — each with `condition: service_healthy`.

**Expected:** 5 new depends_on entries with health check conditions.

---

## TC-06: E2E selector groups compile
**Goal:** All 6 new selector groups and 4 apps selectors are type-safe.

1. Run `cd e2e && npx tsc --noEmit` — expect exit 0.
2. Verify `SEL.todoistSync`, `SEL.asanaSync`, `SEL.caldavCalendarSync`, `SEL.googleCalendarSync`, `SEL.outlookCalendarSync`, `SEL.rss` all exist in selectors.ts.
3. Verify `SEL.apps.installDetails`, `SEL.apps.installPathInput`, `SEL.apps.sidebarAppsSection`, `SEL.apps.appsTree` exist.

**Expected:** Zero TypeScript errors; all selector properties accessible.

---

## TC-07: Admin install form details wrapper
**Goal:** The admin apps list install form is wrapped in a collapsible details element.

1. Open `backend/app/templates/admin/apps/list.html`.
2. Confirm the install form is inside `<details class="install-details">` with a `<summary>` element.
3. Verify Playwright locator `page.locator('details.install-details').locator('summary')` would find exactly one element.

**Expected:** Install form is collapsible; E2E tests can click the summary to expand it.

---

## Edge Cases

### EC-01: CalDAV has no API URL env var
CalDAV sync uses a user-supplied server URL (entered in the connect form), unlike other services that use platform-injected env vars. Verify `docker-compose.test.yml` does NOT have a `CALDAV_API_URL` env var — this is intentional, not a gap.

### EC-02: Mock server directories must exist
If any `e2e/mock-*-api/` directory is missing, the Docker volume mount fails. This slice only adds the Docker service definitions — the mock server implementations are a separate concern.
