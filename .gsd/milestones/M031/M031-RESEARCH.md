# M031 — Views Overhaul, Saved Queries as First-Class, & UI Polish — Research

**Date:** 2026-03-21

## Summary

M031 is a broad UI/UX overhaul milestone spanning 6 areas: (1) removing the carousel view picker and letting the explorer sidebar be the sole view-selection mechanism, (2) making saved queries first-class citizens everywhere, (3) SPARQL console polish, (4) ontology viewer & admin graph improvements, (5) dashboard & workflow builder UX, and (6) a new kanban renderer. The codebase is well-established with proven patterns across all touchpoints — generic views (M007), saved queries (M005), SPARQL console (v2.2), ontology viewer (M003), dashboards/workflows (M006), and the explorer sidebar.

The primary risk is the carousel removal — it's wired into `workspace.js` (`switchCarouselView()`), rendered via `carousel_tab_bar.html`, and integrated with generic views (M007 VIEW-05). Removing it requires re-routing how type-specific view variants are surfaced. The safest approach is to move variant selection into the view toolbar dropdown alongside the saved query scope selector.

The kanban renderer is the only genuinely new subsystem. Everything else is enhancement or refactoring of existing code. The build order should prove the carousel removal first (highest risk), then layer saved query integration, then add kanban, then polish the remaining areas.

## Recommendation

**Slice the work into 6-7 slices ordered by risk and dependency:**

1. **Carousel removal + view toolbar scope** (highest risk) — Remove `carousel_tab_bar.html`, `switchCarouselView()`, and VIEW-05 carousel integration. Add saved query scope dropdown to the view toolbar. Each view (table/cards/graph) becomes a standalone tab accepting an optional `scope_query` parameter.

2. **Multiple view instances + saved views** (depends on S01) — Enable opening multiple instances of the same view type as tabs (e.g., two graph views with different scopes). Fix the "Saved Views" folder in explorer. Add "Save current view" action.

3. **Saved queries everywhere** — Surface saved queries in explorer sidebar, VFS browser, spatial canvas, view toolbar, and object browser dropdown.

4. **Kanban renderer** (independent) — New renderer using the same data pipeline as table/cards/graph. Status-based columns with drag-drop to change status.

5. **SPARQL console + ontology viewer + admin graph polish** (independent) — Graph visualization for triple-pattern results, clickable IRI fixes, prefix shortening, property tooltips, full-height admin graph, edge tooltips.

6. **Dashboard & workflow UX** (independent) — Help text, autocomplete, workflow view step simplification, sample data.

7. **E2E tests + docs** (trailing) — Standing requirement coverage.

## Implementation Landscape

### Key Files

#### Views System (Carousel Removal + Scope)

- `backend/app/templates/browser/carousel_tab_bar.html` — The carousel to remove. Renders a tab bar of ViewSpec variants when a type filter is active. Included by generic view templates.
- `frontend/static/js/workspace.js` — Contains `switchCarouselView()` which routes carousel tab clicks to the correct view endpoint. Also contains `openGenericViewTab()` which creates `special-panel` dockview tabs for generic views.
- `backend/app/views/router.py` (~28K) — View routing. Contains `generic_view()` endpoint that builds `all_specs` from 3 generic specs + `get_view_specs_for_type(type_iri)` for carousel. This carousel-building logic needs removal.
- `backend/app/views/service.py` (~56K) — ViewSpecService with TTL cache, generic view registration, SHACL column discovery (`get_generic_columns()`, `build_dynamic_query()`).
- `backend/app/views/registry.py` (~2K) — ViewSpec dataclass and generic spec registration.
- `backend/app/templates/browser/view_toolbar.html` — Toolbar above views. Needs saved query scope dropdown added.
- `backend/app/templates/browser/table_view.html`, `cards_view.html`, `graph_view.html` — View templates that include carousel_tab_bar.html.
- `backend/app/templates/browser/type_filter_pills.html` — Type filter pills (these STAY — useful for sub-filtering).

#### Saved Views & Queries

- `backend/app/templates/browser/my_views.html` — Saved views rendering (currently broken/incomplete per CONTEXT).
- `backend/app/browser/workspace.py` (~46K) — Contains `my_views()` endpoint at `/browser/my-views`.
- `backend/app/services/query_service.py` — `promote_query()`, `list_promoted_views()` for saved query → view promotion. RDF-backed in triplestore.
- `backend/app/sparql/router.py` — SPARQL endpoints including saved query CRUD.

#### SPARQL Console

- `frontend/static/js/sparql-console.js` — Client-side SPARQL console with `shortenUri()` that needs `urn:sempkm:model:*` prefix support.
- `backend/app/sparql/router.py` — SPARQL execution endpoints.

#### Ontology Viewer

- `backend/app/templates/browser/ontology/tbox_detail.html` — TBox detail page. Properties table needs tooltip for `rdfs:comment`/`skos:definition`.
- `backend/app/ontology/service.py` — Ontology queries. Property description fetching needs OPTIONAL clause addition.

#### Admin Model Graph

- `backend/app/templates/admin/model_ontology_diagram.html` — Cytoscape.js graph. Has `min-height: 600px` but not full viewport height.
- `frontend/static/css/style.css` — Admin CSS including graph container sizing.

#### Dashboard & Workflow Builders

- `backend/app/templates/browser/dashboard_builder.html` — Dashboard builder form.
- `backend/app/templates/browser/workflow_builder.html` — Workflow builder form.
- `backend/app/dashboard/` — Dashboard models/service.
- `backend/app/workflow/` — Workflow models/service (if exists, likely similar structure).

#### Graph View

- `frontend/static/js/graph.js` — Cytoscape.js graph rendering. Node popover z-index issue lives here.

### Build Order

**S01: Carousel Removal + View Scope Binding (prove first — highest risk)**
- Remove `carousel_tab_bar.html` includes from all view templates
- Remove `switchCarouselView()` from workspace.js
- Remove `all_specs` carousel-building logic from `views/router.py` generic_view endpoint
- Add `scope_query` URL parameter to generic view endpoints
- Add scope query dropdown to `view_toolbar.html` populated from saved queries API
- Keep type filter pills (they stay)
- Verify: Opening "Table View" from explorer shows table with type pills, no carousel. Selecting a scope query filters results.

**S02: Multiple View Instances + Saved Views Fix (depends on S01)**
- Allow opening multiple tabs of same view type (currently reuses tab by specialType)
- Fix `/browser/my-views` rendering in `my_views.html`
- Add "Save current view" action (name + renderer + type filter + scope query + filter text → PromotedQueryView)
- Verify: Two graph view tabs open simultaneously with different scopes. Saved views folder shows entries.

**S03: Saved Queries Everywhere (independent of S01/S02 but benefits from them)**
- Explorer sidebar: dedicated "Saved Queries" section or integration
- VFS browser: scope by saved query (partially exists via VFS-06)
- Spatial canvas: drag saved query onto canvas → scoped view widget embed
- View toolbar: dropdown (done in S01)
- Object browser dropdown: scope option

**S04: Kanban Renderer (independent)**
- New `kanban_view.html` template
- New kanban endpoint in views/router.py
- Status-based columns from `bpkm:taskStatus` or type-declared status field
- Drag-drop to change status via object.patch command
- Register as 4th generic ViewSpec
- Explorer entry for "Kanban View"

**S05: SPARQL + Ontology + Admin Graph Polish (independent)**
- SPARQL: graph visualization tab for triple-pattern results (Cytoscape.js, already a dep)
- SPARQL: fix URI pills falling through to plain `<span class="sparql-uri">`
- SPARQL: extend `shortenUri()` for `urn:sempkm:model:*` prefixes dynamically
- Ontology: add OPTIONAL `rdfs:comment`/`skos:definition` to property query in `ontology/service.py`
- Ontology: render property tooltips in `tbox_detail.html`
- Admin graph: full-width/full-height Cytoscape container
- Admin graph: edge hover tooltips with domain/range/comment
- Graph view: fix node popover z-index (CSS stacking context fix)
- All views: ensure 100% available height (CSS `height: 100%` / `flex: 1` audit)

**S06: Dashboard & Workflow UX (independent)**
- Help text for dashboard/workflow builder forms (following SHACL helptext pattern from HELP-01)
- Autocomplete for object/type reference fields in builder forms
- Workflow "view" step: replace renderer dropdown with view/saved-view picker
- Sample dashboards and workflows as seed data fixtures

**S07: E2E Tests + User Guide Docs (trailing)**

### Verification Approach

- **Carousel removal:** Open each view type from explorer → no carousel tab bar visible. Type filter pills still work. Opening a model-declared view (e.g., "Projects Table") via Saved Views still renders correctly.
- **Scope binding:** Select a saved query in view toolbar → view shows only matching objects. Change scope → view updates. Clear scope → shows all objects.
- **Multiple instances:** Open "Table View" twice with different scopes → two tabs visible, each showing different data.
- **Kanban:** Open Kanban View → status columns visible. Drag task between columns → status changes. New object with status appears in correct column.
- **Full height:** All view containers use 100% of available viewport height below toolbar. No unnecessary outer scrollbar on the view container itself.
- **Graph z-index:** Click graph node → popover appears above the top toolbar.

## Constraints

- **htmx-driven, no SPA framework.** Views load as HTML fragments via htmx. All view templates extend `base.html` or `base_embed.html`.
- **Cytoscape.js for all graph rendering** — already a dependency, used in graph view (`graph.js`), admin model diagram, spatial canvas.
- **Saved queries are RDF-backed** via `QueryService` (triplestore `urn:sempkm:queries` graph), not SQLite.
- **Promoted views use SQLite** (`promoted_query_views` table) via `PromotedQueryView` model — this is the saved view storage layer.
- **Must work with existing tab system** — `workspace.js` `openTab()`, `openGenericViewTab()`, special panels in dockview.
- **esbuild build pipeline** (M029) — any new JS files need to be added to the build configuration in `frontend/build.js`.
- **CSS code-splitting** (M029) — workspace CSS is loaded only on workspace pages. New view CSS goes in workspace.css or a new file loaded by the workspace template.
- **3 generic ViewSpecs registered in-memory** (D093) — kanban would be a 4th.

## Common Pitfalls

- **Carousel removal breaks model-declared views** — Model-declared ViewSpecs (e.g., "Projects Table", "Contacts Pipeline") currently surface via the carousel when a type filter pill is active (VIEW-05). After carousel removal, these need an alternative surface — either the view toolbar dropdown, or entries in the Saved Views folder, or both. Simply deleting the carousel without providing an alternative loses access to model-declared view variants.

- **Multiple view instances with same specialType** — dockview deduplicates tabs by ID. `openGenericViewTab()` currently creates tabs with IDs like `generic-view-table`. Opening a second table view needs a unique tab ID (e.g., `generic-view-table-{uuid}`). Must also handle the dockview `addPanel` logic in `workspace-layout.js`.

- **Graph popover z-index** — The graph view's node popover is likely positioned inside the view container which has `overflow: hidden` or a stacking context that clips it below the toolbar. Fix may require the popover to be appended to `document.body` rather than the graph container, or adjusting the toolbar's z-index.

- **Kanban drag-drop conflicts with dockview** — dockview's panel drag system may intercept drag events intended for kanban column reordering. Need `stopPropagation()` isolation (same pattern as canvas resize handles, D127/CANVAS-01).

- **Full-height views** — The generic view container sits inside a dockview panel which has its own sizing. The container hierarchy is: dockview panel → special-panel wrapper → htmx-loaded content. Each layer must propagate height correctly. Likely needs `height: 100%` on each intermediate container and `flex: 1` or `overflow: auto` on the view content.

## Open Risks

- **Model-declared view variant access after carousel removal** — The carousel is the ONLY current surface for model-declared ViewSpecs when a type is selected. Need to design an alternative before removing it. The view toolbar scope dropdown could double as a variant selector, or model-declared views could become entries in the Saved Views folder.

- **Kanban status field discovery** — Not all types have a status field. `bpkm:taskStatus` is specific to Task. The kanban renderer needs a way to discover which field to use for columns — either hardcoded to `bpkm:taskStatus` for v1, or discovered from SHACL shapes by looking for `sh:in` constraints with status-like values.

- **VFS saved query integration scope** — VFS-06 already partially wired saved query scoping in VFS. Need to verify what works and what's broken before adding more saved query surfaces.

- **SPARQL graph visualization for results** — Determining when results "contain subject-predicate-object patterns" is non-trivial. A simple heuristic: if the query has exactly 3 projected variables and result bindings look like (IRI, IRI, IRI|literal), offer the graph tab. More complex detection could look at variable names (?s, ?p, ?o patterns).

## Candidate Requirements

Based on M031-CONTEXT.md scope, these are the candidate requirements:

| ID | Description | Priority |
|----|-------------|----------|
| VIEW-08 | Carousel removal — explorer sidebar is sole view selector | Must-have |
| VIEW-09 | Saved query scope binding on all view types | Must-have |
| VIEW-10 | Multiple view instances as tabs with different scopes | Should-have |
| VIEW-11 | Saved views load/display/create/unpin correctly | Must-have |
| VIEW-12 | Kanban renderer with status-based columns and drag-drop | Should-have |
| VIEW-13 | All views use 100% available height | Must-have |
| VIEW-14 | Graph view node popover z-index fix | Must-have |
| SQ-01 | Saved queries accessible in explorer sidebar | Should-have |
| SQ-02 | Saved queries as canvas embed source | Nice-to-have |
| SQ-03 | Saved queries in object browser dropdown | Nice-to-have |
| SPARQL-09 | Graph visualization tab for triple-pattern SPARQL results | Should-have |
| SPARQL-10 | Fix IRI pills falling through to plain spans | Must-have |
| SPARQL-11 | Dynamic model prefix shortening in shortenUri() | Should-have |
| ONTO-04 | Property description tooltips in TBox detail | Should-have |
| ONTO-05 | Admin model graph full-width/full-height | Should-have |
| ONTO-06 | Edge tooltips in admin model graph | Nice-to-have |
| DBUIX-01 | Dashboard/workflow builder help text | Should-have |
| DBUIX-02 | Autocomplete for object/type references in builders | Should-have |
| DBUIX-03 | Workflow view step simplification | Should-have |
| DBUIX-04 | Sample dashboard and workflow seed data | Nice-to-have |

**Table stakes:** VIEW-08, VIEW-09, VIEW-11, VIEW-13, VIEW-14, SPARQL-10. These are bug fixes or core UX fixes that users would notice immediately.

**High value but bounded risk:** VIEW-12 (kanban), SPARQL-09 (graph viz), SQ-01 (explorer queries). These add new capability with clear boundaries.

**Polish items:** ONTO-04/05/06, DBUIX-01/02/03/04. Lower risk, can be batched into a single slice.

## Sources

- M031-CONTEXT.md scope definition (inline)
- M007 shipped features: generic views, SHACL columns, type filter pills, carousel integration (VIEW-01 through VIEW-05)
- M005 shipped features: saved query RDF migration, views rethink design doc
- D093: Generic views registered in-memory at startup
- D095: Type filter pills for cross-type generic views
- D096: sempkm:scopeQuery for view-to-query scope binding
- D114: Generic view tabs use special-panel dockview component
- D115: Saved Views replaces MY VIEWS as htmx lazy-loaded folder
- `.gsd/design/VIEWS-RETHINK.md` — referenced but not fully read (context budget)
