# S01: Validation Pipeline Fix & Performance Measurement

**Goal:** Fix the two broken links in the validation pipeline so that SHACL-AF SPARQLConstraint rules (overdue tasks, stale contacts, unprocessed notes, etc.) fire during validation and appear in the lint panel. Measure pyshacl performance with `advanced=True` and rules loaded.

**Demo:** User creates a Task with a past due date and status "todo" → runs validation → the overdue-task warning from basic-pkm's rules appears in the lint panel for the first time in production.

## Must-Haves

- `model_shapes_loader()` returns both shapes AND rules graphs merged into one rdflib Graph
- `ValidationService.validate()` passes `advanced=True` to `pyshacl.validate()`
- Existing M011 SHACL-AF validation rules fire and produce results visible in the lint panel
- Performance measurement documented: pyshacl execution time with `advanced=True` on representative data
- Unit tests prove the loader merges rules and the service passes `advanced=True`

## Proof Level

- This slice proves: integration (pipeline fix proven against real triplestore + pyshacl)
- Real runtime required: yes (Docker stack for integration verification)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/pytest tests/test_validation_pipeline.py -v` — unit tests for loader merge + advanced flag + performance timing
- Docker stack integration: create overdue task → trigger validation → lint panel shows warning
- Diagnostic check: `grep -rn "advanced=True" backend/app/services/validation.py` confirms the flag is present; `grep -n "rules" backend/app/services/models.py | grep -i "from\|construct\|merge"` confirms rules graph loading code exists
- Failure-path check: when no models are installed, `model_shapes_loader` returns an empty Graph and `validate()` returns synthetic conforms=True (no crash). Verified by unit test with empty registry mock.

## Observability / Diagnostics

- Runtime signals: `logger.info` in `model_shapes_loader` already logs triple count; add rules triple count
- Inspection surfaces: lint dashboard at `/browser/lint-dashboard` shows validation results; lint panel on object tab shows per-object results
- Failure visibility: if rules don't fire, lint panel shows 0 warnings — absence of results is the diagnostic signal
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `backend/app/services/models.py` (`model_shapes_loader`), `backend/app/services/validation.py` (`ValidationService.validate`), `backend/app/main.py` (wiring)
- New wiring introduced: none — `model_shapes_loader` is already called by `main.py:shapes_loader()` and passed to `ValidationService`; changes are internal to these functions
- What remains before the milestone is truly usable end-to-end: S02 (new data quality rules), S03 (lint filter system), S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Fix model_shapes_loader to include rules graphs and pass advanced=True in ValidationService** `est:1h`
  - Why: These are the two broken links preventing all SHACL-AF SPARQLConstraint rules from firing. The loader only fetches shapes graphs but not rules graphs. The validation service doesn't enable SHACL-AF processing. Both must be fixed together since fixing only one still produces zero results.
  - Files: `backend/app/services/models.py`, `backend/app/services/validation.py`
  - Do: (1) In `model_shapes_loader()`, add a second set of FROM clauses for rules graphs (`urn:sempkm:model:{model_id}:rules`) and merge them into the returned Graph alongside shapes. Use a second CONSTRUCT query for rules, then merge via `shapes_graph += rules_graph`. Log both shapes and rules triple counts. (2) In `ValidationService.validate()`, add `advanced=True` to the `pyshacl.validate()` call at line ~100. This enables SHACL-AF processing (SPARQLRule + SPARQLConstraint). The inference service already does this correctly at lines 144 and 157 of `backend/app/inference/service.py` — match that pattern.
  - Verify: `cd backend && .venv/bin/pytest tests/test_validation_pipeline.py -v`
  - Done when: Unit tests pass confirming (a) loader returns graph containing both shapes and rules triples, (b) validate() calls pyshacl with advanced=True

- [ ] **T02: Write unit tests for pipeline fix and measure performance** `est:1h`
  - Why: Need tests proving the fix works and performance measurement to retire the risk identified in the roadmap. The performance baseline is critical — S02 adds 9 more rules and we need to know if `advanced=True` causes unacceptable slowdowns.
  - Files: `backend/tests/test_validation_pipeline.py`
  - Do: (1) Write unit tests in `test_validation_pipeline.py` covering: (a) `model_shapes_loader` returns a Graph that includes triples from both shapes and rules named graphs (mock the triplestore client to return canned Turtle for shapes and rules CONSTRUCTs), (b) `ValidationService.validate()` passes `advanced=True` to pyshacl (mock pyshacl.validate and inspect kwargs), (c) When no models installed, loader returns empty graph (existing behavior preserved), (d) When rules graph is empty but shapes exist, loader still returns shapes (backward compat). (2) Write a performance measurement test that: creates a realistic data graph (~100 objects with types from basic-pkm), loads the real basic-pkm shapes+rules files from `models/basic-pkm/`, runs `pyshacl.validate()` with `advanced=True`, measures wall-clock time, and asserts it completes in <10 seconds. Log the timing. (3) Include a test with an overdue task (dueDate in past, status "todo") that proves the SPARQLConstraint fires and produces a sh:Warning result.
  - Verify: `cd backend && .venv/bin/pytest tests/test_validation_pipeline.py -v` — all tests pass, performance test logs timing
  - Done when: All tests pass. Performance measurement logged showing pyshacl execution time with advanced=True. At least one test proves SPARQLConstraint rules actually fire (overdue task warning detected in results).

- [ ] **T03: Docker integration verification and performance documentation** `est:45m`
  - Why: Unit tests with mocks prove the code changes are correct, but the pipeline fix must be verified against the real Docker stack to confirm rules fire in production. Performance must be documented to retire the roadmap risk.
  - Files: `backend/app/services/models.py` (no changes, just verify), `backend/app/services/validation.py` (no changes, just verify)
  - Do: (1) Start the Docker test stack (`docker compose -f docker-compose.test.yml up -d`). (2) Create a Task with a past due date via the API or UI. (3) Trigger validation (via the lint dashboard or object edit). (4) Check the lint panel — the overdue-task warning should appear. (5) Check Docker API logs for the `model_shapes_loader` log line showing both shapes AND rules triple counts. (6) Document performance findings: record the pyshacl execution time from T02's performance test and from Docker logs. Write a brief performance baseline note in the slice summary. (7) If performance is acceptable (<5s for ~100 objects with all rules), note this retires the roadmap risk. If >5s, flag for S02 planning.
  - Verify: Lint panel shows overdue-task warning on the created task. Docker logs show rules triples loaded.
  - Done when: Screenshot or log evidence of the overdue-task warning appearing in the lint panel. Performance baseline documented.

## Files Likely Touched

- `backend/app/services/models.py` — `model_shapes_loader()` function
- `backend/app/services/validation.py` — `ValidationService.validate()` method
- `backend/tests/test_validation_pipeline.py` — new test file
