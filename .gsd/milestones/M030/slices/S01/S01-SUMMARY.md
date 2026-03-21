# S01: Validation Pipeline Fix & Performance Measurement — Summary

## Outcome

The SHACL-AF validation pipeline is fully operational end-to-end. All broken links have been fixed:

1. **model_shapes_loader** fetches and merges rules graphs alongside shapes graphs (1143 shapes + 35 rules triples from basic-pkm)
2. **ValidationService.validate()** passes `advanced=True` to pyshacl, enabling SPARQLConstraint/SPARQLRule processing
3. **_store_report** fixed to use Graph Store protocol instead of SPARQL INSERT DATA (blank node IRI issues)
4. **_rdf_term_to_sparql** fixed to handle BNodes explicitly
5. **Commands API** now auto-types YYYY-MM-DD strings as xsd:date literals

## Performance Baseline

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| pyshacl advanced=True on 1178 triples (unit test) | **0.037s** | <10s | ✅ Well within budget |
| pyshacl advanced=True on 271 data + 1178 shapes triples (Docker) | **0.266s** | <5s | ✅ Acceptable |
| Combined shapes+rules triple count (basic-pkm) | 1178 | — | Baseline |
| SPARQLConstraint rules fired | 2 warnings (overdue tasks) | ≥1 | ✅ Confirmed |

**Performance risk retired.** S02's addition of ~9 more rules will not cause performance issues.

## Docker Integration Evidence

- **Lint dashboard** shows 2 overdue-task warnings (0 violations) — both seed and API-created tasks
- **Docker logs** show: `model_shapes_loader: Loaded 1143 shapes + 35 rules triples from 1 model(s)`
- **API lint status**: `{conforms: true, warning_count: 2}`
- **model_shapes_loader** confirmed via direct execution and Docker log output

## Observability

- `docker compose logs api | grep "rules triples"` — shows whether rules are loading
- `/api/lint/status` — JSON with latest run results
- `/browser/lint-dashboard` — visual dashboard with filterable results
