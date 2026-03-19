---
id: S01
parent: M015
milestone: M015
provides:
  - contextQuery({url, title, keywords}) method on SemPKMClient
  - Service worker context pipeline (tab listener → 2s debounce → query → rank → cache → badge)
  - LRU cache (max 100) for URL→results in service worker memory
  - Chrome Side Panel sidebar with grouped results, Open action, stub Link/Evidence buttons
  - Firefox sidebar_action pointing to same sidebar HTML
  - Alt+K keyboard shortcut to open sidebar (both browsers)
  - Settings keys: autoCheckContext, contextCheckDelay, contextTimeout
  - Pure utility module: rankResults, groupByType, LRUCache (context-utils.js)
  - 23 Node.js unit tests for all pure functions
requires:
  - slice: M014/S01
    provides: SemPKMClient base class, storage.js DEFAULTS pattern, dual manifests
  - slice: M013/S03
    provides: POST /api/context-query endpoint with url/title/keywords fields
affects:
  - S02 (Link to page and Add Evidence actions wire into sidebar stub buttons)
  - S03 (Settings UI reads autoCheckContext/contextCheckDelay/contextTimeout keys; E2E tests exercise badge + sidebar)
key_files:
  - extension/shared/api-client.js
  - extension/shared/storage.js
  - extension/shared/context-utils.js
  - extension/background/service-worker.js
  - extension/sidebar/sidebar.html
  - extension/sidebar/sidebar.js
  - extension/sidebar/sidebar.css
  - extension/manifest.json
  - extension/manifest.firefox.json
  - extension/tests/test-context-utils.js
key_decisions:
  - D194: Chrome Side Panel API over Shadow DOM injection for sidebar
  - D195: Popup and sidebar coexistence — icon click opens popup, Alt+K opens sidebar
  - D196: contextQuery() sends separate url/title/keywords fields (not reusing searchObjects)
  - D197: Client-side ranking (URL > title > keyword, top 10) before rendering
  - D198: In-memory LRU cache, no chrome.storage persistence (re-query is cheap)
patterns_established:
  - globalThis + module.exports dual-export for pure JS modules (works in importScripts, Node require, and ES module wrapper)
  - Inline fetch in classic service worker instead of importing ES module api-client.js
  - _getApiConfig() reads chrome.storage.sync directly in service worker context
  - State management via _showState() toggling hidden attributes on named panels in sidebar
  - "[SemPKM]" prefixed console logs for service worker lifecycle; "[SemPKM Sidebar]" for sidebar
observability_surfaces:
  - Service worker console ([SemPKM] prefixed): tab detection, cache hit/miss, query start/success/error, sidebar open
  - Badge "!" (red) on query error; numeric (teal) on results; empty on zero results or unconfigured
  - Sidebar DOM state panels (#loading, #error, #empty, #results) with hidden attribute toggling
  - Error state in sidebar shows message text and Retry button
  - Toast notifications for action feedback in sidebar
drill_down_paths:
  - .gsd/milestones/M015/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M015/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M015/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M015/slices/S01/tasks/T04-SUMMARY.md
duration: 1h15m
verification_result: passed
completed_at: 2026-03-18
---

# S01: Context queries, badge count, and sidebar with grouped results

**Extension queries the SemPKM graph on tab navigation, shows badge count per tab, and opens a dark-themed sidebar via Alt+K displaying related objects grouped by type with a working Open action**

## What Happened

T01 extended the API client and manifests. `contextQuery({url, title, keywords})` was added to `SemPKMClient`, sending only non-empty fields to `POST /api/context-query`. Three settings keys (`autoCheckContext`, `contextCheckDelay`, `contextTimeout`) were added to storage.js DEFAULTS. Chrome manifest gained `sidePanel` + `tabs` permissions with `side_panel.default_path`. Firefox manifest gained `sidebar_action` with `open_at_install: false`. Both manifests got the `open-context-sidebar` Alt+K command.

T02 built the core data pipeline. A new `context-utils.js` module exports three pure functions via `globalThis.SemPKMContextUtils`: `rankResults()` (URL > title > keyword, top 10), `groupByType()` (Map of typeLabel → results[]), and `LRUCache` (max 100 entries). The service worker was extended with a `chrome.tabs.onUpdated` listener that filters for `status === 'complete'` + http URLs, debounces via `setTimeout` (keyed by tabId, delay from settings), queries the API with AbortController timeout, ranks results, caches them, and sets per-tab badge text. Message handlers respond to `getContextResults` (return cached) and `refreshContextResults` (force re-query). Alt+K opens the sidebar via `chrome.sidePanel.open()` with Firefox `browser.sidebarAction.open()` fallback. The service worker uses inline `fetch()` with `_getApiConfig()` because classic service workers can't import ES modules.

T03 created the sidebar UI. Three files: `sidebar.html` (shell with header, four state panels, footer), `sidebar.js` (IIFE handling init, rendering, messaging), `sidebar.css` (dark theme with teal accent). The sidebar sends `getContextResults` on load, renders results grouped by type using collapsible sections with match-type badges (URL green, title blue, keyword gray). "Open" creates a new tab via `chrome.tabs.create()`. "Link to this page" and "Add Evidence" show "coming soon" toasts with dashed-border visual signal. Auto-refreshes on `contextResultsUpdated` messages from the service worker.

T04 added 23 Node.js unit tests using `node:test` + `node:assert` — 8 for rankResults, 7 for groupByType, 8 for LRUCache — covering ordering, truncation, edge cases, immutability, eviction, and promotion.

## Verification

- `node --test extension/tests/test-context-utils.js` — 23/23 tests pass (3 suites, 0 failures)
- `node --check` passes on all 5 JS files: api-client.js, storage.js, context-utils.js, service-worker.js, sidebar.js
- Chrome manifest validated: sidePanel + tabs permissions, side_panel.default_path, open-context-sidebar command
- Firefox manifest validated: tabs permission, sidebar_action.default_panel, open-context-sidebar command
- Sidebar HTML references resolve: sidebar.css, sidebar.js, ../shared/context-utils.js all exist

## Requirements Advanced

- EXT-14 (badge) — badge count set per-tab from context query results; "!" on error; clears when no results. Not yet validated (needs sideload verification against Docker stack in S03).
- EXT-15 (sidebar) — sidebar HTML/JS/CSS complete, opens via Alt+K, renders grouped results. Not yet validated (needs E2E test in S03).
- EXT-16 (open action) — "Open" button navigates to SemPKM object in new tab. Not yet validated (needs sideload verification in S03).
- EXT-20 (URL caching) — LRU cache (max 100) in service worker memory, per-URL keying. Not yet validated (needs runtime verification in S03).

## Requirements Validated

- None — all four requirements advanced but await S03 E2E test validation.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T03 used `chrome.tabs.create()` instead of `window.open()` for "Open" action — `chrome.tabs.create` is the correct extension API for side panel context
- T03 added a refresh button in the sidebar header (not in plan) — natural UX for manual context re-check

## Known Limitations

- Sideload integration testing (badge → sidebar → Open flow) not exercised in this slice — deferred to S03's E2E tests
- Service worker cache is ephemeral (lost on MV3 shutdown after ~30s idle) — acceptable per D198
- Sidebar dark theme doesn't match the popup's light theme — intentional design choice (sidebar is a persistent browsing companion, popup is a quick capture overlay)
- "Link to this page" and "Add Evidence" buttons are stubs showing "coming soon" toasts — wired in S02

## Follow-ups

- S02: Wire "Link to this page" (createEdge) and "Add Evidence" (content script text selection → createObject → createEdge) into sidebar stub buttons
- S03: Add autoCheckContext toggle to settings UI, write E2E Playwright tests proving badge + sidebar + Open against Docker stack, write user guide Chapter 33

## Files Created/Modified

- `extension/shared/api-client.js` — added `contextQuery({url, title, keywords})` method
- `extension/shared/storage.js` — added `autoCheckContext`, `contextCheckDelay`, `contextTimeout` to DEFAULTS
- `extension/shared/context-utils.js` — new: rankResults, groupByType, LRUCache with globalThis + module.exports export
- `extension/background/service-worker.js` — extended: importScripts, tab listener, debounce, query pipeline, LRU cache, badge, message handlers, Alt+K command
- `extension/sidebar/sidebar.html` — new: sidebar shell with header, state panels, footer, script tags
- `extension/sidebar/sidebar.js` — new: IIFE with init, rendering, messaging, Open action, stub actions, toast
- `extension/sidebar/sidebar.css` — new: dark theme with teal accent, collapsible groups, badges, toast
- `extension/manifest.json` — added sidePanel/tabs permissions, side_panel key, open-context-sidebar command
- `extension/manifest.firefox.json` — added tabs permission, sidebar_action key, open-context-sidebar command
- `extension/tests/test-context-utils.js` — new: 23 unit tests for rankResults, groupByType, LRUCache

## Forward Intelligence

### What the next slice should know
- The sidebar sends messages to the service worker via `chrome.runtime.sendMessage({type: 'getContextResults'})` and `{type: 'refreshContextResults'}`. S02's "Link to page" and "Add Evidence" actions should follow this same messaging pattern — sidebar sends action request to service worker, service worker executes API call, responds with result.
- The stub button click handlers in sidebar.js are at the bottom of the `_renderResults()` function — look for `linkBtn.addEventListener` and `evidenceBtn.addEventListener`. Replace the toast calls with real action logic.
- `_getApiConfig()` in the service worker returns `{instanceUrl, apiKey}` from chrome.storage.sync — reuse this for the createEdge and createObject API calls in S02.

### What's fragile
- The `globalThis.SemPKMContextUtils` dual-export pattern — if anyone converts context-utils.js to an ES module, the service worker's `importScripts()` will break silently (no error, just undefined). The service worker must remain a classic script for Firefox compatibility.
- Debounce timers are keyed by tabId in a plain Map (`_debounceTimers`) — if Chrome reuses tabIds rapidly, old timers could fire for the wrong page. Not observed in practice but worth knowing.

### Authoritative diagnostics
- Service worker console (`chrome://extensions` → Inspect) shows `[SemPKM]` prefixed logs for the entire query lifecycle — this is the first place to look if badge/sidebar aren't working.
- `node --test extension/tests/test-context-utils.js` — 23 tests in <100ms, covers all pure logic. If ranking or grouping looks wrong, run this first.

### What assumptions changed
- No assumptions changed. The context-query endpoint, storage pattern, and dual-manifest approach all worked as expected from M013/M014.
