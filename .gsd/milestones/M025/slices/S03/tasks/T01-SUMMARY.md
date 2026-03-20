---
id: T01
parent: S03
milestone: M025
provides:
  - window.startDemoTour() — 7-step auto-navigating Driver.js tour for demo mode
  - demo_mode template context variable in workspace.py
  - Auto-start script block and manual restart button in workspace.html
key_files:
  - frontend/static/js/tutorials.js
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/workspace.html
  - frontend/static/css/workspace.css
key_decisions:
  - Navigation triggers moved to onNextClick of the *preceding* step so the destination view is loaded before Driver.js renders the next popover
patterns_established:
  - Demo tour step pattern: onNextClick on step N calls navigation global + 500ms setTimeout + moveNext to prepare step N+1's DOM
observability_surfaces:
  - console.log '[SemPKM] Demo tour started' and '[SemPKM] Demo tour completed'
  - console.warn '[SemPKM] Driver.js not loaded' when tour cannot start
  - localStorage key 'sempkm_demo_tour_done' set to '1' on completion
  - Custom DOM event 'sempkm:demo-tour-done' dispatched on document
  - window.startDemoTour() callable from browser console
duration: 20m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Add demo tour with auto-navigation and demo_mode template context

**Added 7-step auto-navigating demo tour (startDemoTour) with demo_mode template context, auto-start on first visit, and manual restart button**

## What Happened

Built `window.startDemoTour()` in `tutorials.js` following the established IIFE pattern from the existing Welcome and Create Object tours. The tour has 7 steps that auto-navigate between workspace views:

1. **Explorer** — highlights #section-objects, onNextClick opens graph view
2. **Graph View** — lazy .group-editor-area element, onNextClick opens a seed note
3. **Object View** — shows typed properties, onNextClick opens bottom panel
4. **Validation/Lint** — lazy #bottom-panel element, onNextClick opens canvas
5. **Spatial Canvas** — lazy .group-editor-area, onNextClick opens demo dashboard
6. **Dashboard** — shows cross-filtering description
7. **CTA** — centered popover with done button, links to GitHub

Each navigation step uses the existing workspace globals (`openGenericViewTab`, `openTab`, `toggleBottomPanel`, `openCanvasTab`, `openDashboardTab`) via `typeof` guards so the tour degrades gracefully if a function isn't available. Navigation is triggered in the *preceding* step's `onNextClick` with a 500ms setTimeout to allow DOM loading before Driver.js renders the next popover.

On completion (via `onDestroyStarted`), the tour sets `localStorage.sempkm_demo_tour_done = '1'` and dispatches a `sempkm:demo-tour-done` custom event for the CTA banner (T03) to react to.

Added `"demo_mode": settings.demo_mode` to the workspace template context dict (one line), and added two blocks to workspace.html conditional on `{% if demo_mode %}`: an auto-start script that fires `startDemoTour()` after 1500ms on first visit, and a floating play-circle button (bottom-right, z-index 50) for manual restart.

## Verification

- `grep -c "startDemoTour" tutorials.js` → 2 (JSDoc header + function definition)
- `grep "demo_mode" workspace.py` → context variable present
- `grep "startDemoTour" workspace.html` → 3 matches (button onclick, typeof check, function call)
- `grep "sempkm_demo_tour_done" tutorials.js` → localStorage.setItem confirmed
- `grep "sempkm:demo-tour-done" tutorials.js` → CustomEvent dispatch confirmed
- `node --check tutorials.js` → passes (no syntax errors)
- `grep "^<<<<<<< "` → 0 conflict markers
- Restart button present in template with correct ID

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "startDemoTour" frontend/static/js/tutorials.js` | 0 (count=2) | ✅ pass | <1s |
| 2 | `grep "demo_mode" backend/app/browser/workspace.py` | 0 | ✅ pass | <1s |
| 3 | `grep "startDemoTour" backend/app/templates/browser/workspace.html` | 0 (3 matches) | ✅ pass | <1s |
| 4 | `grep "sempkm_demo_tour_done" frontend/static/js/tutorials.js` | 0 | ✅ pass | <1s |
| 5 | `node --check frontend/static/js/tutorials.js` | 0 | ✅ pass | <1s |
| 6 | `grep -rn "^<<<<<<< " (conflict markers)` | 0 (0 markers) | ✅ pass | <1s |
| 7 | `grep "demo-tour-restart-btn" workspace.html` | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T01 is first of 3 tasks)

| Check | Status | Notes |
|-------|--------|-------|
| Tour auto-starts on first visit | ⏳ | Needs running demo stack (T02 seeds data) |
| Complete 7 steps without JS errors | ⏳ | Needs running demo stack |
| localStorage flag set after completion | ✅ | Code confirmed: `localStorage.setItem('sempkm_demo_tour_done', '1')` |
| CTA banner visible after tour | ⏳ | T03 implements CTA banner |
| Refresh → tour does NOT re-start | ✅ | Auto-start checks `localStorage.getItem('sempkm_demo_tour_done')` |
| Dashboard exists in explorer | ⏳ | T02 creates dashboard via seed script |
| JS syntax check | ✅ | `node --check` passes |
| Zero conflict markers | ✅ | Confirmed 0 markers |

## Diagnostics

- **Console signals:** `[SemPKM] Demo tour started` and `[SemPKM] Demo tour completed` logged at tour boundaries
- **Manual trigger:** `window.startDemoTour()` from browser console
- **Reset tour:** Delete `localStorage.removeItem('sempkm_demo_tour_done')` then refresh
- **Driver.js missing:** `console.warn('[SemPKM] Driver.js not loaded — cannot start Demo tour')` fires if getDriver() returns null
- **Navigation guard:** Each navigation global is checked with `typeof` — tour continues in degraded mode if a function is missing

## Deviations

- Restructured navigation triggers: the plan placed `onNextClick` navigation calls on the step being *displayed*, but Driver.js semantics require the navigation to happen in the *preceding* step's `onNextClick` callback (step N prepares step N+1's DOM). This was corrected during implementation.
- Added `onPrevClick` handlers on navigation steps so backward navigation works correctly (Driver.js requires explicit `movePrevious()` calls when `onNextClick` is overridden).

## Known Issues

- Tour step 6 (Dashboard) references UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` which will only exist after T02 runs the seed script. Without it, `openDashboardTab` still opens a tab but the dashboard may show empty content.
- The restart button uses an inline style for simplicity. If more demo-mode UI is added in T03, consider consolidating styles into CSS classes.

## Files Created/Modified

- `frontend/static/js/tutorials.js` — Added `window.startDemoTour()` (~130 lines) with 7 auto-navigating steps inside existing IIFE
- `backend/app/browser/workspace.py` — Added `"demo_mode": settings.demo_mode` to workspace template context dict
- `backend/app/templates/browser/workspace.html` — Added `{% if demo_mode %}` block with auto-start script and floating restart button
- `frontend/static/css/workspace.css` — Added `#demo-tour-restart-btn svg` sizing rules (flex-shrink: 0 per CLAUDE.md)
- `.gsd/milestones/M025/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
