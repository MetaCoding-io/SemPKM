---
phase: quick-12
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/services/models.py
  - backend/app/admin/router.py
  - backend/app/templates/admin/model_detail.html
  - backend/app/templates/admin/model_connections.html
  - backend/app/templates/admin/model_ontology_diagram.html
  - frontend/static/css/style.css
autonomous: true
requirements: [QUICK-12]

must_haves:
  truths:
    - "Model detail page has Schema and Relationships tabs"
    - "Relationships tab shows an SVG diagram of type-to-type connections derived from OWL ObjectProperties"
    - "Diagram shows model types as labeled nodes with icons/colors"
    - "Diagram shows ObjectProperty relationships as labeled directed edges between type nodes"
    - "Self-referential relationships (e.g. Concept --broader--> Concept) render as visible loops"
    - "Old connections tab (raw SPARQL triples) is fully removed"
  artifacts:
    - path: "backend/app/templates/admin/model_ontology_diagram.html"
      provides: "SVG diagram partial template for type-to-type relationships"
    - path: "backend/app/admin/router.py"
      provides: "GET /admin/models/{model_id}/ontology-diagram endpoint"
  key_links:
    - from: "backend/app/templates/admin/model_detail.html"
      to: "/admin/models/{model_id}/ontology-diagram"
      via: "htmx hx-get on Relationships tab click"
      pattern: "hx-get.*ontology-diagram"
    - from: "backend/app/admin/router.py"
      to: "detail['properties'] ObjectProperty data"
      via: "existing get_model_detail() method"
      pattern: "get_model_detail"
---

<objective>
Replace the "Connections" tab (added in quick-11, showing raw SPARQL triples) with a "Relationships" tab that renders an inline SVG diagram showing how model types relate to each other via their OWL ObjectProperties.

Purpose: The raw triple list is not useful for understanding a model's structure. A visual diagram showing type-to-type relationships (e.g. Note --creator--> Person, Concept --broader--> Concept) gives immediate understanding of the ontology's shape.

Output: SVG relationship diagram on the model detail dashboard, loaded lazily via htmx tab click. No external JS libraries -- pure server-rendered SVG.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/11-add-connections-tab-to-mental-model-deta/11-SUMMARY.md

Key existing data flow:
- `admin_model_detail()` in router.py already calls `model_service.get_model_detail(model_id)` which returns `detail["properties"]` -- a list of dicts with keys: iri, label, comment, prop_type ("Object" or "Datatype"), domain, range, inverse
- ObjectProperty entries already have domain/range as short local names (e.g. "Note", "Person", "Project")
- `detail["types"]` has: iri, local_name, label, comment, icon, color
- The existing "Relationship Map" section in the schema tab (lines 242-267 of model_detail.html) already iterates `object_props` from `detail.properties` -- this proves the data is available
- Tab bar pattern established in quick-11: `.model-detail-tabs` with `data-tab` attributes, `switchModelTab()` JS, htmx lazy-load on `hx-trigger="click once"`

<interfaces>
<!-- From backend/app/admin/router.py admin_model_detail() -->
detail["properties"] = [
    {
        "iri": "urn:sempkm:model:basic-pkm:hasParticipant",
        "label": "Has Participant",
        "prop_type": "Object",      # <-- only these matter for diagram
        "domain": "Project",        # short local name
        "range": "Person",          # short local name
        "inverse": "Participates In"
    },
    ...
]

detail["types"] = [
    {
        "iri": "urn:sempkm:model:basic-pkm:Note",
        "local_name": "Note",
        "label": "Note",
        "icon": "sticky-note",
        "color": "#4CAF50"
    },
    ...
]
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove quick-11 connections code, add ontology diagram endpoint</name>
  <files>
    backend/app/services/models.py
    backend/app/admin/router.py
    backend/app/templates/admin/model_connections.html
    backend/app/templates/admin/model_ontology_diagram.html
  </files>
  <action>
1. **Remove `get_model_connections()` method** from `backend/app/services/models.py` (lines 631-749). This is the entire method that queries outbound/inbound SPARQL triples. Keep everything else in the file unchanged.

2. **Replace the `/admin/models/{model_id}/connections` endpoint** in `backend/app/admin/router.py` (lines 137-158) with a new endpoint:

```python
@router.get("/models/{model_id}/ontology-diagram")
async def admin_model_ontology_diagram(
    request: Request,
    model_id: str,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
):
    """Render SVG ontology relationship diagram for a model.

    Shows type-to-type relationships derived from OWL ObjectProperties.
    Returns an htmx partial with inline SVG.
    """
    detail = await model_service.get_model_detail(model_id)
    if detail is None:
        return HTMLResponse(
            '<div class="diagram-empty"><p>Model not found.</p></div>',
            status_code=404,
        )

    # Get icon data from IconService for type colors
    from app.services.icons import IconService
    icon_svc = IconService(models_dir="/app/models")
    icon_map = icon_svc.get_icon_map("tree")

    # Build type info with colors
    type_info = {}
    for t in detail["types"]:
        icon_data = icon_map.get(t["iri"], {"icon": "circle", "color": "#999"})
        type_info[t["local_name"]] = {
            "label": t["label"],
            "color": icon_data["color"],
        }

    # Filter to ObjectProperties only, building edges
    edges = []
    for p in detail["properties"]:
        if p["prop_type"] == "Object" and p["domain"] and p["range"]:
            edges.append({
                "from": p["domain"],
                "to": p["range"],
                "label": p["label"],
                "inverse": p.get("inverse", ""),
            })

    # Compute node positions -- circular layout
    type_names = list(type_info.keys())
    node_count = len(type_names)
    import math
    # SVG dimensions
    svg_w, svg_h = 700, 500
    cx, cy = svg_w / 2, svg_h / 2
    radius = min(svg_w, svg_h) * 0.35
    nodes = {}
    for i, name in enumerate(type_names):
        angle = (2 * math.pi * i / node_count) - math.pi / 2  # start from top
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        nodes[name] = {
            "x": round(x, 1),
            "y": round(y, 1),
            "label": type_info[name]["label"],
            "color": type_info[name]["color"],
        }

    context = {
        "request": request,
        "model_id": model_id,
        "nodes": nodes,
        "edges": edges,
        "svg_w": svg_w,
        "svg_h": svg_h,
    }
    return templates_response(request, "admin/model_ontology_diagram.html", context)
```

Remove the `LabelService` import from the get_label_service dependency if it was only used for the connections endpoint. Check: `get_label_service` is still used elsewhere, so keep the import but remove the `label_service` parameter from the deleted endpoint.

3. **Delete** `backend/app/templates/admin/model_connections.html` entirely.

4. **Create** `backend/app/templates/admin/model_ontology_diagram.html` -- an htmx partial that renders an inline SVG:

```html
{# Ontology relationship diagram for model detail dashboard.
   Rendered as htmx partial loaded on Relationships tab click.
   Accepts:
     nodes: dict of {type_name: {x, y, label, color}}
     edges: list of {from, to, label, inverse}
     svg_w: int, svg_h: int
     model_id: str
#}

<div class="ontology-diagram-panel">
    {% if not edges %}
    <div class="diagram-empty">
        <i data-lucide="git-branch"></i>
        <p>No relationships defined between types in this model.</p>
    </div>
    {% else %}
    <svg viewBox="0 0 {{ svg_w }} {{ svg_h }}" class="ontology-diagram-svg"
         xmlns="http://www.w3.org/2000/svg">
        <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6"
                    refX="8" refY="3" orient="auto" fill="var(--color-text-muted)">
                <polygon points="0 0, 8 3, 0 6" />
            </marker>
        </defs>

        {# Render edges #}
        {% for edge in edges %}
        {% set src = nodes[edge['from']] %}
        {% set tgt = nodes[edge['to']] %}
        {% if src and tgt %}
            {% if edge['from'] == edge['to'] %}
            {# Self-referencing loop -- draw arc above the node #}
            <path d="M {{ src.x - 20 }} {{ src.y - 22 }}
                     C {{ src.x - 50 }} {{ src.y - 80 }},
                       {{ src.x + 50 }} {{ src.y - 80 }},
                       {{ src.x + 20 }} {{ src.y - 22 }}"
                  fill="none" stroke="var(--color-text-faint)" stroke-width="1.5"
                  marker-end="url(#arrowhead)" />
            <text x="{{ src.x }}" y="{{ src.y - 68 }}"
                  text-anchor="middle" class="edge-label">{{ edge.label }}</text>
            {% else %}
            {# Normal edge between two different nodes #}
            {# Offset line endpoints by ~25px from node center to avoid overlap with circle #}
            {% set dx = tgt.x - src.x %}
            {% set dy = tgt.y - src.y %}
            <line x1="{{ src.x }}" y1="{{ src.y }}"
                  x2="{{ tgt.x }}" y2="{{ tgt.y }}"
                  stroke="var(--color-text-faint)" stroke-width="1.5"
                  marker-end="url(#arrowhead)" />
            <text x="{{ (src.x + tgt.x) / 2 }}" y="{{ (src.y + tgt.y) / 2 - 8 }}"
                  text-anchor="middle" class="edge-label">{{ edge.label }}</text>
            {% if edge.inverse %}
            <text x="{{ (src.x + tgt.x) / 2 }}" y="{{ (src.y + tgt.y) / 2 + 14 }}"
                  text-anchor="middle" class="edge-label edge-inverse">{{ edge.inverse }}</text>
            {% endif %}
            {% endif %}
        {% endif %}
        {% endfor %}

        {# Render nodes #}
        {% for name, node in nodes.items() %}
        <circle cx="{{ node.x }}" cy="{{ node.y }}" r="24"
                fill="{{ node.color }}22" stroke="{{ node.color }}" stroke-width="2" />
        <text x="{{ node.x }}" y="{{ node.y + 4 }}"
              text-anchor="middle" class="node-label"
              fill="{{ node.color }}">{{ node.label }}</text>
        {% endfor %}
    </svg>
    {% endif %}
</div>

<script>
if (typeof lucide !== 'undefined') lucide.createIcons();
</script>
```

The SVG uses CSS variables for theming, circular layout computed server-side, arrowhead markers for edge direction, and self-loop arcs for reflexive properties. No external JS libraries.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "
import ast, sys
# Verify get_model_connections is removed from models.py
tree = ast.parse(open('backend/app/services/models.py').read())
methods = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
assert 'get_model_connections' not in methods, 'get_model_connections should be removed'
print('OK: get_model_connections removed')

# Verify new endpoint exists in router
router_src = open('backend/app/admin/router.py').read()
assert 'ontology-diagram' in router_src, 'ontology-diagram endpoint missing'
assert '/connections' not in router_src or 'ontology' in router_src, 'old connections endpoint should be gone'
print('OK: ontology-diagram endpoint exists')

# Verify new template exists
import os
assert os.path.exists('backend/app/templates/admin/model_ontology_diagram.html'), 'diagram template missing'
assert not os.path.exists('backend/app/templates/admin/model_connections.html'), 'old connections template should be deleted'
print('OK: templates correct')
print('ALL CHECKS PASSED')
"</automated>
  </verify>
  <done>
    - `get_model_connections()` method removed from ModelService
    - `/connections` endpoint replaced with `/ontology-diagram` endpoint
    - `model_connections.html` deleted, `model_ontology_diagram.html` created
    - New endpoint computes circular SVG layout from existing ObjectProperty data
  </done>
</task>

<task type="auto">
  <name>Task 2: Update model_detail.html tab UI and CSS</name>
  <files>
    backend/app/templates/admin/model_detail.html
    frontend/static/css/style.css
  </files>
  <action>
1. **Update `model_detail.html`** tab bar and panels:

   a. **Rename the tab** from "Connections" to "Relationships" and update the htmx target:
   Change the second tab button (line 50-56) from:
   ```html
   <button class="model-tab" data-tab="connections" onclick="switchModelTab('connections')"
           hx-get="/admin/models/{{ detail.info.model_id }}/connections"
           hx-target="#connections-content"
           hx-swap="innerHTML"
           hx-trigger="click once">
       <i data-lucide="network"></i> Connections
   </button>
   ```
   To:
   ```html
   <button class="model-tab" data-tab="relationships" onclick="switchModelTab('relationships')"
           hx-get="/admin/models/{{ detail.info.model_id }}/ontology-diagram"
           hx-target="#relationships-content"
           hx-swap="innerHTML"
           hx-trigger="click once">
       <i data-lucide="git-branch"></i> Relationships
   </button>
   ```

   b. **Rename the connections panel** (lines 297-303) from:
   ```html
   <div id="connections-panel" class="model-tab-panel" style="display:none;">
       <div id="connections-content">
           <div class="connections-loading">...</div>
       </div>
   </div>
   ```
   To:
   ```html
   <div id="relationships-panel" class="model-tab-panel" style="display:none;">
       <div id="relationships-content">
           <div class="diagram-loading">
               <i data-lucide="loader-2" class="spin"></i> Loading diagram...
           </div>
       </div>
   </div>
   ```

   c. **Update `switchModelTab()` JS** (lines 311-321) to reference `relationships` instead of `connections`:
   ```javascript
   function switchModelTab(tabName) {
       document.querySelectorAll('.model-tab').forEach(function(btn) {
           btn.classList.toggle('active', btn.dataset.tab === tabName);
       });
       document.getElementById('schema-panel').style.display = tabName === 'schema' ? '' : 'none';
       document.getElementById('relationships-panel').style.display = tabName === 'relationships' ? '' : 'none';
       if (typeof lucide !== 'undefined') lucide.createIcons();
   }
   ```

   d. **Remove the "Relationship Map" section** from the schema panel (lines 241-267). This old flat list of domain--label-->range is being superseded by the SVG diagram in the Relationships tab. Remove the entire block from `{% set object_props = [] %}` through the closing `{% endif %}` after the `.rel-map-card` div.

2. **Update `style.css`**:

   a. **Remove ALL connections-related CSS** (lines 1888-2033 approximately): `.connections-summary`, `.connections-stat`, `.connections-empty`, `.connections-direction-section`, `.connection-group`, `.connection-predicate`, `.connection-items`, `.connection-item`, `.connection-label`, `.connection-type-badge`, `.connections-loading`. Keep the `.spin` and `@keyframes spin` rules (lines 2025-2033) -- those are reusable.

   b. **Remove the `.rel-map-*` CSS** (lines 1710-1846 approximately): `.rel-map-card`, `.rel-map-row`, `.rel-map-domain`, `.rel-map-range`, `.rel-map-edge`, `.rel-map-label`, `.rel-map-arrow`, `.rel-map-inverse-label` and their responsive breakpoint rule at line 1842.

   c. **Add new SVG diagram CSS** in place of the removed blocks (after `.model-tab.active`):

   ```css
   /* Ontology Diagram */
   .ontology-diagram-panel {
     padding: 0.5rem 0;
   }

   .ontology-diagram-svg {
     width: 100%;
     max-width: 700px;
     height: auto;
     margin: 0 auto;
     display: block;
   }

   .ontology-diagram-svg .node-label {
     font-size: 13px;
     font-weight: 600;
     font-family: var(--font-sans);
     pointer-events: none;
   }

   .ontology-diagram-svg .edge-label {
     font-size: 10px;
     fill: var(--color-text-muted);
     font-family: var(--font-sans);
     pointer-events: none;
   }

   .ontology-diagram-svg .edge-inverse {
     font-style: italic;
     fill: var(--color-text-faint);
   }

   .diagram-empty {
     text-align: center;
     padding: 2.5rem 1rem;
     color: var(--color-text-faint);
   }

   .diagram-empty i, .diagram-empty svg {
     width: 32px;
     height: 32px;
     margin-bottom: 0.5rem;
     opacity: 0.5;
   }

   .diagram-empty p {
     font-size: 0.88rem;
     max-width: 400px;
     margin: 0 auto;
     line-height: 1.5;
   }

   .diagram-loading {
     text-align: center;
     padding: 2rem;
     color: var(--color-text-faint);
     font-size: 0.85rem;
   }

   .diagram-loading i, .diagram-loading svg {
     width: 18px;
     height: 18px;
     margin-right: 0.3rem;
     vertical-align: middle;
   }
   ```

   d. Keep the `.model-detail-tabs` and `.model-tab` CSS unchanged -- those are reused.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "
# Verify model_detail.html updates
html = open('backend/app/templates/admin/model_detail.html').read()
assert 'relationships-panel' in html, 'relationships-panel missing'
assert 'connections-panel' not in html, 'old connections-panel still present'
assert 'ontology-diagram' in html, 'ontology-diagram htmx URL missing'
assert 'rel-map' not in html, 'old rel-map section should be removed'
print('OK: model_detail.html updated')

# Verify CSS updates
css = open('frontend/static/css/style.css').read()
assert '.ontology-diagram-svg' in css, 'diagram CSS missing'
assert '.connections-summary' not in css, 'old connections CSS still present'
assert '.connections-stat' not in css, 'old connections stat CSS still present'
assert '.rel-map-card' not in css, 'old rel-map CSS still present'
assert '.diagram-empty' in css, 'diagram-empty CSS missing'
assert '.spin' in css, 'spin animation should be preserved'
print('OK: style.css updated')
print('ALL CHECKS PASSED')
"</automated>
  </verify>
  <done>
    - "Connections" tab renamed to "Relationships" with git-branch icon
    - Tab targets new `/ontology-diagram` endpoint via htmx
    - Old "Relationship Map" flat list removed from schema panel (superseded by diagram)
    - All connections-related CSS removed, new diagram CSS added
    - `.spin` animation preserved for loading state reuse
  </done>
</task>

</tasks>

<verification>
After both tasks:
1. Model detail page loads without errors
2. Schema tab shows types with fields, views, relationships (per-type), analytics -- no "Relationship Map" section at bottom
3. Relationships tab shows SVG diagram with type nodes in a circle, labeled directed edges for ObjectProperties
4. Self-referential properties (if any) render as arcs
5. Empty model (no ObjectProperties) shows empty state message
6. No references to old connections code remain
</verification>

<success_criteria>
- Model detail page has two tabs: Schema and Relationships
- Relationships tab renders server-side SVG showing type-to-type connections
- SVG uses model type colors for nodes, labeled edges with arrows, no external JS
- All quick-11 connections code is fully removed (method, endpoint, template, CSS)
- Page functions correctly with htmx lazy-load pattern preserved
</success_criteria>

<output>
After completion, create `.planning/quick/12-replace-connections-tab-with-ontology-re/12-SUMMARY.md`
</output>
