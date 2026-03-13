---
estimated_steps: 6
estimated_files: 8
---

# T03: Build ABox Browser and RBox Legend with ontology viewer panel

**Slice:** S07 — Ontology Viewer & Gist Foundation
**Milestone:** M003

## Description

Complete the ontology viewer by adding the ABox Browser (instances grouped by type with counts), the RBox Legend (property reference table), and the main ontology viewer page with three-tab layout. Wire the viewer into the workspace as a `special-panel` dockview tab accessible via command palette and sidebar. This task connects all ontology routes into a usable workspace experience.

## Steps

1. **Add ABox query methods to OntologyService** — In `backend/app/ontology/service.py`:
   - `async get_type_counts(self) -> list[dict]` — batched VALUES query across `urn:sempkm:current` and `urn:sempkm:inferred`:
     ```sparql
     SELECT ?type (COUNT(DISTINCT ?instance) AS ?count) WHERE {
       FROM <urn:sempkm:current>
       FROM <urn:sempkm:inferred>
       ?instance a ?type .
       VALUES ?type { <iri1> <iri2> ... }
     }
     GROUP BY ?type
     ```
     Get the type IRI list from `get_root_classes()` + `get_subclasses()` recursively, or simpler: query all `owl:Class` IRIs from ontology graphs, then count instances. Only return types with count > 0 (exclude gist classes with zero instances to reduce clutter).
   - `async get_instances(self, class_iri: str, limit: int = 50) -> list[dict]` — query instances of the given class from current+inferred graphs, resolve labels, return `[{iri, label, type_icon}]`
   
2. **Add RBox query methods to OntologyService** — In `backend/app/ontology/service.py`:
   - `async get_properties(self) -> list[dict]` — query `owl:ObjectProperty` and `owl:DatatypeProperty` from all ontology graphs (using FROM clause aggregation, same as TBox). Return `[{iri, label, prop_type, domain_iri, domain_label, range_iri, range_label}]`. Use OPTIONAL for domain/range. Resolve labels for domain/range IRIs. Group result as `{object_properties: [...], datatype_properties: [...]}`.
   - Reuse the pattern from `ModelService._query_properties()` but extend across all ontology graphs instead of a single graph.

3. **Add ABox and RBox routes to ontology_router** — In `backend/app/ontology/router.py`:
   - `GET /browser/ontology/abox` — calls `get_type_counts()`, renders `abox_browser.html`
   - `GET /browser/ontology/abox/instances?class={iri}` — calls `get_instances(iri)`, renders `abox_instances.html`
   - `GET /browser/ontology/rbox` — calls `get_properties()`, renders `rbox_legend.html`

4. **Create ontology viewer main page and tab templates** — 
   - `backend/app/templates/browser/ontology/ontology_page.html` — main container with three-tab layout:
     - Tab header bar with "TBox", "ABox", "RBox" tabs (htmx-driven tab switching)
     - TBox tab: `hx-get="/browser/ontology/tbox"` with `hx-trigger="load"` — loads immediately
     - ABox tab: `hx-get="/browser/ontology/abox"` with `hx-trigger="click"` — lazy load on click
     - RBox tab: `hx-get="/browser/ontology/rbox"` with `hx-trigger="click"` — lazy load on click
   - `GET /browser/ontology` route returns `ontology_page.html` — this is what `special-panel` fetches
   - `abox_browser.html` — type list with counts, each type clickable to show instances:
     - `hx-get="/browser/ontology/abox/instances?class={{ type.iri | urlencode }}"` on click
     - Badge with instance count
     - Type label and icon
   - `abox_instances.html` — instance list with labels, each clickable via `openTab(iri, label)`
   - `rbox_legend.html` — two-section table: Object Properties and Datatype Properties, columns: Name, Domain, Range

5. **Wire ontology viewer into workspace** — Edit `frontend/static/js/workspace.js`:
   - Add `openOntologyTab()` following `openCanvasTab()` pattern:
     ```javascript
     function openOntologyTab() {
       var tabKey = 'special:ontology';
       // ... same pattern: check existing, add panel with special-panel component
       params: { specialType: 'ontology', isView: false, isSpecial: true }
     }
     window.openOntologyTab = openOntologyTab;
     ```
   - Add command palette entry: `{ id: 'nav-ontology', title: 'Open: Ontology Viewer', handler: function() { openOntologyTab(); } }`
   - Add keyboard shortcut if appropriate (optional — command palette access is sufficient)

6. **Add CSS for ontology viewer** — Edit `frontend/static/css/workspace.css`:
   - `.ontology-tabs` — tab header bar styling
   - `.ontology-tab-content` — content area styling
   - `.tbox-tree` — reuse existing tree-node styles where possible
   - `.abox-type-row` — type entry with count badge
   - `.rbox-table` — property table styling
   - `.source-badge` — small muted badge for class source (gist, basic-pkm, etc.)
   - Follow existing workspace panel styling patterns (canvas_page, vfs_browser)

## Must-Haves

- [ ] ABox type counts query using batched VALUES across current+inferred graphs
- [ ] ABox instance list with labels and click-to-open via `openTab()`
- [ ] RBox property table with object/datatype split, domain, and range columns
- [ ] Three-tab ontology viewer page (`/browser/ontology`)
- [ ] `openOntologyTab()` in workspace.js following special-panel pattern
- [ ] Command palette entry "Open: Ontology Viewer"
- [ ] CSS styles for ontology viewer (tabs, tree nodes, type rows, property table)
- [ ] Lazy tab loading (ABox and RBox only load on click, TBox loads immediately)

## Verification

- Start Docker stack → open browser → command palette → type "Ontology" → select "Open: Ontology Viewer"
- TBox tab shows gist class hierarchy tree with expandable nodes
- ABox tab shows types with instance counts (e.g., "Note (5)", "Project (3)")
- Click a type in ABox → instance list appears → click instance → opens in workspace tab
- RBox tab shows property table with domain/range columns

## Observability Impact

- Signals added/changed: `logger.debug("ABox: %d types with instances")`, `logger.debug("RBox: %d properties")`, timing logs for each query
- How a future agent inspects this: open ontology viewer in browser; curl individual endpoints; check SPARQL queries in DEBUG logs
- Failure state exposed: each tab section shows error message on SPARQL failure rather than blank content; ABox shows "No instances found" for types with zero count

## Inputs

- `backend/app/ontology/service.py` — from T01+T02, has gist loading + TBox queries
- `backend/app/ontology/router.py` — from T02, has TBox routes
- `backend/app/services/models.py:_query_properties()` — property query pattern for RBox
- `backend/app/services/models.py:get_type_analytics()` — VALUES-based instance count query pattern
- `frontend/static/js/workspace.js:openCanvasTab()` — special-panel tab opening pattern
- `frontend/static/css/workspace.css` — existing panel styling patterns
- `backend/app/templates/browser/ontology/tbox_tree.html` — from T02

## Expected Output

- `backend/app/ontology/service.py` — extended with ABox and RBox query methods
- `backend/app/ontology/router.py` — extended with ABox, RBox, and main page routes
- `backend/app/templates/browser/ontology/ontology_page.html` — new three-tab layout
- `backend/app/templates/browser/ontology/abox_browser.html` — new type counts view
- `backend/app/templates/browser/ontology/abox_instances.html` — new instance list view
- `backend/app/templates/browser/ontology/rbox_legend.html` — new property table view
- `frontend/static/js/workspace.js` — modified with openOntologyTab + command palette entry
- `frontend/static/css/workspace.css` — modified with ontology viewer styles
