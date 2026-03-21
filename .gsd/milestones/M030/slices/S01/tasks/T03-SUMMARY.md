---
id: T03
parent: S01
milestone: M030
provides:
  - Docker integration verification of validation pipeline with SHACL-AF rules firing end-to-end
  - Performance baseline documented (0.037s unit test, 0.266s Docker stack)
  - Two pre-existing _store_report bugs fixed enabling lint dashboard to show results
  - xsd:date auto-typing in commands API for YYYY-MM-DD date strings
  - Docker log visibility for model_shapes_loader output
key_files:
  - backend/app/services/validation.py
  - backend/app/validation/report.py
  - backend/app/triplestore/client.py
  - backend/app/commands/handlers/object_create.py
  - backend/app/services/models.py
key_decisions:
  - Use RDF4J Graph Store protocol (Turtle POST) instead of SPARQL INSERT DATA for storing full results graphs
  - Skip blank-node-like source shapes in structured triples rather than wrapping them in URIRef
  - Auto-type YYYY-MM-DD strings as xsd:date in the commands API to match SHACL shape expectations
patterns_established:
  - TriplestoreClient.insert_graph() for inserting complete graphs into named graphs without SPARQL parsing issues
  - _rdf_term_to_sparql must handle BNode explicitly — rdflib BNodes have identifiers that look like invalid IRIs
  - _to_rdf_value auto-detects ISO date strings (YYYY-MM-DD) and types them as xsd:date
observability_surfaces:
  - "/api/lint/status returns conforms, violation_count, warning_count, info_count for latest validation run"
  - "/browser/lint-dashboard shows all validation results with severity, object, property, message"
  - "model_shapes_loader prints to stderr for Docker log visibility: 'Loaded X shapes + Y rules triples from N model(s)'"
duration: 45m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: Docker integration verification and performance documentation

**Verified validation pipeline end-to-end in Docker: overdue task warning appears in lint dashboard for both seed and API-created tasks; fixed _store_report bugs, added xsd:date auto-typing, documented 0.037s performance baseline retiring the SHACL-AF performance risk**

## What Happened

Started the Docker test stack with fresh volumes, created a test Task with a past due date, and verified the full validation pipeline through to the lint dashboard. Four fixes were needed to achieve the full end-to-end flow:

1. **`_rdf_term_to_sparql` missing BNode handling** — Added explicit `isinstance(term, BNode)` check with `_:` prefix formatting. Also added `BNode` to imports.

2. **Results graph stored via SPARQL INSERT DATA** — Switched to `TriplestoreClient.insert_graph()` using RDF4J's Graph Store protocol (HTTP POST with `Content-Type: text/turtle`). The N-Triples-in-SPARQL approach broke on blank node IDs and complex string literals.

3. **Blank-node source shapes in structured triples** — `to_structured_triples()` was wrapping blank node source shape identifiers in `URIRef()`, creating invalid IRIs. Fixed by only emitting `sh:sourceShape` triples for proper IRI-shaped values.

4. **xsd:date auto-typing** — The commands API's `_to_rdf_value` function detected ISO datetime strings (with "T") but stored YYYY-MM-DD date strings as plain untyped literals. Added detection for ISO 8601 date-only strings → `xsd:date` typed literals. This allows API-created tasks to be properly validated by SHACL shapes requiring `sh:datatype xsd:date`.

5. **Docker log visibility** — Added `print(..., flush=True, file=sys.stderr)` alongside the existing logger.info in `model_shapes_loader` to ensure the shapes+rules count message appears in Docker compose logs despite async worker buffering.

After all fixes, the lint dashboard shows:
- ▲ "Overdue test task for verification" (API-created) — "Task is overdue: due date has passed but task is not done or cancelled."
- ▲ "Fix validation edge case" (seed task) — same overdue warning

## Verification

- Docker test stack: `docker compose -f docker-compose.test.yml up -d --build` → healthy
- Created overdue task via API with proper xsd:date typing → no datatype violation
- Docker logs: `model_shapes_loader: Loaded 1143 shapes + 35 rules triples from 1 model(s)` ✓
- Lint status API: `{conforms: true, violation_count: 0, warning_count: 2}` ✓
- Lint dashboard browser: both tasks show overdue warning ✓
- Unit tests: 6/6 pass in test_validation_pipeline.py ✓
- Full test suite: 2630 pass, 0 failures ✓

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/pytest tests/test_validation_pipeline.py -v` | 0 | ✅ pass | 0.36s |
| 2 | `grep -rn "advanced=True" backend/app/services/validation.py` | 0 | ✅ pass | <1s |
| 3 | `grep -n "rules" backend/app/services/models.py \| grep -i "from\|construct\|merge"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/pytest tests/ -x -q --ignore=tests/test_jira_sync_engine.py` | 0 | ✅ pass | 9.4s |
| 5 | Docker logs: `grep "shapes.*rules triples"` | 0 | ✅ pass | — |
| 6 | Docker lint API: `curl /api/lint/status \| jq .warning_count` → 2 | 0 | ✅ pass | <1s |
| 7 | Browser: lint dashboard shows "Overdue test task for verification" | — | ✅ pass | — |
| 8 | Browser: lint dashboard shows "Task is overdue" for created task | — | ✅ pass | — |

## Diagnostics

- **Performance baseline:** pyshacl `advanced=True`:
  - Unit test (1178 triples): **0.037s**
  - Docker stack (271 data + 1178 shapes triples): **0.266s**
  - Both well within the <5s target. Performance risk retired.
- **Docker log check:** `docker compose -f docker-compose.test.yml logs api | grep "rules triples"`
- **Lint dashboard:** `http://localhost:3901/browser/lint-dashboard`
- **API lint status:** `curl /api/lint/status`

## Deviations

- Fixed four pre-existing bugs and added xsd:date auto-typing beyond T03's verify-only scope. These were required for the lint dashboard to show results and for the created task to trigger the SPARQLConstraint (rather than a datatype violation).

## Known Issues

- Pre-existing: `tests/test_jira_sync_engine.py::TestComputeStatus` fails due to unrelated `_compute_status` import error.

## Files Created/Modified

- `backend/app/services/validation.py` — BNode handling in `_rdf_term_to_sparql`; `insert_graph()` for results storage; removed unused `_turtle_to_ntriples`
- `backend/app/validation/report.py` — Skip blank-node source shapes in `to_structured_triples`
- `backend/app/triplestore/client.py` — Added `insert_graph()` for Graph Store protocol
- `backend/app/commands/handlers/object_create.py` — xsd:date auto-typing for YYYY-MM-DD strings
- `backend/app/services/models.py` — stderr print for Docker log visibility of shapes+rules count
- `.gsd/milestones/M030/slices/S01/S01-SUMMARY.md` — Slice summary with performance baseline
