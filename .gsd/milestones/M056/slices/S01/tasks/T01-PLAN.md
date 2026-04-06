---
estimated_steps: 37
estimated_files: 3
skills_used: []
---

# T01: Build TBox graph-data JSON API endpoint

Create a new JSON endpoint at `/browser/ontology/tbox/graph-data` that queries all TBox classes across gist + installed model ontology graphs + user-types and returns Cytoscape-compatible graph data.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| RDF4J triplestore | Return empty {nodes:[], edges:[]} with logged error | Same — async query timeout logged | Should not occur — SPARQL result format is fixed |

## Steps

1. Read `backend/app/ontology/service.py` — understand `get_ontology_graph_iris()`, `get_root_classes()`, `_build_from_clauses()` patterns
2. Add a new method `get_tbox_graph_data()` to `OntologyService` that:
   - Gets all ontology graph IRIs via `get_ontology_graph_iris()`
   - Queries ALL `owl:Class` instances (not just roots) with their labels and `rdfs:subClassOf` parents
   - Returns nodes as `[{id: iri, label: str, source: 'gist'|'model-id'|'user'}]`
   - Returns edges as `[{source: parent_iri, target: child_iri, label: 'subClassOf'}]` (direction: parent→child for dagre TB to put parents on top)
   - Determines `source` using the existing `_property_source()` helper
   - Filters out owl:Thing and blank nodes
3. Add a new route `GET /browser/ontology/tbox/graph-data` to `backend/app/ontology/router.py` that:
   - Calls `ontology_service.get_tbox_graph_data()`
   - Returns `JSONResponse` with `{nodes: [...], edges: [...]}`
   - Catches exceptions and returns empty arrays with error logged
4. Write unit tests in `backend/tests/test_ontology_graph.py`:
   - Test that `get_tbox_graph_data()` returns correct node structure
   - Test that edges connect correct parent→child pairs
   - Test that source labels are correctly assigned
   - Mock the triplestore client to return known SPARQL results

## Must-Haves

- [ ] `get_tbox_graph_data()` queries ALL classes across all ontology graphs, not just roots
- [ ] Nodes include `id` (IRI), `label`, and `source` fields
- [ ] Edges represent `rdfs:subClassOf` with direction parent→child (so dagre TB puts parents at top)
- [ ] owl:Thing nodes and blank nodes are excluded
- [ ] Endpoint returns JSON, not HTML
- [ ] Error handling: empty arrays returned on SPARQL failure, not 500

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_ontology_graph.py -v` passes
- The endpoint is reachable and returns valid JSON with nodes and edges arrays

## Observability Impact

- Signals added: `logger.info("TBox graph-data: %d nodes, %d edges from %d graphs", ...)` on successful query
- How a future agent inspects: `curl localhost:4000/browser/ontology/tbox/graph-data` (with auth cookie)
- Failure state exposed: SPARQL errors logged with `exc_info=True`

## Inputs

- ``backend/app/ontology/service.py` — existing OntologyService with SPARQL query patterns and _property_source() helper`
- ``backend/app/ontology/router.py` — existing ontology router to add new endpoint to`

## Expected Output

- ``backend/app/ontology/service.py` — new get_tbox_graph_data() method added`
- ``backend/app/ontology/router.py` — new GET /browser/ontology/tbox/graph-data endpoint added`
- ``backend/tests/test_ontology_graph.py` — unit tests for graph data endpoint`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_ontology_graph.py -v
