---
id: S02
parent: M015
milestone: M015
provides:
  - "Link to this page" action calling edge.create API via service worker relay with loading state and toast feedback
  - "Add Evidence" action with content script text selection capture, two-step API (object.create + edge.create), and partial failure handling
  - Conditional Evidence button rendering for Claim-type results only
  - Evidence capture prompt panel UI in sidebar (instructions, text preview, Capture/Cancel)
  - _currentTabUrl tracking in sidebar (init + contextResultsUpdated refresh)
requires:
  - slice: S01
    provides: sidebar.js with stub action handlers, service-worker.js with _getApiConfig() and message handler pattern, sidebar.css with .action-stub styles
affects:
  - S03
key_files:
  - extension/background/service-worker.js
  - extension/sidebar/sidebar.js
  - extension/sidebar/sidebar.css
  - extension/sidebar/sidebar.html
key_decisions: []
patterns_established:
  - Service worker async IIFE pattern for message handlers that call APIs (linkToPage, addEvidence)
  - Two-step API call pattern with partial failure reporting (orphaned IRI in error response)
  - chrome.scripting.executeScript with self-contained function for cross-context text extraction from sidebar
observability_surfaces:
  - "[SemPKM] linkToPage: success/error" in service worker console
  - "[SemPKM] addEvidence: creating/created/linking/success/error" step-by-step in service worker console
  - Sidebar toasts — "✓ Linked to this page", "✓ Evidence captured and linked", error detail with Evidence IRI on partial failure
  - Button loading states — "Linking…" / "Capturing…" with disabled attribute during API calls
drill_down_paths:
  - .gsd/milestones/M015/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M015/slices/S02/tasks/T02-SUMMARY.md
duration: 27m
verification_result: passed
completed_at: 2026-03-18
---

# S02: In-context actions — Link to page and Add Evidence

**Replaced both stub sidebar action buttons with real API flows: "Link to this page" creates a schema:url edge, "Add Evidence" captures highlighted text and creates/links an Evidence object to a Claim**

## What Happened

T01 wired the "Link to this page" action. Added a `linkToPage` message handler to the service worker that reads API config via `_getApiConfig()`, POSTs an `edge.create` command with `{source: objectIri, target: pageUrl, predicate: 'schema:url'}`, and responds with success/error. In the sidebar, added `_currentTabUrl` and `_currentTabTitle` module-level variables populated on init via `chrome.tabs.query` and refreshed on every `contextResultsUpdated` event. The stub handler was replaced with `_linkToPage(objectIri, btn)` which disables the button, shows "Linking…", sends the message, and restores on response. CSS class changed from `.action-stub` to `.action-link` (solid border).

T02 wired the "Add Evidence" action — the more complex flow. Added `addEvidence` message handler to the service worker making two sequential API calls: first `object.create` for the Evidence object (with the selected text as body, page URL as source), then `edge.create` linking Evidence→Claim via `res:supports`. Partial failure (object created, edge failed) returns the Evidence IRI in the error response so the user can link manually. In the sidebar, the Evidence button is conditionally rendered only when `item.type_iri` contains `research:Claim`. Clicking it shows an evidence capture prompt panel, user selects text on the page, clicks Capture, which executes `chrome.scripting.executeScript` with a self-contained function to get `window.getSelection().toString().trim()`. After validation, the selected text preview is shown and the message sent to the service worker.

All `.action-stub` references removed from sidebar.js — both actions are now real implementations.

## Verification

- `node --check extension/background/service-worker.js` — syntax valid
- `node --check extension/sidebar/sidebar.js` — syntax valid
- `node --test extension/tests/test-context-utils.js` — 23/23 tests pass (no regressions)
- Link button uses `.action-link` class (not `.action-stub`)
- Evidence button uses `.action-evidence` class, conditionally rendered for Claim types only
- `linkToPage` and `addEvidence` message handlers both present in service worker
- Evidence prompt container with Capture/Cancel buttons present in sidebar.html
- `chrome.scripting.executeScript` call present for text selection capture
- Zero `.action-stub` references remain in sidebar.js

## Requirements Advanced

- EXT-17 (link action) — "Link to this page" button sends edge.create command via service worker relay, shows success/error toast. Full validation requires E2E test in S03.
- EXT-18 (evidence capture) — "Add Evidence" button on Claim-type results triggers capture flow: prompt → text selection → Evidence object created → linked to Claim. Full validation requires E2E test in S03.

## Requirements Validated

- None — both EXT-17 and EXT-18 require E2E tests (S03) for full validation.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None.

## Known Limitations

- Evidence capture requires `scripting` permission in the extension manifest — already declared from M014 (used for page data extraction), but users who restrict permissions may block this flow.
- Partial failure in the two-step Evidence flow (object created, edge failed) leaves an orphaned Evidence object. The IRI is shown in the error toast for manual linking, but there's no automatic retry or cleanup.
- Both actions require the extension to be configured with a valid API key and instance URL — "SemPKM not configured" toast shown if `_getApiConfig()` returns null.

## Follow-ups

- S03 must register EXT-14 through EXT-21 requirements and write E2E Playwright tests covering both actions against the Docker test stack.
- S03 should add auto-context toggle in settings UI and user guide documentation for the full context overlay feature.

## Files Created/Modified

- `extension/background/service-worker.js` — Added `linkToPage` and `addEvidence` message handlers with API calls and step-by-step console logging
- `extension/sidebar/sidebar.js` — `_currentTabUrl`/`_currentTabTitle` tracking, `_linkToPage()` with loading state and toast, conditional Evidence button for Claims, evidence capture prompt flow with `chrome.scripting.executeScript`
- `extension/sidebar/sidebar.css` — `.action-link` solid-border styles, `.action-evidence` amber button styles, `.evidence-prompt` panel styles with title/instructions/preview/actions
- `extension/sidebar/sidebar.html` — Added `#evidence-prompt` container with title, instructions, selected-text preview, Capture/Cancel buttons

## Forward Intelligence

### What the next slice should know
- Both action buttons are fully wired — S03 does not need to touch the action logic, only test it end-to-end and document it.
- The `linkToPage` action creates a `schema:url` edge (predicate is `schema:url`, not a custom predicate). Verify this in the SemPKM Relations panel.
- The `addEvidence` action creates an Evidence object typed as `urn:sempkm:model:research:Evidence` with `res:supports` edge to the Claim. The body contains the selected text and `schema:url` contains the source page URL.
- Settings keys for auto-context (`autoCheckContext`, `contextCheckDelay`, `contextTimeout`) are already defined in `extension/shared/storage.js` from S01 — S03 just needs to wire them in the options page UI.

### What's fragile
- `chrome.scripting.executeScript` for text selection capture — the self-contained function must not reference any outer scope variables (serialization boundary). If someone adds a closure reference, it will silently fail.
- The two-step Evidence API flow has no transaction guarantee — if edge.create fails after object.create succeeds, the Evidence object exists but is unlinked. The orphaned IRI is logged in the error toast, but there's no programmatic recovery.

### Authoritative diagnostics
- Service worker console (`chrome://extensions` → service worker "Inspect") — all `[SemPKM]` prefixed logs show exact step progression for both actions
- Sidebar toast messages — user-visible feedback for success/error on both actions
- Button disabled state — observable indicator that an API call is in-flight

### What assumptions changed
- No assumptions changed. Both tasks completed within plan scope with zero deviations.
