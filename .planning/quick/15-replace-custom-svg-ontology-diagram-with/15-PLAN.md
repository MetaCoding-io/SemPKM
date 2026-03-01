---
phase: quick-15
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/admin/router.py
  - backend/app/templates/admin/model_ontology_diagram.html
  - frontend/static/css/style.css
autonomous: true
requirements: [QUICK-15]

must_haves:
  truths:
    - "Relationships tab renders a Cytoscape.js interactive graph instead of static SVG"
    - "Each model type appears as a colored node with label"
    - "ObjectProperty relationships appear as directed edges with labels"
    - "Bidirectional edges (e.g. Note->Project and Project->Note) render as two visually separated curved edges"
    - "Hovering a node shows a popover with SHACL properties and instance count"
    - "Self-referential edges render correctly (loops)"
  artifacts:
    - path: "backend/app/admin/router.py"
      provides: "Simplified ontology-diagram endpoint returning HTML partial with JSON data"
    - path: "backend/app/templates/admin/model_ontology_diagram.html"
      provides: "Cytoscape container + inline JS initialization"
    - path: "frontend/static/css/style.css"
      provides: "Updated ontology diagram CSS (container sizing, removed SVG-specific rules)"
  key_links:
    - from: "backend/app/admin/router.py"
      to: "backend/app/templates/admin/model_ontology_diagram.html"
      via: "Jinja2 template rendering with nodes/edges JSON context"
      pattern: "templates_response.*model_ontology_diagram"
    - from: "backend/app/templates/admin/model_ontology_diagram.html"
      to: "cytoscape (global CDN)"
      via: "inline script calling cytoscape({container, elements, style, layout})"
      pattern: "cytoscape\\("
    - from: "model_detail.html"
      to: "ontology-diagram endpoint"
      via: "htmx hx-get on Relationships tab click"
      pattern: "hx-get.*ontology-diagram"
---

<objective>
Replace the custom SVG ontology relationship diagram with Cytoscape.js in the mental model detail dashboard's "Relationships" tab.

Purpose: The custom SVG approach manually computes circular layout, edge paths, and bidirectional curve offsets, but bidirectional edges still visually overlap. Cytoscape handles parallel edge separation natively via its bezier curve style, and provides pan/zoom/interaction for free.

Output: The Relationships tab loads an HTML partial containing a Cytoscape container that self-initializes with nodes (model types) and edges (ObjectProperties), with hover popovers showing SHACL properties and instance counts.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@backend/app/admin/router.py
@backend/app/templates/admin/model_ontology_diagram.html
@backend/app/templates/admin/model_detail.html
@frontend/static/js/graph.js (reference for Cytoscape patterns — do NOT import, write standalone)
@frontend/static/css/style.css (lines 1820-1877: ontology diagram CSS)
@frontend/static/css/views.css (lines 527-628: graph-popover CSS — reuse these classes)

<interfaces>
<!-- Cytoscape.js is globally available via CDN in base.html (v3.33.1 + fcose 2.2.0 + dagre 2.5.0) -->
<!-- graph-popover CSS classes are already defined in views.css — reuse for node hover tooltips -->

From backend/app/admin/router.py (existing endpoint context):
```python
# admin_model_ontology_diagram() already gathers:
# - detail["types"] with iri, label, local_name
# - detail["properties"] with prop_type, domain, range, label
# - detail["shapes"] with target_class, properties[]
# - IconService color per type
# - get_type_analytics() for instance counts
```

From frontend/static/css/views.css (popover classes to reuse):
```css
.graph-popover { display: none; position: absolute; background: var(--color-surface); ... }
.graph-popover-header { display: flex; align-items: baseline; gap: 8px; ... }
.graph-popover-label { font-weight: 600; ... }
.graph-popover-type { font-size: 0.72rem; background: var(--color-primary); ... }
.graph-popover-props { padding: 6px 14px 10px; }
.graph-popover-prop { display: flex; gap: 6px; ... }
.graph-popover-prop-name { font-weight: 600; ... }
.graph-popover-prop-val { color: var(--color-text); ... }
.graph-popover-empty { padding: 8px 14px 10px; ... }
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Simplify the backend endpoint to pass JSON-serializable data to template</name>
  <files>backend/app/admin/router.py</files>
  <action>
Modify `admin_model_ontology_diagram()` in `backend/app/admin/router.py` to remove ALL the manual SVG layout computation (circular layout, edge path geometry, viewBox calculation, bidirectional curve offsets). Cytoscape handles all of this.

The endpoint should still:
1. Fetch `detail` via `model_service.get_model_detail(model_id)`
2. Get type colors from `IconService.get_icon_map("tree")`
3. Build a `nodes` list: one dict per type with keys `id` (local_name), `label`, `color`
4. Build an `edges` list: one dict per ObjectProperty with keys `id` (unique string), `source` (domain local_name), `target` (range local_name), `label` (property label)
5. Gather SHACL properties per type from `detail["shapes"]` — max 6 per node
6. Fetch instance counts via `get_type_analytics()`
7. Build a `node_data` dict keyed by local_name with `label`, `color`, `instance_count`, `properties` (list of {name, type}) — this is for the hover popovers

Pass to template context: `model_id`, `nodes` (list), `edges` (list), `node_data` (dict), and a boolean `has_edges` (len(edges) > 0).

Remove the following code entirely:
- `import math` (no longer needed)
- Circular layout position computation (the for loop with cos/sin)
- `edge_pair_key` bidirectional detection and `curve_offset` assignment
- Edge endpoint shortening and control point computation
- `view_box` computation
- The old `nodes` dict format (was {name: {x, y, label, color, ...}})

Keep the same URL route: `GET /admin/models/{model_id}/ontology-diagram`
  </action>
  <verify>Python syntax check: `python -c "import ast; ast.parse(open('backend/app/admin/router.py').read())"` passes. Verify `import math` is removed. Verify no references to `view_box`, `curve_offset`, `ctrl_x`, `ctrl_y`, `self_loop` remain in the file.</verify>
  <done>Endpoint returns template response with nodes list, edges list, node_data dict, and has_edges boolean. All SVG layout math removed.</done>
</task>

<task type="auto">
  <name>Task 2: Replace SVG template with Cytoscape container and inline initialization</name>
  <files>backend/app/templates/admin/model_ontology_diagram.html, frontend/static/css/style.css</files>
  <action>
**Template (`model_ontology_diagram.html`):**

Rewrite the template to replace the SVG with a Cytoscape.js graph. The template is loaded as an htmx partial (innerHTML swap into `#relationships-content`).

Structure:
```
<div class="ontology-diagram-panel">
  {% if not has_edges %}
    <div class="diagram-empty">...</div>
  {% else %}
    <div id="ontology-cy" class="ontology-cy-container"></div>
    <div class="graph-popover" id="ontology-popover"></div>
    <script> ... Cytoscape init ... </script>
  {% endif %}
</div>
```

The inline `<script>` should:

1. **Build Cytoscape elements** from Jinja-injected JSON:
   - Use `{{ nodes | tojson }}` and `{{ edges | tojson }}` to get the data
   - Map nodes to: `{ group: 'nodes', data: { id: n.id, label: n.label, color: n.color } }`
   - Map edges to: `{ group: 'edges', data: { id: e.id, source: e.source, target: e.target, label: e.label } }`

2. **Initialize Cytoscape:**
   ```js
   var cy = cytoscape({
     container: document.getElementById('ontology-cy'),
     elements: elements,
     style: [ ... ],
     layout: { name: 'fcose', animate: true, animationDuration: 600, quality: 'default', nodeSeparation: 120 },
     minZoom: 0.3,
     maxZoom: 3,
     wheelSensitivity: 0.3
   });
   ```

3. **Style array** (standalone, do NOT import from graph.js):
   - Node style: `background-color: data(color)`, `label: data(label)`, `text-valign: bottom`, `text-halign: center`, `font-size: 11px`, `width: 40`, `height: 40`, `border-width: 2`, `border-color` from data(color) darkened, `text-margin-y: 5`, `color: var(--color-text)` (use the CSS var resolved value or just '#333')
   - Edge style: `curve-style: bezier` (CRITICAL — this is what auto-separates parallel edges), `target-arrow-shape: triangle`, `target-arrow-color: #bbb`, `line-color: #ccc`, `width: 1.5`, `label: data(label)`, `font-size: 9px`, `text-rotation: autorotate`, `color: #888`, `text-background-color: #fff`, `text-background-opacity: 0.85`, `text-background-padding: 2px`
   - For per-node colors, use `data(color)` in the style directly since each node has its own color in data

4. **Hover popover** (reuse graph-popover CSS classes from views.css):
   - Embed `{{ node_data | tojson }}` as `var _nodeData = ...;`
   - On `cy.on('mouseover', 'node', ...)`: after 200ms delay, show popover with same HTML structure as quick-14's SVG popover (header with label + instance count badge, properties list)
   - On `cy.on('mouseout', 'node', ...)`: hide after 150ms delay (allow mouse to enter popover)
   - Popover positioning: use `evt.renderedPosition` relative to the container element
   - Wire popover mouseenter/mouseleave to keep it visible while hovered
   - The `.ontology-diagram-panel` must have `position: relative` for absolute popover positioning

5. **Fit button** (optional nice-to-have): Add a small button at top-right of the container `<button class="cy-fit-btn" onclick="...">` that calls `cy.fit(undefined, 30)` to re-center. Style it absolutely positioned.

**CSS (`style.css`):**

Replace the SVG-specific ontology diagram CSS (lines ~1820-1877) with:

```css
/* Ontology Diagram (Cytoscape) */
.ontology-diagram-panel {
  padding: 0.5rem 0;
  position: relative;
}

.ontology-cy-container {
  width: 100%;
  height: 500px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 6px;
  background: var(--color-surface);
}

.cy-fit-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 0.78rem;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
}

.cy-fit-btn:hover {
  background: var(--color-surface-raised);
  color: var(--color-text);
}
```

Keep `.diagram-empty`, `.diagram-loading` CSS rules unchanged. Remove `.ontology-diagram-svg`, `.ontology-diagram-svg .node-label`, `.ontology-diagram-svg .edge-label` rules (no longer needed).
  </action>
  <verify>
Check template renders without Jinja syntax errors by verifying balanced braces and valid tojson usage. Check CSS has no syntax errors. Verify the template does NOT contain any `<svg>` elements. Verify `cytoscape({` appears in the template script. Verify `curve-style.*bezier` appears in the style config (the key feature for parallel edge separation).
  </verify>
  <done>
Relationships tab loads an HTML partial that initializes a Cytoscape.js graph with: type-colored nodes, labeled directed edges, auto-separated bidirectional edges (via bezier curve-style), hover popovers with SHACL properties and instance counts, and a fit/re-center button. All SVG rendering code removed.
  </done>
</task>

</tasks>

<verification>
1. Navigate to Admin > Models > [any model] > Relationships tab
2. Graph renders with colored nodes for each type
3. Edges show labels and directional arrows
4. Bidirectional edges (e.g., Note <-> Project) display as two separate curved edges (not overlapping)
5. Self-referential edges (if any) render as loops
6. Hovering a node shows popover with SHACL fields and instance count
7. Fit button re-centers the graph
8. Pan and zoom work (drag to pan, scroll to zoom)
</verification>

<success_criteria>
- Cytoscape.js graph replaces SVG in Relationships tab
- Bidirectional edges are visually distinguishable (the primary motivation)
- Node hover popovers show the same data as before (properties + instance count)
- No regressions in the Schema tab or other model detail functionality
- No new JS imports needed (Cytoscape already in global scope via base.html CDN)
</success_criteria>

<output>
After completion, create `.planning/quick/15-replace-custom-svg-ontology-diagram-with/15-SUMMARY.md`
</output>
