---
id: T03
parent: S05
milestone: M031
provides:
  - Property descriptions (rdfs:comment / skos:definition) fetched in get_class_detail() SPARQL query
  - TBox detail property names show description tooltips on hover
  - Admin model graph fills viewport height via flex layout + calc(100vh - 250px)
  - Edge data in admin graph includes description, domain_label, and range_label fields
  - Edge hover popover in admin graph showing label, domain→range, and description
key_files:
  - backend/app/ontology/service.py
  - backend/app/templates/browser/ontology/tbox_detail.html
  - frontend/static/css/style.css
  - backend/app/admin/router.py
  - backend/app/templates/admin/model_ontology_diagram.html
key_decisions:
  - Reused existing graph-popover element and positioning logic for edge hovers rather than creating a separate edge popover element — keeps DOM simpler and CSS consistent
  - Mapped property comment field from _query_properties() to edge description in admin router rather than adding a new SPARQL query — the data was already available
patterns_established:
  - Edge hover handlers follow the same showTimer/hideTimer pattern (200ms/150ms) as node hovers for consistent UX
  - Property descriptions use COALESCE(rdfs:comment, skos:definition) priority — same pattern used for class descriptions elsewhere in the ontology service
observability_surfaces:
  - TBox property tooltips are pure HTML title attributes — inspect DOM for title= on .tbox-detail-key elements
  - Edge hover data visible in Cytoscape edge data — use cy.edges()[0].data() in browser console to inspect description/domain_label/range_label fields
  - Admin graph sizing is CSS-only — inspect computed styles on .ontology-cy-container for height value
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Add ontology property tooltips + admin graph sizing and edge tooltips

**Add property description tooltips to TBox detail, make admin model graph full-viewport, and add edge hover popovers to the admin ontology diagram**

## What Happened

Three ontology subsystem improvements implemented across five files:

1. **Property description tooltips (ONTO-04):** Extended the `get_class_detail()` SPARQL query in `ontology/service.py` to fetch `rdfs:comment` and `skos:definition` on property IRIs via OPTIONAL clauses, bound as `?propDescription` using COALESCE. The property dict now includes a `description` field. The TBox detail template conditionally renders `title="{{ p.description }}"` on property label cells (only when truthy, avoiding empty tooltips).

2. **Full-viewport admin graph (ONTO-05):** Changed `.ontology-diagram-panel` to `display: flex; flex-direction: column` and `.ontology-cy-container` from `min-height: 600px` to `flex: 1; min-height: 400px; height: calc(100vh - 250px)`. The 250px offset accounts for the admin nav bar, model detail header/tabs, and padding.

3. **Edge hover tooltips (ONTO-06):** Enriched edge data in `admin/router.py` with `description` (from the property's existing `comment` field), `domain_label`, and `range_label`. In the Cytoscape template, added `mouseover`/`mouseout` handlers on edges following the existing node hover pattern (200ms show delay, 150ms hide delay). The popover shows the property label, domain→range path, and description if available.

## Verification

All six task-level checks pass. All nine slice-level structural checks pass (check 9 — popover z-index — was already implemented in T02).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/ontology/service.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/admin/router.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep -q "propDescription" backend/app/ontology/service.py` | 0 | ✅ pass | <1s |
| 4 | `grep -q 'title=.*description' backend/app/templates/browser/ontology/tbox_detail.html` | 0 | ✅ pass | <1s |
| 5 | `grep -q "calc(100vh" frontend/static/css/style.css` | 0 | ✅ pass | <1s |
| 6 | `grep -q "edge.*mouseover" backend/app/templates/admin/model_ontology_diagram.html` | 0 | ✅ pass | <1s |
| 7 | `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` (slice) | 0 | ✅ pass | <1s |
| 8 | `grep -q "sparql-vocab-pill" frontend/static/css/workspace.css` (slice) | 0 | ✅ pass | <1s |
| 9 | `grep -q "sparql-graph-tab\|sparql-result-tabs" frontend/static/js/sparql-console.js` (slice) | 0 | ✅ pass | <1s |
| 10 | `grep -q "propDescription\|title=.*description" backend/app/templates/browser/ontology/tbox_detail.html` (slice) | 0 | ✅ pass | <1s |
| 11 | `grep -q "calc(100vh\|flex.*1" frontend/static/css/style.css` (slice) | 0 | ✅ pass | <1s |
| 12 | `grep -q "z-index.*[3-9][0-9][0-9]" frontend/static/css/views.css` (slice) | 0 | ✅ pass | <1s |

## Diagnostics

- **TBox property tooltips:** Inspect DOM for `title=` attributes on `.tbox-detail-key` elements in the TBox class detail panel. Absence means the property's `rdfs:comment`/`skos:definition` is empty in the triplestore.
- **Admin graph sizing:** Inspect computed CSS on `.ontology-cy-container` — should show a height based on `calc(100vh - 250px)` rather than the old `min-height: 600px`.
- **Edge hover data:** In browser console on the admin model diagram, access the Cytoscape instance and check `cy.edges()[0].data()` to see `description`, `domain_label`, `range_label` fields.
- **Edge hover popover:** Hover an edge in the admin model graph — the `#ontology-popover` element should appear with the property label and domain→range path. If missing, verify edge data includes description field (check `/admin/models/{id}/ontology-diagram` response).

## Deviations

- Used the existing `comment` field from `_query_properties()` for edge descriptions rather than adding a separate description query — the data was already fetched and available in `detail["properties"]`.

## Known Issues

None.

## Files Created/Modified

- `backend/app/ontology/service.py` — Added `?propDescription` (COALESCE of rdfs:comment/skos:definition) to `get_class_detail()` prop_sparql SELECT and WHERE clauses; added `description` to property dict
- `backend/app/templates/browser/ontology/tbox_detail.html` — Added conditional `title="{{ p.description }}"` on `.tbox-detail-key` property label cells
- `frontend/static/css/style.css` — Changed `.ontology-diagram-panel` to flex column layout; changed `.ontology-cy-container` from `min-height: 600px` to `flex: 1; min-height: 400px; height: calc(100vh - 250px)`
- `backend/app/admin/router.py` — Added `description`, `domain_label`, `range_label` fields to edge data construction
- `backend/app/templates/admin/model_ontology_diagram.html` — Passed edge description/domain_label/range_label into Cytoscape edge data; added edge mouseover/mouseout handlers with popover display following the node hover pattern
