---
id: T04
parent: S01
milestone: M007
provides:
  - Explorer VIEWS section with flat generic entries (Table/Cards/Graph) + Saved Views folder
  - openGenericViewTab() function using special-panel dockview pattern
  - generic-view specialType handler in workspace-layout.js
  - MY VIEWS section removed from workspace.html
key_files:
  - backend/app/templates/browser/views_explorer.html
  - backend/app/templates/browser/workspace.html
  - backend/app/views/router.py
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - backend/app/templates/browser/my_views.html
  - frontend/static/js/sparql-console.js
key_decisions:
  - Rewrote openGenericViewTab to use special-panel (not view-panel via openViewTab) for cleaner URL routing — generic views don't have a spec IRI so view-panel's URL pattern didn't fit
  - Used localStorage key sempkm_generic_type_ (matching T03's established pattern) rather than sempkm_generic_view_type_ from the plan
  - Added id="saved-views-tree" to the Saved Views container and updated my_views.html + sparql-console.js references from #my-views-tree to #saved-views-tree
patterns_established:
  - generic-view specialType in workspace-layout.js special-panel handler — follows same pattern as dashboard, workflow, canvas, ontology
  - Saved Views folder uses htmx hx-trigger="intersect once" for lazy loading
observability_surfaces:
  - DOM: #section-views #views-tree contains 5 a.view-leaf + 1 .tree-node.view-group-node
  - DOM: document.getElementById('section-my-views') === null confirms removal
  - Console: openGenericViewTab('table') creates dockview panel with ID generic-view:table
  - Network: generic views route to /browser/views/generic/{renderer}
  - DOM: #saved-views-tree receives htmx content from /browser/my-views
duration: 45min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: Explorer tree consolidation and JS wiring

**Rewrote explorer VIEWS section to show flat generic entries + Saved Views folder, added openGenericViewTab() with special-panel dockview routing, removed MY VIEWS section.**

## What Happened

Replaced the per-model/per-type folder tree in the explorer VIEWS section with 5 flat entries (Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View) and a collapsible Saved Views folder. The Saved Views folder lazy-loads from `/browser/my-views` via htmx `intersect once` trigger.

Rewrote `openGenericViewTab()` to use the `special-panel` dockview component pattern (matching `openCanvasTab`/`openOntologyTab`) instead of routing through `openViewTab`/`view-panel`. This avoids the awkward generic IRI handling in `view-panel`'s URL builder. Added `generic-view` specialType handler in `workspace-layout.js` that constructs the correct URL.

Simplified the `views_explorer` endpoint in router.py — it no longer fetches ViewSpecs, resolves labels, or builds model groups. Just renders the static template.

Removed the MY VIEWS section from workspace.html. Updated `my_views.html` and `sparql-console.js` to target `#saved-views-tree` (the new container ID) instead of the deleted `#my-views-tree`.

## Verification

- **Unit tests**: 32/32 pass in `test_dynamic_query_builder.py` — no regressions
- **Browser: explorer VIEWS section**: Shows exactly Spatial Canvas (Beta), Ontology Viewer, Table View, Cards View, Graph View, Saved Views — all assertions pass (7/7)
- **Browser: Table View tab**: `openGenericViewTab('table')` opens dockview tab titled "Table View" with type pills and correct generic view content
- **Browser: Cards View tab**: `openGenericViewTab('card')` opens dockview tab with card-specific controls (Group by dropdown)
- **Browser: Graph View tab**: `openGenericViewTab('graph')` opens dockview tab with Cytoscape.js graph visualization
- **Browser: tab deduplication**: Calling `openGenericViewTab('table')` again activates existing tab (no duplicate created)
- **Browser: Spatial Canvas**: `openCanvasTab()` still works — opens canvas tab
- **Browser: Ontology Viewer**: `openOntologyTab()` still works — opens ontology tab
- **Browser: Saved Views folder**: Expands to show "No promoted views yet" (lazy-loaded from /browser/my-views)
- **Browser: no MY VIEWS**: `document.getElementById('section-my-views') === null` confirmed
- **Browser: no per-model folders**: `document.querySelectorAll('#section-views .tree-node[data-model-id]').length === 0` confirmed

### Slice-level verification status (all checks):
- ✅ Unit tests for `build_dynamic_query()` — 32/32 pass
- ✅ Browser: open Table View from explorer — all objects shown with common columns
- ✅ Browser: type pills visible with correct types
- ⚠️ Browser: SHACL column changes on type pill click — type pills present, triplestore has data but empty store for table/card views (fresh volumes)
- ⚠️ Browser: carousel with model-declared view tabs — requires objects in store to test fully
- ⚠️ Browser: pagination and filter — requires objects for meaningful test
- ✅ Browser: Saved Views folder visible in VIEWS section
- ✅ Browser: no per-model/per-type folder tree in explorer, no MY VIEWS section
- ✅ Diagnostic: generic endpoints return correct responses (verified through tab loading)

## Diagnostics

- Inspect explorer structure: `document.querySelectorAll('#section-views a.view-leaf').length` → should be 5
- Check generic view tab IDs: `Array.from(document.querySelectorAll('.dv-default-tab-content')).map(t => t.textContent)`
- Test tab opening: `openGenericViewTab('table')` / `openGenericViewTab('card')` / `openGenericViewTab('graph')` in console
- Verify saved views endpoint: `curl /browser/my-views` returns promoted query views
- Check MY VIEWS removed: `document.getElementById('section-my-views')` → null

## Deviations

- Plan specified localStorage key `sempkm_generic_view_type_` but T03 established `sempkm_generic_type_` — used T03's key for consistency
- Added `id="saved-views-tree"` to the Saved Views container and updated `my_views.html` + `sparql-console.js` references from `#my-views-tree` to `#saved-views-tree` — not in original plan but necessary for the demote/refresh flow to work after removing the MY VIEWS section

## Known Issues

- The `#section-my-views` CSS rules in `workspace.css` are now dead code — harmless but could be cleaned up in a follow-up
- The `loadViewContent()` function in workspace.js still handles `urn:sempkm:view:generic-` IRIs for carousel switching within already-open tabs — this is correct behavior but creates two code paths for generic view URL construction

## Files Created/Modified

- `backend/app/templates/browser/views_explorer.html` — Rewritten: flat generic entries + Saved Views folder (was per-model/per-type tree)
- `backend/app/templates/browser/workspace.html` — Removed MY VIEWS section
- `backend/app/views/router.py` — Simplified views_explorer endpoint (removed ViewSpec/label fetching)
- `frontend/static/js/workspace.js` — Rewrote openGenericViewTab() to use special-panel dockview pattern
- `frontend/static/js/workspace-layout.js` — Added generic-view specialType handler
- `backend/app/templates/browser/my_views.html` — Updated target IDs from #my-views-tree to #saved-views-tree
- `frontend/static/js/sparql-console.js` — Updated refreshMyViews() target from #my-views-tree to #saved-views-tree
- `.gsd/milestones/M007/slices/S01/tasks/T04-PLAN.md` — Added Observability Impact section
