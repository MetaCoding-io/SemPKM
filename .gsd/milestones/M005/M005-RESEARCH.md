# M005 S06: Views Rethink — Research Notes

**Date:** 2026-03-14  
**Status:** Discussion captured, ready for design doc authoring

## Current State

### How Views Work Today

Each `ViewSpec` in a model's `views.jsonld` is a complete, self-contained unit:
- Specific SPARQL query baked to a specific type (`?s a bpkm:Project`)
- Specific renderer type (table, card, graph)
- Specific column/card configuration

The `ViewSpecService` loads all specs from installed model views graphs, caches them (TTL 300s), and executes queries with pagination, sorting, and filtering.

### The Problem (Visible in UI)

The VIEWS explorer section shows **12 entries** for basic-pkm alone:
- 📁 `sempkm:model:basic-pk...` (3) → Concepts Cards, Concepts Graph, Concepts Table
- 📁 `sempkm:model:basic-pk...` (3) → Notes Cards, Notes Graph, Notes Table  
- 📁 `sempkm:model:basic-pk...` (3) → People Cards, People Graph, People Table
- 📁 `sempkm:model:basic-pk...` (3) → Projects Cards, Projects Graph, Projects Table

Grouped by truncated IRI (not even type name). Every new type × 3 renderers = 3 more entries. The folder labels are useless.

### Existing Infrastructure

- `ViewSpecService.get_view_specs_for_type(type_iri)` — already filters specs by target class
- `ViewSpecService.get_user_promoted_view_specs()` — user-created views from promoted SPARQL queries (stored in SQL, not RDF)
- Carousel tab bar on object pages already shows per-type view tabs
- `_group_specs_by_type()` groups by target class for the explorer tree

## Design Decision: Option 3 (Hybrid)

**Agreed direction:** Keep model-declared rich views + add generic cross-type views.

### Model-Declared Views (Authored)
- Models ship `ViewSpec` entries with custom SPARQL, columns, card hints, CONSTRUCT queries
- These carry real value: a "Projects Table" knows to show `title, status, priority, startDate`
- Presented as renderer tabs when a type is selected, not as 12 tree entries
- Mental Models can also ship **named queries** (read-only to user, copyable for modification)

### Generic Views (System-Provided)
- Three built-in views: Table, Cards, Graph
- Work across all objects by default (no type filter)
- In-view type filtering via pills/dropdown
- Column discovery from SHACL shapes when no model-declared view exists for a type
- Scoped by saved queries for custom filtering

### Saved Queries as Universal Scope
- Models ship named queries (read-only to user; user can copy to create their own)
- Users create their own via SPARQL console (existing feature)
- Both views and VFS mounts reference saved queries as scope
- This is the shared primitive between views and VFS — design it once, use everywhere

## UI Presentation Ideas

### Explorer Tree Redesign
Instead of 12 per-type entries, the VIEWS section could show:

```
VIEWS
  ◻ Spatial Canvas (Beta)
  ◆ Ontology Viewer
  ▦ All Objects (Table)        ← generic, opens with type filter pills
  ▦ All Objects (Cards)
  ◎ All Objects (Graph)        ← "knowledge graph" across everything
  📁 Saved Views               ← user-saved view configurations
    My Project Cards
    Research Notes Table
```

When a user is on a type page (e.g. clicked "Project" in the OBJECTS tree), the carousel tab bar shows the model-declared views for that type: Table | Cards | Graph.

### View Scoping Flow
1. User opens "All Objects (Table)"
2. Sees all objects across all types
3. Clicks type filter pill "Note" → table now shows only Notes with Note-specific columns
4. Clicks "Save View" → prompted for name, saved as a user view
5. Saved view appears under MY VIEWS in explorer

## Open Questions for Design Doc

- Should generic views dynamically discover columns from SHACL shapes, or use a fixed set (title, type, created, modified)?
- How do model-declared named queries appear in the UI? Under VIEWS? Under a new QUERIES section?
- Should the carousel tab bar on type pages also show user-created views scoped to that type?
- Can a model declare a view without `targetClass` (cross-type view)? Currently all model views have `targetClass`.

## Key Files

- `backend/app/views/service.py` — ViewSpecService, ViewSpec dataclass
- `backend/app/views/router.py` — views_explorer, view rendering endpoints
- `backend/app/templates/browser/views_explorer.html` — current tree template
- `models/basic-pkm/views/basic-pkm.jsonld` — 12 ViewSpec definitions
- `backend/app/sparql/models.py` — SavedSparqlQuery, PromotedQueryView models
