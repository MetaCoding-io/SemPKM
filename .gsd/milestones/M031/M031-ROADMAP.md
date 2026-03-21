# M031: Views Overhaul, Saved Queries as First-Class, & UI Polish

**Vision:** Users control what they see through the explorer sidebar, not through an in-view carousel picker. Saved queries are prominent throughout the UI. Several UX gaps in SPARQL console, ontology viewer, admin model graph, and dashboard/workflow builders are fixed.

## Success Criteria

- User clicks "Table View" / "Cards View" / "Graph View" in the explorer and gets that view immediately — no carousel tab bar inside the view
- Model-declared view variants (e.g., "Projects Table") are accessible via a view toolbar dropdown and/or the Saved Views folder — not lost after carousel removal
- Each view (table, cards, graph) accepts an optional saved query as its data scope, selectable from a toolbar dropdown
- Users can open multiple instances of the same view type as tabs with different scopes
- Saved Views folder in explorer loads correctly, showing saved view entries with renderer type icons, labels, and unpin actions
- Users can save any current view configuration as a named saved view
- Kanban view renders status-based columns with drag-drop to change status
- All views use 100% of available height — no unnecessary outer scrollbar on the view container
- Graph view node popover appears above the top toolbar (z-index fix)
- SPARQL console IRI pills render correctly for all `urn:sempkm:model:*` prefixes and no IRIs fall through to plain `<span class="sparql-uri">`
- Ontology TBox property names show `rdfs:comment` / `skos:definition` tooltips on hover
- Admin model graph is full-width/full-height with edge hover tooltips
- Dashboard and workflow builder forms have contextual help text and autocomplete for object/type references

## Key Risks / Unknowns

- **Carousel removal breaks model-declared view access** — The carousel is currently the ONLY surface for model-declared ViewSpecs when a type filter pill is active. Removing it without an alternative loses access to type-specific views like "Projects Table" or "Contacts Pipeline". This is the highest risk because it touches the core view routing in `workspace.js` and `views/router.py`.
- **Multiple view instances conflict with dockview tab deduplication** — `openGenericViewTab()` creates tabs with IDs like `generic-view-table`. Opening a second table view with a different scope needs unique tab IDs, and dockview's `addPanel` logic must handle this without breaking existing tab management.
- **Kanban drag-drop conflicts with dockview** — dockview's panel drag system may intercept drag events intended for kanban column reordering. Needs `stopPropagation()` isolation (same pattern as canvas resize handles, D127/CANVAS-01).
- **Full-height CSS propagation** — The container hierarchy (dockview panel → special-panel wrapper → htmx-loaded content) requires each layer to propagate height correctly. Getting this wrong causes views to collapse or double-scroll.

## Proof Strategy

- **Carousel removal + model-declared view access** → retire in S01 by proving: user opens Table View from explorer, selects a type filter pill, sees model-declared variants in a toolbar dropdown, selects one, and the correct view renders. No carousel visible anywhere.
- **Multiple view instances** → retire in S02 by proving: two tabs of the same view type open simultaneously with different query scopes, each showing different filtered data.
- **Kanban drag-drop isolation** → retire in S04 by proving: drag-drop between kanban columns changes object status without triggering dockview panel drag.

## Verification Classes

- Contract verification: backend unit tests for new endpoints, SPARQL query builders, view toolbar logic
- Integration verification: E2E Playwright tests against Docker stack proving carousel removal, scope binding, saved views, kanban drag-drop, SPARQL IRI pills, ontology tooltips
- Operational verification: none (no new services or lifecycle changes)
- UAT / human verification: visual confirmation of full-height views, z-index fixes, tooltip rendering

## Milestone Definition of Done

This milestone is complete only when all are true:

- Carousel tab bar is completely removed from all view templates and workspace.js
- Model-declared view variants are accessible via the view toolbar dropdown when a type is selected
- Saved query scope dropdown works on all view types (table, cards, graph, kanban)
- Multiple view instances open as separate tabs with independent scopes
- Saved Views folder renders correctly with CRUD operations
- Kanban renderer works with status-based columns and drag-drop
- All views use 100% available height
- Graph view popover z-index is fixed
- SPARQL console prefix shortening and IRI pill fixes are deployed
- Ontology property tooltips and admin graph improvements are deployed
- Dashboard/workflow builder UX improvements are deployed
- E2E tests cover all new and changed user-visible behavior
- User guide docs updated for all new features
- Success criteria are re-checked against live behavior

## Requirement Coverage

### New Requirements for M031

| ID | Description | Priority | Primary Slice |
|----|-------------|----------|---------------|
| VIEW-08 | Carousel removal — explorer sidebar is sole view selector | Must-have | S01 |
| VIEW-09 | Saved query scope binding on all view types | Must-have | S01 |
| VIEW-10 | Multiple view instances as tabs with different scopes | Should-have | S02 |
| VIEW-11 | Saved views load/display/create/unpin correctly | Must-have | S02 |
| VIEW-12 | Kanban renderer with status-based columns and drag-drop | Should-have | S04 |
| VIEW-13 | All views use 100% available height | Must-have | S05 |
| VIEW-14 | Graph view node popover z-index fix | Must-have | S05 |
| SQ-01 | Saved queries accessible in explorer sidebar | Should-have | S03 |
| SQ-02 | Saved queries as canvas embed source | Nice-to-have | S03 |
| SQ-03 | Saved queries in object browser dropdown | Nice-to-have | S03 |
| SPARQL-09 | Graph visualization tab for triple-pattern SPARQL results | Should-have | S05 |
| SPARQL-10 | Fix IRI pills falling through to plain spans | Must-have | S05 |
| SPARQL-11 | Dynamic model prefix shortening in shortenUri() | Should-have | S05 |
| ONTO-04 | Property description tooltips in TBox detail | Should-have | S05 |
| ONTO-05 | Admin model graph full-width/full-height | Should-have | S05 |
| ONTO-06 | Edge tooltips in admin model graph | Nice-to-have | S05 |
| DBUIX-01 | Dashboard/workflow builder help text | Should-have | S06 |
| DBUIX-02 | Autocomplete for object/type references in builders | Should-have | S06 |
| DBUIX-03 | Workflow view step simplification | Should-have | S06 |
| DBUIX-04 | Sample dashboard and workflow seed data | Nice-to-have | S06 |

### Coverage Summary

- Covers: VIEW-08, VIEW-09, VIEW-10, VIEW-11, VIEW-12, VIEW-13, VIEW-14, SQ-01, SQ-02, SQ-03, SPARQL-09, SPARQL-10, SPARQL-11, ONTO-04, ONTO-05, ONTO-06, DBUIX-01, DBUIX-02, DBUIX-03, DBUIX-04
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — all 20 candidate requirements are mapped to slices

## Slices

- [x] **S01: Carousel Removal + View Scope Binding** `risk:high` `depends:[]`
  > After this: User clicks "Table View" in explorer and gets a table view with no carousel. Type filter pills still work. A view toolbar dropdown shows model-declared view variants when a type is selected, and a separate scope dropdown lets users filter by saved query. Opening a model-declared view (e.g., "Projects Table") from the toolbar dropdown renders correctly.

- [x] **S02: Multiple View Instances + Saved Views Fix** `risk:medium` `depends:[S01]`
  > After this: User can open two graph views as separate tabs with different saved query scopes. The Saved Views folder in the explorer loads entries correctly. User can save the current view configuration as a named saved view and reopen it later.

- [x] **S03: Saved Queries Everywhere** `risk:low` `depends:[S01]`
  > After this: Saved queries appear as a dedicated section in the explorer sidebar. Users can drag a saved query onto the spatial canvas to create a scoped view widget. Object browser dropdown has a "scope by query" option. VFS browser scope works correctly with saved queries.

- [ ] **S04: Kanban Renderer** `risk:medium` `depends:[S01]`
  > After this: User opens "Kanban View" from explorer, sees status-based columns (todo, in-progress, done, etc.), and can drag tasks between columns to change their status. Type filter pills filter which objects appear in the kanban.

- [ ] **S05: SPARQL + Ontology + Graph + Full-Height Polish** `risk:low` `depends:[S01]`
  > After this: SPARQL console correctly shortens all `urn:sempkm:model:*` IRIs, no pills fall through to plain spans, and triple-pattern results have a graph visualization tab. TBox property names show description tooltips. Admin model graph is full-viewport with edge hover tooltips. All views use 100% available height. Graph node popover renders above the toolbar.

- [ ] **S06: Dashboard & Workflow Builder UX** `risk:low` `depends:[]`
  > After this: Dashboard and workflow builder forms have contextual help text following the SHACL helptext pattern. Object/type reference fields have autocomplete. Workflow "view" step uses a view/saved-view picker instead of a raw renderer dropdown. Sample dashboards and workflows appear as seed data fixtures.

- [ ] **S07: E2E Tests + User Guide Docs** `risk:low` `depends:[S01,S02,S03,S04,S05,S06]`
  > After this: Playwright E2E tests cover carousel removal, scope binding, saved views, kanban, SPARQL fixes, ontology tooltips, builder UX. User guide pages document all new features. Standing requirements fully satisfied.

## Boundary Map

### S01 → S02

Produces:
- View toolbar with saved query scope dropdown (`view_toolbar.html` + JS handlers)
- View toolbar with model-declared variant dropdown when type filter is active
- `scope_query` URL parameter on generic view endpoints (`views/router.py`)
- `openGenericViewTab()` updated to accept scope parameters (`workspace.js`)
- Carousel tab bar fully removed from all templates and JS

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- Saved query scope dropdown pattern in view toolbar (reusable for other surfaces)
- `scope_query` parameter wiring on generic view endpoints

Consumes:
- nothing (first slice)

### S01 → S04

Produces:
- Generic view endpoint pattern with type filter pills and scope query support
- View toolbar template with dropdown slots

Consumes:
- nothing (first slice)

### S01 → S05

Produces:
- Carousel-free view templates (clean CSS/JS foundation for height fixes)

Consumes:
- nothing (first slice)

### S02 → S07

Produces:
- Working saved views CRUD (create/list/open/unpin)
- Multiple view instance tab IDs

Consumes:
- S01 view toolbar and scope binding

### S04 → S07

Produces:
- Working kanban renderer with drag-drop status changes
- Explorer entry for Kanban View

Consumes:
- S01 generic view endpoint pattern

### S05 → S07

Produces:
- Fixed SPARQL IRI pills and prefix shortening
- Ontology property tooltips
- Full-height CSS and graph z-index fix
- SPARQL graph visualization tab

Consumes:
- S01 carousel-free view templates

### S06 → S07

Produces:
- Builder help text and autocomplete
- Simplified workflow view step
- Sample seed data

Consumes:
- nothing (independent)
