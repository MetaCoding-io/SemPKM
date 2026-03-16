# S01: Generic Views & Explorer Consolidation — UAT

**Milestone:** M007
**Written:** 2026-03-16

## UAT Type

- UAT mode: mixed (artifact-driven for unit tests + live-runtime for browser verification)
- Why this mode is sufficient: Unit tests prove query builder correctness; browser verification proves UI integration. The combination covers contract + integration levels without needing human gut-check.

## Preconditions

- Docker stack running (`docker compose up -d` from project root)
- At least one Mental Model installed (basic-pkm) with some seed objects
- Browser pointed at `http://localhost:3000`
- Logged in as any user

## Smoke Test

Click "Table View" in the explorer VIEWS section → a new tab opens showing all objects in a table with columns: label, type, created, modified. Type filter pills appear above the table.

## Test Cases

### 1. Unit tests pass

1. `cd backend && uv run --extra dev python -m pytest tests/test_dynamic_query_builder.py -v`
2. **Expected:** 32/32 tests pass in <2 seconds

### 2. Explorer VIEWS section shows correct entries

1. Open the workspace at `/browser/workspace`
2. Look at the VIEWS section in the left sidebar explorer
3. **Expected:** Exactly these entries visible: Spatial Canvas (Beta), Ontology Viewer, Table View, Cards View, Graph View, and a collapsible "Saved Views" folder
4. **Expected:** No per-model folders (e.g., no "Basic PKM" group), no per-type entries (e.g., no "Note Table View")

### 3. MY VIEWS section is gone

1. Look at the left sidebar below VIEWS section
2. **Expected:** No "MY VIEWS" section exists. Saved/promoted views are inside the "Saved Views" folder in VIEWS.

### 4. Table View opens from explorer

1. Click "Table View" in the VIEWS section
2. **Expected:** A dockview tab opens titled "Table View"
3. **Expected:** Table shows all objects with columns: label, type, created, modified
4. **Expected:** Filter toolbar visible at top
5. **Expected:** Type filter pills visible above the table content

### 5. Cards View opens from explorer

1. Click "Cards View" in the VIEWS section
2. **Expected:** A dockview tab opens titled "Cards View"
3. **Expected:** Cards layout with "Group by" dropdown visible
4. **Expected:** Type filter pills visible above cards

### 6. Graph View opens from explorer

1. Click "Graph View" in the VIEWS section
2. **Expected:** A dockview tab opens titled "Graph View"
3. **Expected:** Cytoscape.js graph renders with nodes and edges
4. **Expected:** Type filter pills visible above graph

### 7. Tab deduplication works

1. Click "Table View" in explorer → tab opens
2. Click "Table View" in explorer again
3. **Expected:** The existing Table View tab activates — no duplicate tab created

### 8. Type pill filtering (Table View)

1. Open Table View (or activate existing tab)
2. Note the "All Types" pill is active (highlighted)
3. Click a type pill (e.g., "Note" or "Project")
4. **Expected:** Table reloads showing only objects of that type
5. **Expected:** Column headers change to SHACL-discovered properties for that type (e.g., for Note: title, body, noteType, etc.)
6. **Expected:** "All Types" pill is no longer active; the clicked pill is active

### 9. Type pill "All Types" reset

1. With a type pill selected (from test 8), click "All Types"
2. **Expected:** Table shows all objects again with default columns (label, type, created, modified)
3. **Expected:** "All Types" pill is active

### 10. Carousel appears for typed view

1. Open Table View, click a type pill (e.g., "Note")
2. **Expected:** Carousel tab bar appears below the type pills, showing tabs like "Table", "Cards", "Graph" plus any model-declared views for that type
3. Click "Cards" in the carousel
4. **Expected:** View switches to cards layout for the same filtered type

### 11. Carousel hidden for "All Types"

1. Click "All Types" pill
2. **Expected:** Carousel tab bar disappears (or shows only generic renderers)

### 12. Type selection persists in localStorage

1. Open Table View, click a type pill
2. Open browser DevTools → Application → Local Storage
3. **Expected:** Key `sempkm_generic_type_table` contains the selected type IRI
4. Close and reopen the Table View tab
5. **Expected:** The previously selected type is restored

### 13. Pagination works in generic table

1. Open Table View with enough objects to paginate (>25)
2. **Expected:** Pagination controls appear at bottom
3. Click page 2 (or Next)
4. **Expected:** Next page loads correctly, URL updates, type filter (if any) persists

### 14. Filter toolbar works

1. Open Table View, type a search term in the filter input
2. **Expected:** Table filters to matching objects
3. **Expected:** With a type pill selected, filter applies within that type

### 15. Sort headers work in generic table

1. Open Table View, click a column header (e.g., "label")
2. **Expected:** Table sorts by that column
3. **Expected:** Sort direction indicator changes on second click

### 16. Saved Views folder

1. Expand the "Saved Views" folder in VIEWS section
2. **Expected:** Shows promoted query views (or "No promoted views yet" if none exist)

### 17. Spatial Canvas still works

1. Click "Spatial Canvas (Beta)" in VIEWS
2. **Expected:** Canvas tab opens normally — no regression

### 18. Ontology Viewer still works

1. Click "Ontology Viewer" in VIEWS
2. **Expected:** Ontology Viewer tab opens normally — no regression

### 19. Existing model-declared views still work

1. Open a model-declared view (e.g., from a type pill → carousel → model view tab)
2. **Expected:** View renders correctly with its own pagination, sort, and filter — no regression from pagination_base_url refactor

## Edge Cases

### Invalid renderer returns 404

1. Navigate directly to `/browser/views/generic/invalid`
2. **Expected:** 404 HTML page (not a 500 crash)

### Type pills with no objects of a type

1. Open Table View, click a type pill for a type with zero objects
2. **Expected:** Empty table with "No objects found" message (not an error)

### SHACL column fallback for sparse types

1. If a type has ≤2 SHACL properties, open Table View and select that type
2. **Expected:** Table falls back to default columns (label, type, created, modified) rather than showing only 1-2 sparse columns

### Graph View data endpoint

1. Navigate directly to `/browser/views/generic/graph/data`
2. **Expected:** JSON response with `nodes` and `edges` arrays

### Type pills endpoint

1. Navigate to `/browser/views/type-pills?renderer=table`
2. **Expected:** JSON with type entries including IRI, label, and href fields

## Failure Signals

- Table View shows 0 rows when objects exist in the triplestore → check `_build_default_select()` query has mandatory rdf:type binding
- Type pill click causes 500 error → check `build_dynamic_query(type_iri)` and ShapesService availability
- Carousel doesn't appear when type selected → check `all_specs` template variable and `get_view_specs_for_type()` return
- Pagination links go to wrong URLs → check `pagination_base_url` and `pag_extra` template variables
- Sort headers 404 → check `sort_base` uses `pagination_base_url | default()`
- Explorer still shows per-model folders → check `views_explorer.html` template was fully replaced
- MY VIEWS section visible → check `workspace.html` for `section-my-views` div
- Saved Views content fails to load → check `#saved-views-tree` ID matches in `my_views.html`
- Graph View shows no data → check `graph_data_url` template variable and `customDataUrl` param in `initGraph()`

## Requirements Proved By This UAT

- VIEW-01 — Tests 2, 4, 5, 6 prove 3 generic entries in explorer opening cross-type views
- VIEW-02 — Tests 8, 9, edge case "sparse types" prove SHACL column discovery with fallback
- VIEW-03 — Tests 8, 9, 12 prove type pills with filtering, persistence, and "All Types" reset
- VIEW-04 — Tests 2, 3, 16 prove explorer consolidation with Saved Views, no per-type tree, no MY VIEWS
- VIEW-05 — Tests 10, 11 prove carousel shows model-declared views when type selected

## Not Proven By This UAT

- Performance under large object counts (hundreds of types, thousands of objects) — would need load testing
- Type pill usability with >15 types — pills may overflow and need scrolling or a different UI pattern
- Carousel behavior with many model-declared views per type — layout overflow not tested

## Notes for Tester

- The triplestore must have objects of multiple types to fully test type pills and column switching. If running on a fresh install, import a vault or create objects of different types first.
- The "Saved Views" folder may show "No promoted views yet" if no queries have been promoted — this is correct behavior.
- Sort headers only appear in Table View, not Cards or Graph.
- The Graph View may take a moment to render if there are many objects — LIMIT 200 caps the CONSTRUCT query.
