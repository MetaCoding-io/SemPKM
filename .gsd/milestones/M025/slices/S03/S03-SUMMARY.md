---
id: S03
parent: M025
milestone: M025
provides:
  - window.startDemoTour() — 7-step auto-navigating Driver.js tour for demo mode
  - demo_mode template context variable in workspace.py
  - Auto-start script block and manual restart button in workspace.html
  - Phase 4 in seed-demo-data.py — demo user row + pre-built Demo Dashboard with deterministic UUID
  - Dismissible "Try SemPKM" CTA banner with localStorage persistence
requires:
  - slice: S01
    provides: DEMO_MODE config flag and anonymous access bypass
  - slice: S02
    provides: 30-50 sample objects across 4 Mental Models via seed script
affects:
  - S04
key_files:
  - frontend/static/js/tutorials.js
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/workspace.html
  - frontend/static/css/workspace.css
  - scripts/seed-demo-data.py
key_decisions:
  - "D253: Deterministic UUID (aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee) shared between tour JS and seed script for demo dashboard"
  - "Navigation triggers in preceding step's onNextClick — Driver.js requires DOM to exist before rendering the next popover"
  - "Used spec_iri (not view_iri) in dashboard block config to match codebase convention in dashboard/router.py"
patterns_established:
  - "Demo tour step pattern: onNextClick on step N calls navigation global + 500ms setTimeout + moveNext to prepare step N+1's DOM"
  - "CTA banner show/dismiss pattern: localStorage flag prevents re-showing; custom event (sempkm:demo-tour-done) triggers initial display"
  - "SQLAlchemy merge for idempotent user upsert in seed scripts; select-before-insert for dashboard idempotency"
observability_surfaces:
  - "console.log '[SemPKM] Demo tour started' and '[SemPKM] Demo tour completed'"
  - "console.warn '[SemPKM] Driver.js not loaded' when tour cannot start"
  - "console.log '[SemPKM] CTA banner shown' when banner becomes visible"
  - "localStorage keys: sempkm_demo_tour_done (tour completion), sempkm_demo_cta_dismissed (CTA dismissed)"
  - "window.startDemoTour() callable from browser console for manual trigger"
  - "Seed script Phase 4 prints dashboard creation status; Phase 5 verification table includes Dashboards row"
drill_down_paths:
  - .gsd/milestones/M025/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M025/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M025/slices/S03/tasks/T03-SUMMARY.md
duration: 45m
verification_result: passed
completed_at: 2026-03-20
---

# S03: Demo tour + dashboard + CTA banner

**7-step auto-navigating Driver.js tour with demo dashboard, auto-start on first visit, dismissible CTA banner, and localStorage completion tracking**

## What Happened

Three tasks delivered the demo's user-facing experience layer on top of the S01 anonymous access and S02 sample data:

**T01 — Demo tour (tutorials.js + workspace context).** Added `window.startDemoTour()` to the existing tutorials.js IIFE, following the established Welcome/Create Object tour patterns. The tour has 7 steps that auto-navigate between workspace views using existing globals (`openGenericViewTab`, `openTab`, `toggleBottomPanel`, `openCanvasTab`, `openDashboardTab`), each guarded by `typeof` checks for graceful degradation. Navigation is triggered in the *preceding* step's `onNextClick` callback with a 500ms delay, because Driver.js requires the target DOM element to exist before rendering its popover. Steps cover: Explorer → Graph View → Object View → Validation/Lint → Spatial Canvas → Dashboard → CTA done. On completion, the tour sets `localStorage.sempkm_demo_tour_done = '1'` and dispatches a `sempkm:demo-tour-done` custom event. Added `"demo_mode": settings.demo_mode` to the workspace template context (one line in workspace.py). Added auto-start block and floating restart button to workspace.html, both conditional on `{% if demo_mode %}`.

**T02 — Demo dashboard in seed script.** Extended `scripts/seed-demo-data.py` with Phase 4 that creates the demo infrastructure: (1) `session.merge()` upserts a demo user row (UUID `00000000-...`, email `demo@sempkm.app`, role `guest`) to satisfy the FK constraint on `dashboard_specs.user_id`, then (2) checks for existing dashboard before inserting a `DashboardSpec` with deterministic UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`, `sidebar-main` layout, and two view-embed blocks (table emitting context + graph listening to context) for cross-view filtering demonstration. Renumbered all phases from /4 to /5 total and added dashboard count to Phase 5 verification.

**T03 — CTA banner.** Added a fixed-bottom `.demo-cta-banner` div to workspace.html inside the existing `{% if demo_mode %}` block. Contains rocket icon, installation text, "Get Started" GitHub link, and X dismiss button. Starts hidden; shown via `showDemoCta()` when the `sempkm:demo-tour-done` event fires (first visit) or on page load when `sempkm_demo_tour_done` localStorage is set (return visit). Dismiss sets `sempkm_demo_cta_dismissed` to prevent re-showing. CSS uses slide-up/slide-down `@keyframes` animations, z-index 50 (below ninja-keys 100+, below Driver.js overlay), and all Lucide SVGs follow CLAUDE.md rules (CSS-only sizing, `flex-shrink: 0`).

## Verification

| Check | Status | Evidence |
|-------|--------|----------|
| `startDemoTour` function exists | ✅ | `grep -c "startDemoTour" tutorials.js` → 2 |
| `demo_mode` in workspace context | ✅ | `grep "demo_mode" workspace.py` → context variable present |
| Auto-start wired in workspace.html | ✅ | 3 matches (button onclick, typeof check, function call) |
| localStorage completion flag | ✅ | `localStorage.setItem('sempkm_demo_tour_done', '1')` in tutorials.js |
| Custom event dispatch | ✅ | `new CustomEvent('sempkm:demo-tour-done')` in tutorials.js |
| JS syntax valid | ✅ | `node --check tutorials.js` passes |
| Python syntax valid | ✅ | `python3 -c "import ast; ast.parse(...)"` on seed script passes |
| Dashboard UUID in seed script | ✅ | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` present |
| sidebar-main layout | ✅ | `grep "sidebar-main" seed-demo-data.py` confirms |
| CTA banner in HTML | ✅ | `grep "demo-cta-banner" workspace.html` → div present |
| CTA banner CSS | ✅ | `.demo-cta-banner` styles in workspace.css |
| CTA z-index 50 | ✅ | `grep "z-index: 50" workspace.css` confirms |
| CTA dismiss localStorage | ✅ | `sempkm_demo_cta_dismissed` get/set in template |
| CTA event listener | ✅ | `sempkm:demo-tour-done` addEventListener in template |
| flex-shrink: 0 on SVGs | ✅ | 5 occurrences in CTA CSS section |
| Zero conflict markers | ✅ | `grep -rn "^<<<<<<< "` returns 0 results |
| Restart button present | ✅ | `demo-tour-restart-btn` in workspace.html |

## Requirements Advanced

- DEMO-03 — Sample data browser visibility: the demo dashboard created by Phase 4 of the seed script adds the dashboard to the DASHBOARDS explorer section, making sample data browsable through the cross-view context filtering interface. Full browser-level visibility verification (explorer, graph, table) deferred to S04 E2E test.

## Requirements Validated

- none — DEMO-04/05/06 requirements are not yet registered in REQUIREMENTS.md. They will be registered and validated when S04's E2E test proves the full demo flow end-to-end against a running stack.

## New Requirements Surfaced

- DEMO-04 — Demo tour completes 7 steps without errors (to be registered and validated in S04)
- DEMO-05 — Pre-built demo dashboard renders with cross-view context filtering (to be registered and validated in S04)
- DEMO-06 — CTA banner visible after tour completion with install link (to be registered and validated in S04)

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **onNextClick placement:** Plan placed navigation calls on the step being displayed, but Driver.js semantics require navigation in the *preceding* step's onNextClick (step N prepares step N+1's DOM). Corrected during T01 implementation.
- **spec_iri vs view_iri:** Plan specified `view_iri` as the config key for view-embed blocks, but the actual codebase (`dashboard/router.py`) uses `spec_iri`. Used the correct codebase key in T02.
- **Phase numbering:** Plan vacillated between 5 and 6 total phases. Settled on 5 total which matches the simplest interpretation.
- **JS syntax check method:** Plan specified `python3 -c "import ast; ast.parse(...)"` for tutorials.js, but Python's `ast` module only parses Python. Used `node --check` instead.

## Known Limitations

- Tour and dashboard have not been tested against a live demo stack — all verification is static (code analysis, grep, syntax checks). Full runtime verification requires S04's E2E Playwright test against the Docker demo stack.
- Tour step 6 (Dashboard) references UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` which only exists after the seed script runs Phase 4. Without it, `openDashboardTab` opens a tab but the dashboard may show empty content.
- The restart button uses an inline style for simplicity — could be consolidated into CSS if more demo-mode UI elements are added.
- No user guide docs task in S03 — docs coverage is handled by S04 which writes the deployment guide.

## Follow-ups

- S04 must register DEMO-04/05/06 requirements and validate them via E2E Playwright test
- S04 E2E test must verify: tour auto-starts on fresh anonymous session, all 7 steps complete without JS errors, localStorage flag set, CTA banner visible, dashboard renders with data, context filtering works
- S04 should verify that the demo restart button works correctly

## Files Created/Modified

- `frontend/static/js/tutorials.js` — Added `window.startDemoTour()` (~130 lines) with 7 auto-navigating steps inside existing IIFE
- `backend/app/browser/workspace.py` — Added `"demo_mode": settings.demo_mode` to workspace template context dict
- `backend/app/templates/browser/workspace.html` — Added `{% if demo_mode %}` block with auto-start script, floating restart button, and CTA banner with show/dismiss logic
- `frontend/static/css/workspace.css` — Added `#demo-tour-restart-btn svg` sizing + ~90 lines of `.demo-cta-banner` styles with animations
- `scripts/seed-demo-data.py` — Added Phase 4 (demo user + dashboard creation), dashboard count in Phase 5 verification, renumbered phases

## Forward Intelligence

### What the next slice should know
- The tour, dashboard, and CTA banner are all conditional on `demo_mode` template variable — S04's docker-compose.demo.yml already passes `DEMO_MODE=true` which feeds `settings.demo_mode` which is passed as template context.
- The seed script must be re-run (`docker compose exec api python /app/scripts/seed-demo-data.py`) to create the dashboard after the S03 code changes are deployed. The seed script is idempotent — Phase 4 skips if dashboard already exists.
- The deterministic dashboard UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` is the contract between `tutorials.js` step 6 and `seed-demo-data.py` Phase 4. If either side changes this UUID, the tour's dashboard step breaks silently (opens empty tab instead of dashboard).
- The E2E test should check `localStorage.getItem('sempkm_demo_tour_done')` after tour completion and `document.getElementById('demo-cta-banner').style.display` for CTA visibility.

### What's fragile
- **Tour step timing** — 500ms delays between navigation and `moveNext()` are hardcoded. On slow containers or high-latency networks, DOM elements may not be ready when Driver.js tries to highlight them. The tour degrades (shows popover without highlight) rather than crashes.
- **Dashboard block config** — Uses `spec_iri` key (matching `dashboard/router.py`). If the dashboard rendering code changes this key, the demo dashboard's blocks will render empty.

### Authoritative diagnostics
- `localStorage.sempkm_demo_tour_done` — `'1'` means tour completed; absence means first visit
- `localStorage.sempkm_demo_cta_dismissed` — `'1'` means CTA was dismissed; delete to re-show
- `window.startDemoTour()` — manual trigger from browser console
- `console.log('[SemPKM] Demo tour started/completed')` — tour lifecycle signals
- Seed script Phase 4/5 output — dashboard creation status and verification table

### What assumptions changed
- **onNextClick semantics:** Original assumption was that navigation calls go on the step being displayed. Actual Driver.js behavior requires navigation in the preceding step's callback so the destination view loads before the next popover renders.
- **Dashboard block config key:** Plan assumed `view_iri`, codebase uses `spec_iri`. No functional impact — corrected during implementation.
