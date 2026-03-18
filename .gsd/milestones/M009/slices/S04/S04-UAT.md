# S04: Frontend Level 1 — Standalone Pages & Sidebar — UAT

**Milestone:** M009
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for unit tests + live-runtime for Docker integration)
- Why this mode is sufficient: Unit tests prove endpoint logic and filtering. Live Docker verification (S07) will exercise the full proxy chain with a real app.

## Preconditions

- Docker stack running (`docker compose up -d` from project root)
- At least one app installed and running via admin portal (or use the test-app from S07)
- The installed app must declare `ui.pages` entries with `nav: "apps"` in its manifest
- Backend unit test venv available (`backend/.venv/`)

## Smoke Test

Open the workspace in a browser. The left sidebar should have an **APPS** section between WORKFLOWS and the shared navigation section. If an app with `nav: "apps"` pages is installed and running, those pages should appear as clickable entries.

## Test Cases

### 1. APPS sidebar section exists in workspace

1. Navigate to the workspace (`/browser/workspace`)
2. Look at the left sidebar sections
3. **Expected:** An APPS section appears between WORKFLOWS and the shared navigation section. It loads via htmx on page load.

### 2. APPS sidebar shows pages from running apps

1. Install a test app that declares `ui.pages` with at least one page having `nav: "apps"`
2. Start the app via admin portal
3. Navigate to the workspace
4. **Expected:** The APPS sidebar section shows the app's page entry with icon and label. The entry has an `onclick` handler calling `openAppPageTab()`.

### 3. APPS sidebar excludes stopped apps

1. Install a test app with `nav: "apps"` pages
2. Stop the app via admin portal
3. Navigate to the workspace (or trigger `htmx.trigger(document.body, 'appsRefreshed')` in console)
4. **Expected:** The APPS sidebar shows "No apps installed" or does not display the stopped app's pages.

### 4. APPS sidebar excludes pages without nav: "apps"

1. Install a test app that has pages with `nav: null` or other nav values (not `"apps"`)
2. Start the app
3. **Expected:** Only pages with `nav: "apps"` appear in the sidebar. Other pages are excluded.

### 5. Clicking an app page opens a dockview tab

1. With a running app visible in the APPS sidebar, click a page entry
2. **Expected:** A new dockview tab opens with the app page's label. The tab content area loads the app's fragment via htmx from `/app/{appId}/_fragments/{fragment}`.

### 6. App CSS and JS included in page tab

1. Open an app page tab (as in test case 5)
2. Inspect the tab content's HTML source
3. **Expected:** `<link>` tags for each CSS file in the manifest's `frontend.css` array, using `/app-static/{appId}/` paths. `<script>` tags for each JS file similarly.

### 7. Tab dedup — opening same page twice reuses tab

1. Click the same app page entry in the sidebar twice
2. **Expected:** Only one tab is created. The second click focuses the existing tab instead of opening a duplicate.

### 8. 404 for unknown app

1. Navigate directly to `/browser/apps/nonexistent/page/foo`
2. **Expected:** HTTP 404 response with detail message "App nonexistent not found".

### 9. 404 for unknown page in valid app

1. Navigate to `/browser/apps/{valid_app_id}/page/nonexistent`
2. **Expected:** HTTP 404 response with detail message "Page nonexistent not found in app {valid_app_id}".

### 10. Multiple running apps show all pages

1. Install and start two apps, each with `nav: "apps"` pages
2. Navigate to the workspace
3. **Expected:** The APPS sidebar shows pages from both apps.

## Edge Cases

### App becomes unavailable mid-session

1. Open the workspace with a running app's page in the APPS sidebar
2. Stop the app via admin portal
3. Trigger `htmx.trigger(document.body, 'appsRefreshed')` in browser console
4. **Expected:** The sidebar updates — the stopped app's pages disappear. Any open tab for that app may show an error when the fragment fails to load (htmx error swap).

### App with empty pages array

1. Install an app whose manifest has `ui.pages: []` (empty)
2. Start the app
3. **Expected:** No entries appear for this app in the sidebar. No errors.

### openAppPageTab from browser console

1. Open browser console
2. Run: `openAppPageTab('test-app', 'main', 'Test Page')`
3. **Expected:** A dockview tab opens with title "Test Page". Content loads from `/browser/apps/test-app/page/main`. If the app isn't installed, the tab shows a 404 error from the backend.

## Failure Signals

- APPS section missing from workspace sidebar → check `workspace.html` for the section, check `/browser/apps/explorer` endpoint directly
- Sidebar shows "No apps installed" when apps are running → check `app_manager.get_status()` returns `{"status": "running"}`, check app registry has the app
- Clicking sidebar entry does nothing → check browser console for JS errors, verify `openAppPageTab` is defined on `window`
- Tab opens but shows blank/error → check network tab for the htmx request to `/browser/apps/{appId}/page/{pageId}`, check proxy chain to `/app/{appId}/_fragments/{fragment}`
- CSS/JS not loading → check `/app-static/{appId}/` nginx location is configured, verify static assets were copied during install

## Requirements Proved By This UAT

- APP-07 (Frontend integration Level 1 — standalone pages) — Test cases 1-7 prove the full sidebar → tab → fragment chain works with app CSS/JS inclusion. Test cases 8-9 prove failure paths are handled correctly.

## Not Proven By This UAT

- Live proxy chain (nginx → API → AppProxy → UDS → app subprocess) — requires real Docker stack with running app (S07)
- Fragment content rendering inside the tab — unit tests verify the htmx wrapper but not the actual fragment response
- E2E Playwright automation of the full flow — deferred to S07

## Notes for Tester

- The unit tests (`python -m pytest tests/test_app_browser.py -v`) validate all filtering logic without Docker. Run these first.
- For live testing, you need a test app installed and running. S07's test-app will be the canonical fixture for this.
- The `appsRefreshed` event is the refresh mechanism — you can trigger it manually from the browser console to test sidebar updates.
- The fragment URL in the htmx wrapper (`/app/{appId}/_fragments/{fragment}`) goes through the nginx → API proxy chain from S03. If static assets aren't loading, check the nginx `/app-static/` location.
