---
phase: quick-13
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/admin/router.py
  - backend/app/templates/admin/model_ontology_diagram.html
  - frontend/static/css/style.css
autonomous: true
requirements: [QUICK-13]

must_haves:
  truths:
    - "Diagram auto-scales to fill available viewport space regardless of node count"
    - "Arrowheads terminate at node circle boundary, not overlapping node text"
    - "Bidirectional relationships render as two visually distinct curved edges"
  artifacts:
    - path: "backend/app/admin/router.py"
      provides: "Computed viewBox, edge shortening, bidirectional edge separation with curve offsets"
      contains: "viewBox"
    - path: "backend/app/templates/admin/model_ontology_diagram.html"
      provides: "SVG with dynamic viewBox, shortened edges via path, curved bidirectional edges"
      contains: "viewBox"
    - path: "frontend/static/css/style.css"
      provides: "Diagram CSS without max-width constraint"
      contains: "ontology-diagram-svg"
  key_links:
    - from: "backend/app/admin/router.py"
      to: "backend/app/templates/admin/model_ontology_diagram.html"
      via: "Template context variables (viewBox, edge coordinates, curve offsets)"
      pattern: "view_box|curve_offset|shortened"
---

<objective>
Fix three visual issues in the ontology relationship diagram on the mental model detail page:
(1) zoom-to-fit so the diagram fills the viewport, (2) arrowheads stop at node circle edges
not overlapping text, (3) bidirectional edges render as two separate curved lines.

Purpose: The diagram was added in quick task 12 but has visual polish issues that reduce readability.
Output: Updated router, template, and CSS producing a properly scaled, readable diagram.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@backend/app/admin/router.py (ontology-diagram endpoint, lines 136-208)
@backend/app/templates/admin/model_ontology_diagram.html (SVG template)
@frontend/static/css/style.css (lines 1821-1870, diagram styles)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Compute viewBox, shorten edges, and separate bidirectional edges in router</name>
  <files>backend/app/admin/router.py</files>
  <action>
Modify the `admin_model_ontology_diagram` endpoint (lines 136-208) with three changes:

**1. Compute tight viewBox instead of fixed 700x500:**
After computing node positions (circular layout), find the bounding box of all nodes:
```python
min_x = min(n["x"] for n in nodes.values()) - 60  # padding for labels
max_x = max(n["x"] for n in nodes.values()) + 60
min_y = min(n["y"] for n in nodes.values()) - 60
max_y = max(n["y"] for n in nodes.values()) + 60
view_box = f"{min_x} {min_y} {max_x - min_x} {max_y - min_y}"
```
Pass `view_box` to template context instead of `svg_w`/`svg_h`.

**2. Pre-compute shortened edge endpoints and arc points in the router:**
For each edge, compute the unit vector from src to tgt, then shorten both ends by the node radius (24px) so the line starts/ends at the circle boundary, not the center. The arrowhead marker refX is 8, so shorten the target end by 24+8=32px total. Store `x1, y1, x2, y2` on each edge dict.

For self-referencing edges (from==to), keep existing arc approach but adjust control points to start/end at circle boundary.

**3. Separate bidirectional edges with curve offsets:**
After building the edges list, detect bidirectional pairs: group edges by frozenset(from, to). When a pair of edges share the same two nodes (A->B and B->A):
- Remove the `inverse` field from both (each edge is its own direction now)
- Add a `curve_offset` field: +20 for the first edge, -20 for the second
- For non-paired edges, set `curve_offset` to 0

For curved edges, compute a control point perpendicular to the midpoint:
```python
mx, my = (x1+x2)/2, (y1+y2)/2
dx, dy = x2-x1, y2-y1
length = math.sqrt(dx*dx + dy*dy)
if length > 0:
    nx, ny = -dy/length, dx/length  # perpendicular normal
    ctrl_x = mx + nx * curve_offset
    ctrl_y = my + ny * curve_offset
```
Store `ctrl_x, ctrl_y` on the edge dict (None for straight edges with offset=0).

For edge label positioning on curved edges, use the control point (offset slightly) instead of the raw midpoint.

Keep the existing circular layout math. Only change the post-processing of nodes/edges and the context passed to the template.
  </action>
  <verify>
Run: docker compose exec backend python -c "print('router syntax OK')" from /home/james/Code/SemPKM to confirm no import errors. Then curl the endpoint to verify it returns valid SVG:
curl -s -b /tmp/sempkm-cookies http://localhost:3901/admin/models/basic-pkm/ontology-diagram | grep -c "viewBox"
Should return 1 (viewBox attribute present).
  </verify>
  <done>
Router computes tight viewBox from node bounds, shortens edge endpoints by node radius, and separates bidirectional edges into distinct entries with curve offsets.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update SVG template for dynamic viewBox, path-based edges, and curved bidirectional edges</name>
  <files>backend/app/templates/admin/model_ontology_diagram.html, frontend/static/css/style.css</files>
  <action>
**Template changes (model_ontology_diagram.html):**

1. Replace the fixed `viewBox="0 0 {{ svg_w }} {{ svg_h }}"` with `viewBox="{{ view_box }}"`. Add `preserveAspectRatio="xMidYMid meet"` to ensure centered scaling.

2. Update the arrowhead marker: set `refX="0"` since edge endpoints are already pre-shortened in the router to account for the arrowhead. The marker should render right at the line endpoint.

3. Replace `<line>` elements with `<path>` elements for all non-self-referencing edges:
   - For straight edges (curve_offset == 0): `<path d="M {x1} {y1} L {x2} {y2}" ...>`
   - For curved edges (ctrl_x is not None): `<path d="M {x1} {y1} Q {ctrl_x} {ctrl_y} {x2} {y2}" ...>`
   Both get `marker-end="url(#arrowhead)"`, stroke, and stroke-width.

4. For edge labels:
   - Straight edges: position text at midpoint `((x1+x2)/2, (y1+y2)/2 - 8)` as before
   - Curved edges: position text near the control point. Use `{{ edge.ctrl_x }}` and `{{ edge.ctrl_y - 8 }}` for the label position so it sits along the curve, not on the straight midpoint.
   - Remove the `edge.inverse` text rendering entirely (inverse labels no longer exist -- each direction is its own edge now).

5. Self-referencing edges: keep existing `<path>` with cubic bezier arc. Pre-shorten start/end points from router.

**CSS changes (style.css):**

Remove `max-width: 700px` from `.ontology-diagram-svg` so the SVG fills its container width. The viewBox + preserveAspectRatio handles proper scaling. Keep `width: 100%` and `height: auto`.
  </action>
  <verify>
Restart the frontend container to pick up any nginx cache, then visually verify by loading the diagram:
curl -s -b /tmp/sempkm-cookies http://localhost:3901/admin/models/basic-pkm/ontology-diagram | head -30
Confirm: viewBox is dynamic (not "0 0 700 500"), edges use path elements, no max-width in inline styles.
Also grep the CSS: grep "max-width" frontend/static/css/style.css | grep -c "ontology" should return 0.
  </verify>
  <done>
SVG diagram auto-scales to viewport via dynamic viewBox. Edges rendered as paths (straight or quadratic bezier curves). Bidirectional edges visually separated with distinct curves. Arrowheads terminate at node circle boundary. No max-width constraint on SVG.
  </done>
</task>

</tasks>

<verification>
1. Load the mental model detail page and click the Relationships tab
2. Diagram should fill the available panel width, scaling proportionally
3. Arrowheads should point to node circles without overlapping the type name text inside
4. Bidirectional relationships (e.g., Note<->Project) should show two separate curved edges, each with its own label, arcing in opposite directions
5. Self-referencing edges should still render as arcs above the node
6. Single-direction edges should render as straight lines with arrows
</verification>

<success_criteria>
- viewBox is computed from actual node positions (not hardcoded 700x500)
- SVG scales to fill container width without max-width cap
- Edge lines terminate at node circle boundary (radius 24), arrowheads do not overlap node text
- Bidirectional edge pairs render as two separate quadratic bezier curves offset in opposite directions
- Each directional edge has its own label positioned along its curve
- Self-referencing edges still work correctly
</success_criteria>

<output>
After completion, create `.planning/quick/13-fix-ontology-diagram-visuals-zoom-to-fit/13-SUMMARY.md`
</output>
