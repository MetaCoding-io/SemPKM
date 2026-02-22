# Phase 5: Data Browsing and Visualization - Research

**Researched:** 2026-02-22
**Domain:** Data browsing views (table, cards, graph) with SPARQL-powered view specs, htmx server-rendered patterns, Cytoscape.js graph visualization
**Confidence:** HIGH

## Summary

Phase 5 builds three browsable view types (table, cards, graph) and a view spec execution engine on top of the existing IDE workspace from Phase 4. The existing codebase already has view spec data stored in the triplestore (see `models/basic-pkm/views/basic-pkm.jsonld`) with SPARQL queries, renderer types, and layout configuration -- the task is to build the backend service that loads and executes these specs, plus the frontend renderers.

The table and cards views are server-rendered via htmx (consistent with the existing htmx + Jinja2 patterns throughout the project). The graph view requires a client-side JavaScript library; Cytoscape.js is the recommended choice -- it is framework-agnostic (works with vanilla JS, no React dependency), has built-in force-directed (CoSE), hierarchical (Breadthfirst/Dagre), and radial (Concentric) layouts, and handles the RDF subject-predicate-object to node-edge-node mapping naturally.

**Primary recommendation:** Use htmx server-side rendering for table and cards views (matching existing patterns), Cytoscape.js v3.33+ via CDN for graph visualization, and a new `ViewSpecService` that loads view specs from model views graphs and executes their SPARQL queries.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Table View**: Columns auto-generated from SHACL properties (sh:order for column order, sh:name for headers) as defaults. Users can customize which columns are visible and their order -- saved as a preference per type. Traditional numbered pagination with prev/next, total count, and jump-to-page. Columns are sortable.
- **Cards View**: Flippable cards with CSS flip animation. Front: object title/label + first ~100 chars of Markdown body snippet. Back: all properties + outbound and inbound relationships. Flip toggle button in upper-right corner of each card. Flat card grid by default -- no grouping. User can optionally enable grouping by a property. Same numbered pagination as table view.
- **Graph Visualization**: Default layout: force-directed. Layout picker with options: force-directed, hierarchical, radial -- plus Mental Models can register custom layout algorithms. Semantic-aware styling: Mental Models define node colors and edge styles in their shapes -- falls back to auto-assigned color palette if not defined by model. Interaction: click a node to select it (shows details in right pane), double-click to expand its neighbors into the graph. Graph scope is contextual -- shows whatever the user is currently browsing (type, search results, or full graph). Starts with everything in the current context visible. Pan and zoom for navigation.
- **View Specs System**: View specs defined by both Mental Models (packaged with the model) and users at runtime (saved per-user). Built-in renderer types: table, cards, graph. Mental Models can register custom renderer types (e.g., timeline, kanban, calendar) -- extensible renderer registry. Installing a model automatically makes its view specs available for the types it targets -- zero config, auto-appear. Views discoverable via both a view menu (grouped by model vs user-created) and the command palette ("Open view: ...").
- **View Switching & Navigation**: Views open as tabs in the center pane alongside object tabs -- shared tab bar. Each view type opens in its own tab -- user can have table and graph of the same data open simultaneously. Filters and sort state persist when switching between view types for the same data set. Clicking an object in any view (table row, card, graph node) opens it in a new editor tab -- view stays where it is.

### Claude's Discretion
- Filter UI design (sidebar vs inline vs toolbar)
- Graph rendering library choice (e.g., D3, Cytoscape, Sigma.js)
- Card grid responsive layout breakpoints
- View spec storage format and schema
- Custom renderer registration API design

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEW-01 | User can browse objects in a table view with sortable columns, filtering, and pagination | htmx server-rendered table pattern with query parameter state management; SHACL shapes provide column metadata (sh:order, sh:name); SPARQL SELECT queries with ORDER BY, LIMIT, OFFSET for pagination |
| VIEW-02 | User can browse objects in a cards view with summary display and optional grouping | htmx server-rendered card grid with CSS flip animation; SPARQL SELECT for card data; optional GROUP BY for grouping; same pagination as table |
| VIEW-03 | User can view objects and relationships in a 2D graph with semantic-aware styling (node color by type, edge style by predicate) | Cytoscape.js with SPARQL CONSTRUCT results converted to Cytoscape elements; CoSE/Breadthfirst/Concentric built-in layouts; semantic styling via model-defined or auto-assigned color palettes |
| VIEW-07 | System executes view specs (SPARQL query + renderer type + layout config) to render views | ViewSpecService loads sempkm:ViewSpec instances from model views graphs; dispatches to renderer by type; view specs already exist in Basic PKM model |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cytoscape.js | 3.33.x | Graph visualization (2D force-directed, hierarchical, radial) | Framework-agnostic, no external deps, built-in layouts, rich interaction API, widely adopted for knowledge graphs |
| htmx | 2.0.4 (already in project) | Server-side rendered table and cards views | Already the project's frontend interaction pattern |
| Jinja2Blocks | (already in project) | Partial template rendering for htmx swaps | Already used for workspace, admin, browser partials |
| Split.js | 1.6.5 (already in project) | Resizable pane layout | Already integrated in workspace |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cytoscape-fcose | 2.2.x | Fast Compound Spring Embedder layout (improved force-directed) | Default force-directed layout -- faster and better quality than built-in CoSE |
| cytoscape-dagre | 2.5.x | Hierarchical DAG layout | When user selects hierarchical layout from layout picker |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Cytoscape.js | D3.js force-simulation | D3 gives more control but requires hand-rolling everything (node rendering, zoom, pan, selection, layouts). Cytoscape provides all of these out of the box. |
| Cytoscape.js | Sigma.js | Sigma is faster for very large graphs (10K+ nodes) via WebGL, but has poor documentation and requires more custom code. SemPKM's PKM graphs are typically hundreds of nodes, not thousands. |
| Server-side table/cards | Client-side DataTables/AG-Grid | Client-side JS table libraries would introduce a framework mismatch with the htmx architecture. Server-side rendering keeps the pattern consistent. |

**CDN Installation (no npm/build step needed -- matches project's CDN pattern):**
```html
<!-- Cytoscape.js core -->
<script src="https://unpkg.com/cytoscape@3.33.1/dist/cytoscape.min.js"></script>

<!-- Force-directed layout (fCoSE - optional upgrade over built-in CoSE) -->
<script src="https://unpkg.com/layout-base@2.0.1/layout-base.js"></script>
<script src="https://unpkg.com/cose-base@2.2.0/cose-base.js"></script>
<script src="https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js"></script>

<!-- Hierarchical layout (Dagre) -->
<script src="https://unpkg.com/dagre@0.8.5/dist/dagre.min.js"></script>
<script src="https://unpkg.com/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── views/                    # NEW: View spec execution
│   ├── __init__.py
│   ├── service.py            # ViewSpecService - loads & executes view specs
│   ├── registry.py           # Renderer registry (table, cards, graph + extensible)
│   └── router.py             # View endpoints: /browser/views/...
├── browser/
│   └── router.py             # Extended with view tab opening, filter endpoints
├── templates/
│   └── browser/
│       ├── table_view.html   # Server-rendered table with pagination
│       ├── cards_view.html   # Server-rendered card grid
│       ├── graph_view.html   # Container + Cytoscape init script
│       ├── view_toolbar.html # Shared toolbar: view switching, filters, layout picker
│       ├── pagination.html   # Shared pagination partial
│       └── view_menu.html    # View menu dropdown (model views + user views)
frontend/static/
├── js/
│   └── graph.js              # Cytoscape.js initialization, RDF-to-elements, interaction
├── css/
│   └── views.css             # Table, cards, graph view styles
```

### Pattern 1: View Spec Execution Pipeline
**What:** ViewSpecService loads view specs from the triplestore, executes their SPARQL queries, and dispatches results to the appropriate renderer.
**When to use:** Every time a user opens a view tab (table, cards, graph) or a view menu entry.
**Example:**
```python
# ViewSpecService: load view spec from model's views graph
class ViewSpecService:
    async def get_view_specs_for_type(self, type_iri: str) -> list[ViewSpec]:
        """Query all sempkm:ViewSpec instances targeting this class."""
        sparql = f"""
        SELECT ?spec ?label ?renderer ?query ?columns ?sortDefault
        WHERE {{
          ?spec a <urn:sempkm:vocab:ViewSpec> ;
                <urn:sempkm:vocab:targetClass> <{type_iri}> ;
                <urn:sempkm:vocab:rendererType> ?renderer .
          OPTIONAL {{ ?spec rdfs:label ?label }}
          OPTIONAL {{ ?spec <urn:sempkm:vocab:sparqlQuery> ?query }}
          OPTIONAL {{ ?spec <urn:sempkm:vocab:columns> ?columns }}
          OPTIONAL {{ ?spec <urn:sempkm:vocab:sortDefault> ?sortDefault }}
        }}
        """
        # Query across all model views graphs using FROM clauses
        ...

    async def execute_view_spec(self, spec: ViewSpec, params: ViewParams) -> ViewResult:
        """Execute the SPARQL query from the spec, apply pagination/sorting."""
        if spec.renderer_type == "table":
            return await self._execute_table(spec, params)
        elif spec.renderer_type == "card":
            return await self._execute_cards(spec, params)
        elif spec.renderer_type == "graph":
            return await self._execute_graph(spec)
```

### Pattern 2: htmx Server-Rendered Table with Query Parameter State
**What:** Table sorting, filtering, and pagination managed entirely via query parameters. The server renders the complete table partial on each request, htmx swaps it in.
**When to use:** Table view and cards view pagination/sorting.
**Example:**
```html
<!-- Table header with sortable columns -->
<th>
  <a href="#" hx-get="/browser/views/table/{{ view_id }}?sort=title&dir=asc&page=1&filter={{ current_filter }}"
     hx-target="#view-content" hx-swap="innerHTML" hx-push-url="true">
    Title
    {% if sort_column == 'title' %}
      <span class="sort-indicator">{{ '↑' if sort_dir == 'asc' else '↓' }}</span>
    {% endif %}
  </a>
</th>

<!-- Pagination controls -->
<div class="pagination">
  {% if page > 1 %}
    <a hx-get="/browser/views/table/{{ view_id }}?page={{ page - 1 }}&sort={{ sort }}&dir={{ dir }}"
       hx-target="#view-content">Previous</a>
  {% endif %}
  <span>Page {{ page }} of {{ total_pages }}</span>
  {% if page < total_pages %}
    <a hx-get="/browser/views/table/{{ view_id }}?page={{ page + 1 }}&sort={{ sort }}&dir={{ dir }}"
       hx-target="#view-content">Next</a>
  {% endif %}
</div>
```

### Pattern 3: CSS Card Flip Animation
**What:** Pure CSS 3D card flip using perspective and transform.
**When to use:** Cards view -- each card flips on button click to show back face.
**Example:**
```css
.flip-card {
  perspective: 1000px;
  width: 100%;
  height: 240px;
}

.flip-card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.6s;
  transform-style: preserve-3d;
}

.flip-card.flipped .flip-card-inner {
  transform: rotateY(180deg);
}

.flip-card-front, .flip-card-back {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  border-radius: 8px;
  overflow: hidden;
}

.flip-card-back {
  transform: rotateY(180deg);
}
```

### Pattern 4: SPARQL CONSTRUCT to Cytoscape.js Elements
**What:** Convert RDF triples from SPARQL CONSTRUCT results (Turtle format) to Cytoscape.js node/edge elements.
**When to use:** Graph view initialization and neighbor expansion.
**Example:**
```javascript
// Backend returns JSON with nodes and edges pre-parsed from CONSTRUCT results
// POST /browser/views/graph/{view_id}/data
// Response: { nodes: [{id, label, type, ...}], edges: [{source, target, predicate, ...}] }

function initGraph(containerId, graphData, styleConfig) {
  var cy = cytoscape({
    container: document.getElementById(containerId),
    elements: {
      nodes: graphData.nodes.map(function(n) {
        return { data: { id: n.id, label: n.label, type: n.type } };
      }),
      edges: graphData.edges.map(function(e) {
        return { data: { source: e.source, target: e.target, label: e.predicate } };
      })
    },
    style: buildSemanticStyle(styleConfig),
    layout: { name: 'cose', animate: true }
  });

  // Click node: show details in right pane
  cy.on('tap', 'node', function(evt) {
    var nodeId = evt.target.data('id');
    loadRightPane(nodeId, 'relations');
  });

  // Double-click node: expand neighbors
  cy.on('dbltap', 'node', function(evt) {
    expandNeighbors(cy, evt.target.data('id'));
  });
}
```

### Pattern 5: View Tabs Integration with Existing Tab System
**What:** View tabs share the same tab bar as object tabs but use a different loading mechanism (view content vs object content).
**When to use:** When user opens a view from the view menu or command palette.
**Example:**
```javascript
// Extend existing workspace.js tab system
function openViewTab(viewId, viewLabel, viewType) {
  var tabKey = 'view:' + viewId;  // Prefix to distinguish from object tabs
  var tabs = getTabs();
  var existing = tabs.find(function(t) { return t.iri === tabKey; });

  if (!existing) {
    tabs.push({ iri: tabKey, label: viewLabel, dirty: false, isView: true });
    saveTabs(tabs);
  }

  setActiveTabIri(tabKey);
  renderTabBar();
  loadViewContent(viewId, viewType);
}
```

### Anti-Patterns to Avoid
- **Client-side pagination for table/cards:** The project uses htmx for all dynamic content. Don't introduce a client-side DataTable library. Let the server handle pagination with SPARQL LIMIT/OFFSET.
- **Fetching all data then filtering client-side:** With SPARQL, filtering belongs in the query. SPARQL FILTER, ORDER BY, LIMIT, OFFSET are efficient server-side operations.
- **Building a custom graph layout algorithm:** Cytoscape.js provides CoSE (force-directed), Breadthfirst (hierarchical), and Concentric (radial) out of the box. Use the extensions (fCoSE, Dagre) for better results, don't hand-roll physics simulation.
- **Embedding Cytoscape.js in an iframe:** The graph view should live in the same DOM as the workspace. Cytoscape works with any DOM container element.
- **Animating CSS properties during card flip that trigger layout reflow:** Only use `transform` and `opacity` for flip animation. Never animate `width`, `height`, `box-shadow`, or `filter` during the flip transition.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph force-directed layout | Custom physics simulation | Cytoscape.js CoSE / fCoSE layout | Force-directed layout is a well-studied problem with many edge cases (node overlap, convergence, stability) |
| Graph pan/zoom | Custom mouse/touch event handlers | Cytoscape.js built-in viewport navigation | Cytoscape handles pinch-to-zoom, mouse wheel, touch gestures, and viewport bounds |
| Graph node selection/highlighting | Custom DOM event delegation | Cytoscape.js event system (`cy.on('tap', ...)`) | The library handles hit testing, selection state, and visual feedback |
| Table pagination math | Custom page calculation | SPARQL COUNT + LIMIT/OFFSET + simple arithmetic | SPARQL already supports the primitives; just wrap with total count |
| Card flip animation | JavaScript animation library | Pure CSS `transform: rotateY(180deg)` with `perspective` | CSS 3D transforms run on the GPU compositor, no JS frame loop needed |
| RDF triple to graph element conversion | Custom parser for arbitrary RDF serializations | Backend converts CONSTRUCT results to JSON, frontend consumes structured data | The backend already has rdflib for RDF parsing; serialize to a simple JSON structure for the frontend |

**Key insight:** The graph visualization space is mature. Cytoscape.js handles the hard problems (layout algorithms, viewport management, event handling, rendering optimization). The project's job is data transformation (SPARQL results to Cytoscape elements) and UX integration (connecting graph events to the workspace tab system).

## Common Pitfalls

### Pitfall 1: SPARQL Query Scoping for View Specs
**What goes wrong:** View spec SPARQL queries in the model views graph use full IRIs (not prefixes) and may lack graph scoping. If executed without `FROM <urn:sempkm:current>`, they would query ALL named graphs including event graphs, returning duplicate/stale data.
**Why it happens:** The existing view specs in `basic-pkm.jsonld` contain raw SPARQL strings with full IRIs, stored as literal values. They don't include FROM clauses because the model doesn't know the graph architecture.
**How to avoid:** The ViewSpecService MUST inject `FROM <urn:sempkm:current>` into all view spec SPARQL queries before execution. Use the existing `scope_to_current_graph()` function from `app/sparql/client.py`.
**Warning signs:** Query results include historical/event data, duplicate entries, or data from other named graphs.

### Pitfall 2: Cytoscape.js Container Must Have Explicit Dimensions
**What goes wrong:** Cytoscape.js renders an empty/invisible canvas because the container has `height: 0` or `display: none`.
**Why it happens:** When the graph view tab is created via htmx swap, the container might be injected before the layout is computed, or the container inherits `height: auto` which collapses to 0 when empty.
**How to avoid:** Set explicit height on the graph container (e.g., `height: calc(100vh - 120px)` or use the existing pane layout height). Initialize Cytoscape AFTER the container is visible in the DOM. Use `cy.resize()` if the container size changes (e.g., Split.js drag).
**Warning signs:** Graph area appears blank despite data loading. Check computed styles on the container element.

### Pitfall 3: Tab State Collision Between Object Tabs and View Tabs
**What goes wrong:** Opening a view tab with the same IRI as an object causes the workspace to confuse view state with object state, loading object content into a view tab or vice versa.
**Why it happens:** The existing tab system uses `iri` as the unique key. View specs also have IRIs. If both use the same key space, collisions occur.
**How to avoid:** Prefix view tab keys with `view:` (e.g., `view:bpkm:view-project-table`) to namespace them separately from object IRIs. The `loadObjectContent` vs `loadViewContent` function dispatch should check this prefix.
**Warning signs:** Clicking a view tab loads an object form, or vice versa.

### Pitfall 4: SPARQL CONSTRUCT Results Need Server-Side Conversion
**What goes wrong:** Sending raw Turtle bytes to the frontend for Cytoscape.js rendering, expecting the browser to parse RDF.
**Why it happens:** The triplestore client's `construct()` method returns Turtle bytes. It seems efficient to pass them directly to the frontend.
**How to avoid:** Parse CONSTRUCT results server-side with rdflib (already in the project), convert triples to a simple JSON structure `{nodes: [...], edges: [...]}`, and return that via a JSON API endpoint. The frontend receives a clean data structure it can map directly to Cytoscape elements.
**Warning signs:** Importing an RDF parser (n3.js, rdflib.js) in the browser, adding 100KB+ to the frontend bundle.

### Pitfall 5: View Spec SPARQL Queries with OPTIONAL Patterns and Pagination
**What goes wrong:** SPARQL SELECT queries with multiple OPTIONAL clauses produce cross-product results (one row per combination of optional values), inflating row counts and breaking pagination.
**Why it happens:** The existing view spec queries in basic-pkm.jsonld use OPTIONAL for non-required properties. When an object has 3 tags and 2 participants, SPARQL returns 6 rows for that one object.
**How to avoid:** For table/cards pagination, use a two-phase approach: (1) SELECT DISTINCT ?s with LIMIT/OFFSET to get the page of object IRIs, (2) Fetch properties for those specific objects. Or use SPARQL subqueries to paginate the distinct subjects first.
**Warning signs:** Table shows duplicate rows, pagination count is wildly higher than expected, cards view shows the same object multiple times.

### Pitfall 6: Cytoscape.js Layout Re-Running on Neighbor Expansion
**What goes wrong:** Adding expanded neighbor nodes triggers a full layout recalculation, causing all existing nodes to rearrange and losing the user's mental map.
**Why it happens:** By default, calling `cy.layout({name: 'cose'}).run()` after adding elements re-layouts the entire graph.
**How to avoid:** Use Cytoscape's `eles.layout()` to layout only the newly added elements, keeping existing node positions fixed. Alternatively, use `animate: true` and `fit: false` on the layout to smoothly integrate new nodes without disrupting existing positions.
**Warning signs:** The entire graph "jumps" when double-clicking a node to expand neighbors.

## Code Examples

### Example 1: ViewSpecService - Loading View Specs from Triplestore
```python
# Source: Derived from existing ShapesService pattern (app/services/shapes.py)
# and model views graph structure (models/basic-pkm/views/basic-pkm.jsonld)

from dataclasses import dataclass, field

SEMPKM_VOCAB = "urn:sempkm:vocab:"

@dataclass
class ViewSpec:
    """A view specification loaded from a model or user-defined."""
    spec_iri: str
    label: str
    target_class: str
    renderer_type: str  # "table", "card", "graph"
    sparql_query: str
    columns: list[str] = field(default_factory=list)
    sort_default: str = ""
    card_title: str = ""
    card_subtitle: str = ""
    source_model: str = ""  # model ID or "user"

class ViewSpecService:
    def __init__(self, client):
        self._client = client

    async def get_all_view_specs(self) -> list[ViewSpec]:
        """Load all view specs from all installed model views graphs."""
        # Similar to ShapesService._fetch_shapes_graph pattern:
        # 1. List installed model IDs
        # 2. Build SPARQL with FROM clauses for each model's views graph
        # 3. Query view spec properties
        ...

    async def execute_table_query(self, spec: ViewSpec, page: int, page_size: int,
                                   sort_col: str, sort_dir: str, filter_text: str) -> dict:
        """Execute a table view spec with pagination and sorting."""
        # Inject FROM <urn:sempkm:current> via scope_to_current_graph()
        base_query = scope_to_current_graph(spec.sparql_query)

        # Count total results
        count_query = f"SELECT (COUNT(DISTINCT ?s) AS ?total) WHERE {{ {_extract_where(base_query)} }}"

        # Apply sorting
        sorted_query = f"{base_query} ORDER BY {'DESC' if sort_dir == 'desc' else 'ASC'}(?{sort_col})"

        # Apply pagination
        offset = (page - 1) * page_size
        paginated_query = f"{sorted_query} LIMIT {page_size} OFFSET {offset}"
        ...
```

### Example 2: Graph Data Endpoint - CONSTRUCT to JSON
```python
# Source: Existing construct() pattern from app/triplestore/client.py
# combined with rdflib graph traversal from app/services/shapes.py

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

async def graph_data(spec: ViewSpec, label_service) -> dict:
    """Execute CONSTRUCT query and convert to Cytoscape-compatible JSON."""
    scoped_query = scope_to_current_graph(spec.sparql_query)
    turtle_bytes = await client.construct(scoped_query)

    g = Graph()
    g.parse(data=turtle_bytes, format="turtle")

    nodes = {}
    edges = []

    for s, p, o in g:
        s_str, p_str, o_str = str(s), str(p), str(o)

        # Subjects are always nodes
        if s_str not in nodes:
            nodes[s_str] = {"id": s_str, "types": set()}

        # rdf:type -> record the type on the node
        if p == RDF.type:
            nodes[s_str]["types"].add(o_str)
        # Object property (IRI object) -> edge + target node
        elif isinstance(o, URIRef):
            if o_str not in nodes:
                nodes[o_str] = {"id": o_str, "types": set()}
            edges.append({"source": s_str, "target": o_str, "predicate": p_str})
        # Datatype property -> label attribute on the node
        else:
            # Use label properties as the display label
            if p_str in LABEL_PROPERTIES:
                nodes[s_str]["label"] = str(o)

    # Resolve labels for all node IRIs
    all_iris = list(nodes.keys())
    labels = await label_service.resolve_batch(all_iris)

    node_list = []
    for iri, data in nodes.items():
        node_list.append({
            "id": iri,
            "label": data.get("label", labels.get(iri, iri)),
            "type": list(data["types"])[0] if data["types"] else "unknown",
        })

    return {"nodes": node_list, "edges": edges}
```

### Example 3: Cytoscape.js Initialization with Semantic Styling
```javascript
// Source: Cytoscape.js official docs (https://js.cytoscape.org/)

function buildSemanticStyle(typeColors) {
  var styles = [
    // Default node style
    { selector: 'node',
      style: {
        'label': 'data(label)',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'font-size': '11px',
        'width': 30,
        'height': 30,
        'background-color': '#999'
      }
    },
    // Default edge style
    { selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#ccc',
        'target-arrow-color': '#ccc',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'label': 'data(label)',
        'font-size': '9px',
        'text-rotation': 'autorotate'
      }
    },
    // Selected node
    { selector: 'node:selected',
      style: {
        'border-width': 3,
        'border-color': '#2d5a9e'
      }
    }
  ];

  // Add type-specific node colors from model or auto-palette
  Object.keys(typeColors).forEach(function(typeIri) {
    styles.push({
      selector: 'node[type="' + typeIri + '"]',
      style: { 'background-color': typeColors[typeIri] }
    });
  });

  return styles;
}
```

### Example 4: Flippable Card HTML Structure
```html
<!-- Server-rendered card via Jinja2 -->
<div class="flip-card" data-iri="{{ obj.iri }}">
  <div class="flip-card-inner">
    <div class="flip-card-front">
      <div class="card-title">{{ obj.label }}</div>
      <div class="card-snippet">{{ obj.body_snippet }}</div>
      <button class="flip-toggle" onclick="this.closest('.flip-card').classList.toggle('flipped')"
              title="Flip card">&#x21BB;</button>
    </div>
    <div class="flip-card-back">
      <div class="card-back-header">
        <span class="card-back-title">{{ obj.label }}</span>
        <button class="flip-toggle" onclick="this.closest('.flip-card').classList.toggle('flipped')"
                title="Flip card">&#x21BB;</button>
      </div>
      <div class="card-properties">
        {% for prop in obj.properties %}
          <div class="card-prop"><span class="card-prop-name">{{ prop.name }}:</span> {{ prop.value }}</div>
        {% endfor %}
      </div>
      <div class="card-relations">
        {% for rel in obj.relations %}
          <div class="card-rel">
            <span class="card-rel-predicate">{{ rel.predicate }}</span>
            <a onclick="openTab('{{ rel.target_iri }}', '{{ rel.target_label }}')">{{ rel.target_label }}</a>
          </div>
        {% endfor %}
      </div>
    </div>
  </div>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side DataTable libraries (DataTables.js, AG-Grid) | htmx server-rendered tables with SPARQL backend | 2023+ (htmx maturation) | Eliminates client-side JS framework dependency; server controls all state |
| D3.js hand-coded force layouts | Cytoscape.js declarative graph API | Ongoing | Cytoscape provides layout algorithms, events, and rendering; D3 requires building all from scratch |
| Canvas-based graph rendering | Cytoscape.js HTML5 Canvas (default) or WebGL (via extensions) | Cytoscape 3.x | Built-in support for both rendering backends |
| iframe-embedded React for complex UI | htmx with progressive enhancement for most views | Project decision | htmx for table/cards, vanilla JS for graph -- no React needed for Phase 5 |

**Deprecated/outdated:**
- Cytoscape.js `cose-bilkent` layout: Superseded by `fcose` (faster, better quality) since 2021
- D3 v3 force layout API: D3 v4+ uses `d3.forceSimulation()`, but for SemPKM using Cytoscape.js instead

## Open Questions

1. **User-defined view specs storage location**
   - What we know: Model-defined view specs live in `urn:sempkm:model:{id}:views` named graphs. User-created view specs need to be stored somewhere.
   - What's unclear: Should user view specs go in a dedicated named graph (e.g., `urn:sempkm:user:views`) or in the current state graph? The user constraint says "saved per-user" but Phase 6 auth is in progress -- should this be user-scoped now or use a single user graph for v1?
   - Recommendation: Use a single `urn:sempkm:user:views` named graph for v1 (single-user). Store with `sempkm:createdBy` triple for future multi-user scoping.

2. **Custom renderer registration API mechanics**
   - What we know: Mental Models should be able to register custom renderer types (timeline, kanban, calendar). The decision says "extensible renderer registry."
   - What's unclear: How does a Mental Model register a custom renderer? It would need to ship JavaScript code, which the current model archive format does not support.
   - Recommendation: For v1, define the renderer registry as a Python dict mapping renderer type strings to handler functions. Custom renderers from models are a v2 concern. Document the registry pattern so it can be extended later. The three built-in renderers (table, cards, graph) are sufficient for v1.

3. **Semantic styling data source**
   - What we know: The decision says "Mental Models define node colors and edge styles in their shapes." The current shapes graph uses standard SHACL properties, with no custom styling properties defined.
   - What's unclear: What RDF properties should Mental Models use to declare node colors and edge styles? This needs a vocabulary extension (e.g., `sempkm:nodeColor`, `sempkm:edgeStyle`).
   - Recommendation: Define optional `sempkm:nodeColor` (hex string) on ontology classes and `sempkm:edgeStyle` (solid/dashed/dotted) on object properties. Fall back to an auto-assigned color palette based on type IRI hash. This can be added to the Basic PKM model as an enhancement.

4. **Filter UI design (Claude's discretion)**
   - What we know: Filtering is needed for table and cards views. State should be URL-driven for bookmarkability.
   - Recommendation: Use an inline filter toolbar above the table/cards view. A single text search input plus optional type-specific property dropdowns (generated from SHACL `sh:in` values). Keep it simple -- toolbar pattern, not sidebar.

## Sources

### Primary (HIGH confidence)
- Cytoscape.js official docs (https://js.cytoscape.org/) - API patterns, layouts, styling, events, v3.33.1 current
- Existing project codebase: `app/services/shapes.py`, `app/browser/router.py`, `app/sparql/client.py` - established patterns for SPARQL queries, shapes graph traversal, htmx rendering
- Existing view specs: `models/basic-pkm/views/basic-pkm.jsonld` - actual view spec format with SPARQL queries, renderer types, columns

### Secondary (MEDIUM confidence)
- htmx server-rendered table pattern (https://benoitaverty.com/articles/en/data-table-with-htmx) - query parameter state management, partial rendering
- CSS card flip animation (https://3dtransforms.desandro.com/card-flip, https://www.w3schools.com/howto/howto_css_flip_card.asp) - perspective, transform-style, backface-visibility
- Graph visualization library comparison (https://npm-compare.com/@antv/graphlib,cytoscape,d3-graphviz,graphlib,sigma,vis-network) - npm download stats, feature comparison

### Tertiary (LOW confidence)
- rdf-cytoscape React component (https://github.com/underlay/rdf-cytoscape) - Reference for RDF-to-Cytoscape mapping, but React-specific and not directly applicable

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Cytoscape.js is well-documented, actively maintained, and the right fit for this project's scale and architecture (vanilla JS, CDN, built-in layouts). htmx patterns already proven in this codebase.
- Architecture: HIGH - The ViewSpecService pattern directly follows the existing ShapesService pattern. View specs already exist in the Basic PKM model. Server-rendered table/cards follow existing htmx patterns.
- Pitfalls: HIGH - SPARQL graph scoping is a known issue with documented solutions in this project. Cytoscape container sizing and layout re-running are well-documented in official docs.

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable domain, libraries are mature)
