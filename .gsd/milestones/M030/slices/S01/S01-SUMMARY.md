# S01: Validation Pipeline Fix & Performance Measurement — Summary

## Outcome

The SHACL-AF validation pipeline is fully operational. Both broken links identified in M030 planning have been fixed:

1. **model_shapes_loader** now fetches and merges rules graphs alongside shapes graphs (1143 shapes + 35 rules triples from basic-pkm)
2. **ValidationService.validate()** passes `advanced=True` to pyshacl, enabling SPARQLConstraint and SPARQLRule processing
3. Two pre-existing bugs in `_store_report` were fixed during Docker integration verification to enable end-to-end flow

## Performance Baseline

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| pyshacl advanced=True on 1178 triples (unit test) | **0.037s** | <10s | ✅ Well within budget |
| pyshacl advanced=True on 271 data + 1178 shapes triples (Docker stack) | **0.266s** | <5s | ✅ Acceptable |
| Combined shapes+rules triple count (basic-pkm) | 1178 | — | Baseline |
| SPARQLConstraint rules fired | 1 warning (overdue task) | ≥1 | ✅ Confirmed |

**Performance risk retired:** Even with `advanced=True` and all SHACL-AF rules loaded, validation completes in under 0.3s for a real-world data graph. S02's addition of ~9 more rules will not cause performance issues — the overhead is dominated by data graph size, not rule count.

## Docker Integration Evidence

- **Lint dashboard** shows 1 violation + 1 warning after creating objects in the test stack
- **Overdue task warning**: "Task is overdue: due date has passed but task is not done or cancelled." appears for the seed task `urn:sempkm:model:basic-pkm:seed-task-fix-validation`
- **Datatype violation**: Detected for a test task created with plain string dueDate (not xsd:date typed)
- **model_shapes_loader** confirmed via `docker exec` to load `1143 shapes + 35 rules triples from 1 model(s)`

## Bugs Fixed During Integration

Two pre-existing bugs in `_store_report` were exposed and fixed:

1. **`_rdf_term_to_sparql` didn't handle BNodes** — blank node terms were wrapped in `<...>` angle brackets (IRI syntax), producing invalid IRIs like `<nf943a8d5e6d8...>`. Fixed by adding explicit `BNode` handling with `_:` prefix.

2. **Results graph INSERT used SPARQL INSERT DATA with N-Triples** — the full pyshacl results graph (including SPARQLConstraint source with embedded SPARQL queries) was serialized to N-Triples and embedded in a SPARQL INSERT DATA block. The blank node identifiers and complex string literals caused RDF4J SPARQL parser errors. Fixed by using `insert_graph()` with RDF4J's Graph Store protocol (direct Turtle POST to named graph).

These bugs were dormant because SHACL-AF rules never fired before T01's fix — no results_graph ever contained SPARQLConstraint metadata with blank nodes.

## Observability

- `docker compose logs api | grep "shapes.*rules triples"` — shows whether rules are loading (not always visible due to log buffering; confirmed working via docker exec)
- `/api/lint/status` — shows current validation run results (conforms, violation/warning/info counts)
- `/browser/lint-dashboard` — visual dashboard with filterable results
- Failure signal: if lint panel shows 0 warnings on objects with overdue tasks, check model_shapes_loader output
