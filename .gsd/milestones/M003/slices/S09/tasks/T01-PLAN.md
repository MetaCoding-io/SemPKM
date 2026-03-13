---
estimated_steps: 6
estimated_files: 2
---

# T01: Extend ModelService with SPARQL analytics queries

**Slice:** S09 — Admin Model Detail Stats & Charts
**Milestone:** M003

## Description

Add four new SPARQL aggregate queries to `ModelService.get_type_analytics()` so each type returns avg connections, last modified date, growth trend (weekly object.create counts for 8 weeks), and link distribution histogram. Create unit tests that verify query result parsing with mock triplestore responses.

## Steps

1. Read `backend/app/services/models.py` `get_type_analytics()` method (starts ~line 640) to understand the existing query pattern and return structure.
2. Add **avg connections** query per type: count all non-`rdf:type` triples in `urn:sempkm:current` where `?s a <type>` and either `?s ?p ?o` or `?o2 ?p2 ?s`, aggregate as `SUM / instance_count`. Store as `avg_connections` (float rounded to 1 decimal). Default to 0.0 on error or zero instances.
3. Add **last modified** query per type: `SELECT (MAX(?mod) AS ?lastMod) WHERE { GRAPH <urn:sempkm:current> { ?s a <type> . ?s <dcterms:modified> ?mod } }`. If empty, fall back to a second query: `SELECT (MAX(?ts) AS ?lastMod) WHERE { GRAPH ?ev { ?ev sempkm:operationType ?op ; sempkm:affectedIRI ?aff ; sempkm:timestamp ?ts . FILTER(CONTAINS(STR(?op), "object")) } FILTER(STRSTARTS(STR(?ev), "urn:sempkm:event:")) GRAPH <urn:sempkm:current> { ?aff a <type> } }`. Store as ISO date string or `None`. Default to `None` on error.
4. Add **growth trend** query: count `object.create` events per ISO week for the last 8 weeks whose `affectedIRI` is a current instance of the type. Use `xsd:dateTime` filter for the 8-week window. Return list of `{"week": "YYYY-Www", "count": int}` dicts, padded with zeros for weeks with no activity. Default to empty list on error.
5. Add **link distribution** query per type: for each instance, count incoming + outgoing non-rdf:type links, then bucket into (0, 1-2, 3-5, 6-10, 11+). Return list of `{"bucket": str, "count": int}` dicts. Default to empty list on error or zero instances.
6. Create `backend/tests/test_model_analytics.py` with mock-based unit tests: (a) test avg connections parsing with sample bindings, (b) test last modified with dcterms:modified present and absent, (c) test growth trend with partial weeks and empty results, (d) test link distribution bucketing logic, (e) test graceful defaults on query exception.

## Must-Haves

- [ ] `get_type_analytics()` returns `avg_connections` (float) per type
- [ ] `get_type_analytics()` returns `last_modified` (ISO string or None) per type
- [ ] `get_type_analytics()` returns `growth_trend` (list of week/count dicts) per type
- [ ] `get_type_analytics()` returns `link_distribution` (list of bucket/count dicts) per type
- [ ] All four stats default gracefully on SPARQL error (no exceptions propagate)
- [ ] Unit tests verify parsing logic for all four stats
- [ ] Existing `count` and `top_nodes` behavior unchanged

## Verification

- `cd backend && python -m pytest tests/test_model_analytics.py -v` — all tests pass
- `cd backend && python -m pytest tests/ -v` — no regressions in existing tests

## Observability Impact

- Signals added/changed: Each new SPARQL query section has a try/except that logs failures at WARNING level with the type IRI, mirroring the existing `pass` pattern for top_nodes queries. Future improvement would use structured logging but matches current codebase convention.
- How a future agent inspects this: Read `get_type_analytics()` return dict — each type IRI maps to a dict with 6 keys (count, top_nodes, avg_connections, last_modified, growth_trend, link_distribution). Mock tests document the expected shapes.
- Failure state exposed: Query failures produce default values (0.0, None, [], []) — the template renders fallback text. WARNING logs indicate which query failed.

## Inputs

- `backend/app/services/models.py` — existing `get_type_analytics()` to extend
- `backend/app/events/models.py` — event RDF predicates (EVENT_TIMESTAMP, EVENT_OPERATION, EVENT_AFFECTED)
- `backend/app/events/query.py` — reference for cross-graph event SPARQL patterns (GRAPH ?event, STRSTARTS filter)
- S09-RESEARCH.md — query designs, bucketing scheme, constraints

## Expected Output

- `backend/app/services/models.py` — `get_type_analytics()` extended with 4 new query sections returning enriched dicts
- `backend/tests/test_model_analytics.py` — new test file with 5+ test cases covering all analytics parsing paths
