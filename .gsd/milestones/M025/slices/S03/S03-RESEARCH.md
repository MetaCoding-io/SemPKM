# S03: Demo tour + dashboard + CTA banner — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S03 has three deliverables: (1) a 7-step demo-optimized Driver.js tour exposed as `window.startDemoTour()`, (2) a pre-built dashboard created by extending the seed script, and (3) a CTA banner in the workspace visible in demo mode. All three are straightforward applications of existing patterns — the existing `tutorials.js` IIFE provides the exact tour pattern, `DashboardService` handles dashboard creation via SQLAlchemy, and the workspace template already receives a `settings` import that can expose `demo_mode`.

The primary risk is tour step timing — the demo tour must auto-navigate between views (graph, canvas, objects, dashboard) using existing global functions (`openGenericViewTab`, `openCanvasTab`, `openTab`, `openDashboardTab`, `toggleBottomPanel`), and each step must wait for the target DOM element to render before Driver.js positions the popover. The existing tours handle this with lazy element functions (`element: function() { return document.querySelector(...) }`), which is sufficient.

The dashboard must be owned by the demo user (UUID `00000000-0000-0000-0000-000000000000`) so `DashboardService.list_for_user()` returns it. Since nginx blocks POST in demo mode, the dashboard must be created by the seed script running inside the container — same pattern as edge/body creation (D252).

## Recommendation

Three tasks in sequence:

1. **T01: Demo tour in tutorials.js** — Add `window.startDemoTour()` with 7 steps using auto-navigation. Add `demo_mode` to workspace template context. Add auto-start logic (check localStorage flag to avoid re-triggering on every page load).
2. **T02: Pre-built demo dashboard** — Extend `scripts/seed-demo-data.py` with Phase 5 that creates a demo dashboard via direct SQLAlchemy insert (DashboardService), owned by demo user UUID.
3. **T03: CTA banner** — Add a dismissible "Try SemPKM" banner to workspace.html, conditional on `demo_mode` template variable, shown after tour completion or on subsequent visits.

## Implementation Landscape

### Key Files

- `frontend/static/js/tutorials.js` — Add `window.startDemoTour()` following the exact IIFE pattern of `startWelcomeTour()`. Uses `getDriver()` helper (already defined), lazy element functions, and `onNextClick` handlers for auto-navigation between steps. ~120 lines.
- `backend/app/browser/workspace.py` — The `workspace()` endpoint (line 600) already does `from app.config import settings` and builds a `context` dict. Add `"demo_mode": settings.demo_mode` to context dict (~1 line).
- `backend/app/templates/browser/workspace.html` — Two additions: (a) CTA banner div at end of `#editor-pane`, conditional on `{{ demo_mode }}`. (b) Script block at bottom to auto-start demo tour if `demo_mode` and `!localStorage.getItem('sempkm_demo_tour_done')`.
- `scripts/seed-demo-data.py` — Add Phase 5: create demo dashboard via `DashboardService.create()` using `async_session_factory` and the demo user UUID `00000000-0000-0000-0000-000000000000`. Dashboard uses `sidebar-main` layout with a table view-embed block (emits context) and a markdown block (describes the demo).
- `frontend/static/css/workspace.css` — Add `.demo-cta-banner` styles: fixed bottom bar or floating card with install link, dismiss button.
- `backend/app/dashboard/service.py` — No changes needed; `create()` accepts any UUID for `user_id` and doesn't verify it exists in the users table (FK constraint may be an issue — check below).
- `backend/app/dashboard/models.py` — `user_id` has `ForeignKey("users.id", ondelete="CASCADE")`. The demo user UUID is NOT in the users table (it's synthetic). The seed script must either: (a) insert a matching user row first, or (b) insert the dashboard row directly via SQLAlchemy bypassing FK check. Option (a) is cleaner.

### Tour Step Design (7 steps)

1. **Explorer** (`#section-objects`) — "Your knowledge base has 74 objects across 4 Mental Models." Side: right.
2. **Graph View** — Auto-navigate via `openGenericViewTab('graph')`. Element: `.group-editor-area` (lazy). "See your knowledge as an interconnected graph."
3. **Open an Object** — Auto-navigate via `openTab('urn:sempkm:model:basic-pkm:seed-note-architecture', 'Architecture Decision')`. Element: `.group-editor-area` (lazy). "Every object has typed properties and a rich body."
4. **Validation/Lint** — Auto-navigate: `toggleBottomPanel()` + set `panelState.activeTab = 'lint-dashboard'`. Element: `#panel-lint-dashboard` (lazy). "SHACL validation catches data quality issues automatically."
5. **Spatial Canvas** — Auto-navigate via `openCanvasTab()`. Element: `.group-editor-area` (lazy). "Arrange knowledge spatially on an infinite canvas."
6. **Dashboard** — Auto-navigate via `openDashboardTab(dashboardId, 'Demo Dashboard')`. Element: `.group-editor-area` (lazy). "Build dashboards that combine views with cross-filtering."
7. **CTA** — Centered popover (no element). "Ready to try SemPKM? Install with Docker in 2 minutes." Done button. Sets `localStorage.sempkm_demo_tour_done = '1'` and shows CTA banner.

### Navigation Functions Available (all on `window`)

| Function | What it does | Element to wait for |
|----------|-------------|-------------------|
| `openGenericViewTab('graph')` | Opens Graph View tab | `.group-editor-area` content |
| `openTab(iri, label)` | Opens object in editor | `.group-editor-area` content |
| `openCanvasTab()` | Opens Spatial Canvas tab | `.group-editor-area` content |
| `openDashboardTab(id, name)` | Opens dashboard tab | `.group-editor-area` content |
| `toggleBottomPanel()` | Opens/closes bottom panel | `#bottom-panel` |

### Dashboard FK Constraint Issue

`DashboardSpec.user_id` has `ForeignKey("users.id", ondelete="CASCADE")`. The synthetic demo user (UUID `00000000...`) doesn't exist in the `users` table because `_demo_user()` returns a transient SQLAlchemy object never added to any session. The seed script must insert a matching user row before creating the dashboard:

```python
from app.auth.models import User
user = User(id=DEMO_USER_UUID, email="demo@sempkm.app", display_name="Demo Visitor", role="guest")
session.merge(user)  # merge = insert-or-update, idempotent
await session.flush()
# Then create dashboard
```

### Dashboard Block Configuration

The demo dashboard should demonstrate cross-view context filtering (DEMO-05). Recommended layout: `sidebar-main` with:
- **sidebar slot**: `view-embed` block with table view (`urn:sempkm:view:generic-table`), `emits_context: true`
- **main slot**: `view-embed` block with graph view (`urn:sempkm:view:generic-graph`), `listens_to_context: "iri"`

This shows: click a row in the table → graph filters to show that object's connections. Alternative simpler layout: `top-bottom` with a markdown welcome block + a table view-embed.

### Build Order

1. **T01: Demo tour** — The tour is the core user-facing deliverable. Build it first so timing/navigation issues surface early. Requires `demo_mode` in template context (trivial workspace.py change) and auto-start logic in workspace.html.
2. **T02: Demo dashboard** — Extend seed script to create a dashboard. Must run after T01 so the dashboard ID can be hardcoded in the tour step. Alternatively, use a well-known UUID for the dashboard so both can be developed independently.
3. **T03: CTA banner** — Pure frontend work (HTML + CSS). Conditional on `demo_mode`. Shown after tour sets localStorage flag. Lowest risk.

### Verification Approach

1. **Tour works**: Start demo stack → visit `http://localhost:3902/browser/` → tour auto-starts → complete all 7 steps without JS errors → browser console shows no errors → localStorage flag set
2. **Dashboard renders**: After seed script runs with Phase 5 → dashboard visible in DASHBOARDS explorer section → clicking opens dashboard → blocks render with data → context filtering works (click table row → graph updates)
3. **CTA banner**: After tour completes → banner visible at bottom/center of workspace → dismiss button hides it → subsequent visits show banner (localStorage check)
4. **E2E test**: Playwright test against demo stack — navigate to `/browser/`, verify tour trigger element exists, verify dashboard in explorer, verify CTA banner DOM element exists when `demo_mode` is true

## Constraints

- **Dashboard is SQLite, not RDF** (D150) — Must be created via SQLAlchemy/DashboardService, not SPARQL. Seed script needs DB session access.
- **Demo user not in users table** — FK constraint on `dashboard_specs.user_id` requires inserting a user row first. Use `session.merge()` for idempotency.
- **nginx blocks all POST** — Dashboard creation must happen inside the container via direct Python, not HTTP API (same as D252 pattern).
- **Tour auto-navigation depends on dockview** — `openGenericViewTab()`, `openCanvasTab()`, etc. require dockview to be initialized. Tour must wait for workspace load before starting.
- **Driver.js loaded from CDN** — `driver.js@1.4.0` via `cdn.jsdelivr.net`. Already loaded in `base.html` for all pages.

## Common Pitfalls

- **Tour step timing after auto-navigation** — After calling `openGenericViewTab('graph')`, the graph tab content loads asynchronously via htmx. The next tour step must use a lazy element function AND may need a small delay or `htmx:afterSwap` listener to ensure the target element exists before Driver.js tries to position the popover. The existing `startCreateObjectTour()` pattern with `onNextClick` + `htmx:afterSwap` listener is the reference.
- **Dashboard ID must be deterministic** — If the tour step references the dashboard by ID, the seed script must use a well-known UUID (not `uuid4()`). Use `uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")` or similar deterministic value.
- **Lucide icons after tour popover render** — Driver.js popovers are injected into the DOM outside the normal htmx flow. If any tour step description contains Lucide icon markup, `lucide.createIcons()` won't auto-run. Use plain text/HTML in descriptions only.
- **CTA banner z-index** — The workspace has dockview, the bottom panel, the right pane, and ninja-keys modal — all with various z-indices. The CTA banner must sit below modals but above content. Use `z-index: 50` (below ninja-keys at 100+).

## Open Risks

- **Tour fragility on slow connections** — CDN-loaded driver.js could be slow on first visit. The tour auto-start must check that `getDriver()` returns non-null before attempting to start.
- **Cross-view context filtering in demo** — The dashboard context filtering requires clicking a table row to emit a `dashboardContextChanged` event, which re-fetches the dependent block. In read-only mode, htmx GET requests work fine, but the table view must have clickable rows with `data-emits-context` attributes configured correctly in the block config.

## Sources

- `frontend/static/js/tutorials.js` — Existing Driver.js tour infrastructure (Welcome 10-step + Create Object 4-step). IIFE pattern, lazy element functions, htmx-gated auto-navigation.
- `backend/app/browser/workspace.py` — Workspace endpoint with `settings` import at line 611. Template context dict at line 613.
- `backend/app/dashboard/service.py` — `DashboardService.create()` with user_id, name, layout, blocks, description params.
- `backend/app/dashboard/models.py` — `DashboardSpec` with `user_id` FK to `users.id`. Valid layouts: single, sidebar-main, grid-2x2, grid-3, top-bottom. Valid block types: view-embed, markdown, object-embed, create-form, sparql-result, divider.
- `backend/app/auth/dependencies.py` — Demo user UUID: `00000000-0000-0000-0000-000000000000`, role: "guest", email: "demo@sempkm.app".
- `scripts/seed-demo-data.py` — 4-phase seed script with direct module imports (D252). Phase 5 for dashboard follows same container-side pattern.
- `frontend/static/js/workspace.js` — Global navigation functions: `openTab()`, `openGenericViewTab()`, `openCanvasTab()`, `openDashboardTab()`, `toggleBottomPanel()`.
