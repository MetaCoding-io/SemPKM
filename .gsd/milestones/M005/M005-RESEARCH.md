# M005 Research: Views Rethink & Query Migration

**Date:** 2026-03-14  
**Status:** Discussion captured, ready for design doc authoring

---

## Query Storage: SQL → RDF (S01 prerequisite)

### Motivation

Current principle: **SQL for auth, graph for everything else.** Four SQL tables violate this:

| SQL Table | Records | Used By |
|-----------|---------|---------|
| `SparqlQueryHistory` | Auto-saved executions per user | `sparql/router.py` |
| `SavedSparqlQuery` | Named queries | `sparql/router.py`, `views/service.py`, `browser/workspace.py` |
| `SharedQueryAccess` | Query sharing join table | `sparql/router.py` |
| `PromotedQueryView` | Queries promoted to views | `sparql/router.py`, `views/service.py`, `browser/workspace.py` |

~65 references in `sparql/router.py` alone. Also touched by `ViewSpecService` for promoted views.

### Why This Enables M005

Once queries are RDF resources with IRIs:
- **Model-shipped named queries** and user queries are the same shape, differing only by `sempkm:source`
- **VFS mounts** reference queries by IRI (no SQL join needed)
- **Views** reference queries by IRI for scoping
- Saved queries become the **universal scope primitive** for both views and VFS

### RDF Data Model

```turtle
# User's named query
<urn:sempkm:query:{uuid}> a sempkm:SavedQuery ;
    sempkm:owner <urn:sempkm:user:{uuid}> ;
    rdfs:label "My Research Notes" ;
    dcterms:description "All notes tagged research" ;
    sempkm:queryText "SELECT ?s WHERE { ... }" ;
    dcterms:created "2026-03-14T..."^^xsd:dateTime ;
    dcterms:modified "2026-03-14T..."^^xsd:dateTime .

# Model-shipped named query (read-only, same shape)
<urn:sempkm:model:basic-pkm:query:active-projects> a sempkm:SavedQuery ;
    sempkm:source "model:basic-pkm" ;
    rdfs:label "Active Projects" ;
    sempkm:queryText "SELECT ?s WHERE { ... }" .

# Sharing — a single triple
<urn:sempkm:query:{uuid}> sempkm:sharedWith <urn:sempkm:user:{uuid2}> .

# Promoted to view
<urn:sempkm:query-view:{uuid}> a sempkm:PromotedView ;
    sempkm:fromQuery <urn:sempkm:query:{uuid}> ;
    sempkm:owner <urn:sempkm:user:{uuid}> ;
    rdfs:label "My Research Table" ;
    sempkm:rendererType "table" .

# Query execution history
<urn:sempkm:query-exec:{uuid}> a sempkm:QueryExecution ;
    sempkm:executedBy <urn:sempkm:user:{uuid}> ;
    sempkm:queryText "SELECT ..." ;
    prov:startedAtTime "2026-03-14T..."^^xsd:dateTime .
```

### Graph Organization

Option A: Single `urn:sempkm:queries` graph for all users' queries, filtered by `sempkm:owner`.  
Option B: Per-user graphs `urn:sempkm:user:{uuid}:queries`.  

Leaning A — simpler to query across users for sharing, and query volume is low.

### Migration Strategy

1. Build `QueryService` backed by RDF (new service, clean interface)
2. Update `sparql/router.py` to use `QueryService` instead of SQLAlchemy
3. Data migration script: read SQL tables → write RDF triples
4. Alembic migration to drop SQL tables
5. Keep SQL tables temporarily with a deprecation marker until migration runs

### Performance Considerations

The SPARQL console hits query list/history on every page load. If triplestore latency is noticeable:
- TTLCache on `QueryService` (same pattern as `ViewSpecService` — 300s TTL)
- HTTP caching headers on list endpoints
- Query history could be capped (already has cap logic in current SQL implementation)

### Other SQL Models — Gray Area

| SQL Model | Decision | Rationale |
|-----------|----------|-----------|
| `UserFavorite` | Defer | Hot-path query (every page load); `sempkm:favorited` triple is clean but perf risk. Revisit later. |
| `InferenceTripleState` | Defer | Per-triple UI state (dismiss/promote). High write volume during inference. Keep in SQL. |
| `UserSetting` | Keep | Pure user preferences, key/value. Auth-adjacent. |

---

## Views Rethink (S07)

### The Problem

12 view entries in the explorer for 4 types × 3 renderers. Grouped by truncated IRI. Every new type multiplies by 3.

### Design Decision: Hybrid (Option 3)

**Model-declared rich views** + **generic cross-type views**.

#### Model-Declared Views (Authored)
- Models ship `ViewSpec` entries with custom SPARQL, columns, card hints, CONSTRUCT queries
- Carry real value: "Projects Table" knows columns `title, status, priority, startDate`
- Presented as renderer tabs when a type is selected, not as 12 tree entries
- Models can ship **named queries** — read-only to user, copyable for modification
- After S01, model queries are RDF resources in model views graph, same shape as user queries

#### Generic Views (System-Provided)
- Three built-in views: Table, Cards, Graph
- Work across all objects by default
- In-view type filtering via pills/dropdown
- Column discovery from SHACL shapes when no model-declared view exists
- Scoped by saved queries

#### Saved Queries as Universal Scope
- Both views and VFS mounts reference queries by IRI
- Model queries: read-only, copyable
- User queries: full CRUD via SPARQL console
- S01 (Query SQL→RDF) is prerequisite — queries must be IRI-addressable RDF resources

### Explorer Tree Redesign

```
VIEWS
  ◻ Spatial Canvas (Beta)
  ◆ Ontology Viewer
  ▦ All Objects (Table)        ← generic, type filter pills
  ▦ All Objects (Cards)
  ◎ All Objects (Graph)        ← knowledge graph across everything
  📁 Saved Views
    My Project Cards
    Research Notes Table
```

Type-specific views shown as carousel tabs when a type is selected.

### Open Questions

- Dynamic column discovery from SHACL shapes vs fixed column set for generic views?
- Model-declared named queries: show under VIEWS, or a new QUERIES section?
- Carousel tab bar: include user-created views scoped to that type?
- Can models declare cross-type views (no `targetClass`)?

### Key Files

- `backend/app/views/service.py` — ViewSpecService, ViewSpec dataclass
- `backend/app/views/router.py` — views_explorer, rendering endpoints
- `backend/app/templates/browser/views_explorer.html` — current tree template
- `models/basic-pkm/views/basic-pkm.jsonld` — 12 ViewSpec definitions
