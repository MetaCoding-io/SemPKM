# S05 Research: SPARQL + Ontology + Graph + Full-Height Polish

**Date:** 2026-03-21  
**Depth:** Targeted — established patterns, known code, no unfamiliar technology

## Summary

S05 is a collection of 8 independent polish tasks across 4 subsystems: SPARQL console (IRI pills, prefix shortening, graph viz tab), ontology viewer (property tooltips), admin model graph (full-size + edge tooltips), and cross-view polish (full-height CSS, graph popover z-index). All tasks use established patterns and existing dependencies (Cytoscape.js, htmx, Jinja2 templates). The only novel piece is the SPARQL graph visualization tab (SPARQL-09), which reuses the existing Cytoscape.js `initGraph`-style pattern.

## Requirement Coverage

| Req ID | Description | Priority | Approach |
|--------|-------------|----------|----------|
| SPARQL-10 | Fix IRI pills falling through to plain spans | Must-have | Backend: widen `_is_object_iri()` to also match `urn:sempkm:model:*` class/property IRIs. Frontend: no change needed — `renderCell()` already renders enriched IRIs as pills |
| SPARQL-11 | Dynamic model prefix shortening in `shortenUri()` | Should-have | Replace hardcoded prefix map in `shortenUri()` with `prefixCache` (already fetched from `/api/sparql/vocabulary`) |
| SPARQL-09 | Graph visualization tab for triple-pattern SPARQL results | Should-have | Add tab switcher (Table / Graph) below results info. Detect triple-pattern vars (s/p/o or subject/predicate/object). Render Cytoscape.js graph inline |
| ONTO-04 | Property description tooltips in TBox detail | Should-have | Add OPTIONAL `rdfs:comment`/`skos:definition` to property query in `get_class_detail()`. Render as `title` attr on property label in `tbox_detail.html` |
| ONTO-05 | Admin model graph full-width/full-height | Should-have | CSS: change `.ontology-cy-container` from `min-height: 600px` to `height: calc(100vh - 200px)` or flexbox fill. Make `.ontology-diagram-panel` a flex column |
| ONTO-06 | Edge tooltips in admin model graph | Nice-to-have | Backend: pass `description` in edge data from property detail. Frontend: add edge hover handler (existing graph.js pattern) to `model_ontology_diagram.html` |
| VIEW-13 | All views use 100% available height | Must-have | CSS flex audit on view template containers. The `.group-editor-area` already has `height:100%`. Views need `display:flex; flex-direction:column` with the scrollable content area getting `flex:1; min-height:0; overflow:auto` |
| VIEW-14 | Graph view node popover z-index fix | Must-have | `.graph-popover` has `z-index: 200`. The `.view-toolbar` and `.type-filter-pills` have no explicit stacking context. Issue is likely that the popover is positioned relative to `.graph-container` which has `position: relative` — creating a stacking context. Fix: ensure popover z-index is above toolbar or move popover outside the container |

## Implementation Landscape

### File Map

| Task | Backend Files | Frontend Files |
|------|--------------|----------------|
| SPARQL-10 (IRI pill fix) | `backend/app/sparql/router.py` (lines 67-78, 177-186) | — |
| SPARQL-11 (prefix shortening) | — | `frontend/static/js/sparql-console.js` (lines 380-404) |
| SPARQL-09 (graph viz tab) | — | `frontend/static/js/sparql-console.js` (lines 210-290), `frontend/static/css/workspace.css` or new section in sparql CSS |
| ONTO-04 (property tooltips) | `backend/app/ontology/service.py` (lines 876-910) | `backend/app/templates/browser/ontology/tbox_detail.html` (line 101) |
| ONTO-05 (admin graph size) | — | `frontend/static/css/style.css` (lines 2046-2060), `backend/app/templates/admin/model_ontology_diagram.html` |
| ONTO-06 (edge tooltips) | `backend/app/admin/router.py` (lines 340-348) | `backend/app/templates/admin/model_ontology_diagram.html` (add edge hover handler) |
| VIEW-13 (full-height) | — | `frontend/static/css/views.css` (multiple sections), `frontend/static/css/workspace.css` |
| VIEW-14 (popover z-index) | — | `frontend/static/css/views.css` (line 569+), `frontend/static/js/graph.js` (line 385) |

### Key Findings

#### SPARQL-10: IRI Pill Fallthrough

**Root cause identified.** The `_is_object_iri()` function at `sparql/router.py:177` returns `True` only for IRIs starting with `settings.base_namespace` (e.g., `urn:sempkm:current:`). But `urn:sempkm:model:basic-pkm:Person` starts with `urn:sempkm:` which is in `_VOCAB_PREFIXES` (line 78) — so model class/property IRIs are explicitly excluded from enrichment.

**Fix:** Either (a) remove `urn:sempkm:` from `_VOCAB_PREFIXES` and add more specific entries (`urn:sempkm:current:`, `urn:sempkm:model:*` etc.), or (b) add a special case in `_is_object_iri()` for `urn:sempkm:model:*:ontology` IRIs. Approach (a) is cleaner — the broad `urn:sempkm:` entry is too aggressive. But note: `_is_object_iri` is used to decide which IRIs to enrich (resolve labels, types, icons). Model ontology IRIs (classes/properties) aren't "objects" in the triplestore — they won't have types via `?s a ?type` in the default graph. The enrichment for them should follow a different path.

**Better fix:** In `renderCell()` on the JS side, after the `if (enr)` check for enriched IRIs, add a second path that checks if the URI matches a known vocabulary QName from `prefixCache` and renders it as a styled `<span class="sparql-iri-pill sparql-vocab-pill">` with the QName as label. This way model ontology IRIs get a pill without needing backend enrichment. They're class/property IRIs, not data objects — no icon/type resolution needed.

Actually, the simplest fix: check `vocabCache` (already loaded) — if the URI matches a vocabulary item, render it with its QName as label. The vocabulary endpoint already returns all model ontology entities with QNames and badges.

#### SPARQL-11: Dynamic Prefix Shortening

**Straightforward.** `shortenUri()` (line 380) uses a hardcoded prefix map. `prefixCache` (line 52, populated at line 834 from `/api/sparql/vocabulary`) already contains all model prefixes from `PrefixRegistry.get_all_prefixes()`. Fix: replace the hardcoded map lookup with iteration over `prefixCache` (which maps prefix→namespace), inverting to namespace→prefix for matching.

Note: `prefixCache` format is `{ "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", ... }` (prefix→namespace). `shortenUri()` needs namespace→prefix. Build a reverse map lazily on first call after `prefixCache` updates.

#### SPARQL-09: Graph Visualization Tab

**New feature, moderate complexity.** Currently results render into a single `#sparql-results-table-wrap` div. Need to:

1. Detect triple-pattern results: check if `vars` contains 3 variables that look like subject/predicate/object (heuristic: 3 vars where all are URIs, or var names contain s/p/o patterns)
2. Add tab switcher UI above results (Table | Graph)
3. On "Graph" tab click, parse bindings into Cytoscape elements (nodes = unique subjects + objects, edges = predicates) and render inline
4. Cytoscape.js is already loaded globally (CDN in `base.html`)

Pattern to follow: The admin `model_ontology_diagram.html` inline Cytoscape initialization (lines 73-130) is the closest analog. Create a container div, initialize `cytoscape({...})` with extracted elements.

#### ONTO-04: Property Description Tooltips

**Simple query extension.** The `prop_sparql` in `get_class_detail()` (line 876) queries `?prop ?propLabel ?range ?rangeLabel` but doesn't fetch `rdfs:comment` or `skos:definition` for the property. Add:

```sparql
OPTIONAL { ?prop rdfs:comment ?propComment .
           FILTER(LANG(?propComment) = "" || LANG(?propComment) = "en") }
OPTIONAL { ?prop skos:definition ?propDef .
           FILTER(LANG(?propDef) = "" || LANG(?propDef) = "en") }
BIND(COALESCE(?propComment, ?propDef) AS ?propDescription)
```

Then include `description` in the property dict. In `tbox_detail.html` line 101, add `title="{{ p.description }}"` to the `<td class="tbox-detail-key">` element.

#### ONTO-05: Admin Graph Full-Size

**CSS-only fix.** Current state:
- `.ontology-diagram-panel` has `padding: 0.5rem 0; position: relative` — no explicit height
- `.ontology-cy-container` has `width: 100%; min-height: 600px` — fixed minimum, no flex fill

Fix: Make `.ontology-diagram-panel` a flex column with `display: flex; flex-direction: column; height: calc(100vh - 200px)` (accounts for admin nav/tab bar). Make `.ontology-cy-container` have `flex: 1; min-height: 400px` instead of fixed `min-height: 600px`.

Alternatively, use a simpler approach: set `.ontology-cy-container` to `height: calc(100vh - 250px)` directly. The admin model detail page loads this as an htmx partial within a tab panel — the offset needs to account for the admin header + tab bar + model detail header.

#### ONTO-06: Edge Tooltips in Admin Graph

**Moderate.** The admin graph currently has node hover popovers but no edge hover. The edge data passed from `admin/router.py` (line 340-348) only includes `id, source, target, label` — no `description` or `domain_label`/`range_label`.

Fix backend: In `admin_model_ontology_diagram()`, include the property description. The `detail["properties"]` already has `label`, `domain`, `range`, `prop_type`. Need to also pass `domain_label` and `range_label` (human-readable) and optionally `description` if available from the model detail.

Fix frontend: In `model_ontology_diagram.html`, add edge hover handler (same pattern as node hover at lines 207-225). Show label, domain→range, and description if available.

#### VIEW-13: Full-Height Views

**CSS flex audit.** The height propagation chain:

```
dockview panel → .group-editor-area (height:100%, overflow:auto) → htmx content
```

Current issues:
- `.group-editor-area` has `overflow:auto` which means it scrolls itself. Views inside don't get a height constraint — they just grow and the outer container scrolls. For table/cards views this is fine (scrolling list). For graph view and kanban, they need the container to NOT scroll so they can fill the available space.
- `.graph-container` uses `height: calc(100% - 90px)` — this only works if the parent has an explicit height AND doesn't scroll. Since `.group-editor-area` has `overflow:auto`, the parent height is the scrollable content height, not the visible viewport height.

**Fix strategy:** Make the `.group-editor-area` container a flex column. The htmx content should use `display:flex; flex-direction:column; height:100%` as a wrapper. Graph/kanban containers use `flex:1; min-height:0; overflow:hidden`. Table/cards containers use `flex:1; min-height:0; overflow:auto`.

But since htmx loads raw HTML fragments (not wrapped in a flex container), the templates themselves need the flex layout. Each view template's root content should be wrapped in a flex column container.

Simplest approach: Keep `.group-editor-area` as `overflow:auto` for table/cards (natural scrolling). For graph and kanban views only, make the view template root a flex column that fills height. The graph container already has `height: calc(100% - 90px)` — the issue is that 90px is fragile. Better: wrap graph view in `display:flex; flex-direction:column; height:100%` where toolbar gets natural size and `#cy-container` gets `flex:1`.

#### VIEW-14: Graph Popover Z-Index

**The popover (`z-index: 200`) is inside `.graph-container` (`position: relative`).** The view toolbar (`.view-toolbar`) and type filter pills (`.type-filter-pills`) are siblings ABOVE the graph container in the DOM — they're not inside `.graph-container`. Since the popover is absolutely positioned within `.graph-container`, its z-index only competes within that stacking context.

But `.graph-container` itself doesn't have an explicit `z-index`, so it participates in the parent stacking context. The real issue is likely that the popover overflows above the `.graph-container` bounds (positioned at negative top) but `.graph-container` has no `overflow: visible`. Let me check...

Actually, `.graph-container` has no `overflow` set, so it defaults to `visible`. The popover positioning in `graph.js` (line 385) positions relative to the container. When a node is near the top, the popover tries to position above the node but may clip under the toolbar.

**Root cause:** The popover is positioned using `popover.style.top = top + 'px'` relative to the container. If `top` is negative (node near top), the popover renders above the container boundary. The `.view-toolbar` is a separate element above — its background covers the popover because the toolbar is later in painting order (or has its own stacking context).

**Fix options:**
1. Set `z-index: 300` on `.graph-popover` and ensure `.view-toolbar` and `.type-filter-pills` have lower z-index (or none). Currently `.view-toolbar` has no z-index.
2. Move popover to be a sibling of the toolbar (outside `.graph-container`) — changes positioning math
3. Give `.graph-container` `z-index: 1` and the popover `z-index: 9999` — won't help since the stacking context is on `.graph-container`

Actually the most likely fix: the `.graph-container` has `position: relative` which creates a stacking context. The popover is inside it. The toolbar is a sibling. Since the popover is inside `.graph-container`, it can't render above siblings that paint after in the normal flow... wait, the toolbar is BEFORE the graph container in DOM order. So the graph container (and its popover) paint AFTER the toolbar, meaning the popover should appear ON TOP of the toolbar.

Let me re-read the DOM order: In `graph_view.html`, the toolbar includes come BEFORE `#cy-container`. So the stacking order is: pills, toolbar, graph-toolbar, cy-container. The cy-container (and its children) paint LAST, so a z-index:200 popover inside it should paint above everything.

The real z-index issue is likely with dockview's own toolbar/header that sits ABOVE the panel content. Dockview's tab bar or group header might have a high z-index that covers the popover when a node is near the very top of the view.

**Fix:** Move the popover DOM element from being inside `.graph-container` to being a child of `.group-editor-area` (or `document.body`). Then use absolute positioning relative to the viewport. This is the reliable approach for any popover that needs to escape container bounds.

Simpler fix: Keep popover inside container but clamp `top` to be >= 0 so it never goes above the container. Downside: popover may overlap the node.

Most practical fix: Add `z-index` to `.graph-container` or its popover at a value higher than dockview's tab chrome. Check what dockview uses.

## Recommendation

### Build Order (8 tasks, 3 natural groups)

**Group A — SPARQL Console (3 tasks, independent)**
1. **T01: SPARQL prefix shortening + IRI pill fix** (SPARQL-10, SPARQL-11) — These are tightly coupled. Fix `shortenUri()` to use `prefixCache`, and fix IRI pill fallthrough by checking `vocabCache` in `renderCell()`.
2. **T02: SPARQL graph visualization tab** (SPARQL-09) — New tab UI in results area with Cytoscape.js rendering for triple-pattern results.

**Group B — Ontology + Admin Graph (2 tasks, independent)**
3. **T03: Ontology property tooltips** (ONTO-04) — Backend query change + template `title` attribute.
4. **T04: Admin model graph sizing + edge tooltips** (ONTO-05, ONTO-06) — CSS resize + edge hover handler + backend edge data enrichment.

**Group C — View CSS Polish (2 tasks, coupled)**
5. **T05: Full-height views** (VIEW-13) — CSS flex layout audit across all view templates.
6. **T06: Graph popover z-index fix** (VIEW-14) — CSS/JS fix for popover stacking.

Groups A, B, and C are fully independent — they touch different files. Within each group, tasks are sequential.

### Verification Strategy

- **SPARQL-10/11:** Open SPARQL console, run `SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 20`. Model ontology IRIs should render as pills or shortened QNames, not raw `urn:sempkm:model:*` strings.
- **SPARQL-09:** Run a triple-pattern query, verify Table/Graph tab switcher appears, Graph tab renders Cytoscape visualization.
- **ONTO-04:** Open ontology browser, click a class with properties. Hover property name, see tooltip with description.
- **ONTO-05/06:** Open admin → model → Relationships tab. Graph should fill available space. Hover edge, see tooltip.
- **VIEW-13:** Open Table View, Cards View, Graph View, Kanban View. Each should fill the panel height — no outer scrollbar on the view container (inner scrolling for table/cards is fine).
- **VIEW-14:** Open Graph View, hover a node near the top of the view. Popover should render above the toolbar, fully visible.

All verifications are visual (UAT) — no unit tests needed for CSS/template changes. The SPARQL prefix fix could have a simple JS-level test if desired.

### Risks

- **LOW:** The full-height CSS fix (VIEW-13) might break existing scroll behavior in table/cards views if flex layout is applied too broadly. Each view template needs individual attention.
- **LOW:** The SPARQL graph visualization (SPARQL-09) is the most complex new feature, but Cytoscape.js patterns are well-established in the codebase.
- **NEGLIGIBLE:** All other tasks are straightforward template/CSS/JS changes.
