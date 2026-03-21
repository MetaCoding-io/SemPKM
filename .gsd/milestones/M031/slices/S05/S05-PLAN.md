# S05: SPARQL + Ontology + Graph + Full-Height Polish

**Goal:** Fix SPARQL IRI pill fallthrough and prefix shortening, add graph visualization for triple-pattern results, add ontology property tooltips, make admin model graph full-viewport with edge tooltips, fix full-height CSS for all views, and fix graph popover z-index.
**Demo:** Run a SPARQL query — model ontology IRIs render as vocab pills with QNames (not raw `urn:sempkm:model:*` strings) and `shortenUri()` uses dynamic prefixes from `prefixCache`. Triple-pattern results show a Table/Graph tab switcher. In ontology browser, property names have description tooltips. Admin model graph fills the viewport with edge hover tooltips. All views use 100% available height. Graph node popover renders above all toolbars.

## Must-Haves

- SPARQL-10: IRI pills render for all `urn:sempkm:model:*` IRIs (no fallthrough to plain `<span class="sparql-uri">`)
- SPARQL-11: `shortenUri()` uses dynamic `prefixCache` instead of hardcoded prefix map
- SPARQL-09: Triple-pattern SPARQL results have a Graph visualization tab
- ONTO-04: TBox property names show `rdfs:comment` / `skos:definition` tooltips on hover
- ONTO-05: Admin model graph is full-width/full-height
- ONTO-06: Edge hover tooltips in admin model graph
- VIEW-13: All views (table, cards, graph, kanban) use 100% available height
- VIEW-14: Graph view node popover renders above the toolbar (z-index fix)

## Verification

All tasks in this slice are CSS/JS/template polish. Verification is a combination of structural checks and UAT:

- `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` — backend syntax OK
- `python3 -c "import ast; ast.parse(open('backend/app/ontology/service.py').read())"` — ontology service syntax OK
- `python3 -c "import ast; ast.parse(open('backend/app/admin/router.py').read())"` — admin router syntax OK
- `grep -c "urn:sempkm:" backend/app/sparql/router.py` — `urn:sempkm:` no longer a single broad entry in `_VOCAB_PREFIXES`
- `grep -q "sparql-vocab-pill" frontend/static/css/workspace.css` — vocab pill CSS exists
- `grep -q "sparql-graph-tab\|sparql-result-tabs" frontend/static/js/sparql-console.js` — graph tab UI exists
- `grep -q "propDescription\|propComment\|title=.*description" backend/app/templates/browser/ontology/tbox_detail.html` — tooltip attribute present
- `grep -q "calc(100vh\|flex.*1\|min-height.*0" frontend/static/css/style.css` — admin graph uses viewport height
- `grep -q "z-index.*[3-9][0-9][0-9]" frontend/static/css/views.css` — popover z-index elevated
- Docker stack visual verification (UAT) of all 8 requirement areas

## Tasks

- [x] **T01: Fix SPARQL prefix shortening and IRI pill fallthrough** `est:45m`
  - Why: SPARQL-10 (must-have) and SPARQL-11 (should-have) — model ontology IRIs fall through to plain spans because `urn:sempkm:` is in `_VOCAB_PREFIXES` and `shortenUri()` uses a hardcoded prefix map that doesn't include model-specific prefixes.
  - Files: `frontend/static/js/sparql-console.js`, `backend/app/sparql/router.py`
  - Do: (1) Replace the single broad `urn:sempkm:` in `_VOCAB_PREFIXES` with more specific entries that exclude model class/property IRIs. (2) In `shortenUri()`, build a reverse map from `prefixCache` (namespace→prefix) and check it after the hardcoded map. (3) In `renderCell()`, after the enrichment check, add a second path that checks `vocabCache` for matching vocabulary items and renders them as styled vocab pills.
  - Verify: `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` passes; `grep -c "urn:sempkm:" backend/app/sparql/router.py` shows no broad `urn:sempkm:` in vocab prefixes; `grep -q "prefixCache" frontend/static/js/sparql-console.js` in `shortenUri`
  - Done when: Model ontology IRIs in SPARQL results render as vocab pills or shortened QNames, not raw `urn:sempkm:model:*` strings

- [x] **T02: Add SPARQL graph visualization tab for triple-pattern results** `est:1h`
  - Why: SPARQL-09 (should-have) — users querying triple patterns (s/p/o) have no way to see results as a graph, despite Cytoscape.js being globally available.
  - Files: `frontend/static/js/sparql-console.js`, `frontend/static/css/views.css`
  - Do: (1) Add triple-pattern detection heuristic (3 URI-heavy vars or s/p/o naming). (2) Add Table/Graph tab switcher UI above results. (3) On Graph tab click, parse bindings into Cytoscape.js elements (nodes = unique subjects + objects, edges = predicates) and render inline in a new container. Follow the `model_ontology_diagram.html` Cytoscape init pattern.
  - Verify: `grep -q "sparql-graph-tab\|sparql-result-tabs" frontend/static/js/sparql-console.js`
  - Done when: Running a triple-pattern query shows a Table/Graph tab switcher; Graph tab renders a Cytoscape visualization

- [x] **T03: Add ontology property tooltips + admin graph sizing and edge tooltips** `est:45m`
  - Why: ONTO-04, ONTO-05, ONTO-06 — ontology property names lack description tooltips; admin model graph is fixed-height (min-height:600px) instead of viewport-filling; admin graph edges have no hover tooltips.
  - Files: `backend/app/ontology/service.py`, `backend/app/templates/browser/ontology/tbox_detail.html`, `frontend/static/css/style.css`, `backend/app/templates/admin/model_ontology_diagram.html`, `backend/app/admin/router.py`
  - Do: (1) In `get_class_detail()` prop_sparql, add OPTIONAL for `rdfs:comment`/`skos:definition` on properties, BIND as `?propDescription`. Include `description` in property dict. (2) In `tbox_detail.html`, add `title="{{ p.description }}"` on property labels. (3) In `style.css`, change `.ontology-cy-container` from `min-height:600px` to `height:calc(100vh - 250px)`. Make `.ontology-diagram-panel` a flex column. (4) In `admin/router.py`, include property description in edge data. (5) In `model_ontology_diagram.html`, add edge hover handler following the existing node hover pattern.
  - Verify: `python3 -c "import ast; ast.parse(open('backend/app/ontology/service.py').read())"` passes; `grep -q "propDescription\|title=.*description" backend/app/templates/browser/ontology/tbox_detail.html`; `grep -q "calc(100vh" frontend/static/css/style.css` in ontology section
  - Done when: TBox property names show description tooltips on hover; admin model graph fills viewport height; edge hover shows tooltip with label and description

- [x] **T04: Full-height views and graph popover z-index fix** `est:45m`
  - Why: VIEW-13 (must-have) and VIEW-14 (must-have) — graph and kanban views don't fill available height because their templates lack flex layout; graph node popover is clipped under toolbars because the stacking context is constrained to `.graph-container`.
  - Files: `frontend/static/css/views.css`, `frontend/static/js/graph.js`, `backend/app/templates/browser/graph_view.html`, `backend/app/templates/browser/kanban_view.html`
  - Do: (1) For graph view: wrap template content in a flex column container that fills height (toolbar gets natural size, `#cy-container` gets `flex:1; min-height:0`). Remove fragile `height: calc(100% - 90px)` from `.graph-container`. (2) For kanban view: make `.kanban-board` use `flex:1; min-height:0; overflow-x:auto` inside a flex column wrapper. (3) For table/cards views: these already scroll naturally — verify no regression. (4) Fix graph popover z-index: either elevate popover z-index above dockview chrome, or append popover to `document.body` with viewport-relative positioning.
  - Verify: `grep -q "flex.*1\|min-height.*0" frontend/static/css/views.css` in graph section; `grep -q "z-index.*[3-9][0-9][0-9]\|document\.body" frontend/static/js/graph.js` (popover fix); no `calc(100% - 90px)` in `.graph-container`
  - Done when: Graph view and kanban view fill their panel height with no outer scrollbar; graph node popover near top of view renders fully visible above all chrome

## Files Likely Touched

- `frontend/static/js/sparql-console.js`
- `backend/app/sparql/router.py`
- `frontend/static/css/views.css`
- `frontend/static/js/graph.js`
- `backend/app/ontology/service.py`
- `backend/app/templates/browser/ontology/tbox_detail.html`
- `frontend/static/css/style.css`
- `backend/app/templates/admin/model_ontology_diagram.html`
- `backend/app/admin/router.py`
- `backend/app/templates/browser/graph_view.html`
- `backend/app/templates/browser/kanban_view.html`

## Observability / Diagnostics

- **SPARQL prefix shortening:** `console.warn('Failed to fetch SPARQL vocabulary:', err)` in `fetchVocabulary()` logs vocabulary cache failures. The `vocabIriIndex` and `reversePrefixMap` objects are module-level — inspect via browser console with `vocabIriIndex` / `reversePrefixMap` for debugging.
- **Vocab pill rendering:** Vocab pills use `.sparql-vocab-pill` class — inspect DOM for this class to verify IRI pill fallthrough is working. Missing pills mean `vocabCache` doesn't include the IRI (check `/api/sparql/vocabulary` response).
- **Backend `_VOCAB_PREFIXES`:** If model IRIs aren't enriched, check whether new internal namespaces were added without updating this tuple. The pattern is explicit inclusion of internal prefixes — any new `urn:sempkm:X:` namespace used for internal machinery must be added here.
- **Graph tab / Full-height / Popover:** Visual-only; inspect DOM structure and computed CSS in devtools. No runtime logs for these pure-CSS/template changes.
