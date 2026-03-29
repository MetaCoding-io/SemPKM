# S03: App Platform — Subprocess Lifecycle in Test Container

**Goal:** Fix all infrastructure preventing sync app E2E tests from passing: backend bugs (scheduler datetime crash, wrong APP_BASE_URL), missing Docker mock services (todoist, asana, caldav, google-calendar, outlook), missing E2E selectors (6 app selector groups + 4 apps selectors), and admin template mismatch (install form needs <details> wrapper).
**Demo:** After this: Sync app tests (linear, github, jira, monday, todoist, caldav, asana, app-platform) find running processes and render settings UI

## Tasks
- [x] **T01: Fix naive/aware datetime crash in scheduler and add APP_BASE_URL to test compose for app subprocess startup** — Fix two backend bugs that prevent all app subprocesses from working in the test container:

1. **Scheduler naive/aware datetime crash** — `backend/app/apps/scheduler.py` line 257: `now - last_run.started_at` crashes with TypeError because `now` is timezone-aware (UTC) but `last_run.started_at` from SQLite is naive. Apply the same pattern from Knowledge entry about SQLite naive datetimes: normalize `started_at` before subtraction.

2. **APP_BASE_URL missing** — `docker-compose.test.yml` api service environment block has no `APP_BASE_URL`. The default in `backend/app/main.py` is `http://localhost:4000` which is wrong inside the test container (the API listens on port 8000). Add `APP_BASE_URL: http://localhost:8000` to the api service environment.
  - Estimate: 15m
  - Files: backend/app/apps/scheduler.py, docker-compose.test.yml
  - Verify: cd backend && python -c "import ast; ast.parse(open('app/apps/scheduler.py').read())" && grep -q 'APP_BASE_URL' ../docker-compose.test.yml && echo 'PASS'
- [x] **T02: Added 5 mock API services (todoist, asana, caldav, google-calendar, outlook) with env vars and depends_on entries to docker-compose.test.yml** — Add 5 mock API Docker services and their corresponding environment variables to `docker-compose.test.yml`. Follow the exact pattern of the existing mock-linear/mock-github/mock-jira/mock-monday services.

**Services to add (all use same pattern: python:3.12-slim, volume mount, python server.py, health check, sempkm-test network):**

1. `mock-todoist` — volume `./e2e/mock-todoist-api:/app:ro`
2. `mock-asana` — volume `./e2e/mock-asana-api:/app:ro`
3. `mock-caldav` — volume `./e2e/mock-caldav-api:/app:ro`
4. `mock-google-calendar` — volume `./e2e/mock-google-calendar-api:/app:ro`
5. `mock-outlook` — volume `./e2e/mock-outlook-api:/app:ro`

**Environment variables to add to the api service (apps inherit the API container's env):**
- `TODOIST_API_URL: http://mock-todoist:8080`
- `ASANA_API_URL: http://mock-asana:8080`
- `ASANA_TOKEN_URL: http://mock-asana:8080/-/oauth_token`
- `GCAL_API_URL: http://mock-google-calendar:8080`
- `GOOGLE_TOKEN_URL: http://mock-google-calendar:8080/oauth/token`
- `OUTLOOK_API_URL: http://mock-outlook:8080`
- `OUTLOOK_TOKEN_URL: http://mock-outlook:8080/oauth2/v2.0/token`

Note: CalDAV doesn't need an env var — the server URL is user-supplied via the connect form.

**Add depends_on entries** for all 5 new mock services to the api service's depends_on block (with `condition: service_healthy`).
  - Estimate: 20m
  - Files: docker-compose.test.yml
  - Verify: grep -c 'mock-todoist\|mock-asana\|mock-caldav\|mock-google-calendar\|mock-outlook' docker-compose.test.yml | grep -q '[5-9]' && grep -q 'TODOIST_API_URL' docker-compose.test.yml && grep -q 'GCAL_API_URL' docker-compose.test.yml && grep -q 'OUTLOOK_API_URL' docker-compose.test.yml && echo 'PASS'
- [x] **T03: Add 6 E2E selector groups (todoistSync, asanaSync, caldavCalendarSync, googleCalendarSync, outlookCalendarSync, rss), 4 apps selectors, and wrap admin install form in details element** — Add 6 missing selector groups and 4 missing `apps` selectors to `e2e/helpers/selectors.ts`, and fix the admin apps list template to match the test's expected `<details>` wrapper.

**Selector groups to add (derive values from app HTML templates):**

1. **todoistSync** — from `apps/todoist-sync/frontend/templates/`:
   - `patInput: '#todoist-token'`
   - `connectBtn: '.api-key-form button[type="submit"]'`
   - `connectStatus: '.connection-status'`
   - `tokenPreview: '.token-preview'`
   - `projectCheckbox: '.project-checkbox-item input[type="checkbox"]'`
   - `saveProjectsBtn: '.projects-section button[type="submit"]'`
   - `syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]'`
   - `saveConfigBtn: '.sync-config-form button[type="submit"]'`
   - `syncNowBtn: '#sync-now-btn'`
   - `syncStats: '.sync-stats'`
   - `statValue: '.stat-value'`

2. **asanaSync** — from `apps/asana-sync/frontend/templates/`:
   - `patInput: '#asana-pat'`
   - `connectBtn: '.api-key-form button[type="submit"]'`
   - `connectStatus: '.connection-status'`
   - `projectCheckbox: '.project-checkbox-item input[type="checkbox"]'`
   - `saveProjectsBtn: '.projects-section button[type="submit"]'`
   - `discoverFieldsBtn: '.discover-section button[type="submit"]'`
   - `saveMappingBtn: '.field-mapping-form button[type="submit"]'`
   - `statusSourceSection: '.status-source-radios'`
   - `syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]'`
   - `saveConfigBtn: '.sync-config-form button[type="submit"]'`
   - `syncNowBtn: '#sync-now-btn'`
   - `syncStats: '.sync-stats'`

3. **caldavCalendarSync** — from `apps/caldav-calendar/frontend/templates/`:
   - `serverUrlInput: '#caldav-server-url'`
   - `usernameInput: '#caldav-username'`
   - `passwordInput: '#caldav-password'`
   - `credentialsSubmitBtn: '.credentials-form button[type="submit"]'`
   - `connectStatus: '.connection-status'`
   - `accountUsername: '.account-username'`
   - `calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]'`
   - `saveCalendarsBtn: '.calendars-section button[type="submit"]'`
   - `syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]'`
   - `saveConfigBtn: '.sync-config-form button[type="submit"]'`
   - `syncNowBtn: '#sync-now-btn'`
   - `syncStats: '.sync-stats'`

4. **googleCalendarSync** — from `apps/google-calendar/frontend/templates/`:
   - `clientIdInput: '#gcal-client-id'`
   - `clientSecretInput: '#gcal-client-secret'`
   - `credentialsSubmitBtn: '.credentials-form button[type="submit"]'`
   - `connectGoogleBtn: '.btn-google'`
   - `connectStatus: '.connection-status'`
   - `accountEmail: '.account-email'`
   - `calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]'`
   - `saveCalendarsBtn: '.calendars-section button[type="submit"]'`
   - `syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]'`
   - `saveConfigBtn: '.sync-config-form button[type="submit"]'`
   - `syncNowBtn: '#sync-now-btn'`
   - `syncStats: '.sync-stats'`

5. **outlookCalendarSync** — from `apps/outlook-calendar/frontend/templates/`:
   - `clientIdInput: '#outlook-client-id'`
   - `clientSecretInput: '#outlook-client-secret'`
   - `credentialsSubmitBtn: '.credentials-form button[type="submit"]'`
   - `connectMicrosoftBtn: '.btn-microsoft'`
   - `connectStatus: '.connection-status'`
   - `accountEmail: '.account-email'`
   - `calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]'`
   - `saveCalendarsBtn: '.calendars-section button[type="submit"]'`
   - `syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]'`
   - `saveConfigBtn: '.sync-config-form button[type="submit"]'`
   - `syncNowBtn: '#sync-now-btn'`
   - `syncStats: '.sync-stats'`

6. **rss** — from `apps/rss-reader/frontend/templates/`:
   - `readerContainer: '#rss-reader-container'`
   - `feedSidebar: '#rss-feed-sidebar'`
   - `articleList: '#rss-article-list'`
   - `readingPane: '#rss-reading-pane'`
   - `feedItem: '.rss-feed-item'`
   - `articleItem: '.rss-article-item'`
   - `subscribeBtn: '.rss-subscribe-btn'`
   - `subscribeDialog: '#rss-subscribe-dialog'`
   - `feedUrlInput: '#feed-url-input'`
   - `emptyState: '.rss-empty-state'`
   - `starBtn: '.rss-star-btn'`
   - `opmlImportForm: '#rss-opml-import'`
   - `opmlResult: '#opml-import-result'`
   - `successMessage: '.alert-success, .success-box'`
   - `settingsForm: '.rss-settings'`
   - `settingsResult: '#rss-settings-result'`
   - `sidebarIconBtn: '.rss-sidebar-actions button'`

**Missing apps selectors:**
   - `installDetails: 'details.install-details'`
   - `installPathInput: '#app_path'`
   - `sidebarAppsSection: '#section-apps'`
   - `appsTree: '#apps-tree'`

**Admin template fix:** Wrap the install form section in `backend/app/templates/admin/apps/list.html` with a `<details class="install-details">` element and add a `<summary>` so the test's `installDetails.locator('summary').click()` works.
  - Estimate: 30m
  - Files: e2e/helpers/selectors.ts, backend/app/templates/admin/apps/list.html
  - Verify: cd e2e && npx tsc --noEmit 2>&1 | grep -c 'todoistSync\|asanaSync\|caldavCalendarSync\|googleCalendarSync\|outlookCalendarSync\|SEL.rss' | grep -q '^0$' && echo 'PASS'
