---
id: S01
parent: M055
milestone: M055
provides:
  - ?tab= URL sync — all workspace tab types update the URL on activation
  - Browser back/forward navigation between tabs
  - Deep-link support — ?tab=<id> opens correct tab on page load
  - 6 E2E tests in e2e/tests/55-browser-history/history.spec.ts
requires:
  []
affects:
  []
key_files:
  - frontend/static/js/workspace-layout.js
  - frontend/static/js/workspace.js
  - e2e/tests/55-browser-history/history.spec.ts
key_decisions:
  - Two guard flags (_historyReady, _navigatingFromHistory) prevent history pollution during layout restore and popstate handling
  - History state shape is { tabId: string } — minimal, sufficient for panel lookup
  - replaceState for initial load, pushState for user-driven tab switches
  - Deep-link ?tab= captured before initWorkspaceLayout because replaceState inside init overwrites URL params
  - Deep-link supports all 9 tab ID formats via prefix dispatch (IRIs, special:*, view:*, etc.)
patterns_established:
  - History API pushState/popstate wiring pattern with guard flags for dockview integration
  - Deep-link ?tab= capture-before-init pattern for workspace URL processing
  - page_settle E2E helper (500ms + networkidle) for async History API operations
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M055/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M055/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M055/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T06:31:37.410Z
blocker_discovered: false
---

# S01: URL Sync & History Navigation

**Wired History API to dockview panel activation — URL reflects active tab via ?tab=, back/forward navigates tab history, and deep-link URLs open correct tabs on page load.**

## What Happened

Three tasks delivered the full URL sync feature. T01 wired pushState/popstate to dockview's onDidActivePanelChange handler with two guard flags: `_historyReady` (suppresses pushState during layout restore to prevent history pollution) and `_navigatingFromHistory` (suppresses pushState during popstate-triggered panel activation to prevent infinite loops). Initial state uses replaceState to avoid double-entry. Ephemeral `__new-object-` tabs are excluded from history. Stale entries from closed panels trigger replaceState cleanup instead of errors. Existing `?panel=sparql` handling was fixed to use surgical `searchParams.delete` instead of stripping all params — preserving `?tab=` when both are present.

T02 added the deep-link handler. The key challenge: `initWorkspaceLayout()` includes a replaceState that overwrites URL params with the restored layout's active panel. Solution: capture `?tab=` before calling init, then process it after layout restore completes. The handler supports all 9 tab ID formats (object IRIs, special:*, view:*, generic-view:*, dashboard:*, workflow:*, catalog:*, app-page:*, app-view:*) via prefix dispatch. If the panel was already restored from saved layout, it calls setActive() instead of opening a duplicate.

T03 wrote 6 Playwright E2E tests covering URL update on tab open, tab switch URL sync, back/forward navigation, deep-link via ?tab=, stale entry cleanup after tab close, and ephemeral tab exclusion. Tests use `page.evaluate` for panel activation (more reliable than UI clicks) and a `page_settle` helper (500ms + waitForIdle) for async pushState/popstate completion. All 6 pass on both Chromium and Firefox.

## Verification

6 Playwright E2E tests pass on Chromium (16.1s) and Firefox. Tests cover: (1) URL update on tab open, (2) tab switch URL sync, (3) back/forward navigation, (4) deep-link via ?tab= query param, (5) stale entry cleanup after closing a tab, (6) ephemeral tabs excluded from history. Source code verified: pushState/popstate/replaceState wiring in workspace-layout.js, deep-link handler in workspace.js.

## Requirements Advanced

None.

## Requirements Validated

- R015 — E2E tests 1-3 prove pushState on tab open, URL update on switch, and back/forward navigation. 6/6 pass on Chromium and Firefox.
- R016 — E2E test 4 navigates to /browser/?tab=<iri> and confirms correct object tab opens on page load. Manual verification: deep-link works, refresh preserves tab.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T01 added `_historyReady` guard flag (not in plan) to prevent layout restore from polluting history. T01 fixed existing `?panel=sparql` URL cleanup in workspace.js to preserve `?tab=` — a necessary compatibility fix not in the plan. T02 had to capture `?tab=` before initWorkspaceLayout() instead of after, because replaceState inside init overwrites the URL. T03 did not modify selectors.ts — tests use JS APIs and URL assertions, not CSS selectors.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/js/workspace-layout.js` — Added pushState on panel activation, popstate listener for back/forward, replaceState for initial state, _historyReady and _navigatingFromHistory guard flags
- `frontend/static/js/workspace.js` — Added deep-link handler reading ?tab= before init, supports 9 tab ID formats. Fixed ?panel=sparql cleanup to preserve ?tab=.
- `e2e/tests/55-browser-history/history.spec.ts` — 6 Playwright E2E tests covering URL sync, back/forward, deep-link, stale cleanup, ephemeral exclusion
