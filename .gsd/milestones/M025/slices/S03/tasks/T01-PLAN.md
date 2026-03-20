---
estimated_steps: 8
estimated_files: 3
---

# T01: Add demo tour with auto-navigation and demo_mode template context

**Slice:** S03 — Demo tour + dashboard + CTA banner
**Milestone:** M025

## Description

Build the 7-step demo tour as `window.startDemoTour()` in `tutorials.js`, following the exact IIFE pattern established by the existing `startWelcomeTour()` and `startCreateObjectTour()`. The tour auto-navigates between workspace views (graph, object, validation panel, canvas, dashboard) using existing global functions (`openGenericViewTab`, `openTab`, `toggleBottomPanel`, `openCanvasTab`, `openDashboardTab`), with each step using lazy element functions to handle async DOM loading. Also wire `demo_mode` into the workspace template context and add auto-start logic.

**Skills:** No special skills needed. This is vanilla JS following existing patterns in the file.

## Steps

1. **Add `demo_mode` to workspace template context** — In `backend/app/browser/workspace.py`, the `workspace()` function (around line 613) builds a `context` dict. The file already does `from app.config import settings` at line 611. Add `"demo_mode": settings.demo_mode` to the context dict alongside the existing `"base_namespace": settings.base_namespace`.

2. **Define the well-known dashboard UUID constant** — At the top of the new tour definition in `tutorials.js`, define `var DEMO_DASHBOARD_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';` and `var DEMO_DASHBOARD_NAME = 'Demo Dashboard';`. These must match what the seed script creates in T02.

3. **Add `window.startDemoTour()` in tutorials.js** — Inside the existing IIFE (after `startCreateObjectTour`), add a new tour definition. The tour uses the same `getDriver()` helper already defined. 7 steps:

   **Step 1 — Explorer** (`#section-objects`, side: right): "Your knowledge base has objects across 4 Mental Models — browse them by type, hierarchy, or tags." No auto-navigation needed.

   **Step 2 — Graph View**: `onNextClick` calls `openGenericViewTab('graph')`. Lazy element: `function() { return document.querySelector('.group-editor-area'); }`. Wait for DOM via `setTimeout` (500ms) before calling `driverObj.moveNext()`. Side: left. Description: "See your knowledge as an interconnected graph. Nodes represent objects and edges show relationships."

   **Step 3 — Open an Object**: `onNextClick` calls `openTab('urn:sempkm:model:basic-pkm:seed-note-architecture', 'Architecture Decision Records')`. Lazy element: `.group-editor-area`. Same wait pattern. Description: "Every object has typed properties and a rich markdown body. Click the Edit button to modify."

   **Step 4 — Validation/Lint**: `onNextClick` opens bottom panel via `toggleBottomPanel()` then sets the active tab. Lazy element: `function() { return document.querySelector('#bottom-panel'); }`. Description: "SHACL validation catches data quality issues automatically — overdue tasks, stale contacts, and more."

   **Step 5 — Spatial Canvas**: `onNextClick` calls `openCanvasTab()`. Lazy element: `.group-editor-area`. Description: "Arrange knowledge spatially on an infinite canvas. Add embeds, draw connections, resize freely."

   **Step 6 — Dashboard**: `onNextClick` calls `openDashboardTab(DEMO_DASHBOARD_ID, DEMO_DASHBOARD_NAME)`. Lazy element: `.group-editor-area`. Description: "Build dashboards that combine views with cross-filtering. Click a table row to filter the connected graph."

   **Step 7 — CTA (centered, no element)**: Description: "Ready to try SemPKM? Install with Docker in 2 minutes." `showButtons: ['done']`. `onDestroyStarted` callback sets `localStorage.setItem('sempkm_demo_tour_done', '1')` and dispatches a custom event `sempkm:demo-tour-done` (so the CTA banner can listen for it).

4. **Add console logging** — At tour start: `console.log('[SemPKM] Demo tour started');`. On destroy/complete: `console.log('[SemPKM] Demo tour completed');`.

5. **Handle Driver.js availability guard** — Before starting, check `getDriver()` returns non-null. If null, `console.warn('[SemPKM] Driver.js not loaded — cannot start Demo tour');` and return. Same pattern as existing tours.

6. **Add auto-start script block in workspace.html** — At the very end of the `{% block content %}` (after `<ninja-keys></ninja-keys>` but before `{% endblock %}`), add:
   ```html
   {% if demo_mode %}
   <script>
   (function() {
     // Auto-start demo tour on first visit
     if (!localStorage.getItem('sempkm_demo_tour_done')) {
       // Wait for dockview and workspace to initialize
       setTimeout(function() {
         if (typeof window.startDemoTour === 'function') {
           window.startDemoTour();
         }
       }, 1500);
     }
   })();
   </script>
   {% endif %}
   ```
   The 1500ms delay ensures dockview is initialized (it loads after DOMContentLoaded). The Jinja2 `{% if demo_mode %}` ensures this only runs in demo mode.

7. **Add manual tour start button** — Also in the `{% if demo_mode %}` block, add a small floating button (e.g., a help/play icon) in the bottom-right area that calls `startDemoTour()` on click — so visitors who dismissed the tour can restart it. Style it with `position: fixed; bottom: 80px; right: 20px; z-index: 50;`.

8. **Verify syntax** — Run `python3 -c "import ast"` (JS doesn't have ast, but check for obvious syntax errors). Grep for the expected function name and context variable.

## Must-Haves

- [ ] `window.startDemoTour()` defined in `tutorials.js` with 7 steps matching the design
- [ ] Each navigation step uses `onNextClick` + lazy element + delay for async DOM loading
- [ ] `demo_mode` present in workspace.py template context dict
- [ ] Auto-start script block in workspace.html conditional on `{% if demo_mode %}`
- [ ] `localStorage.sempkm_demo_tour_done` set to `'1'` on tour completion
- [ ] Custom event `sempkm:demo-tour-done` dispatched on completion
- [ ] Manual restart button visible in demo mode

## Verification

- `grep -c "startDemoTour" frontend/static/js/tutorials.js` returns at least 2 (definition + export)
- `grep "demo_mode" backend/app/browser/workspace.py` shows the context variable addition
- `grep "startDemoTour" backend/app/templates/browser/workspace.html` shows auto-start block
- `grep "sempkm_demo_tour_done" frontend/static/js/tutorials.js` shows localStorage flag
- No JavaScript syntax errors in tutorials.js (check with `node --check frontend/static/js/tutorials.js` if node available)

## Inputs

- `frontend/static/js/tutorials.js` — Existing file with `startWelcomeTour()` and `startCreateObjectTour()` IIFE pattern. The new tour follows the same structure.
- `backend/app/browser/workspace.py` — Line ~611 does `from app.config import settings`, line ~613 builds context dict. Add one line.
- `backend/app/templates/browser/workspace.html` — Template ending with `<ninja-keys></ninja-keys>{% endblock %}`. Add script block before endblock.
- `backend/app/config.py` — Line 53 has `demo_mode: bool = False`. Already exists, just needs to be referenced.
- Tour step 3 references `urn:sempkm:model:basic-pkm:seed-note-architecture` — this is a seed data IRI from basic-pkm model. Confirm it exists in the demo data by checking the seed script or model seed data.
- Tour step 6 uses dashboard UUID `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` — T02 will create this. If it doesn't exist yet, the tour step will still navigate (openDashboardTab always opens a tab, it just may show empty content).

## Expected Output

- `frontend/static/js/tutorials.js` — Extended with `window.startDemoTour()` (~120 lines) following IIFE pattern
- `backend/app/browser/workspace.py` — One line added to context dict: `"demo_mode": settings.demo_mode`
- `backend/app/templates/browser/workspace.html` — Auto-start script block + manual restart button wrapped in `{% if demo_mode %}`

## Observability Impact

- **New console signals:** `console.log('[SemPKM] Demo tour started')` and `console.log('[SemPKM] Demo tour completed')` emitted at tour lifecycle boundaries; `console.warn('[SemPKM] Driver.js not loaded — cannot start Demo tour')` when the tour cannot start.
- **New localStorage key:** `sempkm_demo_tour_done` — set to `'1'` on tour completion. Inspect via `localStorage.getItem('sempkm_demo_tour_done')` in browser console.
- **New custom DOM event:** `sempkm:demo-tour-done` dispatched on `document` when the tour completes — downstream listeners (CTA banner in T03) react to this.
- **Manual inspection:** Call `window.startDemoTour()` from the browser console to trigger the tour at any time. Delete the localStorage key to reset the auto-start gate.
- **Failure visibility:** If Driver.js isn't loaded, the console.warn fires and the tour silently skips — no error thrown. If workspace globals are missing, the `typeof` guard skips navigation but the tour continues (degraded but non-crashing).
