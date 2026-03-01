---
phase: quick-14
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/admin/router.py
  - backend/app/templates/admin/model_ontology_diagram.html
autonomous: true
requirements: [QUICK-14]

must_haves:
  truths:
    - "Hovering over a node circle in the ontology diagram shows a popover with the type's SHACL properties"
    - "The popover displays property name and type (datatype or linked class) for each SHACL property"
    - "The popover shows instance count when available"
    - "Moving the mouse away from the node hides the popover"
    - "The popover reuses the existing graph-popover CSS classes (no new CSS)"
  artifacts:
    - path: "backend/app/admin/router.py"
      provides: "Enriched node data with SHACL properties and instance counts"
    - path: "backend/app/templates/admin/model_ontology_diagram.html"
      provides: "Popover HTML div + hover JS for SVG nodes"
  key_links:
    - from: "backend/app/admin/router.py"
      to: "backend/app/templates/admin/model_ontology_diagram.html"
      via: "template context nodes dict enriched with properties list"
      pattern: "node.*properties"
---

<objective>
Add hover tooltips to ontology diagram SVG nodes showing SHACL property details per type.

Purpose: When viewing the ontology relationship diagram, users currently see only type names on the nodes. Hovering should reveal the type's schema — its SHACL-defined properties (name + datatype/class) and instance count — using the existing graph-popover CSS pattern.

Output: Enriched ontology diagram with hover popovers on every node.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@backend/app/admin/router.py
@backend/app/templates/admin/model_ontology_diagram.html
@frontend/static/css/views.css (lines 527-631, READ ONLY — graph-popover CSS)
@backend/app/services/models.py (get_model_detail, _query_shapes)

<interfaces>
<!-- Existing graph-popover CSS classes to reuse (from views.css) — DO NOT modify views.css -->
.graph-popover            — container, display:none, position:absolute, styled card
.graph-popover-header     — flex row with label + type badge
.graph-popover-label      — bold type name
.graph-popover-type       — small colored badge
.graph-popover-props      — property list container
.graph-popover-prop       — single property row (flex)
.graph-popover-prop-name  — bold prop name with ::after colon
.graph-popover-prop-val   — prop value text
.graph-popover-empty      — italic "no properties" message

<!-- Existing data from get_model_detail() shapes -->
Each shape has:
  - target_class: str (local_name matching nodes dict key)
  - properties: list of {name, path, type, cardinality, group, required}

<!-- Existing data from get_type_analytics() -->
analytics[type_iri] = {count: int, top_nodes: list}
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Enrich ontology diagram endpoint with SHACL properties and instance counts per node</name>
  <files>backend/app/admin/router.py</files>
  <action>
In `admin_model_ontology_diagram()`, after building the `nodes` dict (line ~196), add SHACL property data and instance counts to each node:

1. Build a shape-property lookup from `detail["shapes"]`. For each shape, map `shape["target_class"]` to its `shape["properties"]` list. Each property has keys: `name`, `path`, `type`, `cardinality`, `group`, `required`.

2. Fetch instance counts using `model_service.get_type_analytics()`:
   - Build `type_iris` list: `[t["iri"] for t in detail["types"]]`
   - Call `analytics = await model_service.get_type_analytics(type_iris)`
   - Build a lookup from local_name to count: for each type in `detail["types"]`, map `t["local_name"]` to `analytics.get(t["iri"], {}).get("count", 0)`

3. Enrich each node in the `nodes` dict with two new keys:
   - `"properties"`: list of dicts from the shape lookup (default to empty list if no shape found for that type). Limit to first 6 properties to keep the popover manageable.
   - `"instance_count"`: int from the analytics lookup (default 0).

The `nodes` dict is keyed by `type_name` (which is the `local_name` from `detail["types"]`), matching `shape["target_class"]`.

This is the same pattern already used in `admin_model_detail()` (lines 95-118) where shapes and analytics are merged into type_map. Here we just attach the relevant subset to each node.
  </action>
  <verify>
Read the modified endpoint function and confirm:
- shape_props lookup is built from detail["shapes"]
- get_type_analytics is called
- each node in nodes dict has "properties" (list, max 6) and "instance_count" (int)
- no existing behavior is broken (nodes still have x, y, label, color)
  </verify>
  <done>Every node in the template context includes its SHACL properties list and instance count.</done>
</task>

<task type="auto">
  <name>Task 2: Add popover HTML and hover JS to ontology diagram template</name>
  <files>backend/app/templates/admin/model_ontology_diagram.html</files>
  <action>
Modify the ontology diagram template to add a hover popover for SVG nodes.

**1. Make node circles interactive:**
For each node circle in the SVG `{% for name, node in nodes.items() %}` loop:
- Add `class="ontology-node"` to the `<circle>` element
- Add `data-node-name="{{ name }}"` to the circle
- Remove `pointer-events: none` from the node-label `<text>` or ensure the circle receives hover events (the text already has `pointer-events: none` via CSS, so the circle will get the events)

**2. Embed property data as a JSON script block:**
After the `</svg>` tag but before the closing `{% endif %}`, add a `<script>` tag that builds a JS object mapping node names to their property data. Use Jinja to render the data:

```html
<script>
var _ontologyNodeData = {
{% for name, node in nodes.items() %}
  "{{ name }}": {
    "label": "{{ node.label }}",
    "color": "{{ node.color }}",
    "instance_count": {{ node.instance_count }},
    "properties": [
      {% for prop in node.properties %}
      {"name": "{{ prop.name }}", "type": "{{ prop.type }}"}{% if not loop.last %},{% endif %}
      {% endfor %}
    ]
  }{% if not loop.last %},{% endif %}
{% endfor %}
};
</script>
```

Use Jinja's `|tojson` filter if available for safety, but since the data is controlled (SHACL labels), simple string interpolation is acceptable.

**3. Add popover container div:**
After the SVG (outside the `<svg>` element but inside `.ontology-diagram-panel`), add:

```html
<div class="graph-popover" id="ontology-popover"></div>
```

**4. Add hover JS:**
In the script section (can be in the same script block as the data or a separate one), add:

```javascript
(function() {
  var popover = document.getElementById('ontology-popover');
  var panel = popover.closest('.ontology-diagram-panel');
  var hideTimer = null;

  function showPopover(circle, name) {
    var data = _ontologyNodeData[name];
    if (!data) return;

    var html = '<div class="graph-popover-header">' +
      '<span class="graph-popover-label">' + data.label + '</span>' +
      '<span class="graph-popover-type" style="background:' + data.color + '">' +
        data.instance_count + ' instance' + (data.instance_count !== 1 ? 's' : '') +
      '</span></div>';

    if (data.properties.length > 0) {
      html += '<div class="graph-popover-props">';
      for (var i = 0; i < data.properties.length; i++) {
        var p = data.properties[i];
        html += '<div class="graph-popover-prop">' +
          '<span class="graph-popover-prop-name">' + p.name + '</span>' +
          '<span class="graph-popover-prop-val">' + (p.type || 'any') + '</span></div>';
      }
      html += '</div>';
    } else {
      html += '<div class="graph-popover-empty">No properties defined</div>';
    }

    popover.innerHTML = html;
    popover.style.display = 'block';

    // Position relative to the panel container
    var panelRect = panel.getBoundingClientRect();
    var circleRect = circle.getBoundingClientRect();
    var left = circleRect.right - panelRect.left + 8;
    var top = circleRect.top - panelRect.top - 12;

    popover.style.left = left + 'px';
    popover.style.top = top + 'px';

    // Adjust if overflowing right edge
    var pRect = popover.getBoundingClientRect();
    if (pRect.right > panelRect.right - 8) {
      popover.style.left = (circleRect.left - panelRect.left - pRect.width - 8) + 'px';
    }
    // Adjust if overflowing bottom
    if (pRect.bottom > panelRect.bottom - 8) {
      popover.style.top = (circleRect.top - panelRect.top - pRect.height + 12) + 'px';
    }
  }

  // Set panel to position:relative for absolute popover positioning
  panel.style.position = 'relative';

  document.querySelectorAll('.ontology-node').forEach(function(circle) {
    circle.style.cursor = 'pointer';
    circle.addEventListener('mouseenter', function() {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      showPopover(circle, circle.getAttribute('data-node-name'));
    });
    circle.addEventListener('mouseleave', function() {
      hideTimer = setTimeout(function() { popover.style.display = 'none'; }, 150);
    });
  });

  // Keep popover visible when mouse enters it
  popover.addEventListener('mouseenter', function() {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
  });
  popover.addEventListener('mouseleave', function() {
    popover.style.display = 'none';
  });
})();
```

Key details:
- The popover is positioned relative to `.ontology-diagram-panel` (set to position:relative via JS)
- Uses `getBoundingClientRect()` for SVG element positioning (SVG circles don't have offsetLeft/Top)
- 150ms hide delay allows mouse to travel from node to popover
- The `.graph-popover-type` badge uses the node's color as background for visual association
- Instance count is shown in the type badge area (e.g., "3 instances")
- Properties show name and type (datatype like "xsd:string" or class ref like "Person (ref)")
  </action>
  <verify>
Load the app in browser, navigate to Admin > Models > [model] > Relationships tab. Hover over a type node circle. Verify:
1. Popover appears after short delay showing type label, instance count badge, and property list
2. Moving mouse away hides the popover
3. Moving mouse from node to popover keeps it visible
4. Popover stays within viewport bounds (doesn't overflow right or bottom)

Automated: `grep -c "graph-popover" backend/app/templates/admin/model_ontology_diagram.html` returns at least 5 (confirming popover HTML classes are used in template)
  </verify>
  <done>
Hovering over any ontology diagram node shows a styled popover with the type's SHACL properties (name + type), instance count, and the type label. The popover reuses existing graph-popover CSS. Moving away hides it.
  </done>
</task>

</tasks>

<verification>
1. The ontology diagram endpoint returns nodes with `properties` and `instance_count` fields
2. The template renders a `.graph-popover` div and JS hover handlers
3. No modifications to views.css — all styling via existing classes
4. Existing diagram rendering (SVG, edges, labels) unchanged
</verification>

<success_criteria>
- Hover over any node in the ontology SVG diagram shows a popover with type name, instance count, and SHACL property list
- Popover uses existing `.graph-popover-*` CSS classes from views.css (no new CSS)
- Popover hides on mouse-out with brief delay for mouse-to-popover travel
- Popover positions correctly and adjusts for viewport boundaries
- No regressions in existing diagram rendering
</success_criteria>

<output>
After completion, create `.planning/quick/14-add-hover-tooltips-to-ontology-diagram-n/14-SUMMARY.md`
</output>
