---
estimated_steps: 90
estimated_files: 2
skills_used: []
---

# T03: Add missing E2E selectors and fix admin install template

Add 6 missing selector groups and 4 missing `apps` selectors to `e2e/helpers/selectors.ts`, and fix the admin apps list template to match the test's expected `<details>` wrapper.

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

## Inputs

- ``e2e/helpers/selectors.ts` — existing selector definitions (linearSync, githubSync, jiraSync, mondaySync, apps as pattern reference)`
- ``apps/todoist-sync/frontend/templates/connect.html` — HTML IDs and classes for todoist selectors`
- ``apps/todoist-sync/frontend/templates/connect_status.html` — HTML IDs and classes for todoist status selectors`
- ``apps/asana-sync/frontend/templates/connect.html` — HTML IDs and classes for asana selectors`
- ``apps/asana-sync/frontend/templates/connect_status.html` — HTML IDs and classes for asana status selectors`
- ``apps/caldav-calendar/frontend/templates/connect.html` — HTML IDs and classes for caldav selectors`
- ``apps/caldav-calendar/frontend/templates/connect_status.html` — HTML IDs and classes for caldav status selectors`
- ``apps/google-calendar/frontend/templates/connect.html` — HTML IDs and classes for google-calendar selectors`
- ``apps/google-calendar/frontend/templates/connect_status.html` — HTML IDs and classes for google-calendar status selectors`
- ``apps/outlook-calendar/frontend/templates/connect.html` — HTML IDs and classes for outlook selectors`
- ``apps/outlook-calendar/frontend/templates/connect_status.html` — HTML IDs and classes for outlook status selectors`
- ``apps/rss-reader/frontend/templates/reader.html` — HTML IDs and classes for rss selectors`
- ``apps/rss-reader/frontend/templates/feed-sidebar.html` — HTML IDs and classes for rss feed sidebar`
- ``apps/rss-reader/frontend/templates/subscribe-dialog.html` — HTML IDs and classes for rss subscribe dialog`
- ``apps/rss-reader/frontend/templates/article-list.html` — HTML IDs and classes for rss article list`
- ``apps/rss-reader/frontend/templates/settings.html` — HTML IDs and classes for rss settings`
- ``apps/rss-reader/frontend/templates/opml-import.html` — HTML IDs and classes for rss OPML import`
- ``apps/rss-reader/frontend/templates/star-button.html` — HTML for rss star button`
- ``backend/app/templates/admin/apps/list.html` — admin apps list template needs <details> wrapper`
- ``e2e/tests/31-rss-reader/rss-reader.spec.ts` — test file referencing SEL.rss and SEL.apps selectors`
- ``e2e/tests/37-todoist-sync/todoist-sync.spec.ts` — test file referencing SEL.todoistSync`
- ``e2e/tests/40-asana-sync/asana-sync.spec.ts` — test file referencing SEL.asanaSync`
- ``e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — test file referencing SEL.caldavCalendarSync`
- ``e2e/tests/36-google-calendar-sync/google-calendar-sync.spec.ts` — test file referencing SEL.googleCalendarSync`
- ``e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` — test file referencing SEL.outlookCalendarSync`

## Expected Output

- ``e2e/helpers/selectors.ts` — 6 new selector groups (todoistSync, asanaSync, caldavCalendarSync, googleCalendarSync, outlookCalendarSync, rss) + 4 new apps selectors (installDetails, installPathInput, sidebarAppsSection, appsTree)`
- ``backend/app/templates/admin/apps/list.html` — install form wrapped in <details class="install-details"> element`

## Verification

cd e2e && npx tsc --noEmit 2>&1 | grep -c 'todoistSync\|asanaSync\|caldavCalendarSync\|googleCalendarSync\|outlookCalendarSync\|SEL.rss' | grep -q '^0$' && echo 'PASS'
