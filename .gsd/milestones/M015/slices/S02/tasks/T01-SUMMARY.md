---
id: T01
parent: S02
milestone: M015
provides:
  - linkToPage message handler in service worker calling edge.create API
  - _linkToPage() sidebar action with loading state and toast feedback
  - _currentTabUrl tracking refreshed on init and contextResultsUpdated
  - .action-link CSS class for solid-border link button styling
key_files:
  - extension/background/service-worker.js
  - extension/sidebar/sidebar.js
  - extension/sidebar/sidebar.css
key_decisions: []
patterns_established:
  - Service worker async IIFE pattern for message handlers that call APIs
observability_surfaces:
  - "[SemPKM] linkToPage: success" / "[SemPKM] linkToPage: error: <detail>" in service worker console
  - Sidebar toast: "✓ Linked to this page" on success, API error detail on failure
  - Button loading state: "Linking…" + disabled during API call
duration: 12m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Wire "Link to this page" action through service worker

**Replaced stub "Link to this page" button with real edge.create API call relayed through service worker, with loading state and toast feedback**

## What Happened

Added a `linkToPage` message handler to the service worker that reads API config via `_getApiConfig()`, POSTs to `/api/commands` with `{command: 'edge.create', params: {source, target, predicate: 'schema:url'}}`, and responds with success/error. Used an async IIFE inside the message listener (same pattern as the existing `refreshContextResults` handler uses with its async callback).

In the sidebar, added `_currentTabUrl` and `_currentTabTitle` module-level variables. These are populated on `init()` via `chrome.tabs.query` and refreshed whenever `contextResultsUpdated` fires (handles tab navigation while the sidebar is open).

Replaced the stub link button handler with `_linkToPage(objectIri, btn)` which disables the button, shows "Linking…", sends the message, and restores the button on response. Success shows "✓ Linked to this page" toast; failure shows the API error detail.

Changed the link button CSS class from `.action-stub` to `.action-link` (solid border instead of dashed). The `.action-stub` class remains for the Evidence button which stays as a stub until T02.

## Verification

- `node --check extension/background/service-worker.js` — passes, no syntax errors
- `node --check extension/sidebar/sidebar.js` — passes, no syntax errors
- `node --test extension/tests/test-context-utils.js` — 23/23 tests pass
- `rg 'action-link' extension/sidebar/sidebar.js` — confirms link button uses new class
- `rg "type === 'linkToPage'" extension/background/service-worker.js` — confirms handler exists
- `rg '_currentTabUrl' extension/sidebar/sidebar.js` — confirms tab URL tracking in 5 locations

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 3 | `node --test extension/tests/test-context-utils.js` | 0 | ✅ pass (23/23) | 59ms |
| 4 | `rg 'action-link' extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 5 | `rg "type === 'linkToPage'" extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 6 | `rg '_currentTabUrl' extension/sidebar/sidebar.js` | 0 | ✅ pass (5 hits) | <1s |

## Diagnostics

- **Service worker console** (`chrome://extensions` → service worker "Inspect"): Look for `[SemPKM] linkToPage: success` or `[SemPKM] linkToPage: error: <detail>`
- **Sidebar toast**: "✓ Linked to this page" (green) on success, red toast with error detail on failure
- **Button state**: While API call is in-flight, button shows "Linking…" and is disabled. Re-enables on completion.
- **Not configured**: If `_getApiConfig()` returns null, sidebar shows "SemPKM not configured" toast

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `extension/background/service-worker.js` — Added `linkToPage` message handler with edge.create API call
- `extension/sidebar/sidebar.js` — Added `_currentTabUrl`/`_currentTabTitle` tracking, `_linkToPage()` function, wired link button with `.action-link` class
- `extension/sidebar/sidebar.css` — Added `.action-link`, `.action-link:hover`, `.action-link:disabled` rules
- `.gsd/milestones/M015/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
