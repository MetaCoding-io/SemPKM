---
id: T01
parent: S01
milestone: M056
key_files:
  - backend/app/ontology/service.py
  - backend/app/ontology/router.py
  - backend/tests/test_ontology_graph.py
key_decisions:
  - Edge direction parent→child matches dagre TB convention (parents at top)
  - Error handling returns empty {nodes:[], edges:[]} instead of 500
  - Parent nodes auto-created when only referenced by child bindings
duration: 
verification_result: passed
completed_at: 2026-04-06T07:22:47.570Z
blocker_discovered: false
---

# T01: Added GET /browser/ontology/tbox/graph-data JSON endpoint returning all TBox classes and subClassOf edges as Cytoscape-compatible graph data

**Added GET /browser/ontology/tbox/graph-data JSON endpoint returning all TBox classes and subClassOf edges as Cytoscape-compatible graph data**

## What Happened

Added get_tbox_graph_data() to OntologyService — a single SPARQL query across all ontology graphs (gist + installed models + user-types) that retrieves all owl:Class instances with their labels and optional rdfs:subClassOf parents. The method deduplicates nodes, auto-creates parent nodes when only referenced by children, and assigns source labels via _property_source(). owl:Thing and blank nodes are excluded. Added the GET /browser/ontology/tbox/graph-data route returning JSONResponse with {nodes, edges}. Error handling returns empty arrays on failure. Wrote 16 unit tests covering node structure, edge direction, source labels, deduplication, empty results, SPARQL failure, and query structure.

## Verification

All 16 tests pass: cd backend && .venv/bin/python -m pytest tests/test_ontology_graph.py -v — 16 passed in 0.50s. LSP diagnostics clean on both modified files.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_ontology_graph.py -v` | 0 | ✅ pass | 500ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/ontology/service.py`
- `backend/app/ontology/router.py`
- `backend/tests/test_ontology_graph.py`
