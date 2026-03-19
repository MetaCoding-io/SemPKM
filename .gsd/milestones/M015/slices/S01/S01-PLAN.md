# S01: Context queries, badge count, and sidebar with grouped results

**Goal:** After navigating to any page, the extension queries the SemPKM graph using page URL, title, and keywords. Badge shows the match count. User opens a sidebar (Alt+K) showing related objects grouped by type. Clicking "Open" navigates to the object in SemPKM.
**Demo:** User navigates to a page whose URL matches a `schema:url` property on a Note — badge shows "1", sidebar shows the Note under its type group. User clicks "Open" — object opens in a new SemPKM tab.

## Must-Haves

- `contextQuery({url, title, keywords})` method on SemPKMClient sending separate fields to `POST /api/context-query` (D196)
- Service worker listens to `chrome.tabs.onUpdated` (status=complete), debounces 2s, then calls context-query
- Badge text set per-tab with match count (empty string when 0)
- In-memory LRU cache (max 100 URLs) in service worker for context results (D198)
- Chrome Side Panel API (`chrome.sidePanel`) configured in manifest — sidebar HTML shared with Firefox (D194)
- Firefox `sidebar_action` manifest key pointing to same sidebar HTML
- Alt+K keyboard shortcut opens the sidebar (D195) — popup (Alt+S / icon click) unchanged
- Sidebar receives results from service worker via `chrome.runtime.sendMessage`, renders grouped by type
- Client-side ranking: URL match results first, then title match, then keyword match, truncated to top 10 (D197)
- "Open" action on each result navigates to the object in SemPKM
- "Link to this page" and "Add Evidence" buttons rendered but stubbed (wired in S02)
- Settings keys registered in storage.js: `autoCheckContext`, `contextCheckDelay`, `contextTimeout`

## Proof Level

- This slice proves: integration
- Real runtime required: yes (sideloaded extension against Docker test stack)
- Human/UAT required: no (Node.js unit tests + sideload verification)

## Verification

- `node --test extension/tests/test-context-utils.js` — Unit tests for result ranking, grouping, and LRU cache logic
- Sideload extension against Docker test stack → navigate to page with matching URL → badge shows count → Alt+K opens sidebar → results visible grouped by type → click "Open" navigates to SemPKM
- `node --check extension/sidebar/sidebar.js && node --check extension/shared/context-utils.js && node --check extension/shared/api-client.js` — All new/modified JS files pass syntax check

## Observability / Diagnostics

- Runtime signals: `console.log('[SemPKM]')` prefixed messages in service worker for query lifecycle (start, cache hit, result count, error)
- Inspection surfaces: Service worker console in `chrome://extensions` shows query flow and cache state
- Failure visibility: Badge shows "!" on query timeout/error; sidebar shows error message with retry button
- Redaction constraints: API key never logged; only key name referenced

## Integration Closure

- Upstream surfaces consumed: `POST /api/context-query` (M013, API-04), `extension/shared/api-client.js` (M014), `extension/shared/storage.js` (M014), `extension/content/extractor.js` (M014)
- New wiring introduced: service worker tab listener → context query → badge + cache → sidebar messaging
- What remains before the milestone is truly usable end-to-end: S02 (Link/Evidence actions), S03 (settings UI, E2E tests, docs)

## Tasks

- [x] **T01: Extend API client, storage keys, and manifests for context overlay** `est:45m`
  - Why: All other tasks depend on the `contextQuery()` method, the new storage keys, and the manifest entries for sidePanel/sidebar_action/commands.
  - Files: `extension/shared/api-client.js`, `extension/shared/storage.js`, `extension/manifest.json`, `extension/manifest.firefox.json`
  - Do: Add `contextQuery({url, title, keywords})` to SemPKMClient (separate from the existing `searchObjects()`). Add settings keys `autoCheckContext` (bool, default true), `contextCheckDelay` (number, default 2000), `contextTimeout` (number, default 5000) to storage.js DEFAULTS. Add `sidePanel` permission and `side_panel.default_path` to Chrome manifest. Add `sidebar_action` to Firefox manifest. Add Alt+K command entry (`_execute_sidebar_action` or named command) to both manifests. Add `tabs` permission to both manifests.
  - Verify: `node --check extension/shared/api-client.js && node --check extension/shared/storage.js` passes. Both manifest files are valid JSON.
  - Done when: `contextQuery()` exists on SemPKMClient, storage.js has the 3 new keys, both manifests declare sidebar + Alt+K + tabs permission.

- [x] **T02: Build service worker context pipeline with debounce, cache, and badge** `est:1h30m`
  - Why: This is the core intelligence — listens for tab navigation, debounces, queries the API, caches results, and sets the badge. All downstream UI depends on this data pipeline.
  - Files: `extension/background/service-worker.js`, `extension/shared/context-utils.js` (new)
  - Do: Create `context-utils.js` with pure functions: `rankResults(results)` (URL > title > keyword, top 10), `groupByType(results)` (returns Map of typeLabel → results[]), and `LRUCache` class (max 100, get/set/has). In service worker: add `chrome.tabs.onUpdated` listener filtering `status === 'complete'`, debounce via `setTimeout` (clear on re-trigger), extract page URL + title from tab, call `contextQuery()` via api-client, rank results, cache, call `chrome.action.setBadgeText({text, tabId})`. Add `chrome.runtime.onMessage` handler for `{type: 'getContextResults'}` returning cached results for sender tab. Handle Alt+K command via `chrome.commands.onCommand` to open side panel. Log lifecycle events with `[SemPKM]` prefix.
  - Verify: `node --check extension/background/service-worker.js && node --check extension/shared/context-utils.js` passes. Console logs confirm query flow when sideloaded.
  - Done when: Service worker queries on tab navigation, sets badge count per tab, caches results, responds to `getContextResults` message, and opens sidebar via Alt+K.

- [x] **T03: Build sidebar UI with grouped results and Open action** `est:1h`
  - Why: The user-facing sidebar that renders context results grouped by type. This is what makes the feature visible and useful.
  - Files: `extension/sidebar/sidebar.html` (new), `extension/sidebar/sidebar.js` (new), `extension/sidebar/sidebar.css` (new)
  - Do: Create sidebar.html with SemPKM-branded header, loading state, empty state ("No related objects found"), error state with retry, and results container. sidebar.js: on load, send `{type: 'getContextResults'}` to service worker, receive results, call `groupByType()` from context-utils.js, render each group as a collapsible section with type label + count + icon. Each result item shows label, snippet (if present), match type badge, and action buttons (Open, Link to this page, Add Evidence). "Open" button calls `window.open(instanceUrl + '/browser/objects/' + encodeURIComponent(iri))`. "Link to this page" and "Add Evidence" buttons present but show "Coming soon" toast on click. Listen for `chrome.runtime.onMessage` with `{type: 'contextResultsUpdated'}` to auto-refresh when user navigates. sidebar.css: clean styling matching SemPKM teal accent, compact result cards, type group headers with icons.
  - Verify: `node --check extension/sidebar/sidebar.js` passes. Sideload extension → Alt+K opens sidebar → results render grouped by type → "Open" navigates to SemPKM.
  - Done when: Sidebar opens via Alt+K, shows grouped results from real context-query data, "Open" works, stub actions show toast.

- [ ] **T04: Add Node.js unit tests for ranking, grouping, and LRU cache** `est:45m`
  - Why: The slice's contract verification — proves the pure logic works correctly independent of browser APIs.
  - Files: `extension/tests/test-context-utils.js` (new)
  - Do: Write Node.js tests using `node:test` + `node:assert` (no external deps). Test `rankResults()`: URL matches sort first, then title, then keyword; truncates to 10; handles empty array; handles ties within same match_type. Test `groupByType()`: groups by type_label, preserves order within groups, handles null type_label (groups as "Other"), handles empty array. Test `LRUCache`: set/get round-trip, max size eviction (101st entry evicts oldest), get promotes to most recent, has() works, clear() works, entries with same key update in place.
  - Verify: `node --test extension/tests/test-context-utils.js` — all tests pass.
  - Done when: ≥15 tests pass covering ranking, grouping, and LRU cache logic.

## Files Likely Touched

- `extension/shared/api-client.js` — add `contextQuery()` method
- `extension/shared/storage.js` — add 3 new settings keys
- `extension/shared/context-utils.js` — new: ranking, grouping, LRU cache pure functions
- `extension/manifest.json` — add sidePanel, tabs permission, Alt+K command
- `extension/manifest.firefox.json` — add sidebar_action, tabs permission, Alt+K command
- `extension/background/service-worker.js` — tab listener, debounce, query, cache, badge, message handler
- `extension/sidebar/sidebar.html` — new: sidebar shell
- `extension/sidebar/sidebar.js` — new: result rendering, messaging, actions
- `extension/sidebar/sidebar.css` — new: sidebar styling
- `extension/tests/test-context-utils.js` — new: unit tests
