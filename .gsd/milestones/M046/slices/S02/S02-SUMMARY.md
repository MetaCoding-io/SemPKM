---
id: S02
parent: M046
milestone: M046
provides:
  - All 5 copilot E2E tests passing on chromium
requires:
  []
affects:
  - S06
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - e2e/tests/46-copilot/copilot.spec.ts
key_decisions:
  - pointer-events:none on .editor-empty is safe because it contains no interactive elements — only instructional text and kbd hints
patterns_established:
  - Belt-and-suspenders pattern for E2E helpers: fix the app-side behavior AND add a test-side guard for the same condition
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M046/slices/S02/tasks/T01-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-29T01:52:08.124Z
blocker_discovered: false
---

# S02: Copilot Bottom Panel — Z-Index Fix

**Three surgical edits fix all 5 copilot E2E failures — auto-open collapsed bottom panel on tab click, block pointer events on editor-empty watermark, and harden the E2E helper.**

## What Happened

All 5 copilot E2E tests were failing because Playwright couldn't deliver clicks to the AI COPILOT tab button. The root cause was a two-part interaction:

1. The bottom panel starts collapsed (height: 0, overflow: hidden), so the tab buttons exist in the DOM but are clipped to zero visual area.
2. The `.editor-empty` watermark overlay (position: absolute, covering the full editor area) sat at the click coordinates and intercepted pointer events before they could reach the tab buttons.

Three targeted edits fixed the problem:

**workspace.js** — The `initPanelTabs()` tab click handler now checks `if (!panelState.open)` and sets `panelState.open = true` before saving state. This is both the E2E fix and a UX improvement — clicking a bottom-panel tab when the panel is collapsed now auto-opens it.

**workspace.css** — Added `pointer-events: none` to the `.editor-empty` rule. The watermark contains only instructional text and kbd hints — no interactive elements — so it should never intercept pointer events. This prevents the watermark from blocking clicks on sibling elements like the bottom panel tabs.

**copilot.spec.ts** — The `openCopilotTab()` helper now includes a `page.evaluate()` pre-check that detects if the bottom panel is collapsed (height < 10px) and calls `window.SemPKM.toggleBottomPanel()` to open it. Belt-and-suspenders — the JS fix handles it app-side, this handles it test-side.

## Verification

All 5 copilot E2E tests pass on chromium (26.3s total):
- basic chat flow — send message and receive streaming response ✓
- SPARQL generation and approval flow ✓
- conversation persistence across page reload ✓
- persona switching ✓
- object creation from chat ✓

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — Auto-open bottom panel when a tab button is clicked while panel is collapsed
- `frontend/static/css/workspace.css` — Added pointer-events:none to .editor-empty watermark overlay
- `e2e/tests/46-copilot/copilot.spec.ts` — openCopilotTab() helper now ensures bottom panel is open before clicking tab button
