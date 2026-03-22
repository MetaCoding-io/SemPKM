---
id: T03
parent: S01
milestone: M033
provides:
  - Mirrored property queries in object detail page (GRAPH <urn:sempkm:mirrored>)
  - Mirrored edge UNION blocks in object relations panel
  - Mirrored badge rendering in object_read.html and properties.html templates
  - Mirrored edge style (dotted teal) in graph.js Cytoscape visualization
  - Mirrored edge detection in views/service.py graph data pipeline
  - urn:sempkm:mirror-prov: added to vocab prefix exclusion lists (backend + frontend)
key_files:
  - backend/app/browser/objects.py
  - backend/app/templates/browser/object_read.html
  - backend/app/templates/browser/properties.html
  - frontend/static/css/workspace.css
  - frontend/static/js/graph.js
  - backend/app/views/service.py
  - backend/app/sparql/router.py
  - frontend/static/js/sparql-console.js
key_decisions:
  - Mirrored edge precedence — user > inferred > mirrored; an edge in both mirrored and inferred graphs shows as inferred, not mirrored
  - Dark theme mirrored badge uses lighter teal (#5eead4) for readability against dark backgrounds
patterns_established:
  - Parallel source tracking pattern — mirrored follows exact same code structure as inferred for queries, deduplication, label resolution, and template rendering
observability_surfaces:
  - logger.warning on mirrored property/edge query failures (same pattern as inferred)
  - Edge provenance endpoint returns source:"mirrored" with "Mirrored from external SPARQL endpoint" description
  - Visual signals — teal .mirrored-badge pills and dotted teal .mirrored-edge lines
duration: 10min
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Mirrored triples in object views and graph edges

**Extended object detail, relations panel, and graph visualization to display mirrored triples with teal provenance badges and dotted edge lines**

## What Happened

Added mirrored property queries in `objects.py` — a new SPARQL block queries `GRAPH <urn:sempkm:mirrored>` for properties, deduplicates against both user-created and inferred values, resolves labels, and merges into `read_values` with `"source": "mirrored"`.

Extended the relation edge SPARQL queries (outbound and inbound) with a third UNION block for `GRAPH <urn:sempkm:mirrored>`, with `BIND("mirrored" AS ?source)`. The existing deduplication (user > inferred > mirrored) handles precedence correctly since UNION ordering matches priority.

Added mirrored source handling in the `get_edge_provenance` endpoint — returns "Mirrored from external SPARQL endpoint" description for `source == "mirrored"`.

Updated both `object_read.html` and `properties.html` templates to render `.mirrored-badge` spans with teal styling alongside existing inferred badges. The non-form-properties section now shows both inferred and mirrored items (using `rejectattr("source", "equalto", "user")` instead of `selectattr("source", "equalto", "inferred")`).

Added `.mirrored-badge` CSS in `workspace.css` — teal color scheme (`#14b8a6` light / `#5eead4` dark) with the same layout properties as `.inferred-badge`, plus dark theme override.

Added `.mirrored-edge` Cytoscape style in `graph.js` — dotted teal line (`line-dash-pattern: [2, 4]`) that visually differentiates from the dashed grey inferred edges. Updated both initial render and expand-neighbors code paths to check `edge.mirrored` and apply the class.

Extended `_parse_graph_results` in `views/service.py` to accept `mirrored_edge_set` parameter. Updated `execute_graph_query` and `expand_neighbors` to query `GRAPH <urn:sempkm:mirrored>` for mirrored edge identification, and pass the set through. The expand query also includes `FROM <urn:sempkm:mirrored>` to discover mirrored nodes.

Added `urn:sempkm:mirror-prov:` to `_VOCAB_PREFIXES` in router.py and both `urn:sempkm:mirrored:` and `urn:sempkm:mirror-prov:` to `KNOWN_VOCAB_PREFIXES` in sparql-console.js.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py -v` — 78/78 passed, no regressions
- `rg "urn:sempkm:mirrored" backend/app/browser/objects.py` — 3 matches (property query, outbound edges, inbound edges) ✅
- `rg "mirrored-badge" frontend/static/css/workspace.css` — 3 matches (base, relation-item, dark theme) ✅
- `rg "mirrored-edge" frontend/static/js/graph.js` — 3 matches (style definition, initial render, expand) ✅
- `rg "mirror-prov" backend/app/sparql/router.py` — 1 match ✅
- `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` — constant exists ✅
- Python syntax check on all modified Python files — OK
- Jinja2 template parse check — OK

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py -v` | 0 | ✅ pass | 0.57s |
| 2 | `rg "urn:sempkm:mirrored" backend/app/browser/objects.py` | 0 | ✅ pass | <0.1s |
| 3 | `rg "mirrored-badge" frontend/static/css/workspace.css` | 0 | ✅ pass | <0.1s |
| 4 | `rg "mirrored-edge" frontend/static/js/graph.js` | 0 | ✅ pass | <0.1s |
| 5 | `rg "mirror-prov" backend/app/sparql/router.py` | 0 | ✅ pass | <0.1s |
| 6 | `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- Mirrored property query failures are logged at `logger.warning` level with the object IRI and full traceback.
- Edge provenance endpoint (`GET /browser/edge-provenance?source=mirrored`) returns structured JSON identifying mirrored edges.
- Visual: teal `.mirrored-badge` pills appear next to mirrored property values in the object read view and relations panel. Dotted teal lines appear in graph visualizations for mirrored edges.
- The supplementary properties query in `_parse_graph_results` now includes `FROM <urn:sempkm:mirrored>` so mirrored node properties appear in graph tooltips.

## Deviations

- Extended `views/service.py` (`_parse_graph_results`, `execute_graph_query`, `expand_neighbors`) — not explicitly in the task plan but necessary to propagate mirrored edge styling through the graph data pipeline.
- Added mirrored badge to `properties.html` (right-pane relations panel) — not in the plan but follows the same template pattern and is needed for consistency.
- Changed the non-form-properties section in `object_read.html` from `selectattr("source", "equalto", "inferred")` to `rejectattr("source", "equalto", "user")` so both inferred and mirrored items are shown without repeating the block.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/objects.py` — added mirrored property query, mirrored edge UNION blocks, mirrored edge provenance handler
- `backend/app/templates/browser/object_read.html` — added mirrored-badge rendering alongside inferred badges, updated non-form-property section for both sources
- `backend/app/templates/browser/properties.html` — added mirrored-badge to outbound and inbound relation items
- `frontend/static/css/workspace.css` — added .mirrored-badge base styles, flex container override, dark theme override
- `frontend/static/js/graph.js` — added .mirrored-edge Cytoscape style, mirrored class application in initial render and expand
- `backend/app/views/service.py` — extended _parse_graph_results with mirrored_edge_set, added mirrored edge detection in execute_graph_query and expand_neighbors, added FROM <urn:sempkm:mirrored> to supplementary query
- `backend/app/sparql/router.py` — added urn:sempkm:mirror-prov: to _VOCAB_PREFIXES
- `frontend/static/js/sparql-console.js` — added urn:sempkm:mirrored: and urn:sempkm:mirror-prov: to KNOWN_VOCAB_PREFIXES
- `.gsd/milestones/M033/slices/S01/tasks/T03-PLAN.md` — added Observability Impact section
