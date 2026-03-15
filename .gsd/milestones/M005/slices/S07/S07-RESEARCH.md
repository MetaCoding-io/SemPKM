# S07 — Views Rethink Design: Research

**Date:** 2026-03-14  
**Status:** Research complete

## Summary

This slice produces a design document at `.gsd/design/VIEWS-RETHINK.md` — no code changes. The design must address the concrete scaling problem already visible in the codebase: 2 installed models produce 31 ViewSpec entries in the explorer sidebar, grouped by truncated type IRI. Every new model type adds 3 more entries (table/card/graph). With S01 complete, queries are now RDF resources addressable by IRI, enabling the key architectural shift: saved queries as a universal scope primitive that both views and VFS mounts reference.

The research findings show a well-factored existing system with clear extension points. The main insight is that the problem is **not** the ViewSpec data model (which is clean) but rather the **explorer tree presentation** and **the missing generic cross-type views**. Model-declared views carry real value (custom SPARQL, typed columns, card hints) — the fix is to change how views are accessed, not to eliminate them.

The design doc should propose: (1) generic system-provided views (Table/Cards/Graph) that work across all types with dynamic column discovery from SHACL shapes, (2) model-declared views presented as renderer tabs when a type is selected (not 12 tree entries), and (3) saved queries as the scope binding mechanism for both user-created and model-shipped views.

## Recommendation

Write a design doc following the PROV-O alignment doc format: current state audit, proposed data model, explorer tree redesign, migration path, and open questions. Keep it implementable-in-one-milestone, not aspirational. Ground every proposal in existing code extension points.

**Approach:** Hybrid model (per M005-RESEARCH.md Option 3). Model-declared rich views + generic cross-type views. The explorer tree shrinks from 31+ entries to ~7 fixed entries plus a "Saved Views" folder. Type-specific views become carousel tabs when a type is selected — the carousel tab bar already exists and works well.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| View spec data model | `ViewSpec` dataclass in `views/service.py` | Already has all fields (spec_iri, label, target_class, renderer_type, sparql_query, columns, etc.) — extend, don't replace |
| SPARQL query execution with pagination | `execute_table_query()`, `execute_cards_query()`, `execute_graph_query()` | Proven patterns for all three renderer types; generic views reuse these |
| Column discovery | `ShapesService._extract_node_shape()` / `_extract_property_shape()` | SHACL NodeShapes already carry `sh:path`, `sh:name`, `sh:datatype` — everything needed for dynamic column headers |
| Carousel tab bar for type-scoped views | `carousel_tab_bar.html` + `switchCarouselView()` | Already works: persists selection in localStorage, swaps view body via htmx, preserves filter state |
| Renderer registry | `views/registry.py` `RENDERER_REGISTRY` | Extensible dict; models can register custom renderers at install time |
| Promoted views (user → view) | `QueryService.promote_query()` / `list_promoted_views()` | Already creates `PromotedViewData` RDF resources referencing saved queries by IRI |
| Label resolution | `LabelService.resolve_batch()` | Batch IRI→label for column headers, type names, etc. |

## Existing Code and Patterns

- `backend/app/views/service.py` — `ViewSpecService` loads ViewSpecs from model views graphs via SPARQL. `get_all_view_specs()` queries all models' views graphs using VALUES clause + GRAPH ?g pattern. **Key extension point:** add a method that builds a generic ViewSpec dynamically from SHACL shapes for a given type.
- `backend/app/views/router.py` — 8 endpoints: explorer tree, view menus, table/card/graph rendering, graph data/expand. Has duplicate route definitions for `/explorer` and `/menu` and `/available` (two of each — likely from merge). **Needs cleanup before adding generic view endpoints.**
- `backend/app/views/registry.py` — `RENDERER_REGISTRY` maps renderer type strings → template paths. Models can register custom renderers. **Design doc should define how generic views use the same registry.**
- `backend/app/services/shapes.py` — `ShapesService` extracts SHACL NodeShapes into `NodeShapeForm` / `PropertyShape` dataclasses with `sh:path`, `sh:name`, `sh:description`, `sh:datatype`, `sh:order`. **This is the column discovery source for generic views** — `PropertyShape.path` gives the property IRI, `PropertyShape.name` gives the column header.
- `backend/app/sparql/query_service.py` — `QueryService` manages saved queries as RDF in `urn:sempkm:queries`. `PromotedViewData` links queries to views via `sempkm:fromQuery`. **Saved queries as scope primitive is already plumbed** — design doc formalizes it.
- `backend/app/templates/browser/views_explorer.html` — Current explorer tree: Spatial Canvas, Ontology Viewer as fixed entries, then ViewSpecs grouped by type with folder nodes. **This is what gets redesigned.**
- `backend/app/templates/browser/workspace.html` — Two sidebar sections: VIEWS (model views) and MY VIEWS (promoted queries). **Design doc may merge these or keep separate.**
- `backend/app/templates/browser/carousel_tab_bar.html` — Renders Table/Cards/Graph tabs when a type has multiple ViewSpecs. Uses localStorage persistence. **Already does what the rethink needs for type-scoped views.**
- `models/basic-pkm/views/basic-pkm.jsonld` — 12 ViewSpecs (4 types × 3 renderers) + 3 named queries. **The scaling problem source.** PPV model adds 19 more (31 total with 2 models).
- `frontend/static/js/workspace.js` — `openViewTab()` creates dockview tabs for views. `switchCarouselView()` handles in-place renderer switching. `loadViewContent()` loads view HTML via htmx. **All reusable for generic views.**

## Constraints

- **htmx + vanilla JS only** — no React/Vue. All view rendering is server-side HTML partials swapped by htmx. Generic views must follow this pattern.
- **ViewSpec SPARQL queries must be scoped** — `scope_to_current_graph()` injects `FROM <urn:sempkm:current>` into every query. Generic views building dynamic SPARQL must also pass through this.
- **Queries are RDF resources in `urn:sempkm:queries`** — S01 established this. Design doc assumes queries are IRI-addressable. Model queries use `sempkm:source` predicate to mark read-only.
- **Model-declared ViewSpecs are in named graphs** — `urn:sempkm:model:{id}:views`. Cannot be edited by users. Can be refreshed via MIG-01 (`refresh_artifacts`).
- **Carousel tab bar is per-type, not per-view** — It shows all renderer types for one target class. Generic views (cross-type) won't have a target class — different UX needed (type filter pills instead).
- **Explorer pane has drag-reorderable sections** — `[data-panel-name]` + localStorage positions. New sections must follow this pattern.
- **`ViewSpecService` uses TTLCache (300s)** — Any new view types that hit the triplestore need similar caching or must accept the cache refresh delay.
- **Duplicate route definitions in `views/router.py`** — `/explorer`, `/menu`, `/available` each defined twice (lines 22-59 vs 261-340). FastAPI uses first match. Cleanup needed before design work adds more endpoints.

## Common Pitfalls

- **Over-designing the generic view SPARQL** — Don't try to build a full SPARQL query builder. Use SHACL shapes for column discovery and generate simple `SELECT ?s ?col1 ?col2 ... WHERE { ?s a <type> ... }` queries. The existing `execute_table_query` pattern handles pagination, sorting, filtering.
- **Breaking the carousel tab bar** — The carousel assumes all specs share a `target_class`. Generic cross-type views have no target class. Don't force-fit them into the carousel — use a different type-filter mechanism (pills/dropdown).
- **Explorer tree regression** — Current views_explorer.html is loaded on sidebar init. Changing its structure affects every page load. The redesign must be incremental — keep the current tree working while adding generic entries.
- **Duplicate route definitions** — `views/router.py` has two `views_explorer`, two `views_menu`, and two `views_available` definitions. The first ones (lines 22-59) win at runtime. If the design doc proposes new endpoints, it must account for this duplication and recommend cleanup.
- **Dynamic SHACL column discovery performance** — Fetching SHACL shapes for every generic view render could be expensive. Should cache the shapes → columns mapping (ShapesService already caches internally).
- **Model queries vs. user queries presentation** — Model queries (`sempkm:source` = model) are read-only. User queries are full CRUD. The views explorer must visually distinguish them and prevent editing model queries.

## Open Risks

- **Scope of "implementable in one milestone"** — The full hybrid vision (generic views + query scoping + SHACL column discovery + explorer redesign) is substantial. The design doc must ruthlessly prioritize phase 1 deliverables vs. future phases.
- **Generic graph view performance** — A graph view across ALL types could return thousands of nodes. Needs a default LIMIT or lazy expansion strategy.
- **User-created types with minimal SHACL** — User-created classes (TYPE-01/TYPE-02) generate SHACL shapes, but they may have very few properties. Generic table view needs a sensible default when shapes have only title + description.
- **Saved query scope binding UX** — How does a user attach a saved query to a view? The SPARQL console → promote flow exists but is power-user-only. A simpler "scope this view to a query" dropdown would be better for general users.

## Data Model Notes (for design doc)

### Current ViewSpec RDF vocabulary

```turtle
<spec_iri> a sempkm:ViewSpec ;
    rdfs:label "View Name" ;
    sempkm:targetClass <type_iri> ;
    sempkm:rendererType "table" ;  # "table" | "card" | "graph"
    sempkm:sparqlQuery "SELECT ..." ;
    sempkm:columns "col1,col2,col3" ;
    sempkm:sortDefault "col1" ;
    sempkm:cardTitle <prop_iri> ;
    sempkm:cardSubtitle <prop_iri> .
```

### Proposed additions for design doc

- `sempkm:scopeQuery <query_iri>` — link a view to a saved query for scoping
- `sempkm:isGeneric "true"^^xsd:boolean` — mark system-provided generic views
- `sempkm:typeFilter <type_iri>` — current type filter state for generic views (runtime, not persisted)
- No new RDF vocabulary needed for the explorer tree redesign — it's pure UI/template work

### Explorer tree (proposed structure for design doc)

```
VIEWS
  ◻ Spatial Canvas (Beta)      ← existing special
  ◆ Ontology Viewer            ← existing special
  ▦ All Objects (Table)        ← new generic, type filter pills
  ▦ All Objects (Cards)        ← new generic
  ◎ All Objects (Graph)        ← new generic
  📁 Saved Views               ← existing MY VIEWS, renamed
    My Project Cards
    Research Notes Table
```

Type-specific model views appear as carousel tabs when a type is selected from the explorer tree or within a generic view's type filter.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| RDF/SPARQL | N/A | Core project technology, no external skill needed |
| SHACL | N/A | Already implemented in ShapesService |
| htmx | N/A | Already the project standard |
| FastAPI | N/A | Already the project standard |

No external skill installation recommended — this is a design document slice using established project patterns.

## Sources

- M005-RESEARCH.md Views Rethink section — design decision for Hybrid (Option 3) approach
- S01 forward intelligence — query IRIs use `urn:sempkm:query:{uuid}` pattern, model queries marked with `sempkm:source`
- `views/service.py` codebase exploration — ViewSpecService architecture, 570 LOC
- `views/router.py` codebase exploration — 8 endpoints (with duplicates), 340 LOC
- `models/basic-pkm/views/basic-pkm.jsonld` — 12 ViewSpecs + 3 named queries
- `models/ppv/views/ppv.jsonld` — 19 ViewSpecs (31 total with 2 models)
- PROV-O-ALIGNMENT.md — design doc format reference
