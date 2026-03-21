---
id: T02
parent: S01
milestone: M030
provides:
  - Unit + functional tests proving validation pipeline fix works (loader merge, advanced flag, SPARQLConstraint firing)
  - Performance baseline for pyshacl with advanced=True (0.037s on 1178 triples)
key_files:
  - backend/tests/test_validation_pipeline.py
key_decisions:
  - allow_warnings=True means conforms stays True even with warnings; tests check results graph for warning presence, not conforms flag
patterns_established:
  - Shapes file is JSON-LD (basic-pkm.jsonld), not Turtle — parse with format="json-ld"
  - Patch asyncio.to_thread (not pyshacl.validate directly) to inspect kwargs passed through ValidationService
observability_surfaces:
  - pytest -v -s output shows pyshacl execution time
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Write unit tests for pipeline fix and measure performance

**Added 6 tests proving loader merges shapes+rules, service passes advanced=True, and SPARQLConstraint fires overdue task warning in 0.037s**

## What Happened

Created `backend/tests/test_validation_pipeline.py` with 6 tests covering the full validation pipeline fix from T01:

1. **test_loader_merges_shapes_and_rules** — Mocks TriplestoreClient to return canned shapes and rules Turtle from two CONSTRUCT calls. Asserts the returned graph contains triples from both.
2. **test_loader_no_models_returns_empty_graph** — Mocks query() returning empty bindings. Asserts empty graph.
3. **test_loader_empty_rules_returns_shapes_only** — Mocks construct() returning shapes on first call, empty string on second. Asserts shapes triples present, no crash.
4. **test_validate_passes_advanced_true_to_pyshacl** — Patches `asyncio.to_thread` to inspect kwargs. Asserts `advanced=True`, `allow_infos=True`, `allow_warnings=True` are all present.
5. **test_sparql_constraint_fires_for_overdue_task** — Loads real `basic-pkm.jsonld` shapes + `basic-pkm.ttl` rules into a combined graph, builds a data graph with an overdue task (due 2020-01-01, status "todo"), runs pyshacl with `advanced=True`. Asserts the results graph contains a ValidationResult with severity sh:Warning and message containing "overdue". Measures and prints execution time (0.037s).
6. **test_non_overdue_task_conforms** — Same setup but task status is "done". Asserts no overdue warning fires.

Key discovery: `allow_warnings=True` in pyshacl means warnings do not cause `conforms=False`. The test correctly checks for warning presence in the results graph rather than asserting `conforms is False`.

## Verification

All 6 tests pass. Performance timing printed. Slice-level diagnostic checks confirmed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/pytest tests/test_validation_pipeline.py -v` | 0 | ✅ pass | 0.35s |
| 2 | `grep -rn "advanced=True" backend/app/services/validation.py` | 0 | ✅ pass | <1s |
| 3 | `grep -n "rules" backend/app/services/models.py \| grep -i "from\|construct\|merge"` | 0 | ✅ pass | <1s |

## Diagnostics

- Run `cd backend && .venv/bin/pytest tests/test_validation_pipeline.py -v -s` to see performance timing output
- Performance baseline: pyshacl `advanced=True` on 1178 triples (shapes+rules from basic-pkm) with 1 overdue task completes in **0.037s** — well within the 10s budget. This retires the performance risk for S02's additional rules.

## Deviations

- Plan referenced `models/basic-pkm/shapes/basic-pkm.ttl` but the actual shapes file is `basic-pkm.jsonld` (JSON-LD format). Adjusted the functional test to parse as `json-ld`.
- Plan expected `conforms is False` for the overdue task test, but `allow_warnings=True` means pyshacl reports `conforms=True` even with warnings. Changed assertion to check for warning presence in the results graph instead, which is the correct semantic check.
- Added a 6th test (`test_non_overdue_task_conforms`) beyond the 5 specified — proves the negative case (done task does not trigger overdue warning).

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_validation_pipeline.py` — new: 6 tests covering loader merge, advanced flag, SPARQLConstraint firing, and performance timing
- `.gsd/milestones/M030/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M030/slices/S01/S01-PLAN.md` — marked T02 as done
