# M056 Research: Ontology Visualization Overhaul

## Executive Summary

This milestone replaces the tree-only TBox view in the Ontology Viewer with a Cytoscape.js graph visualization showing the full class hierarchy across gist and all installed models. The codebase already has all the necessary infrastructure — Cytoscape, dagre layout, graph popover system, ontology SPARQL queries — making this primarily an integration and UX challenge rather than a greenfield build.

## What Exists Today

### Ontology Viewer (Browser Workspace)

- **Entry:** `special:ontology` panel in dockview → `GET /browser/ontology` → `ontology_page.html`
- **Layout:** Three tabs (TBox/ABox/RBox) using CSS show/hide (`.ontology-pane--active`). Tab content persists in DOM during switches — **graph persistence across tabs is free** since Cytoscape containers won't be destroyed on tab switch.
- **TBox tab:** Split layout with a 320px tree pane (left) + detail pane (right). Tree loads via htmx (`GET /browser/ontology/tbox`), children expand lazily (`GET /browser/ontology/tbox/children?parent=`). Detail loads on node click (`GET /browser/ontology/tbox/detail?iri=`).
- **Hide gist toggle:** Checkbox reloads the tree filtered to non-gist classes grouped under their gist parents.
- **Class CRUD:** Create/edit/delete forms in modal overlays. Events like `classCreated`, `classDeleted`, `classEdited` trigger htmx refreshes.

### Model Detail Relationship Graph (Admin)

- **Entry:** Admin → Model Detail → Relationships tab → `admin_model_ontology_diagram()`
- **Graph:** Cytoscape with dagre layout (TB direction), inline JS, own popover system
- **Data:** Server builds nodes + edges from model's types, ObjectProperties, and subclass edges. External parent classes (gist supertypes) shown as dashed-border round-rectangles.
- **Key difference from M056 goal:** Shows only ONE model's types. M056 needs ALL models cross-graph.

### Graph Infrastructure (`graph.js`)

- Mature Cytoscape wrapper: layout registry (fcose, dagre, concentric, isometric), semantic styling, body-appended popovers, node expansion, theme switching, icon mode toggle, filter
- `initGraph(containerId, specIri, typeColors, availableLayouts, customDataUrl)` — fetches JSON data and renders
- Popovers use `position: fixed` + body-append (escapes dockview stacking context per KNOWLEDGE.md)
- CSS in `views.css` (`.graph-popover` styles)
- Already exports to `window.SemPKM` namespace

### OntologyService (`backend/app/ontology/service.py`)

- 2180 lines. Cross-graph FROM clause aggregation across gist + all installed model ontology graphs + user-types
- `get_ontology_graph_iris()` — returns all relevant graph IRIs for FROM clauses
- `get_root_classes()` — root owl:Class with no named parent
- `get_subclasses(parent_iri)` — direct children
- `get_class_detail(class_iri)` — full metadata (parents, siblings, properties, instance count, annotations)
- `get_model_classes_with_parents()` — non-gist classes grouped under gist parents (used by "hide gist" filter)
- All queries already handle multi-graph aggregation

### Dependencies Already Vendored

- `cytoscape` 3.33.1
- `cytoscape-dagre` 2.5.0 (dagre 0.8.5)
- `cytoscape-fcose` 2.2.0

## Scale Analysis

| Source | Estimated class count |
|--------|----------------------|
| gist core | ~96 named classes (188 owl:Class references include unions/restrictions) |
| basic-pkm | 7 |
| business-planning | 34 |
| crm | 4 |
| media-scheduler | 5 |
| ppv | 12 |
| research | 5 |
| rss-feeds | 2 |
| zettelkasten | 5 |
| **Total (all models)** | **~170 nodes** |

170 nodes is well within Cytoscape's comfortable range (~1000+ nodes is where perf issues start). No level-of-detail or virtualization needed.

## Technical Design Decisions

### 1. Graph Data Endpoint (New)

Need a new JSON API endpoint: `GET /browser/ontology/tbox/graph?models=all` (or `models=crm,basic-pkm`).

Returns:
```json
{
  "nodes": [{"id": "iri", "label": "...", "source": "gist|crm|...", "layer": 0}],
  "edges": [{"source": "iri", "target": "iri", "type": "subclass|property", "label": "..."}]
}
```

**Layer assignment** should be computed server-side via BFS from gist roots:
- Layer 0: gist root classes (no named parent)
- Layer 1: gist classes with a root parent
- Layer N: classes N hops from roots
- Model classes: max(parent layer) + 1

The `layer` data flows to the dagre layout's `rank` option for proper hierarchical placement.

**Model filter:** Accept comma-separated model IDs. Server filters the FROM clauses to only include selected model ontology graphs (always include gist). Return `available_models` list for the filter UI.

### 2. Layout Strategy

**dagre with `rankDir: 'TB'`** is the right choice — already proven in the model detail diagram. Configure:
- `rankSep: 80` — vertical spacing between layers
- `nodeSep: 30` — horizontal spacing within a layer
- Custom rank assignment via dagre's rank-based layout (or pass layer as node data and use it)

**Alternative considered:** fcose with constraints. More visually organic but doesn't produce clean hierarchical layers. dagre is purpose-built for this.

### 3. Ontology Page Layout Redesign

Current TBox: tree (left 320px) + detail (right flex:1).

Proposed: Graph (top, flex:1) + detail panel (bottom, collapsible ~250px). The tree stays but becomes a sidebar toggle option (some users prefer browsing by tree). The graph becomes the primary view.

Layout options for the TBox tab:
- **Option A:** Replace tree with graph. Keep detail panel as bottom split.
- **Option B:** Three-way split: tree (left 280px) + graph (center flex:1) + detail (bottom 250px).
- **Option C:** Tabbed within TBox: "Graph" sub-tab and "Tree" sub-tab, with shared detail panel.

**Recommendation:** Option A with a toggle to switch between graph/tree view. The graph IS the navigation — clicking a node loads detail in the bottom panel. The tree becomes a secondary access mode (toggle button).

### 4. Graph Persistence Across TBox/ABox/RBox

**Already free.** The `.ontology-pane` elements use `display:none` / `display:block` toggling. The Cytoscape container stays in the DOM with its full state (positions, zoom, pan). Switching back to TBox shows the graph exactly as left.

One thing to watch: the Cytoscape container may report zero dimensions when its parent is `display:none`. Call `cy.resize()` when the TBox pane becomes visible again.

### 5. Popover Positioning Fix

The context doc mentions popovers appearing "far from the node." The model detail diagram uses a simpler popover that positions relative to the container's `getBoundingClientRect()`. The `graph.js` popover already uses body-append with `position: fixed` and viewport-relative coords — this is the correct approach.

For the new ontology graph, reuse the `graph.js` popover system since it already handles dockview stacking context escape and isometric transforms. The model detail diagram's approach is simpler but doesn't handle the workspace context.

### 6. Multi-Model Filter UI

Checkboxes or pills showing installed model names. Filter state persists in the component (JS variable or localStorage). On change, re-fetch graph data with the new model filter applied and re-render.

**Implementation:** A horizontal bar above or beside the graph with model name checkboxes. "All" shortcut. Each model gets its color from the icon service. Live graph update on filter change (re-fetch + re-layout, or client-side show/hide of nodes by `source` attribute).

**Client-side vs server-side filtering:** For 170 nodes, client-side filtering (add/remove `.filtered-out` class based on `source` data attribute) is simpler and more responsive. No need to re-fetch. The `filterGraph()` function in `graph.js` already demonstrates this pattern.

### 7. Node Click → Detail Panel

When a graph node is clicked, load the class detail in the bottom panel. This reuses the existing `GET /browser/ontology/tbox/detail?iri=` endpoint and the `tbox_detail.html` template — no new backend work needed for this feature.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| gist subclass hierarchy is mostly via owl:equivalentClass/intersectionOf, not direct rdfs:subClassOf | Medium | Already handled — `_extract_implied_subclasses()` materializes ~42 implied triples at startup. Verify this covers enough for a clean graph. |
| dagre can't use custom rank assignment directly | Low | dagre supports a `rank` function or we pre-assign ranks as node data. Worst case: let dagre auto-rank by following subclass edges — this naturally produces the right hierarchy. |
| 170 nodes may be visually overwhelming without grouping | Medium | Use model-based coloring (each model gets a color), compound nodes for model grouping (optional), and the filter UI to focus on specific models. |
| Cytoscape resize when switching back to TBox tab from display:none parent | Low | Call `cy.resize()` in the tab switch handler. Well-documented Cytoscape behavior. |

## Existing Patterns to Reuse

1. **`graph.js` popover system** — body-appended, position:fixed, viewport coords. Don't reinvent.
2. **`OntologyService.get_ontology_graph_iris()`** — cross-graph FROM clause construction.
3. **`_property_source()` helper** — determines if a class IRI is from gist, a specific model, user-types, or other.
4. **Model detail diagram popover** — data structure pattern (node_data dict with label, color, properties, instance_count).
5. **dagre layout config** — `rankDir: 'TB'`, `nodeSep: 40`, `rankSep: 60` from the model detail diagram.
6. **`filterGraph()` in `graph.js`** — client-side class-based element filtering.
7. **`switchOntologyTab()` JS** — tab switching. Add `cy.resize()` call here.
8. **Icon service** — `IconService.get_icon_map("tree")` for model type colors.

## Boundary Contracts

### Backend → Frontend (new endpoint)

```
GET /browser/ontology/tbox/graph?models=<comma-separated-ids|all>
Content-Type: application/json

Response: {
  "nodes": [{"id": "<iri>", "label": "...", "source": "gist|model-id|user", "layer": <int>}],
  "edges": [{"source": "<iri>", "target": "<iri>", "type": "subclass|property", "label": "..."}],
  "available_models": [{"id": "crm", "label": "CRM", "class_count": 4}],
  "type_colors": {"<iri>": "#hex"}
}
```

### Detail Panel (existing endpoint, reused)

```
GET /browser/ontology/tbox/detail?iri=<encoded-iri>
Content-Type: text/html (htmx fragment)
```

### Tab Switch (JS contract)

When switching to TBox tab: check if graph exists, call `cy.resize()`. No data re-fetch needed.

## Slice Ordering Recommendation

1. **S01: Graph Data API + Basic Graph Rendering** (highest risk) — New backend endpoint, basic Cytoscape rendering in the TBox tab with dagre layout. Proves the data pipeline and layout algorithm work.

2. **S02: Multi-Model Filter + Node Styling** — Client-side filtering UI, per-model color coding, source-based visual differentiation (gist vs model classes).

3. **S03: Detail Panel + Graph Interaction** — Click-to-select, bottom detail panel, popover on hover (reuse graph.js patterns). Graph-to-tree link (optional).

4. **S04: Polish + Persistence** — Graph persistence across tab switches (cy.resize), full-width/height, tree/graph view toggle, popover positioning refinements.

## Candidate Requirements

| ID | Description | Type | Rationale |
|----|-------------|------|-----------|
| CR-1 | Ontology graph shows all installed model classes organized in hierarchical layers with gist at the top | functional | Core value proposition of M056 |
| CR-2 | Multi-select model filter updates graph in real-time without page reload | functional | User needs to focus on specific model subsets |
| CR-3 | Clicking a graph node shows class detail (properties, relationships, instance count) in a detail panel | functional | Interactive exploration is the point of having a graph |
| CR-4 | Graph state (positions, zoom, pan) persists when switching between TBox/ABox/RBox tabs | functional | Explicit user ask from context doc |
| CR-5 | Hover popover appears correctly anchored to the hovered node | functional | Bug fix mentioned in context doc (#42) |

## Open Questions Resolution

**Q: Server-side or client-side layer assignment?**
→ Server-side. The SPARQL engine can compute shortest path from each class to gist roots efficiently via property path queries. Client-side BFS would require the full edge list to be traversed in JS — possible for 170 nodes but cleaner server-side.

**Q: Property edges (domain/range) or only subclass edges?**
→ Start with subclass edges only (S01). Property edges add visual noise and make the graph much denser. Optionally add property edges as a toggle in S02 or S03, rendered as dashed lines with different styling.

## Skills and Tools

No additional skills needed. The core technologies (Cytoscape.js, dagre, SPARQL, htmx, FastAPI) are already well-established in the codebase with mature patterns. No external libraries to add — everything is vendored.
