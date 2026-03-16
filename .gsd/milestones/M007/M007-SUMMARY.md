---
id: M007
provides:
  - 3 generic views (Table/Cards/Graph) with SHACL-driven dynamic columns replacing per-type explorer tree
  - Type filter pills for cross-type generic views with localStorage persistence
  - Carousel tab bar integration showing model-declared views when type selected
  - Explorer consolidation — flat entries + Saved Views folder (no per-model/per-type tree)
  - VFS type_filter field with VALUES clause (AND-composed with scope)
  - VFS scopeQuery predicate with full IRI storage and migration
  - VFS preview endpoint resolving saved query scope with HTTP 404 on missing
  - VFS path contract documentation and 26 unit tests
  - VFS composable strategy chains (up to 3 levels, cumulative scope narrowing)
  - VFS filename templates with {title}/{date}/{type}/{id} variable expansion
  - Lucide SVG chevrons on all left sidebar sections matching right sidebar
  - Always-visible OBJECTS header action buttons
  - DASHBOARDS/WORKFLOWS header plus-buttons (replacing tree-leaf entries)
  - Normalized inference button + accent Ontology Viewer
  - Horizontal dagre layout for relationships graph
  - Chapter 28 user guide (dashboards and workflows) with 6 glossary entries
key_decisions:
  - D111 — Default SELECT uses mandatory rdf:type binding (all-OPTIONAL left ?s unbound)
  - D112 — Generic graph view uses separate data endpoint (generic specs have empty sparql_query)
  - D113 — pagination_base_url template variable with | default() for backward compatibility
  - D114 — Generic view tabs use special-panel dockview component, not view-panel
  - D115 — Saved Views replaces MY VIEWS as lazy-loaded folder inside VIEWS section
  - D116 — type_filter VALUES uses ?iri a ?type binding
  - D117 — scope_query stores full IRI, not bare UUID
  - D118 — Two-query approach for list_mounts type_filter
  - D119 — Preview returns HTTP 404 for unresolvable scope_query
  - D120 — Chain strategies stored as pipe-delimited string literal (no RDF ordered lists)
  - D121 — Chain scope narrowing is cumulative across all parent levels
  - D122 — Filename template expansion before slugification
  - D123 — Chain by-type narrowing uses SPARQL local name FILTER, not pre-resolved IRI
patterns_established:
  - _var_name_from_iri() for safe SPARQL variable names from property IRIs
  - get_generic_columns() as reusable column resolution with graceful degradation
  - pagination_base_url | default(old_pattern) in all URL-generating templates
  - type_filter_pills.html as htmx-driven filter partial with localStorage persistence
  - Generic IRI detection via indexOf('urn:sempkm:view:generic-') === 0
  - special-panel specialType pattern for tabs without spec IRIs
  - Multi-valued RDF predicate CRUD with two-query merge approach
  - VFS scope references use full IRIs (urn:sempkm:query:{uuid})
  - chain/chain_depth/chain_folder_values parameter triple for chain-aware collections
  - _build_cumulative_scope_filter() for composable chain narrowing
  - view-leaf--accent CSS class for highlighted explorer entries
  - All left sidebar sections use Lucide chevron-right SVG icons consistently
observability_surfaces:
  - logger.info("Registered %d generic views", count) at startup
  - logger.info("generic_view: renderer=%s type=%s") on each request
  - logger.debug("build_dynamic_query: type=%s, columns=%d") on query build
  - GET /browser/views/type-pills returns JSON type list for debugging
  - DEBUG log for type_filter VALUES clause generation
  - DEBUG log for scope_query resolution via sync/async client
  - WARNING log when scope_query IRI not found in triplestore
  - DEBUG logs for chain dispatch, chain narrowing at depth, filename_template expansion
  - Mount API responses include type_filter, scope_query, strategy_chain fields
  - Preview endpoint returns HTTP 404 with {"detail": "Saved query not found"} on missing scope_query
requirement_outcomes:
  - id: VIEW-01
    from_status: active
    to_status: validated
    proof: 3 generic ViewSpec objects registered at startup; explorer shows Table/Cards/Graph View entries; GET /browser/views/generic/{renderer} returns 200; 32 unit tests in test_dynamic_query_builder.py
  - id: VIEW-02
    from_status: active
    to_status: validated
    proof: get_generic_columns() resolves SHACL PropertyShape metadata from ShapesService; fallback to defaults for sparse/missing shapes; unit tests cover rich shapes, sparse shapes, exception fallback
  - id: VIEW-03
    from_status: active
    to_status: validated
    proof: type_filter_pills.html partial renders pills from ShapesService.get_types(); htmx filtering; localStorage persistence; "All Types" default
  - id: VIEW-04
    from_status: active
    to_status: validated
    proof: views_explorer.html rewritten with flat entries + Saved Views folder; MY VIEWS section removed; browser verification shows no per-model folders
  - id: VIEW-05
    from_status: active
    to_status: validated
    proof: Generic endpoint builds all_specs from generic + get_view_specs_for_type(); carousel renders when >1 spec; switchCarouselView() routes generic IRIs correctly
  - id: VFS-07
    from_status: active
    to_status: validated
    proof: type_filter field on MountDefinition; VALUES clause generation tested with 6 unit tests; type multi-select UI verified in browser; full CRUD round-trip
  - id: VFS-08
    from_status: active
    to_status: validated
    proof: savedQueryId renamed to scopeQuery across all code; IRI storage (urn:sempkm:query:{uuid}); migration function; zero grep hits for savedQueryId outside migration
  - id: VFS-09
    from_status: active
    to_status: validated
    proof: Preview endpoint resolves saved query via async TriplestoreClient; returns HTTP 404 on missing; WebDAV resolves via sync client with TTL cache; 5 unit tests
  - id: VFS-10
    from_status: active
    to_status: validated
    proof: Path Contract section in docs/guide/23-vfs.md with forward/reverse mapping; 26 unit tests in test_vfs_path_contract.py (15 slugify + 11 file map)
  - id: VFS-11
    from_status: active
    to_status: validated
    proof: Pipe-delimited chain storage; max 3 levels enforced; cumulative scope narrowing; chain-aware WebDAV dispatch (5-6 segments); 39 unit tests; browser-verified chain builder UI with presets
  - id: VFS-12
    from_status: active
    to_status: validated
    proof: filename_template field with {title}/{date}/{type}/{id} expansion before slugification; 12 unit tests; mount form UI with variable hint; CRUD round-trip
  - id: DOCS-04
    from_status: active
    to_status: validated
    proof: docs/guide/28-dashboards-and-workflows.md (170 lines) covering 5 layouts, 6 block types, cross-view context, 3 step types, stepper UI; 6 glossary entries; README TOC; navigation chain ch. 27 → ch. 28 → Appendix A
  - id: UIPOL-01
    from_status: active
    to_status: validated
    proof: 6/6 items browser-verified — Lucide SVG chevrons on all sections, OBJECTS opacity 1, DASHBOARDS/WORKFLOWS + buttons, inference button normalized at 32px, Ontology Viewer accent color, dagre LR layout at 600px min-height
duration: ~8h across 5 slices
verification_result: passed
completed_at: 2026-03-16
---

# M007: Generic Views, VFS Completion & Polish

**Replaced per-type explorer tree with 3 SHACL-driven generic views (Table/Cards/Graph), completed VFS v2 features (type filters, composable strategy chains, filename templates, scopeQuery IRI alignment), fixed 6 UI inconsistencies, and documented dashboards/workflows in the user guide — validating all 13 active requirements.**

## What Happened

Five slices across three workstreams:

**Generic Views (S01, ~2.5h):** Built the generic views infrastructure from scratch. `build_dynamic_query()` in ViewSpecService uses ShapesService to discover SHACL PropertyShapes for a given type and builds SPARQL SELECT queries with OPTIONAL clauses per property — falling back to 4 default columns (label, type, created, modified) when no type is selected or shapes are sparse. Three generic ViewSpec objects registered in memory at startup with well-known IRIs. Endpoints at `GET /browser/views/generic/{renderer}` build queries dynamically, create transient ViewSpec objects, and delegate to existing query executors. Type filter pills above each generic view allow cross-type filtering with htmx — when a type is selected, columns change to match the type's SHACL shape, and the carousel tab bar shows model-declared view variants alongside the generic renderers. Explorer VIEWS section rewritten from per-model/per-type folder tree to 5 flat entries (Spatial Canvas, Ontology Viewer, Table/Cards/Graph View) plus a collapsible Saved Views folder. MY VIEWS section removed. All pagination, sort-header, filter-toolbar, and group-by templates refactored to `pagination_base_url | default()` for backward compatibility with both generic and model-declared views.

**VFS Completion (S02+S03, ~4.5h):** S02 delivered four quick wins: `type_filter` field with VALUES clause AND-composed with scope, `scopeQuery` IRI alignment (renamed from `savedQueryId`, full IRI storage, migration function), preview endpoint scope resolution (async TriplestoreClient with HTTP 404 on missing), and path contract documentation with 26 unit tests. The type multi-select checkbox UI enables mounting filtered to specific types without SPARQL.

S03 built composable strategy chains on top of S02's foundation. Strategy field now accepts pipe-delimited multi-strategy strings — each level nests inside the previous with cumulative scope narrowing across all parent groupings. Chain-aware WebDAV path dispatch handles 5-6 segment paths. Preview endpoint returns nested tree structures. Chain builder UI with add/remove controls, max 3 levels, and preset combos (Tag → Date, Type → Tag, Type → Date). Filename templates allow `{title}`, `{date}`, `{type}`, `{id}` variables with expansion before slugification.

**Polish & Docs (S04+S05, ~1.3h):** S04 fixed all 6 UI inconsistencies: replaced text chevrons with Lucide SVGs across 7 templates, changed OBJECTS header actions from hover-reveal to always-visible, added plus-buttons to DASHBOARDS/WORKFLOWS headers (removing tree-leaf entries), normalized inference button as `<button>`, added accent color to Ontology Viewer, and switched relationships graph to dagre horizontal layout. S05 wrote Chapter 28 of the user guide covering all dashboard and workflow features, added 6 glossary entries, and linked the navigation chain.

**Test fix (milestone completion):** S04's removal of "New Dashboard"/"New Workflow" tree-leaf entries broke 6 M006 explorer tests that asserted those strings. Updated tests to reflect the new header-button pattern.

## Cross-Slice Verification

### Success Criteria

1. **Explorer VIEWS section shows 3 generic entries + Saved Views folder — no per-type folders** ✅
   - S01 browser verification: exactly Spatial Canvas (Beta), Ontology Viewer, Table View, Cards View, Graph View, Saved Views. `#section-views .tree-node[data-model-id]` count === 0.

2. **Opening Table View shows all objects with common columns** ✅
   - `GET /browser/views/generic/table` → 200, HTML with "All Objects" label, toolbar, filter. Default columns: label, type, created, modified.

3. **Clicking a type pill filters the view and columns change to SHACL-discovered properties** ✅
   - `GET /browser/views/generic/table?type=urn:sempkm:model:basic-pkm:Note` → 200, SHACL columns. Unit tests cover column resolution, sparse shape fallback, exception fallback.

4. **Carousel tab bar shows model-declared view variants when a type is selected** ✅
   - Generic endpoint builds `all_specs` from generic + `get_view_specs_for_type()`. Carousel renders when `all_specs|length > 1`. `switchCarouselView()` routes generic IRIs correctly.

5. **VFS mount with `sempkm:typeFilter` restricts objects to specified types** ✅
   - 6 unit tests for VALUES clause generation. Browser-verified type multi-select UI with full CRUD round-trip.

6. **VFS `sempkm:savedQueryId` renamed to `sempkm:scopeQuery` with full IRI storage** ✅
   - `rg savedQueryId backend/ frontend/ --exclude migration` returns zero results. Migration function in `backend/app/vfs/migrations.py`.

7. **VFS preview endpoint resolves saved query scope and honors type_filter** ✅
   - 5 unit tests. Preview returns HTTP 404 on missing query IRI. Dead SQLite comment removed.

8. **VFS path contract documented and tested** ✅
   - `docs/guide/23-vfs.md` Path Contract section. 26 unit tests in `test_vfs_path_contract.py`.

9. **VFS composable strategy chains produce nested folders (up to 3 levels)** ✅
   - 39 unit tests covering parsing, validation, narrowing filters, Pydantic normalization. Chain builder UI with presets browser-verified (14 assertions).

10. **VFS filename templates allow date-prefixed and type-prefixed names** ✅
    - 12 unit tests for all 4 variables, fallbacks, backward compat, dedup. Mount form UI with variable hint.

11. **Explorer left sidebar uses Lucide chevrons** ✅
    - 6/6 sections render SVG chevrons. Rotation on expand/collapse works.

12. **OBJECTS refresh/plus buttons always visible** ✅
    - Header actions opacity is 1 at rest.

13. **DASHBOARDS/WORKFLOWS headers use plus-sign buttons** ✅
    - Plus-buttons open builder tabs. No "New X" tree-leaf entries.

14. **Inference button sizing normalized; Ontology Viewer button is blue/accent** ✅
    - All admin buttons `<button>` at 32px. `.view-leaf--accent .tree-leaf-label` computed as teal accent.

15. **Relationships graph is full-width with horizontal layout** ✅
    - Dagre LR layout at 860×600px container.

16. **User guide covers dashboards and workflows** ✅
    - `docs/guide/28-dashboards-and-workflows.md` (170 lines). 6 glossary entries. README TOC. Navigation chain intact.

17. **All active requirements validated** ✅
    - 13/13 requirements transitioned from active to validated with evidence.

### Definition of Done

- **All slice deliverables complete with passing tests** ✅ — 761 tests pass (was 641 pre-M007; +120 net new)
- **All 13 active requirements validated with evidence** ✅ — See requirement_outcomes above
- **Explorer tree shows generic entries + Saved Views** ✅ — S01 browser verification
- **VFS mounts support type filter, composable chains, filename templates** ✅ — S02+S03 unit tests + browser verification
- **User guide has dashboard/workflow documentation** ✅ — Chapter 28 with glossary entries
- **UI inconsistencies fixed** ✅ — S04 browser verification (9/9 assertions)
- **No conflict markers in any committed file** ✅ — `grep -rn "^<<<<<<< "` returns zero
- **Full test suite passes** ✅ — 761 passed, 0 failed

## Requirement Changes

- VIEW-01: active → validated — 3 generic ViewSpec entries, explorer shows flat entries, 32 unit tests, endpoints return 200
- VIEW-02: active → validated — SHACL column discovery via ShapesService with fallback, proven by unit tests
- VIEW-03: active → validated — Type pills populated from ShapesService.get_types(), localStorage persistence, htmx filtering
- VIEW-04: active → validated — Explorer consolidated: 5 flat entries + Saved Views, no per-model tree, MY VIEWS removed
- VIEW-05: active → validated — Carousel with generic + model-declared specs when type pill active
- VFS-07: active → validated — type_filter VALUES clause, multi-select UI, 6 unit tests
- VFS-08: active → validated — scopeQuery IRI alignment, zero salvaged occurrences, migration function
- VFS-09: active → validated — Preview resolves scope async, returns 404 on missing, 5 unit tests
- VFS-10: active → validated — Path contract in docs/guide/23-vfs.md, 26 unit tests
- VFS-11: active → validated — Composable chains with cumulative narrowing, 39 unit tests, browser UI
- VFS-12: active → validated — Filename templates with 4 variables, 12 unit tests, browser UI
- DOCS-04: active → validated — Chapter 28 covering dashboards/workflows, 6 glossary entries
- UIPOL-01: active → validated — All 6 items browser-verified

## Forward Intelligence

### What the next milestone should know
- Generic views use transient ViewSpec objects — `build_dynamic_query()` creates them per request. The 3 registered specs have empty `sparql_query` fields; queries are built dynamically. This is by design (D093).
- The `pagination_base_url` pattern is now the standard for all URL-generating templates. Any new view endpoints must pass it in template context.
- VFS is feature-complete except write support (VFS-13 deferred). Mount form has grown significantly — strategy chain builder, filename template, type filter multi-select, scope dropdown all in `_vfs_settings.html`.
- All left sidebar sections follow a consistent pattern: Lucide chevron-right SVG + `.expanded` class toggle + optional `explorer-header-actions`. New sections should follow this.
- Dashboard/workflow explorer sections no longer have "New X" tree-leaf entries — action moved to header + buttons. Tests updated to match.
- `shared_nav_content.html` is an htmx response template that replaces `shared_nav_section.html` — changes to SHARED section header need both files.

### What's fragile
- `switchCarouselView()` in workspace.js has two branches (generic IRI vs non-generic) that each do full innerHTML swap differently — changes to either path must consider the other
- `mountStrategyChanged()` scans ALL chain levels for strategy-specific field visibility — adding a new VFS strategy type requires updating both chain level select options and field-visibility logic
- Chain-aware hx-get URLs in `mount_tree_folders.html` use conditional Jinja2 — non-chain mounts must not pass chain_depth context
- The `pag_extra` chaining in pagination templates concatenates with `&` — adding more non-standard params requires careful string concatenation or a proper URL builder

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_dynamic_query_builder.py tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — 130 tests covering all M007 backend logic, <1s
- `GET /browser/views/type-pills?renderer=table` returns full type list — if types missing here, they won't appear as pills
- `rg savedQueryId backend/ frontend/ --exclude migration` — must return zero
- DEBUG logs: `generic_view:`, `build_dynamic_query:`, `Chain dispatch`, `Chain narrowing at depth`, `filename_template expanded`

### What assumptions changed
- All-OPTIONAL SPARQL patterns don't work for default queries — `?s` must be grounded by at least one mandatory triple pattern (D111)
- Generic graph view needs its own data endpoint because spec.sparql_query is empty for generic specs (D112)
- S04 removing tree-leaf entries broke 6 pre-existing M06 tests — fixed during milestone completion
- Chain by-type narrowing uses SPARQL FILTER on local name rather than pre-resolved IRI — works but less efficient than exact match (D123)
- Collision dedup uses IRI SHA-256 hash prefix, not sequential numbering — tests and docs written against actual behavior

## Files Created/Modified

### S01 (Generic Views)
- `backend/app/views/service.py` — build_dynamic_query(), register_generic_views(), get_generic_columns(), generic spec management
- `backend/app/views/router.py` — generic_view, generic_graph_data, type_pills endpoints; pagination_base_url in all contexts
- `backend/app/main.py` — register_generic_views() at startup, ShapesService wiring
- `backend/app/templates/browser/views_explorer.html` — rewritten: flat entries + Saved Views folder
- `backend/app/templates/browser/type_filter_pills.html` — new partial for type filter pills
- `backend/app/templates/browser/pagination.html` — refactored to pagination_base_url | default()
- `backend/app/templates/browser/view_toolbar.html` — refactored filter URL
- `backend/app/templates/browser/table_view.html` — refactored sort headers, conditional pills include
- `backend/app/templates/browser/cards_view.html` — refactored group-by, conditional pills include
- `backend/app/templates/browser/graph_view.html` — graph_data_url support, conditional pills include
- `frontend/static/js/workspace.js` — openGenericViewTab(), loadViewContent() generic routing, carousel, localStorage
- `frontend/static/js/workspace-layout.js` — generic-view specialType handler
- `frontend/static/js/graph.js` — optional customDataUrl parameter
- `frontend/static/css/views.css` — type pill styles
- `backend/app/templates/browser/workspace.html` — MY VIEWS section removed
- `backend/app/templates/browser/my_views.html` — target ID updated to #saved-views-tree
- `frontend/static/js/sparql-console.js` — refreshMyViews() target updated
- `backend/tests/test_dynamic_query_builder.py` — 32 unit tests

### S02 (VFS Quick Wins)
- `backend/app/vfs/mount_service.py` — type_filter field, scope_query IRI, sync CRUD
- `backend/app/vfs/mount_router.py` — type_filter in Pydantic models, async CRUD, preview scope resolution
- `backend/app/vfs/strategies.py` — build_scope_filter refactored to parts-list, VALUES clause, query resolution
- `backend/app/vfs/mount_collections.py` — sync_client passthrough
- `backend/app/vfs/cache.py` — query_text: key clearing
- `backend/app/vfs/migrations.py` — new: savedQueryId→scopeQuery migration
- `backend/app/browser/workspace.py` — renamed imports/function/SPARQL vars
- `backend/app/templates/browser/_vfs_settings.html` — type filter checkbox container
- `frontend/static/js/workspace.js` — scope_query IRI handling, type filter fetch/populate
- `frontend/static/css/workspace.css` — type filter container styles
- `backend/tests/test_vfs_scope.py` — 11 new tests
- `backend/tests/test_vfs_path_contract.py` — 26 new tests
- `docs/guide/23-vfs.md` — Path Contract section

### S03 (VFS Chains & Templates)
- `backend/app/vfs/mount_service.py` — strategy_chain/is_chain properties, filename_template, validation
- `backend/app/vfs/mount_collections.py` — chain-aware StrategyFolderCollection, template expansion
- `backend/app/vfs/provider.py` — _resolve_mount_path() extended for chain paths
- `backend/app/vfs/strategies.py` — build_chain_narrowing_filter(), dcterms:created OPTIONAL in query builders
- `backend/app/vfs/mount_router.py` — str | list[str] strategy, chain preview, filename_template CRUD
- `backend/app/browser/workspace.py` — mount_children chain dispatch, _get_strategy_folders()
- `backend/app/templates/browser/_vfs_settings.html` — chain builder UI, filename template input
- `backend/app/templates/browser/mount_tree_folders.html` — chain-aware hx-get URLs
- `frontend/static/js/workspace.js` — chain management, updated form functions
- `frontend/static/css/workspace.css` — chain builder styles
- `backend/tests/test_vfs_scope.py` — 39 new tests
- `backend/tests/test_vfs_path_contract.py` — 12 new tests

### S04 (UI Polish)
- `backend/app/templates/browser/workspace.html` — chevron replacements, DASHBOARDS/WORKFLOWS header actions
- `backend/app/templates/browser/partials/favorites_section.html` — chevron replacement
- `backend/app/templates/browser/partials/shared_nav_section.html` — chevron replacement
- `backend/app/templates/browser/partials/shared_nav_content.html` — chevron replacement (htmx template)
- `backend/app/templates/browser/dashboard_explorer.html` — "New Dashboard" tree-leaf removed
- `backend/app/templates/browser/workflow_explorer.html` — "New Workflow" tree-leaf removed
- `backend/app/templates/admin/models.html` — inference button <a>→<button>
- `backend/app/templates/browser/views_explorer.html` — view-leaf--accent on Ontology Viewer
- `backend/app/templates/admin/model_ontology_diagram.html` — dagre LR layout
- `frontend/static/css/workspace.css` — chevron SVG styling, opacity, accent class
- `frontend/static/css/style.css` — ontology container min-height

### S05 (Docs)
- `docs/guide/28-dashboards-and-workflows.md` — Chapter 28 (dashboards + workflows)
- `docs/guide/appendix-d-glossary.md` — 6 glossary entries
- `docs/guide/README.md` — Chapter 28 in TOC
- `docs/guide/27-spatial-canvas.md` — next link updated

### Milestone Completion
- `backend/tests/test_dashboard_builder.py` — removed "New Dashboard" assertions from explorer tests (S04 moved to header)
- `backend/tests/test_workflow_builder.py` — removed "New Workflow" assertions from explorer tests (S04 moved to header)
