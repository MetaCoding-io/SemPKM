# Views Rethink Design

> **Status:** Proposed  
> **Date:** 2026-03-14  
> **Scope:** Redesign how views are accessed and organized — shift from per-type explorer entries to generic cross-type views with SHACL-driven columns, query-scoped view binding, and carousel-based type-specific rendering. Implementable in one milestone.

---

## Summary

Two installed models produce 31 ViewSpec entries in the explorer sidebar. Every additional model type adds 3 more entries (table/cards/graph). The problem is not the ViewSpec data model — which is clean and extensible — but the **explorer tree presentation** and the **lack of generic cross-type views**.

This document proposes:
1. **Generic system-provided views** (Table / Cards / Graph) that work across all types with dynamic column discovery from SHACL shapes
2. **Explorer tree consolidation** from 31+ entries → ~7 fixed entries + Saved Views folder
3. **Model-declared views as carousel tabs** when a type is selected, not 12+ separate explorer entries
4. **Query scope binding** via `sempkm:scopeQuery` predicate, linking views to saved queries by IRI

The approach follows the hybrid model from M005-RESEARCH.md (Option 3): model-declared rich views coexist with a new generic layer. All proposals reference existing extension points — no speculative abstractions.

---

## Current State

### ViewSpec Scaling Problem

`ViewSpecService.get_all_view_specs()` (in `backend/app/views/service.py`) queries all installed models' views graphs using a `VALUES` clause + `GRAPH ?g` pattern. Each model ships ViewSpecs in its views graph (`urn:sempkm:model:{id}:views`):

| Model | File | ViewSpecs | Named Queries | Types Covered |
|-------|------|-----------|---------------|---------------|
| basic-pkm | `models/basic-pkm/views/basic-pkm.jsonld` | 12 | 3 | 4 types × 3 renderers |
| ppv | `models/ppv/views/ppv.jsonld` | 19 | 0 | ~6 types × 3 renderers + extras |
| **Total** | | **31** | **3** | |

Each type gets 3 entries (table, card, graph). Adding a new model with 5 types adds 15 entries. At 5 models the tree would have 75+ entries — unusable.

### Explorer Tree Structure (Current)

`backend/app/templates/browser/views_explorer.html` renders the tree:

```
VIEWS                              ← sidebar section
  ◻ Spatial Canvas (Beta)          ← hardcoded special entry
  ◆ Ontology Viewer                ← hardcoded special entry
  📁 bpkm:Note                    ← type folder (truncated IRI)
    ▦ Notes Table                  ← ViewSpec: table renderer
    🃏 Note Cards                  ← ViewSpec: card renderer
    ◎ Notes Graph                  ← ViewSpec: graph renderer
  📁 bpkm:Project                  ← another type folder
    ▦ Projects Table
    🃏 Project Cards
    ◎ Projects Graph
  ... (repeated for all 10+ types across models)

MY VIEWS                           ← separate sidebar section
  ▦ My Custom View                 ← promoted query → view
```

**Problems:**
- 31+ leaf entries grouped by truncated type IRI — hard to scan
- Folder labels are raw QNames (`bpkm:Note`), not human-readable labels
- Every model install adds N×3 entries with no consolidation
- VIEWS and MY VIEWS are separate sidebar sections — no unified "views" concept
- No way to see all objects across types without picking a type-specific view

### What Works Well (Keep)

- **ViewSpec data model** — `ViewSpec` dataclass has all needed fields (spec_iri, label, target_class, renderer_type, sparql_query, columns, etc.)
- **Renderer execution** — `execute_table_query()`, `execute_cards_query()`, `execute_graph_query()` are proven, paginated patterns
- **Carousel tab bar** — `carousel_tab_bar.html` + `switchCarouselView()` already switches between Table/Cards/Graph for a given type, with localStorage persistence
- **Promoted views** — `QueryService.promote_query()` creates `PromotedViewData` RDF resources referencing saved queries by IRI
- **Label resolution** — `LabelService.resolve_batch()` provides batch IRI→label for column headers, type names
- **RENDERER_REGISTRY** — `backend/app/views/registry.py` maps renderer type strings → template paths; extensible

---

## Proposed Data Model

### Generic System-Provided Views

Three system-level views replace the per-type tree entries as primary navigation:

```turtle
@prefix sempkm: <urn:sempkm:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Generic table view — shows all object types
<urn:sempkm:view:generic-table> a sempkm:ViewSpec ;
    rdfs:label "All Objects (Table)" ;
    sempkm:rendererType "table" ;
    sempkm:isGeneric "true"^^xsd:boolean ;
    sempkm:sortDefault "dcterms:modified" .

# Generic cards view
<urn:sempkm:view:generic-cards> a sempkm:ViewSpec ;
    rdfs:label "All Objects (Cards)" ;
    sempkm:rendererType "card" ;
    sempkm:isGeneric "true"^^xsd:boolean .

# Generic graph view
<urn:sempkm:view:generic-graph> a sempkm:ViewSpec ;
    rdfs:label "All Objects (Graph)" ;
    sempkm:rendererType "graph" ;
    sempkm:isGeneric "true"^^xsd:boolean .
```

Generic views differ from model-declared views:
- **No `sempkm:targetClass`** — they operate across all types (or are filtered at runtime via type filter pills)
- **No `sempkm:sparqlQuery`** — the query is built dynamically from SHACL shapes and current filters
- **`sempkm:isGeneric true`** — marks them for special handling in the explorer tree and query builder

These are registered in `ViewSpecService` at startup, not loaded from model views graphs.

### SHACL Column Discovery

When a generic table view needs columns for a given type, it discovers them from SHACL shapes via `ShapesService`:

```
ShapesService._extract_node_shape(graph, shape_iri)
  → NodeShapeForm
    → properties: List[PropertyShape]
      → PropertyShape.path    # property IRI (e.g., dcterms:title)
      → PropertyShape.name    # column header (e.g., "Title")
      → PropertyShape.datatype # xsd:string, xsd:dateTime, etc.
      → PropertyShape.order   # sh:order for column ordering
```

**Column discovery algorithm:**

1. Get the type IRI from user selection (type filter pill) or from `sempkm:targetClass` (model view)
2. Call `ShapesService.get_shapes_for_class(type_iri)` to get the `NodeShapeForm`
3. Sort `PropertyShape` entries by `sh:order` (ascending), fall back to alphabetical by `sh:name`
4. Map each `PropertyShape` to a table column: `path` → SPARQL variable, `name` → header label, `datatype` → cell formatter
5. Build a dynamic SPARQL SELECT with these columns:

```sparql
SELECT ?s ?type ?label ?col1 ?col2 ?col3
WHERE {
  ?s a ?type .
  ?s rdfs:label ?label .
  OPTIONAL { ?s <path1> ?col1 }
  OPTIONAL { ?s <path2> ?col2 }
  OPTIONAL { ?s <path3> ?col3 }
}
ORDER BY DESC(?col_sort)
LIMIT 51
```

6. Pass through `scope_to_current_graph()` to inject `FROM <urn:sempkm:current>` — mandatory for all view queries

**Fallback for types with sparse SHACL:** If a type's NodeShape has ≤2 properties (e.g., only `dcterms:title` and `dcterms:description`), fall back to a default column set: label, type, created, modified. This covers user-created types (TYPE-01/TYPE-02 from M003) that have minimal shape definitions.

**Caching:** `ShapesService` already caches internally. The shapes→columns mapping should be cached in `ViewSpecService` with the same 300s TTL used by the existing `TTLCache`.

### Query Scope Binding

Views can be scoped to a saved query via the `sempkm:scopeQuery` predicate, linking a view to a query by IRI:

```turtle
@prefix sempkm: <urn:sempkm:> .

# A view scoped to a specific saved query
<urn:sempkm:view:my-research-table> a sempkm:ViewSpec ;
    rdfs:label "Research Notes Table" ;
    sempkm:rendererType "table" ;
    sempkm:scopeQuery <urn:sempkm:query:abc-123> ;
    sempkm:isGeneric "false"^^xsd:boolean .
```

**How scope binding works:**

1. When a view has `sempkm:scopeQuery`, the linked query's SPARQL is executed first to produce a result set of IRIs
2. The view's own SPARQL (or dynamic SHACL-built query) is then filtered to only include those IRIs
3. Implementation: inject a `VALUES ?s { <iri1> <iri2> ... }` clause into the view query, or use a subquery

**Relationship to existing promoted views:** `QueryService.promote_query()` already creates `PromotedViewData` with `sempkm:fromQuery`. The new `sempkm:scopeQuery` predicate extends this pattern — `fromQuery` records provenance (which query created this view), while `scopeQuery` controls runtime filtering (which query limits this view's results).

**UX flow for binding:**
- Power users: SPARQL Console → save query → promote to view (existing flow, adds `sempkm:scopeQuery` automatically)
- General users (future): "Scope this view" dropdown in view toolbar → select from saved queries → writes `sempkm:scopeQuery` triple

---

## Explorer Tree Redesign

### Before (Current — 31+ entries)

```
VIEWS
  ◻ Spatial Canvas (Beta)
  ◆ Ontology Viewer
  📁 bpkm:Note (3 entries)
  📁 bpkm:Project (3 entries)
  📁 bpkm:Concept (3 entries)
  📁 bpkm:AreaOfConcern (3 entries)
  📁 ppv:PersonalValue (3 entries)
  📁 ppv:ValueCluster (3 entries)
  ... (10+ type folders × 3 renderers each)

MY VIEWS
  ▦ My Custom View
```

### After (Proposed — ~7 fixed + Saved Views)

```
VIEWS
  ◻ Spatial Canvas (Beta)         ← unchanged
  ◆ Ontology Viewer               ← unchanged
  ▦ All Objects (Table)            ← new generic view
  🃏 All Objects (Cards)           ← new generic view
  ◎ All Objects (Graph)            ← new generic view
  📁 Saved Views                   ← merged from MY VIEWS
    ▦ Research Notes Table         ← promoted query view
    ▦ Active Projects Board        ← promoted query view
```

### Type-Specific Views as Carousel Tabs

When a user selects a type from within a generic view (via type filter pill), model-declared views for that type become available as carousel tabs. This reuses the existing `carousel_tab_bar.html` + `switchCarouselView()` mechanism:

1. User opens "All Objects (Table)" generic view
2. Type filter pills appear at top: `[Note] [Project] [Concept] [Value] ...`
3. User clicks `[Note]` pill
4. Table filters to notes. Carousel tab bar appears showing model-declared view variants:
   - `Table (default)` | `Notes Table (model)` | `Cards` | `Graph`
5. Selecting "Notes Table (model)" switches to the model's custom SPARQL + columns
6. Selecting "Cards" switches to the cards renderer for notes

**This preserves model-declared view value** (custom SPARQL, typed columns, card hints) while eliminating 31+ explorer entries.

### Type Filter Pills (for Generic Views)

Generic views need type filtering since they have no `target_class`. The carousel tab bar assumes a single target class, so a different UX element is needed:

```html
<!-- Type filter pills — rendered above the view content -->
<div class="type-filter-pills">
  <button class="pill active" data-type="">All Types</button>
  <button class="pill" data-type="urn:...Note">Note</button>
  <button class="pill" data-type="urn:...Project">Project</button>
  <!-- Dynamically populated from installed model types -->
</div>
```

- Pills are populated from `ShapesService` (all types with NodeShapes) + user-created types
- "All Types" shows cross-type results with a common column set (label, type, created, modified)
- Selecting a type pill triggers htmx swap of the view content, now filtered to that type with SHACL-discovered columns
- Pill selection is persisted in localStorage (same pattern as `switchCarouselView()`)

### Template Changes

| File | Change |
|------|--------|
| `views_explorer.html` | Replace per-type folder tree with fixed generic entries + Saved Views folder |
| `carousel_tab_bar.html` | No change — reused as-is when a type is selected |
| New: `type_filter_pills.html` | Partial template for type filter pill bar |
| New: `generic_view_table.html` | Table renderer for generic view (dynamic columns) |

### Router Changes

| Endpoint | Change |
|----------|--------|
| `GET /views/explorer` | Return consolidated tree (generic entries + saved views) |
| New: `GET /views/generic/{renderer}` | Render generic view (table/cards/graph) with optional `?type=` filter |
| New: `GET /views/type-pills` | Return type filter pills HTML partial |
| Existing `/views/table`, `/views/cards`, `/views/graph` | No change — continue serving model-declared view rendering |

**Note:** `backend/app/views/router.py` has duplicate route definitions for `/explorer`, `/menu`, and `/available` (lines 22-59 vs 261-340). These must be cleaned up before adding new endpoints. FastAPI uses first match, so the duplicates are dead code but confusing.

---

## Migration Plan

### Phase 1: Add Generic Views Alongside Existing Tree

**Scope:** Additive only — no removal of existing entries.

1. Register 3 generic `ViewSpec` instances in `ViewSpecService` at startup (not from model views graphs)
2. Add generic view entries to `views_explorer.html` above the existing per-type folders
3. Implement `GET /views/generic/{renderer}` endpoint with dynamic SHACL column discovery
4. Implement type filter pills (new partial template + htmx wiring)
5. Wire `switchCarouselView()` to show model-declared view tabs when a type filter is active

**Result:** Users see both the new generic entries and the old per-type tree. They can choose either navigation path. No existing views break.

### Phase 2: Consolidate Explorer Tree

**Scope:** Restructure the explorer tree; keep all view functionality.

1. Remove per-type folder entries from `views_explorer.html`
2. Merge MY VIEWS into a "Saved Views" folder under VIEWS section
3. Type-specific model views are now only accessible via carousel tabs within generic views
4. Add `sempkm:scopeQuery` binding support to view creation/editing

**Result:** Explorer tree shrinks to ~7 entries. Model-declared views are still accessible but through the type filter → carousel path. Saved views are unified.

### Phase 3: Cleanup

**Scope:** Remove dead code, optimize queries.

1. Clean up duplicate route definitions in `views/router.py`
2. Remove unused CSS/JS for the old per-type folder tree
3. Optimize generic view SPARQL queries based on real usage patterns
4. Add default LIMIT and lazy expansion for generic graph view (performance safety)

### Backward Compatibility

- **Phase 1 is strictly additive** — all existing views continue to work exactly as they do today
- **Phase 2 changes navigation only** — the same `ViewSpec` data, same renderers, same SPARQL queries power the views. Only the explorer tree structure changes.
- **Phase 3 is cleanup** — removes code paths that Phase 2 made unreachable

Model-declared ViewSpecs are never deleted or modified. They remain in their model views graphs and continue to be loaded by `ViewSpecService.get_all_view_specs()`. The change is purely in how they're presented to users.

---

## UI Exposure

### Workspace Users

| Surface | What Changes |
|---------|-------------|
| Explorer sidebar | 3 new generic view entries at top; per-type folders removed in Phase 2 |
| Generic view content area | Type filter pills + dynamic SHACL columns — new UI |
| Carousel tab bar | Unchanged — appears when a type is selected, showing model-declared view variants |
| Saved Views folder | Renamed from MY VIEWS, moved under VIEWS section |

### Admin Surfaces

| Surface | What Changes |
|---------|-------------|
| Model detail page | No change — ViewSpec counts remain accurate |
| SPARQL Console | No change — generic view queries use same `scope_to_current_graph()` |
| Operations log | No change — view operations don't generate ops log entries |

---

## Open Questions / Deferred Scope

### Open Questions

1. **Generic graph view performance:** A graph view across ALL types could return thousands of nodes. Should the default LIMIT be 200 nodes with a "Load More" button, or should the graph view require a type filter before rendering? The spatial canvas already handles large graphs — can its approach (lazy node expansion) be reused?

2. **User-created types with sparse SHACL:** User-created classes (TYPE-01/TYPE-02 from M003/S08) generate SHACL shapes via `create_class()`, but they may have very few properties (just title + description). The fallback column set (label, type, created, modified) handles this, but the table will look sparse. Should generic views show a "Add properties to improve this view" hint for sparse types?

3. **Query → view scope binding UX:** The SPARQL Console → promote flow exists but is power-user-only. For general users, how should "scope this view to a query" work? Options:
   - Dropdown in view toolbar (requires listing saved queries)
   - Drag-and-drop query from Saved Views onto a generic view
   - Automatic scoping when opening a promoted query-view

4. **Duplicate route cleanup timing:** `views/router.py` has duplicate definitions for 3 endpoints. Should cleanup happen in Phase 1 (cleaner base for new endpoints) or Phase 3 (minimize risk during active development)?

5. **Type filter persistence scope:** Should type filter selection be per-view (Table remembers "Note", Cards remembers "Project") or global (selecting "Note" applies to all generic views)? Per-view is more flexible but requires more localStorage keys.

### Deferred Scope (Not This Milestone)

- **Custom column selection UI** — letting users pick which columns to show/hide. SHACL discovery provides defaults; customization can come later.
- **View sharing/exporting** — sharing a configured view (type + columns + sort + scope query) with other users.
- **Faceted search integration** — combining type filter pills with property-value facets (e.g., "Notes tagged 'research' created this week").
- **Generic view SPARQL editing** — exposing the dynamically-built SPARQL for advanced users to customize. Currently, only model-declared ViewSpecs carry custom SPARQL.
- **View-level permissions** — restricting who can see/edit specific views. Currently all views are visible to all users.

---

## Recommendations

### 1. Implement the Hybrid Approach (D020-Compatible)

The existing explorer mode switching (D020) uses a dropdown that replaces section content in-place via htmx. Generic views extend this pattern — the VIEWS section gains fixed entries that load generic content, while the existing mode infrastructure handles rendering.

### 2. Phase 1 Is the Milestone Deliverable

Phase 1 (generic views alongside existing tree) is achievable in one milestone. It delivers the core value — cross-type browsing with SHACL-driven columns — without breaking existing views.

Phase 2 (explorer consolidation) and Phase 3 (cleanup) can be a subsequent milestone once Phase 1 is validated by users.

### 3. Reuse Existing Mechanisms, Don't Rebuild

| Mechanism | Reuse For |
|-----------|----------|
| `ViewSpecService` | Register generic ViewSpecs at startup |
| `ShapesService._extract_node_shape()` | Column discovery for generic table/cards views |
| `execute_table_query()` / `execute_cards_query()` | Paginated rendering with dynamic columns |
| `carousel_tab_bar.html` + `switchCarouselView()` | Type-scoped model view switching |
| `QueryService` + `sempkm:scopeQuery` | View-to-query scope binding |
| `LabelService.resolve_batch()` | Column header labels, type pill labels |
| `RENDERER_REGISTRY` | Template lookup for generic view renderers |
| `scope_to_current_graph()` | All generic view queries must pass through this |
| `TTLCache` (300s) | Cache shapes→columns mapping in ViewSpecService |

### 4. Address Router Duplication First

The duplicate route definitions in `views/router.py` should be cleaned up in Phase 1, not deferred to Phase 3. Adding new generic view endpoints to a file with 3 duplicate route pairs is a maintenance hazard. The cleanup is low-risk — remove the second definition of each duplicated route.

### 5. Key Decisions for Implementation

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Generic views registered at startup | In-memory, not RDF | Avoids a "system views" named graph. Generic views are code-defined, not data-defined. |
| Column discovery source | SHACL shapes via `ShapesService` | Already extracts `sh:path`, `sh:name`, `sh:order` — everything needed for dynamic columns |
| Type filter UX | Pills (not dropdown, not carousel) | Carousel assumes single target_class. Dropdown hides available types. Pills show all types at a glance with active state. |
| Query scope binding predicate | `sempkm:scopeQuery` | Extends existing `sempkm:fromQuery` pattern. Distinct semantics: `fromQuery` = provenance, `scopeQuery` = runtime filter. |
| Migration strategy | 3-phase, additive-first | Phase 1 is risk-free (additive). Phase 2 is low-risk (navigation only). Phase 3 is cleanup. No big-bang. |

---

## Appendix: Code Path Reference

All referenced code paths and their roles in this design:

| Code Path | Role in Design |
|-----------|---------------|
| `backend/app/views/service.py` — `ViewSpecService` | Extend to register generic views, build dynamic queries from SHACL |
| `backend/app/views/router.py` | Add generic view endpoints, clean up duplicate routes |
| `backend/app/views/registry.py` — `RENDERER_REGISTRY` | Template lookup for generic view renderers |
| `backend/app/services/shapes.py` — `ShapesService` | Column discovery via `_extract_node_shape()` / `_extract_property_shape()` |
| `backend/app/sparql/query_service.py` — `QueryService` | Saved queries as scope primitive, `sempkm:scopeQuery` binding |
| `backend/app/templates/browser/views_explorer.html` | Redesigned explorer tree template |
| `backend/app/templates/browser/carousel_tab_bar.html` | Reused for type-scoped model view switching |
| `frontend/static/js/workspace.js` — `switchCarouselView()` | Carousel tab switching logic, localStorage persistence |
| `backend/app/services/label_service.py` — `LabelService` | Batch IRI→label for column headers, type pill labels |
| `models/basic-pkm/views/basic-pkm.jsonld` | 12 ViewSpecs — example of model-declared views |
| `models/ppv/views/ppv.jsonld` | 19 ViewSpecs — demonstrates the scaling problem |
