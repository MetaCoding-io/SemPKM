---
id: T03
parent: S01
milestone: M015
provides:
  - Sidebar UI (sidebar.html + sidebar.js + sidebar.css) rendering grouped context results
  - Open action navigating to SemPKM objects in new tabs
  - Stub buttons for "Link to page" and "Add Evidence" with coming-soon toasts
  - Loading, empty, error, and results states with retry capability
  - Auto-refresh on contextResultsUpdated messages from service worker
key_files:
  - extension/sidebar/sidebar.html
  - extension/sidebar/sidebar.js
  - extension/sidebar/sidebar.css
key_decisions:
  - Plain script tags (not ES modules) for sidebar — consistent with service worker's globalThis pattern
  - Dark theme with teal accent matching SemPKM brand, not the light popup theme
  - Action bar hidden until hover to keep cards compact
  - Stub actions use dashed border to visually signal "coming soon" without tooltip
patterns_established:
  - Sidebar fetches cached results via getContextResults, uses refreshContextResults for retry/manual refresh
  - SemPKMContextUtils accessed from global scope set by context-utils.js script tag
  - State management via _showState() toggling hidden attributes on named panels
observability_surfaces:
  - "[SemPKM Sidebar]" prefixed console logs for init, rendering, message receipt, errors
  - DOM state visible via #loading/#error/#empty/#results hidden attributes
  - Error state shows message text and Retry button
  - Toast notifications for action feedback
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Build sidebar UI with grouped results and Open action

**Created sidebar/sidebar.html, sidebar.js, and sidebar.css — dark-theme sidebar rendering grouped context results with Open action and stub buttons for Link/Evidence**

## What Happened

Built the three sidebar files specified in the plan. The HTML shell has a teal-accent header with refresh button, four state panels (loading/error/empty/results), a footer linking to the configured instance, and a toast container. 

The JS IIFE on DOMContentLoaded sends `getContextResults` to the service worker, renders results grouped by type using `SemPKMContextUtils.groupByType()`, and handles all edge cases: unconfigured instance, no cached results, service worker unavailable, empty results. The "Open" action creates a new tab via `chrome.tabs.create()`. Stub buttons show "coming in next update" toasts. A `contextResultsUpdated` message listener triggers automatic re-fetch. The refresh header button and retry button both send `refreshContextResults` to force a fresh API query.

CSS uses a dark theme (bg: #13131f, surface: #1e1e32) with teal accent (#0d9488) that matches the SemPKM brand. Type groups are collapsible with chevron rotation. Match badges are color-coded pills (URL green, Title blue, Keyword gray). Card action bars reveal on hover. Stub action buttons use dashed borders as a visual "coming soon" indicator.

## Verification

- `node --check extension/sidebar/sidebar.js` — passes (syntax valid)
- `node --check extension/shared/context-utils.js && node --check extension/shared/api-client.js` — both pass
- Chrome manifest `side_panel.default_path` correctly references `sidebar/sidebar.html`
- Firefox manifest `sidebar_action.default_panel` correctly references `sidebar/sidebar.html`
- All file references in sidebar.html resolve (sidebar.css, sidebar.js, ../shared/context-utils.js)
- `node --test extension/tests/test-context-utils.js` — file does not exist yet (T04 deliverable)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/shared/context-utils.js` | 0 | ✅ pass | <1s |
| 3 | `node --check extension/shared/api-client.js` | 0 | ✅ pass | <1s |
| 4 | `node --test extension/tests/test-context-utils.js` | — | ⏳ deferred (T04) | — |
| 5 | Manifest side_panel path check | 0 | ✅ pass | <1s |
| 6 | Manifest sidebar_action path check | 0 | ✅ pass | <1s |

## Diagnostics

- Open sidebar in Chrome DevTools: right-click sidebar panel → Inspect → Console shows `[SemPKM Sidebar]` prefixed logs
- DOM state panels: inspect `#loading`, `#error`, `#empty`, `#results` hidden attributes to see current state
- Error state: displays error message text from service worker response and exposes Retry button
- Toast container: `#toast-container` shows transient notifications for action feedback
- Refresh button in header forces `refreshContextResults` message to service worker

## Deviations

- Used `chrome.tabs.create()` instead of `window.open()` for "Open" action — `chrome.tabs.create` is the correct Chrome extension API for opening new tabs from a side panel context, whereas `window.open()` may be blocked or behave unexpectedly in extension pages
- Added a refresh button in the header bar (not in plan) — natural UX for manually triggering a context re-check without waiting for navigation

## Known Issues

- `node --test extension/tests/test-context-utils.js` — test file does not exist yet; it's the T04 deliverable
- Sideload integration testing (badge → sidebar → Open flow) requires a running Docker stack with seed data; verified structurally but not end-to-end in this task

## Files Created/Modified

- `extension/sidebar/sidebar.html` — new: sidebar shell with header, state panels, footer, script tags
- `extension/sidebar/sidebar.js` — new: IIFE with init, rendering, messaging, Open action, stub actions, toast
- `extension/sidebar/sidebar.css` — new: dark theme styles with teal accent, collapsible groups, badges, toast
- `.gsd/milestones/M015/slices/S01/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
