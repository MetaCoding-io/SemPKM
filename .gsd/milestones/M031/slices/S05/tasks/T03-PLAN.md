---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T03: Add ontology property tooltips + admin graph sizing and edge tooltips

**Slice:** S05 — SPARQL + Ontology + Graph + Full-Height Polish
**Milestone:** M031

## Description

Three related ontology improvements: (1) TBox class detail property names lack description tooltips (ONTO-04), (2) the admin model graph is fixed at `min-height: 600px` instead of filling the viewport (ONTO-05), and (3) admin graph edges have no hover tooltips (ONTO-06). These are grouped because they all modify the ontology subsystem.

## Steps

1. **Add property description to `get_class_detail()` SPARQL** in `backend/app/ontology/service.py` (line ~871). In the `prop_sparql` query, add OPTIONAL clauses for `rdfs:comment` and `skos:definition` on the property IRI, then BIND as `?propDescription`:
   ```sparql
   OPTIONAL { ?prop rdfs:comment ?propComment .
              FILTER(LANG(?propComment) = "" || LANG(?propComment) = "en") }
   OPTIONAL { ?prop skos:definition ?propDef .
              FILTER(LANG(?propDef) = "" || LANG(?propDef) = "en") }
   BIND(COALESCE(?propComment, ?propDef) AS ?propDescription)
   ```
   Add `?propDescription` to the SELECT clause. In the property dict construction (~line 903), include `"description": pb.get("propDescription", {}).get("value", "")`.

2. **Add tooltip to TBox detail template** in `backend/app/templates/browser/ontology/tbox_detail.html`. In the properties table (the `{% for p in cls.properties %}` loop), add `title="{{ p.description }}"` to the `<td class="tbox-detail-key">` element that displays the property label. Only add the title attribute when `p.description` is truthy to avoid empty tooltips.

3. **Make admin model graph full-viewport** in `frontend/static/css/style.css` (line ~2046-2060). Change `.ontology-diagram-panel` to use `display: flex; flex-direction: column;`. Change `.ontology-cy-container` from `min-height: 600px` to `flex: 1; min-height: 400px; height: calc(100vh - 250px)`. The 250px offset accounts for the admin nav bar (~50px), model detail header/tabs (~100px), and padding (~100px).

4. **Enrich edge data with property description** in `backend/app/admin/router.py` (line ~335). The existing edge construction only includes `id, source, target, label`. Add a `description` field from the property detail. The `detail["properties"]` list contains `label`, `domain`, `range`, `prop_type` — check if a `description` key is available. If not, leave description as empty string. Also add `domain_label` and `range_label` for richer edge tooltips.

5. **Add edge hover handler to admin graph** in `backend/app/templates/admin/model_ontology_diagram.html`. After the existing node hover handler (mouseover/mouseout on nodes), add a similar handler for edges. On edge hover, show the `graph-popover` (reuse the same popover element or the `edgePopover` element) displaying the edge label, domain→range description, and property description if available. Follow the existing node hover pattern (showTimer/hideTimer with 200ms/150ms delays).

## Must-Haves

- [ ] Property description (from `rdfs:comment` or `skos:definition`) included in `get_class_detail()` response
- [ ] TBox detail template shows tooltip on hover for properties that have descriptions
- [ ] Admin model graph `.ontology-cy-container` fills available viewport height
- [ ] Edge data in admin graph includes `description` field
- [ ] Edge hover in admin graph shows a popover with label and description

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/ontology/service.py').read())"` — syntax OK
- `python3 -c "import ast; ast.parse(open('backend/app/admin/router.py').read())"` — syntax OK
- `grep -q "propDescription" backend/app/ontology/service.py` — description fetched in SPARQL
- `grep -q 'title=.*description' backend/app/templates/browser/ontology/tbox_detail.html` — tooltip present
- `grep -q "calc(100vh" frontend/static/css/style.css` — viewport height on ontology container
- `grep -q "edge.*mouseover\|mouseover.*edge" backend/app/templates/admin/model_ontology_diagram.html` — edge hover handler

## Inputs

- `backend/app/ontology/service.py` — `get_class_detail()` method with `prop_sparql` query (line ~871)
- `backend/app/templates/browser/ontology/tbox_detail.html` — properties display table
- `frontend/static/css/style.css` — `.ontology-cy-container` and `.ontology-diagram-panel` styles (line ~2046)
- `backend/app/admin/router.py` — `admin_model_ontology_diagram()` edge construction (line ~335)
- `backend/app/templates/admin/model_ontology_diagram.html` — Cytoscape init and node hover handler

## Expected Output

- `backend/app/ontology/service.py` — `get_class_detail()` returns property descriptions
- `backend/app/templates/browser/ontology/tbox_detail.html` — tooltip on property names
- `frontend/static/css/style.css` — `.ontology-cy-container` viewport-filling layout
- `backend/app/admin/router.py` — edge data includes description
- `backend/app/templates/admin/model_ontology_diagram.html` — edge hover handler added
