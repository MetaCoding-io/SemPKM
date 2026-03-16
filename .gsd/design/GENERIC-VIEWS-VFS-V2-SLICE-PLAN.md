# Generic Views & VFS v2 Completion — Slice Plan

**Goal:** Replace per-type explorer entries with 3 generic views (Table / Cards / Graph) that work across all types with SHACL-driven dynamic columns and type filter pills. Complete the VFS v2 quick wins (type filter, query IRI alignment, preview fix). This is Phase 1 of the Views Rethink design — strictly additive, no existing views removed.

**Design source:** `.gsd/design/VIEWS-RETHINK.md` (Phase 1), `.gsd/design/VFS-V2-DESIGN.md` (items 2-5)

**Demo:** Open "Table View" from explorer → see all objects across types with dynamic columns → click a type pill to filter → columns change to SHACL-discovered properties for that type → carousel shows model-declared view variants. VFS mount with type_filter narrows to specific types without SPARQL. Preview endpoint honors saved query scope.

## Acceptance Criteria (from design docs — verbatim)

These must all pass. They are not optional or "nice to have."

### Views Rethink Phase 1
1. **VIEW-01:** Three generic view entries appear in explorer: "Table View", "Cards View", "Graph View"
2. **VIEW-02:** Opening "Table View" shows all objects across all types with a common column set (label, type, created, modified)
3. **VIEW-02:** When a type is selected, columns change to SHACL-discovered properties (sh:path, sh:name, sh:order from NodeShapeForm)
4. **VIEW-03:** Type filter pills appear above the view content, populated from ShapesService.get_types()
5. **VIEW-05:** When a type is selected, carousel tab bar shows model-declared view variants for that type (existing carousel mechanism)
6. **VIEW-01:** Generic views use scope_to_current_graph() for all queries
7. **VIEW-03:** "All Types" pill resets to cross-type common columns
8. **VIEW-03:** Type pill selection persists in localStorage
9. **VIEW-04:** Per-type ViewSpec folders are removed from explorer — replaced by the 3 generic entries + a "Saved Views" folder (merging MY VIEWS)

### VFS v2 Quick Wins
10. **VFS-07:** `sempkm:typeFilter` predicate on MountSpec — list of type IRIs, composed with saved query scope via AND (VALUES clause)
11. **VFS-07:** Mount form UI has type multi-select populated from ShapesService
12. **VFS-08:** `sempkm:savedQueryId` renamed to `sempkm:scopeQuery` with full IRI storage — migration SPARQL UPDATE provided
13. **VFS-09:** Preview endpoint resolves saved query scope (remove stale "would require loading from SQLite" comment)
14. **VFS-09:** Preview endpoint honors type_filter

## Must-Haves

- Generic ViewSpec instances registered at startup in ViewSpecService (D093)
- SHACL column discovery: ShapesService.get_form_for_type() → PropertyShape.path/name/order → dynamic SPARQL SELECT
- Fallback column set for types with ≤2 properties: label, type, created, modified
- Type filter pills partial template + htmx wiring
- Explorer tree rewrite: 3 generic entries + Saved Views folder (no per-type folders)
- VFS type_filter field on MountDefinition + VALUES clause in build_scope_filter()
- VFS query IRI alignment migration
- VFS preview fix

## Non-Goals

- Phase 2 (remove model-declared views from data) — views still exist, just not in explorer tree
- Phase 3 (dead code cleanup) — separate
- Composable strategy chains (VFS design item 6) — medium effort, separate slice
- Filename templates (VFS design item 7) — separate
- Write support (VFS design item 8) — separate milestone
- Custom column selection UI
- Drag-and-drop view customization

## Tasks

- [ ] **T01: Generic ViewSpec registration + SHACL column discovery** `est:1h`
  - Register 3 generic ViewSpecs in ViewSpecService at startup (not RDF — D093)
  - Add `build_dynamic_query(type_iri, shapes_service)` method that:
    - Calls `shapes_service.get_form_for_type(type_iri)` for the selected type
    - Extracts PropertyShape entries, sorts by sh:order
    - Builds `SELECT ?s ?type ?label ?col1 ?col2 ... WHERE { ?s a <type> . OPTIONAL { ?s <path1> ?col1 } ... }` 
    - Falls back to default columns (label, type, created, modified) when type is None or shape has ≤2 properties
    - Passes through `scope_to_current_graph()`
  - Add `get_view_spec_by_iri()` handling for generic spec IRIs (urn:sempkm:view:generic-table etc.)
  - Add `GET /browser/views/generic/{renderer}` endpoint with optional `?type=` filter
    - For table: builds dynamic query, executes, renders with column headers from PropertyShape.name
    - For cards: builds dynamic query, renders card view with title/subtitle from first 2 properties
    - For graph: reuses existing graph query pattern with type filter
  - Tests: generic spec registration, column discovery from SHACL, fallback columns, dynamic query building

- [ ] **T02: Type filter pills + explorer tree rewrite** `est:1h`
  - Create `type_filter_pills.html` partial — pills populated from `ShapesService.get_types()`, "All Types" default, htmx onclick swaps view content with `?type=` param
  - Add `GET /browser/views/type-pills` endpoint returning the pills HTML
  - Wire localStorage persistence for selected type per renderer (key: `sempkm_generic_view_type_{renderer}`)
  - Rewrite `views_explorer.html`:
    - Keep Spatial Canvas and Ontology Viewer entries
    - Add 3 generic view entries: Table View (▦), Cards View (🃏), Graph View (◎) — onclick opens generic view
    - Add "Saved Views" folder containing promoted query views (merge from MY VIEWS)
    - Remove per-model/per-type folder structure entirely
  - Rewrite `views_explorer()` endpoint to return flat list (generic entries + saved views) instead of model-grouped tree
  - Add `openGenericViewTab(renderer, label)` to workspace.js
  - Add `generic-view` specialType to workspace-layout.js
  - Wire carousel tab bar: when type pill is selected, fetch model-declared views for that type and show as carousel tabs
  - Tests: explorer endpoint returns generic entries, type pills endpoint returns correct types

- [ ] **T03: VFS type filter + query IRI alignment + preview fix** `est:45m`
  - Add `type_filter: list[str]` field to MountDefinition
  - Extend `build_scope_filter()`: if mount.type_filter is set, add `?iri a ?filterType . VALUES ?filterType { <iri1> <iri2> }` clause — composes with saved query scope via AND (D101)
  - Add type multi-select to mount form UI — populated from ShapesService.get_types() via htmx endpoint
  - Query IRI alignment (D099): 
    - Rename predicate `sempkm:savedQueryId` → `sempkm:scopeQuery` in MountService read/write
    - Store full IRI `<urn:sempkm:query:{uuid}>` instead of bare UUID
    - Write migration SPARQL UPDATE for existing mounts
  - Preview endpoint fix:
    - Remove stale "would require loading from SQLite" comment
    - Resolve saved query text via async TriplestoreClient (preview runs in async context)
    - Honor type_filter in preview query
  - Tests: type_filter VALUES injection, AND composition with saved query, query IRI round-trip, preview with scope

- [ ] **T04: Integration verification** `est:30m`
  - Browser: open Table View → all objects shown → click Note pill → SHACL columns appear → carousel shows model-declared Note views
  - Browser: open Cards View → all objects → filter by type → cards show type-specific fields
  - Browser: create VFS mount with type_filter → only filtered types appear
  - Browser: VFS mount preview shows scope-filtered results
  - Browser: Saved Views folder shows promoted query views
  - Verify all 14 acceptance criteria
  - Full test suite passes, zero conflict markers

## Verification

- `cd backend && .venv/bin/pytest -x -q` — full suite passes, zero regressions
- `grep -rn "^<<<<<<< " backend/ frontend/` — zero conflict markers
- Browser: all 14 acceptance criteria verified against live Docker
- Explorer tree has exactly 3 generic entries + Spatial Canvas + Ontology Viewer + Saved Views folder (no per-type folders)
- VFS mount with type_filter correctly restricts objects
- VFS preview resolves saved query scope

## Files Likely Touched

### New files
- `backend/app/templates/browser/type_filter_pills.html`
- `backend/app/templates/browser/generic_table_view.html` (or extend existing table_view.html)
- `backend/tests/test_generic_views.py`

### Modified
- `backend/app/views/service.py` — generic ViewSpec registration, build_dynamic_query()
- `backend/app/views/router.py` — generic view endpoints, type-pills endpoint, explorer rewrite
- `backend/app/templates/browser/views_explorer.html` — flat generic entries + Saved Views
- `backend/app/vfs/strategies.py` — type_filter VALUES clause in build_scope_filter()
- `backend/app/vfs/mount_router.py` — preview fix (resolve saved query scope, honor type_filter)
- `backend/app/vfs/mount_service.py` — scopeQuery predicate rename, full IRI storage
- `frontend/static/js/workspace.js` — openGenericViewTab(), type pill localStorage
- `frontend/static/js/workspace-layout.js` — generic-view specialType
- `frontend/static/css/workspace.css` — type filter pills styling

## Risk

- **Low:** SHACL column discovery uses existing ShapesService infrastructure
- **Low:** Type filter pills are a simple htmx pattern (pills → swap view content)
- **Medium:** Explorer tree rewrite removes familiar navigation — but generic views provide equivalent access via type pills + carousel
- **Low:** VFS type_filter is a simple VALUES clause addition
- **Low:** Preview fix uses async TriplestoreClient already available in the endpoint

## Standing Requirements Check

- **E2E tests:** New user-visible views need Playwright coverage — but this slice is purely backend+frontend unit tests + browser verification. E2E can be a coverage slice or added to T04.
- **User guide docs:** Generic views are a significant UX change — needs docs/guide update. Can be a task in this slice or a docs coverage slice.
