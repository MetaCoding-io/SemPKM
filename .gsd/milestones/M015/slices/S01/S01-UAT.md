# S01: Context queries, badge count, and sidebar with grouped results — UAT

**Milestone:** M015
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for unit tests + live-runtime for sideload verification)
- Why this mode is sufficient: Pure logic (ranking, grouping, cache) is covered by 23 automated unit tests. Sidebar rendering, badge behavior, and message passing require sideloading the extension against a running SemPKM instance with seed data.

## Preconditions

1. Docker test stack running (`docker compose -f docker-compose.test.yml up -d` from project root)
2. At least one Mental Model installed (basic-pkm) with seed data containing objects that have `schema:url` properties
3. Extension sideloaded in Chrome via `chrome://extensions` → Developer mode → Load unpacked → select `extension/` directory
4. Extension configured: Options page → Instance URL = `http://localhost:3901`, API key set, connection test green
5. Node.js ≥18 available for unit tests

## Smoke Test

Run `node --test extension/tests/test-context-utils.js` — all 23 tests pass. Sideload the extension, navigate to any page, check that the badge updates within 3 seconds.

## Test Cases

### 1. Unit tests pass

1. Run `node --test extension/tests/test-context-utils.js`
2. **Expected:** 23/23 tests pass, 0 failures, 0 skipped

### 2. All JS files pass syntax check

1. Run `node --check extension/sidebar/sidebar.js && node --check extension/shared/context-utils.js && node --check extension/shared/api-client.js && node --check extension/background/service-worker.js && node --check extension/shared/storage.js`
2. **Expected:** All pass with exit code 0, no output

### 3. Chrome manifest has required entries

1. Parse `extension/manifest.json` as JSON
2. **Expected:** `permissions` includes `sidePanel` and `tabs`. `side_panel.default_path` equals `sidebar/sidebar.html`. `commands.open-context-sidebar` exists with `Alt+K` as suggested key.

### 4. Firefox manifest has required entries

1. Parse `extension/manifest.firefox.json` as JSON
2. **Expected:** `permissions` includes `tabs`. `sidebar_action.default_panel` equals `sidebar/sidebar.html`. `commands.open-context-sidebar` exists with `Alt+K` as suggested key.

### 5. Badge shows count on page with matching URL

1. Create a Note object in SemPKM with `schema:url` set to `https://example.com/test-page`
2. Navigate to `https://example.com/test-page` in a tab
3. Wait 3 seconds (2s debounce + query time)
4. **Expected:** Extension badge on that tab shows "1" with teal background

### 6. Badge clears on page with no matches

1. Navigate to `https://random-nonexistent-domain-xyz.com/nothing` in a tab
2. Wait 3 seconds
3. **Expected:** Extension badge is empty (no text shown)

### 7. Alt+K opens sidebar

1. Press Alt+K on any page
2. **Expected:** Chrome Side Panel opens showing the SemPKM sidebar. Header shows "SemPKM Context" with a refresh button.

### 8. Sidebar shows grouped results

1. Navigate to a page that matches seed data (e.g. a URL stored on a Note, or a page whose title keywords match object labels)
2. Wait for badge to update
3. Press Alt+K to open sidebar
4. **Expected:** Sidebar shows results grouped by type (e.g. "Note", "Concept"). Each group is collapsible with a count badge. Each result card shows label, match type pill (green "url", blue "title", or gray "keyword"), and three action buttons.

### 9. Open action navigates to SemPKM

1. In the sidebar, click "Open" on any result card
2. **Expected:** A new tab opens navigating to `http://localhost:3901/browser/objects/<encoded_iri>`. The SemPKM workspace loads showing the object.

### 10. Stub actions show coming-soon toast

1. In the sidebar, click "Link to this page" on any result card
2. **Expected:** A toast notification appears saying the feature is coming in the next update. The button has a dashed border indicating it's a stub.
3. Click "Add Evidence" on any result card
4. **Expected:** Same toast behavior.

### 11. Sidebar shows empty state when no results

1. Navigate to a page with no matching objects (e.g. `https://random-nonexistent-domain-xyz.com`)
2. Open sidebar via Alt+K
3. **Expected:** Sidebar shows "No related objects found" empty state message.

### 12. Sidebar shows error state on API failure

1. Set the instance URL to an invalid address (e.g. `http://localhost:9999`) in extension options
2. Navigate to any page, wait for badge to show "!"
3. Open sidebar via Alt+K
4. **Expected:** Sidebar shows error state with error message text and a "Retry" button. Clicking Retry re-attempts the query.

### 13. Sidebar auto-refreshes on navigation

1. Open sidebar via Alt+K
2. Navigate to a different page (one with different matching objects)
3. **Expected:** Sidebar automatically updates to show results for the new page without manually pressing refresh.

### 14. Refresh button forces re-query

1. Open sidebar showing cached results
2. Click the refresh button (🔄) in the sidebar header
3. **Expected:** Sidebar briefly shows loading state, then re-renders results from a fresh API query. Service worker console shows `[SemPKM] Context query start` log.

### 15. Settings keys registered correctly

1. Run: `node -e "const s = require('./extension/shared/storage.js'); console.log(s.DEFAULTS.autoCheckContext, s.DEFAULTS.contextCheckDelay, s.DEFAULTS.contextTimeout)"`
2. **Expected:** Output: `true 2000 5000`

## Edge Cases

### Icon click still opens popup (not sidebar)

1. Click the extension icon in the browser toolbar
2. **Expected:** The capture popup opens (not the sidebar). Popup and sidebar are independent — popup via icon click/Alt+S, sidebar via Alt+K.

### Multiple tabs have independent badges

1. Open Tab A navigating to a page matching 3 objects
2. Open Tab B navigating to a page matching 1 object
3. **Expected:** Tab A badge shows "3", Tab B badge shows "1". Switching between tabs shows the correct badge for each.

### Extension unconfigured

1. Clear all extension settings (or fresh install with no configuration)
2. Navigate to any page
3. Open sidebar via Alt+K
4. **Expected:** Sidebar shows an appropriate message about configuring the extension (not a crash or spinner).

### Rapid navigation (debounce)

1. Navigate rapidly through 5 different pages within 2 seconds
2. **Expected:** Only the final page triggers a context query. No duplicate queries. Service worker console shows only one `[SemPKM] Context query start` for the final URL.

## Failure Signals

- Badge never appears on any tab → service worker not loading or API config missing (check `chrome://extensions` service worker console)
- Badge shows "!" on all pages → API key invalid or instance unreachable (check connection in options page)
- Alt+K does nothing → `sidePanel` permission missing or command not registered (check manifest)
- Sidebar shows perpetual loading spinner → `getContextResults` message not reaching service worker (check for JS errors in sidebar DevTools)
- "Open" button opens wrong URL → instance URL misconfigured in settings
- Unit tests fail → context-utils.js modified incompatibly (check test output for specific assertion failures)

## Requirements Proved By This UAT

- EXT-14 (badge) — Tests 5, 6, and edge case "Multiple tabs" prove per-tab badge count from context queries
- EXT-15 (sidebar) — Tests 7, 8, 11, 12, 13 prove sidebar opens via Alt+K with grouped results, empty state, error state, and auto-refresh
- EXT-16 (open action) — Test 9 proves Open action navigates to correct SemPKM object
- EXT-20 (URL caching) — Test 14 proves cache exists (refresh triggers re-query); edge case "Rapid navigation" proves debounce prevents redundant queries

## Not Proven By This UAT

- E2E Playwright automation of badge + sidebar (deferred to S03)
- Auto-context settings toggle disabling badge on navigation (deferred to S03 — settings keys registered but UI not wired)
- Cross-browser Firefox verification (sidebar_action path set but Firefox sideload not tested here)
- "Link to this page" and "Add Evidence" real actions (stubs only — wired in S02)

## Notes for Tester

- The sidebar uses a dark theme that differs from the popup's light theme — this is intentional
- Match type badges in the sidebar are color-coded: green = URL match, blue = title match, gray = keyword match
- The LRU cache is in-memory only — reloading the extension clears it, which is by design
- Seed data in basic-pkm includes Notes with URLs — these are the easiest test targets for URL matching
- If the Docker stack is freshly started, wait a few seconds for RDF4J initialization before running context queries
