# S03: Demo tour + dashboard + CTA banner

**Goal:** Anonymous visitor sees the tour auto-start (or clicks a button), completes 7 steps in under 3 minutes covering graph/forms/validation/canvas/dashboard, sees a CTA banner, and the pre-built dashboard filters correctly.
**Demo:** Visit the demo instance → tour auto-starts on first visit → walks through explorer, graph, object, validation, canvas, dashboard, CTA → localStorage flag prevents re-trigger → CTA banner visible after tour → dashboard in explorer renders with real data.

## Must-Haves

- `window.startDemoTour()` in `tutorials.js` with 7 Driver.js steps using auto-navigation (`openGenericViewTab`, `openTab`, `toggleBottomPanel`, `openCanvasTab`, `openDashboardTab`)
- `demo_mode` template variable passed from `workspace.py` to `workspace.html`
- Auto-start logic in workspace template: starts tour on first visit when `demo_mode` is true and `localStorage.sempkm_demo_tour_done` is not set
- Pre-built demo dashboard created by seed script Phase 5 via direct SQLAlchemy insert, owned by demo user UUID `00000000-0000-0000-0000-000000000000`
- Demo user row inserted into `users` table (FK constraint on `dashboard_specs.user_id`)
- Dashboard uses `sidebar-main` layout with a table view-embed (emits context) and a graph view-embed (listens to context) to demonstrate cross-view filtering
- Deterministic dashboard UUID shared between tour JS and seed script
- Dismissible "Try SemPKM" CTA banner in workspace, conditional on `demo_mode`, visible after tour completion or on subsequent visits
- CTA banner styled with proper z-index (below modals, above content)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker demo stack with seed data)
- Human/UAT required: yes (tour pacing, visual appeal)

## Verification

- Start demo Docker stack → navigate to `http://localhost:3902/browser/` → verify tour auto-starts (Driver.js popover visible)
- Complete all 7 tour steps without JS console errors
- After tour completes, `localStorage.getItem('sempkm_demo_tour_done')` returns `'1'`
- CTA banner is visible in the DOM after tour completion
- Refresh page — tour does NOT re-start, CTA banner is visible
- Dashboard exists in DASHBOARDS explorer section
- Opening dashboard shows blocks rendering with data
- `python3 -c "import ast; ast.parse(open('frontend/static/js/tutorials.js').read())"` — valid JS syntax check
- `grep -rn "^<<<<<<< " frontend/ backend/app/templates/ scripts/ --include="*.js" --include="*.html" --include="*.css" --include="*.py"` — zero conflict markers

## Observability / Diagnostics

- Runtime signals: `console.log('[SemPKM] Demo tour started')` and `console.log('[SemPKM] Demo tour completed')` in tutorials.js
- Inspection surfaces: `localStorage.sempkm_demo_tour_done` flag indicates tour completion; `window.startDemoTour()` can be called manually from console
- Failure visibility: Driver.js `console.warn` when tour can't start (getDriver() returns null); seed script Phase 5 prints dashboard creation status

## Integration Closure

- Upstream surfaces consumed: `scripts/seed-demo-data.py` (S02) — extended with Phase 5; `backend/app/config.settings.demo_mode` (S01); `backend/app/auth/dependencies._DEMO_USER_UUID` (S01); `frontend/static/js/workspace.js` global navigation functions
- New wiring introduced: `demo_mode` template variable in workspace context dict; demo tour IIFE in tutorials.js; CTA banner div in workspace.html; Phase 5 dashboard creation in seed script
- What remains before the milestone is truly usable end-to-end: S04 — Caddy SSL, deployment script integration, E2E Playwright test, user guide docs

## Tasks

- [x] **T01: Add demo tour with auto-navigation and demo_mode template context** `est:1h`
  - Why: The tour is the core user-facing deliverable for S03. It must auto-navigate between workspace views (graph, object, validation, canvas, dashboard) using existing global functions, wait for DOM elements to load, and set a localStorage completion flag. The `demo_mode` template variable is needed for conditional auto-start and CTA banner rendering.
  - Files: `frontend/static/js/tutorials.js`, `backend/app/browser/workspace.py`, `backend/app/templates/browser/workspace.html`
  - Do: (1) Add `"demo_mode": settings.demo_mode` to the workspace context dict. (2) Add `window.startDemoTour()` IIFE in tutorials.js following existing tour pattern — 7 steps with lazy element functions and `onNextClick` handlers that call navigation globals + wait for DOM. (3) Add auto-start script block at bottom of workspace.html: if `demo_mode` and no localStorage flag, call `startDemoTour()` after a brief delay for dockview initialization. Use well-known dashboard UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` in tour step 6.
  - Verify: `python3 -c "import ast; ast.parse(open('frontend/static/js/tutorials.js').read())"` passes; `grep "demo_mode" backend/app/browser/workspace.py` shows context variable; `grep "startDemoTour" frontend/static/js/tutorials.js` shows the function; `grep "startDemoTour" backend/app/templates/browser/workspace.html` shows auto-start block
  - Done when: `window.startDemoTour()` is callable and the auto-start block is wired into workspace.html conditional on `demo_mode`

- [x] **T02: Extend seed script with Phase 5 — create demo dashboard and demo user row** `est:45m`
  - Why: The demo dashboard must exist before the tour's step 6 can navigate to it. The dashboard must be owned by the demo user (UUID `00000000-...`), which requires a matching row in the `users` table due to FK constraint. Uses deterministic dashboard UUID so the tour JS can reference it.
  - Files: `scripts/seed-demo-data.py`
  - Do: (1) Import `async_session_factory` from `app.db.session`, `User` from `app.auth.models`, `DashboardSpec` from `app.dashboard.models`. (2) Add Phase 5 after Phase 3 (before verification). (3) First `session.merge()` a User row with the demo user UUID, email `demo@sempkm.app`, display_name `Demo Visitor`, role `guest`. (4) Then check if dashboard with well-known UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` exists; if not, insert a `DashboardSpec` row directly with `sidebar-main` layout, two view-embed blocks (table emitting context + graph listening to context). (5) Update Phase 4 verification to check dashboard count ≥1.
  - Verify: Run seed script inside container — Phase 5 prints dashboard creation status. Re-run confirms idempotent skip. `--verify-only` shows dashboard count.
  - Done when: Seed script creates a dashboard with deterministic UUID owned by demo user, idempotent on re-run

- [x] **T03: Add dismissible CTA banner conditional on demo_mode** `est:30m`
  - Why: The CTA banner is the final conversion element — after the tour shows value, the banner points visitors to installation. Must be conditional on `demo_mode` to avoid showing on non-demo instances.
  - Files: `backend/app/templates/browser/workspace.html`, `frontend/static/css/workspace.css`
  - Do: (1) Add a `.demo-cta-banner` div at the end of the workspace layout (after the main workspace container, before `</div>` closing), conditional on `{{ demo_mode }}`. Contains heading, description, install link (GitHub repo), and dismiss button. (2) Add CSS: fixed bottom positioning, background color with slight transparency, z-index 50 (below ninja-keys 100+), responsive width, dismiss animation. (3) Dismiss button sets `localStorage.sempkm_demo_cta_dismissed = '1'` and hides banner. (4) Show banner logic: visible if `demo_mode` AND (`sempkm_demo_tour_done` is set OR page has been loaded before). (5) Lucide icon sizing per CLAUDE.md rules (CSS not inline, flex-shrink: 0).
  - Verify: `grep "demo-cta-banner" backend/app/templates/browser/workspace.html` shows the banner div; `grep "demo-cta-banner" frontend/static/css/workspace.css` shows styles; banner div is conditional on `demo_mode`
  - Done when: CTA banner renders in demo mode, dismissible via button, respects localStorage dismissal flag

## Files Likely Touched

- `frontend/static/js/tutorials.js` — new `window.startDemoTour()` function
- `backend/app/browser/workspace.py` — `demo_mode` added to template context
- `backend/app/templates/browser/workspace.html` — auto-start script block + CTA banner div
- `frontend/static/css/workspace.css` — `.demo-cta-banner` styles
- `scripts/seed-demo-data.py` — Phase 5: demo user row + dashboard creation
