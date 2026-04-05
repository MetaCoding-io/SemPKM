---
depends_on: [M048]
---

# M056: Ontology Visualization Overhaul

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Rebuild the ontology graph visualization with a layered hierarchical layout, full TBox coverage across all installed models, interactive multi-model filtering, and persistent graph state across tab switches.

## Why This Milestone

The model detail page has a relationship graph that's "amazing" (user's word) but limited: it shows only one model's types, the hover popover appears far from the node, and the graph resets when switching tabs. The Ontology Viewer (TBox/ABox/RBox) has no graph at all — it's a list view. Users want to see the full ontology hierarchy with gist at the top as the upper ontology, model layers below, and the ability to filter by model to focus on what matters.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open the Ontology Viewer and see a layered graph with gist at the top, then model types below, organized by degree-from-gist and categorical grouping
- Filter the graph by Mental Model (multi-select) — graph updates live as filters change
- Click a node in the graph to see its detail in a bottom panel (class properties, relationships, instances)
- Switch between TBox/ABox/RBox tabs without the graph resetting
- See the graph use 100% available width and height (no whitespace)
- See hover popovers correctly anchored to nodes (not displaced)

### Entry point / environment

- Entry point: http://localhost:4000/browser/ → Ontology Viewer
- Environment: Docker Compose dev stack
- Live dependencies involved: RDF4J triplestore

## Completion Class

- Contract complete means: layered layout algorithm produces correct visual hierarchy, multi-model filter works, graph persists across tab switches
- Integration complete means: full TBox graph renders with all installed models
- Operational complete means: none

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Install 3+ models → Ontology Viewer → graph shows all types with gist at top layer
- Filter to show only CRM model → graph re-renders with just CRM types (plus gist connections)
- Click a CRM Contact node → bottom panel shows Contact properties, relationships, instance count
- Switch to ABox tab → switch back to TBox → graph is in the same position/zoom
- Hover a node → popover appears anchored to the node, not displaced

## Risks and Unknowns

- **Layered layout algorithm** — Cytoscape has dagre/breadthfirst layouts but auto-layering by "degree from gist" needs custom logic. May need to compute layer assignment server-side and pass as node data.
- **Performance** — gist alone has ~96 classes. With 7 models installed, total could be 200+ nodes. May need level-of-detail or collapsing.
- **Graph persistence** — Cytoscape state (positions, zoom, pan) needs to survive htmx tab switches. May need to store state in JS and restore on tab re-focus.

## Existing Codebase / Prior Art

- `backend/app/admin/router.py:314` — `admin_model_ontology_diagram()` builds subclass edges for model detail graph
- `backend/app/ontology/service.py` — OntologyService with TBox/ABox/RBox queries
- `frontend/static/js/graph.js` — Cytoscape.js graph rendering with fcose/dagre layouts
- Model detail graph uses a separate Cytoscape instance in the admin template
- KNOWLEDGE.md documents the stacking context escape pattern for Cytoscape popovers

## Scope

### In Scope

- Layered graph layout: gist at top, model layers below, edges showing rdfs:subClassOf and property relationships
- Multi-select model filter (checkboxes or pills per model)
- Bottom detail panel showing selected node's properties, relationships, instance count
- Graph persistence across TBox/ABox/RBox tab switches
- 100% width/height for graph area
- Fix hover popover positioning (#42)
- Copy relationship graph from model detail to Ontology Viewer (unified implementation)

### Out of Scope / Non-Goals

- 3D/isometric graph (M033 already has isometric mode)
- Graph editing (adding/removing classes from the graph)
- Full ontology editing UI (already exists in M004)

## Open Questions

- Should layer assignment be computed server-side (SPARQL query for shortest path from each class to gist:Category) or client-side (BFS from gist roots)?
- Should the graph show property edges (domain/range) or only subclass edges? Both?
