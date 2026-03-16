# M007: Generic Views, VFS Completion & Polish

**Vision:** Users browse all objects through generic Table/Cards/Graph views with SHACL-driven dynamic columns and type filter pills, replacing the per-type explorer clutter. VFS mounts gain type filters, query IRI alignment, composable strategy chains, and filename templates. UI inconsistencies are fixed and M006 features are documented.

## Success Criteria

- Explorer VIEWS section shows 3 generic entries (Table View, Cards View, Graph View) + Saved Views folder — no per-type folders
- Opening Table View shows all objects with common columns (label, type, created, modified)
- Clicking a type pill filters the view and columns change to SHACL-discovered properties
- Carousel tab bar shows model-declared view variants when a type is selected
- VFS mount with `sempkm:typeFilter` restricts objects to specified types
- VFS `sempkm:savedQueryId` renamed to `sempkm:scopeQuery` with full IRI storage
- VFS preview endpoint resolves saved query scope and honors type_filter
- VFS path contract (IRI→path, path→IRI) is documented and tested
- VFS composable strategy chains produce nested folders (up to 3 levels)
- VFS filename templates allow date-prefixed and type-prefixed names
- Explorer left sidebar uses Lucide chevrons (matching right sidebar)
- OBJECTS refresh/plus buttons are always visible (not hover-only)
- DASHBOARDS/WORKFLOWS headers use plus-sign buttons (no "New X" tree-leaf entries)
- Inference button sizing normalized; Ontology Viewer button is blue/accent
- Relationships graph is full-width with horizontal layout
- User guide covers dashboards and workflows (new page in docs/guide/)
- All active requirements (VIEW-01–05, VFS-07–12, DOCS-04, UIPOL-01) are validated

## Key Risks / Unknowns

- **Generic view performance** — Cross-type table with no filter could return hundreds of objects. Need sensible LIMIT + pagination. Existing `execute_table_query()` already paginates — should be fine.
- **SHACL column discovery edge cases** — Types with sparse shapes (≤2 properties) fall back to default columns. User-created types may have minimal shapes.
- **Composable strategy chains** — Provider path dispatch needs extension from 4 to 6 segments. Medium complexity.
- **Explorer tree removal** — Removing per-type folders changes navigation. Type pills + carousel provide equivalent access but users may initially be disoriented.

## Proof Strategy

- **Generic views** → retire in S01 by proving: open Table View → all objects shown → click type pill → SHACL columns appear → carousel shows model views
- **VFS completion** → retire in S02/S03 by proving: type filter VALUES clause works, preview resolves scope, strategy chains produce nested folders
- **UI polish** → retire in S04 by proving: chevrons match, buttons visible, sizing normalized

## Verification Classes

- Contract verification: pytest unit tests for SHACL column discovery, dynamic query building, type filter VALUES injection, strategy chain nesting
- Integration verification: browser tests for generic views with real triplestore data, VFS mount filtering
- Operational verification: all features persist across Docker restart
- UAT / human verification: explorer tree is clean and scannable, generic views feel intuitive

## Milestone Definition of Done

- All slice deliverables complete with passing tests
- All 13 active requirements validated with evidence
- Explorer tree shows generic entries + Saved Views (no per-type folders)
- VFS mounts support type filter, composable chains, and filename templates
- User guide has dashboard/workflow documentation
- UI inconsistencies fixed (chevrons, buttons, graph layout)
- No conflict markers in any committed file
- Full test suite passes

## Requirement Coverage

- Covers: VIEW-01, VIEW-02, VIEW-03, VIEW-04, VIEW-05, VFS-07, VFS-08, VFS-09, VFS-10, VFS-11, VFS-12, DOCS-04, UIPOL-01
- Leaves for later: VIEW-06 (custom column UI), VIEW-07 (faceted search), VFS-13 (write support)

## Slices

- [x] **S01: Generic Views & Explorer Consolidation** `risk:medium` `depends:[]`
  > After this: 3 generic views (Table/Cards/Graph) in explorer with SHACL-driven columns, type filter pills, carousel integration, Saved Views folder; no per-type folders
  > Covers: VIEW-01, VIEW-02, VIEW-03, VIEW-04, VIEW-05

- [x] **S02: VFS Quick Wins — Type Filter, Query IRI, Preview** `risk:low` `depends:[]`
  > After this: VFS mounts support type filter (VALUES clause, AND-composed with scope), scopeQuery predicate with full IRI, preview resolves saved query scope, path contract documented and tested
  > Covers: VFS-07, VFS-08, VFS-09, VFS-10

- [x] **S03: VFS Composable Chains & Filename Templates** `risk:medium` `depends:[S02]`
  > After this: VFS strategy field accepts ordered list for multi-level folders (max 3), provider path dispatch extended to 6 segments, UI with + button and predefined combos; filename_template field with {title}/{date}/{type}/{id} variables
  > Covers: VFS-11, VFS-12

- [x] **S04: UI Polish & Consistency** `risk:low` `depends:[]`
  > After this: Left sidebar chevrons use Lucide icons; OBJECTS actions always visible; DASHBOARDS/WORKFLOWS use header plus-signs; inference button normalized; Ontology Viewer button blue; relationships graph full-width horizontal
  > Covers: UIPOL-01

- [x] **S05: Dashboard & Workflow User Guide** `risk:low` `depends:[]`
  > After this: docs/guide/ has page(s) covering dashboard creation/editing/rendering/cross-view-context, workflow creation/running/editing, explorer sections; glossary updated
  > Covers: DOCS-04

## Boundary Map

### S01 (Generic Views) — independent

Produces:
- 3 generic ViewSpec instances registered at startup in ViewSpecService
- `build_dynamic_query()` method using ShapesService for SHACL column discovery
- `GET /browser/views/generic/{renderer}` endpoint with `?type=` filter
- `type_filter_pills.html` partial template + `GET /browser/views/type-pills` endpoint
- Rewritten `views_explorer.html` with generic entries + Saved Views folder
- `openGenericViewTab()` JS function + `generic-view` specialType
- Carousel tab bar wiring for type-filtered model views

Consumes:
- ShapesService.get_form_for_type() — existing
- ShapesService.get_types() — existing
- carousel_tab_bar.html + switchCarouselView() — existing
- scope_to_current_graph() — existing

### S02 (VFS Quick Wins) — independent

Produces:
- `type_filter` field on MountDefinition + VALUES clause in build_scope_filter()
- Type multi-select in mount form UI
- `sempkm:scopeQuery` predicate (renamed from savedQueryId) with full IRI
- Migration SPARQL UPDATE for existing mounts
- Preview endpoint resolving saved query scope via async TriplestoreClient
- Path contract documentation + slug/dedup test coverage

Consumes:
- Nothing new (extends existing VFS infrastructure)

### S02 → S03

Produces:
- `strategy` field as `str | list[str]` (backward compatible)
- Generalized folder nesting in WebDAV collections via parent_folder_value
- Provider path dispatch extended to 6 segments
- Chain UI with + button (max 3 levels) and predefined combos
- `filename_template` field with variable expansion in _build_file_map_from_bindings()

Consumes:
- S02: Updated MountDefinition fields and build_scope_filter()

### S04 (UI Polish) — independent

Produces:
- Lucide chevron-right icons in left sidebar explorer sections
- Always-visible OBJECTS header actions (opacity:1 default)
- Plus-sign buttons in DASHBOARDS/WORKFLOWS headers
- Normalized inference button + blue Ontology Viewer button
- Full-width horizontal Cytoscape relationship graph

Consumes:
- Nothing (pure CSS/template changes)

### S05 (Docs) — independent

Produces:
- docs/guide/28-dashboards-and-workflows.md (or split pages)
- Glossary updates in appendix-d-glossary.md

Consumes:
- Nothing (documentation only)
