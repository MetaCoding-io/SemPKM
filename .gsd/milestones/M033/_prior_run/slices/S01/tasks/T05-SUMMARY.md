---
id: T05
parent: S01
milestone: M033
provides:
  - Mirrored triple indicators on object pages with source endpoint provenance
  - ".mirrored-badge" CSS component with teal color scheme and globe icon
  - ".mirrored-edge" dotted teal style for graph view
  - Edge provenance popover support for mirrored edges
  - Mirrored graph UNION queries in relations panel (outbound/inbound)
  - 8 additional test cases (38 total in test_mirror_service.py)
key_files:
  - backend/app/browser/objects.py
  - backend/app/views/service.py
  - backend/app/templates/browser/object_read.html
  - backend/app/templates/browser/properties.html
  - frontend/static/js/workspace.js
  - frontend/static/js/graph.js
  - frontend/static/css/workspace.css
  - backend/tests/test_mirror_service.py
key_decisions:
  - Mirrored badge rendering implemented in Jinja2 templates (object_read.html, properties.html) not workspace.js — properties are server-rendered, not JS-rendered
  - Provenance resolution uses batch-level dcterms:source rather than per-triple provenance — mirrors the PROV-O storage model from T03
  - Non-form properties section updated to show both inferred and mirrored items (was inferred-only)
patterns_established:
  - Mirrored source tagging pattern in read_values — {value, source:"mirrored", source_endpoint:"<url>"} — parallel to inferred {value, source:"inferred"}
  - PROV predicate filtering in SPARQL UNION queries — FILTER(!STRSTARTS(STR(?predicate), "http://www.w3.org/ns/prov#")) prevents provenance metadata from appearing as object properties/edges
observability_surfaces:
  - Mirrored properties visible on object read view with teal badge and endpoint tooltip
  - Graph view edges from mirrored graph rendered as dotted teal lines
  - Edge provenance popover shows "Mirrored from <endpoint>" with timestamp for mirrored edges
  - Backend warnings on mirrored/provenance query failures include object IRI
duration: 18m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T05: Mirrored triple indicators on object pages and comprehensive test suite

**Added mirrored triple visual indicators (teal badges, dotted graph edges, provenance popovers) on object pages and relations panels, with 8 new test cases covering typed literals, language tags, provenance timestamps, error dict shape, and vocab prefix integration.**

## What Happened

1. Extended `object_read_page()` in `objects.py` with a parallel query against `GRAPH <urn:sempkm:mirrored>` after the existing inferred query. Mirrored values are tagged with `source: "mirrored"` and `source_endpoint` from provenance. Provenance resolution queries `prov:Entity` batches for `dcterms:source`. Deduplication skips mirrored triples that already exist in user or inferred data, and filters out PROV-O provenance predicates and internal sempkm metadata (queryHash, tripleCount).

2. Updated `object_read.html` template to render `.mirrored-badge` with globe Lucide icon and endpoint tooltip alongside existing inferred badges. Updated all three badge insertion points: reference pill badges, plain-text value badges, and non-form property section. Changed the non-form property section from inferred-only to showing both inferred and mirrored items using `selectattr("source", "in", ["inferred", "mirrored"])`.

3. Updated `properties.html` (relations panel) with mirrored badges on both outbound and inbound relation items.

4. Updated `workspace.js` edge detail popover to handle `source === 'mirrored'` with "Mirrored from <endpoint>" description text, and exclude mirrored edges from the delete button (like inferred edges).

5. Added mirrored edge provenance endpoint support in `get_edge_provenance()` — queries PROV-O batches for source endpoint and timestamp, returns structured JSON with `source: "mirrored"` and `source_endpoint`.

6. Added `urn:sempkm:mirrored` UNION blocks to the outbound and inbound edge SPARQL queries in `get_relations()`, with PROV predicate filtering to prevent provenance triples from appearing as user-visible edges.

7. Added `.mirrored-badge` CSS styles in workspace.css — teal/blue color scheme (`--color-info-bg`, `--color-info-text`, `--color-info-border`), inline-flex with gap for icon + text, 0.65rem pill. Also added `.prop-mirrored`, `.mirrored-stale`, and relation-item positioning rules.

8. Added `.mirrored-edge` Cytoscape.js style in graph.js — dotted line pattern `[2, 3]`, teal color (`#4db6ac` dark / `#00897b` light), 0.8 opacity. Updated both initial render and expand-neighbors edge building code to check `edge.mirrored` flag.

9. Extended `_parse_graph_results()` in `views/service.py` with `mirrored_edge_set` parameter. Updated `execute_graph_query()` and `expand_neighbors()` to query `GRAPH <urn:sempkm:mirrored>` for mirrored edge identification, with PROV predicate filtering. Added `FROM <urn:sempkm:mirrored>` to expand_neighbors CONSTRUCT query.

10. Added 8 new test cases across 2 new test classes: `TestVocabPrefixIntegration` (3 tests: mirror prefix in _VOCAB_PREFIXES, MIRRORED_GRAPH_IRI constant, scope_to_current_graph default) and `TestMirrorResultsEdgeCases` (5 tests: typed literal preservation, language-tagged literals, URI-URI edges, prov:generatedAtTime presence, error dict shape validation). Total: 38 tests in test_mirror_service.py.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py tests/test_sparql_client.py tests/test_federation_allowlist.py -v` — all 95 tests pass
- `grep -q "mirrored-badge" frontend/static/css/workspace.css` — CSS exists ✅
- `grep -q "mirrored-edge" frontend/static/js/graph.js` — graph style exists ✅
- `grep -q "source.*mirrored" backend/app/browser/objects.py` — source tagging exists ✅
- `node -c frontend/static/js/graph.js` — JS syntax valid ✅
- `node -c frontend/static/js/workspace.js` — JS syntax valid ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py tests/test_sparql_client.py -v` | 0 | ✅ pass | 0.69s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py tests/test_sparql_client.py tests/test_federation_allowlist.py -v` | 0 | ✅ pass | 0.82s |
| 3 | `grep -q "mirrored-badge" frontend/static/css/workspace.css` | 0 | ✅ pass | <1s |
| 4 | `grep -q "mirrored-edge" frontend/static/js/graph.js` | 0 | ✅ pass | <1s |
| 5 | `grep -q "source.*mirrored" backend/app/browser/objects.py` | 0 | ✅ pass | <1s |
| 6 | `node -c frontend/static/js/graph.js` | 0 | ✅ pass | <1s |
| 7 | `node -c frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect mirrored properties:** Open any object that has mirrored data — properties from `urn:sempkm:mirrored` display with a teal "mirrored" badge. Hover badge to see source endpoint in tooltip.
- **Graph view:** Mirrored edges render as dotted teal lines, distinguishable from dashed gray inferred edges and solid user-created edges.
- **Edge provenance:** Click a mirrored edge in the relations panel — the detail popover shows "Mirrored from <endpoint_url>" with timestamp.
- **Backend logs:** Failures to query mirrored graph or provenance produce WARNING-level log entries with the object IRI.
- **Diagnostic SPARQL:** `SELECT ?p ?o WHERE { GRAPH <urn:sempkm:mirrored> { <object_iri> ?p ?o } }` shows mirrored properties for any object.

## Deviations

- Mirrored badge rendering implemented in Jinja2 templates (`object_read.html`, `properties.html`) instead of workspace.js as the plan suggested. The plan assumed JS-based rendering, but the actual codebase renders object properties server-side via Jinja2 templates. workspace.js was updated only for the edge detail popover (source text and delete button exclusion).
- Updated `object_embed.html` was not needed — the existing inline badge pattern there is minimal and the mirrored graph is unlikely to affect embedded views.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/objects.py` — added mirrored graph query in object_read_page(), mirrored UNION blocks in get_relations() edge queries, mirrored edge provenance in get_edge_provenance()
- `backend/app/views/service.py` — added mirrored_edge_set to _parse_graph_results(), mirrored edge identification queries in execute_graph_query() and expand_neighbors(), FROM <urn:sempkm:mirrored> in expand CONSTRUCT
- `backend/app/templates/browser/object_read.html` — mirrored badge rendering in reference pills, plain text values, and non-form properties section
- `backend/app/templates/browser/properties.html` — mirrored badge on outbound and inbound relation items
- `frontend/static/js/workspace.js` — mirrored source handling in edge detail popover, delete button exclusion for mirrored edges
- `frontend/static/js/graph.js` — .mirrored-edge Cytoscape.js style definition, mirrored flag in edge data building (initial render + expand)
- `frontend/static/css/workspace.css` — .mirrored-badge, .mirrored-badge svg, .relation-item .mirrored-badge, .prop-mirrored, .mirrored-stale styles
- `backend/tests/test_mirror_service.py` — added TestVocabPrefixIntegration (3 tests) and TestMirrorResultsEdgeCases (5 tests), total 38 tests
- `.gsd/milestones/M033/slices/S01/tasks/T05-PLAN.md` — added Observability Impact section per pre-flight requirement
