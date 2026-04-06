---
id: S02
parent: M055
milestone: M055
provides:
  - reopenClosedTab() on window.SemPKM for programmatic closed-tab recovery
  - Ctrl+Shift+T keyboard shortcut for closed-tab recovery
  - Command palette 'Reopen Closed Tab' entry
requires:
  []
affects:
  []
key_files:
  - frontend/static/js/workspace-layout.js
  - frontend/static/js/workspace.js
  - e2e/tests/55-browser-history/closed-tab.spec.ts
key_decisions:
  - Module-private _closedTabStack — not exposed on window, accessed only via reopenClosedTab() closure
  - Component type inferred from params flags as fallback during panel disposal
  - Skip-and-try-next when closed tab already manually reopened
  - Multi-tab E2E test uses JS API instead of keyboard shortcut for timing reliability
patterns_established:
  - Closed-tab stack pattern: capture metadata in onDidRemovePanel, dispatch to typed opener in reopenClosedTab()
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M055/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M055/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T06:58:26.110Z
blocker_discovered: false
---

# S02: Closed Tab Recovery

**Added closed-tab recovery with a 20-entry LIFO stack, Ctrl+Shift+T keyboard shortcut, and command palette entry — supports all 18+ tab types with skip-already-open logic.**

## What Happened

Implemented closed-tab recovery in two tasks. T01 added the core feature: a module-private `_closedTabStack` array in workspace-layout.js captures panel metadata (id, component type, params, label) in the `onDidRemovePanel` handler before `_tabMeta` cleanup. The `reopenClosedTab()` function pops from the LIFO stack and dispatches to the correct opener based on component type — covering object-editor, view-panel, special-panel (docs, canvas, settings), dashboard, workflow, and app tabs. The stack is capped at 20 entries. If a popped tab is already open (user manually reopened it), the function skips it and tries the next entry. Ctrl+Shift+T keyboard shortcut and "Reopen Closed Tab" command palette entry were added in workspace.js.

T02 added 4 Playwright E2E tests in `e2e/tests/55-browser-history/closed-tab.spec.ts`: single close-and-reopen, multi-tab LIFO ordering, empty-stack no-op safety, and skip-already-open behavior. All 8 runs pass (4 tests × Chromium + Firefox). The multi-tab test uses the JS API directly (`reopenClosedTab()`) rather than rapid Ctrl+Shift+T presses for timing reliability.

## Verification

All 8 E2E tests pass (4 tests × Chromium + Firefox) covering: (1) close object tab → Ctrl+Shift+T reopens with same IRI, (2) close 3 tabs → reopenClosedTab() 3 times restores in LIFO order, (3) Ctrl+Shift+T on empty stack = safe no-op with no console errors, (4) close 2 tabs → manually reopen one → Ctrl+Shift+T skips already-open and reopens the other. Full 55-browser-history suite of 20 tests passes with no regressions.

## Requirements Advanced

None.

## Requirements Validated

- R014 — 8 E2E tests pass (4 cases × Chromium + Firefox): single close → Ctrl+Shift+T reopens, multi-tab LIFO, empty-stack no-op, skip-already-open.
- R017 — Duplicate of R014 — same 8 E2E tests validate both requirements.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Multi-tab E2E test uses JS API instead of keyboard shortcut for timing reliability — rapid sequential Ctrl+Shift+T has race conditions in Playwright.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/js/workspace-layout.js` — Added _closedTabStack array, metadata capture in onDidRemovePanel, reopenClosedTab() function with dispatch to all tab types, exported on window.SemPKM
- `frontend/static/js/workspace.js` — Added Ctrl+Shift+T keyboard shortcut in initKeyboardShortcuts(), added 'Reopen Closed Tab' command palette entry in initCommandPalette()
- `e2e/tests/55-browser-history/closed-tab.spec.ts` — 4 E2E tests: single reopen, multi-tab LIFO, empty-stack no-op, skip-already-open
