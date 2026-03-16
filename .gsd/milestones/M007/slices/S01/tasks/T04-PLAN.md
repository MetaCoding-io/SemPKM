---
estimated_steps: 6
estimated_files: 5
---

# T04: Explorer tree consolidation and JS wiring

**Slice:** S01 — Generic Views & Explorer Consolidation
**Milestone:** M007

## Description

Rewrite the explorer VIEWS section to show flat generic view entries (Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View) plus a collapsible Saved Views folder. Remove the MY VIEWS section from workspace.html. Add `openGenericViewTab()` JS function and wire it through dockview. This completes VIEW-04 and the slice.

## Steps

1. **Add `openGenericViewTab(renderer)` function** to `frontend/static/js/workspace.js`. Pattern follows existing `openCanvasTab()` / `openOntologyTab()`:
   - `tabKey = 'generic-view:' + renderer`
   - Check for existing dockview panel with that ID — activate if found
   - Otherwise, create new panel via `dv.api.addPanel()` with `component: 'special-panel'`, `params: { specialType: 'generic-view', renderer: renderer, isView: false, isSpecial: true }`, title = renderer display name ("Table View" / "Cards View" / "Graph View")
   - Read stored type from `localStorage.getItem('sempkm_generic_view_type_' + renderer)` and pass as `selectedType` param
   - Expose on window: `window.openGenericViewTab = openGenericViewTab;`

2. **Update `workspace-layout.js` special-panel handler** to handle `generic-view` specialType. In the `init` function's specialType dispatch:
   ```javascript
   if (st === 'generic-view') {
     var renderer = params.params.renderer || 'table';
     var selectedType = params.params.selectedType || '';
     url = '/browser/views/generic/' + renderer + (selectedType ? '?type=' + encodeURIComponent(selectedType) : '');
   }
   ```

3. **Rewrite `views_explorer.html`**. Replace the entire per-model/per-type folder tree with:
   - Spatial Canvas entry (keep existing onclick `openCanvasTab()`)
   - Ontology Viewer entry (keep existing onclick `openOntologyTab()`)
   - Table View entry: `<a class="tree-leaf view-leaf" href="#" onclick="openGenericViewTab('table'); return false;"><span class="tree-leaf-icon">&#9638;</span><span class="tree-leaf-label">Table View</span></a>`
   - Cards View entry: same pattern with `'card'` and cards icon `&#9641;`
   - Graph View entry: same pattern with `'graph'` and graph icon `&#9672;`
   - Collapsible "Saved Views" folder: a `.tree-node` div with toggle, containing a `.view-group-children` div that loads saved views via htmx: `hx-get="/browser/my-views"`, `hx-trigger="click once"`, `hx-target` pointing to the children container. This reuses the existing `/browser/my-views` endpoint unchanged.
   - The template no longer needs `groups` context variable — remove the model-grouping logic from the `views_explorer` endpoint in router.py. The endpoint can simply pass through or return minimal context.

4. **Simplify `views_explorer` endpoint** in `backend/app/views/router.py`. The current endpoint fetches all ViewSpecs, groups by model, resolves labels. With the new template, it needs far less — just render the template (Saved Views loads lazily). Remove or simplify the ViewSpec fetching. Keep the endpoint at `GET /browser/views/explorer` for backward compatibility. Context can be minimal: `{"request": request}`.

5. **Remove MY VIEWS section** from `backend/app/templates/browser/workspace.html`. Delete the entire `<div class="explorer-section" id="section-my-views" ...>` block (the one with `hx-get="/browser/my-views"` and title "MY VIEWS"). The `/browser/my-views` endpoint stays — it's now consumed by the Saved Views folder inside views_explorer.html.

6. **Browser verification** (requires Docker):
   - Start Docker stack
   - Open workspace
   - Verify explorer VIEWS section shows: Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View, Saved Views folder
   - Click Table View → generic table opens in a tab
   - Click Cards View → generic cards view opens
   - Click Graph View → generic graph view opens
   - Expand Saved Views → shows promoted query views (if any)
   - Verify NO per-model/per-type folder tree
   - Verify NO "MY VIEWS" section in sidebar
   - Verify existing Spatial Canvas and Ontology Viewer links still work
   - Verify type pills work in opened generic views (from T03)
   - Verify full flow: open Table View → click type pill → columns change → carousel appears → click model view → model view loads

## Must-Haves

- [ ] Explorer VIEWS section shows exactly: Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View, Saved Views folder
- [ ] No per-model/per-type folder tree in explorer
- [ ] MY VIEWS section removed from workspace.html
- [ ] `openGenericViewTab()` opens correct dockview tab
- [ ] `generic-view` specialType handled in workspace-layout.js
- [ ] Saved Views folder lazy-loads from existing `/browser/my-views` endpoint
- [ ] Existing Spatial Canvas and Ontology Viewer links unaffected

## Verification

- Browser: explorer VIEWS section shows 5 fixed entries + Saved Views folder
- Browser: clicking Table View opens generic table tab with all objects
- Browser: no per-model/per-type folders in explorer
- Browser: no MY VIEWS section in sidebar
- Browser: Saved Views folder expands and shows promoted queries
- Browser: full end-to-end flow (Table View → type pill → SHACL columns → carousel → model view)
- `cd backend && python -m pytest tests/test_dynamic_query_builder.py -v` — no regression

## Inputs

- `backend/app/templates/browser/views_explorer.html` — current per-model template (to be rewritten)
- `backend/app/templates/browser/workspace.html` — contains MY VIEWS section to remove
- `backend/app/views/router.py` — current `views_explorer` endpoint (to be simplified)
- `frontend/static/js/workspace.js` — T03 updated `loadViewContent()`, need to add `openGenericViewTab()`
- `frontend/static/js/workspace-layout.js` — special-panel init handler (needs generic-view case)
- T01-T03 all complete: dynamic query builder, generic endpoints, type pills, carousel integration all working

## Expected Output

- `backend/app/templates/browser/views_explorer.html` — rewritten with flat entries + Saved Views folder
- `backend/app/templates/browser/workspace.html` — MY VIEWS section removed
- `backend/app/views/router.py` — `views_explorer` endpoint simplified
- `frontend/static/js/workspace.js` — `openGenericViewTab()` added and exposed on window

## Observability Impact

- **Explorer VIEWS section**: Inspect `#section-views #views-tree` DOM — should contain exactly 5 `a.view-leaf` elements + 1 `.tree-node.view-group-node` (Saved Views folder)
- **Generic view tab opening**: `openGenericViewTab('table')` in browser console → dockview panel created with `generic-view:table` ID, visible in `document.querySelectorAll('.dv-default-tab-content')` list
- **Saved Views lazy loading**: `#saved-views-tree` container receives htmx content from `/browser/my-views` on `intersect` trigger — check Network tab for the request
- **MY VIEWS removal**: `document.getElementById('section-my-views') === null` confirms successful removal
- **special-panel routing**: Network requests for generic views go to `/browser/views/generic/{renderer}` — inspect via browser Network tab
- `frontend/static/js/workspace-layout.js` — `generic-view` specialType handler added
