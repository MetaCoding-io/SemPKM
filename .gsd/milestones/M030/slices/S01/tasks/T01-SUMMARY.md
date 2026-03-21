---
id: T01
parent: S01
milestone: M030
provides:
  - model_shapes_loader fetches and merges both shapes AND rules graphs from installed models
  - ValidationService.validate passes advanced=True to pyshacl enabling SHACL-AF processing
key_files:
  - backend/app/services/models.py
  - backend/app/services/validation.py
key_decisions: []
patterns_established:
  - rules graphs merged into shapes graph via rdflib Graph.__iadd__ (shapes_graph += rules_graph)
observability_surfaces:
  - "logger.info in model_shapes_loader now shows: 'Loaded %d shapes + %d rules triples from %d model(s)'"
duration: 12m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Fix model_shapes_loader to include rules graphs and pass advanced=True in ValidationService

**Added rules graph loading to model_shapes_loader and advanced=True to ValidationService.validate so SHACL-AF SPARQLConstraint rules fire during validation**

## What Happened

Two fixes applied to unblock the SHACL-AF validation pipeline:

1. **`model_shapes_loader()`** in `backend/app/services/models.py` (line ~1140): Added a second CONSTRUCT query that fetches rules graphs (`urn:sempkm:model:{id}:rules`) for all installed models, parses them into a separate `rules_graph`, and merges into the shapes graph via `shapes_graph += rules_graph`. The log message was updated to show separate shapes and rules triple counts: `"Loaded %d shapes + %d rules triples from %d model(s)"`.

2. **`ValidationService.validate()`** in `backend/app/services/validation.py` (line 105): Added `advanced=True` to the `pyshacl.validate()` call. This enables SHACL-AF features (SPARQLRule, SPARQLConstraint), matching the pattern already used in `inference/service.py` at lines 144 and 157.

Both fixes are required together — without `advanced=True`, pyshacl ignores SHACL-AF constraints even if rules triples are present; without rules triples, there are no SPARQLConstraint definitions to process.

## Verification

- `grep -n "advanced" backend/app/services/validation.py` → shows `advanced=True` at line 105 ✓
- `grep -n "rules" backend/app/services/models.py | grep -i "from\|construct\|merge"` → shows rules graph FROM clauses, CONSTRUCT query, and merge logic ✓
- `grep -rn "model_shapes_loader\|shapes_loader" backend/app/` → confirms single caller in `main.py` ✓
- `cd backend && .venv/bin/pytest tests/ -x -q --ignore=tests/test_jira_sync_engine.py` → 2624 passed, 0 failed ✓
- Pre-existing failure in `test_jira_sync_engine.py` (unrelated `_compute_status` import error) confirmed not caused by our changes

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -n "advanced" backend/app/services/validation.py` | 0 | ✅ pass | <1s |
| 2 | `grep -n "rules" backend/app/services/models.py \| grep -i "from\|construct\|merge"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/pytest tests/ -x -q --ignore=tests/test_jira_sync_engine.py` | 0 | ✅ pass | 9.2s |
| 4 | `cd backend && .venv/bin/pytest tests/test_validation_pipeline.py -v` | N/A | ⏳ deferred | T02 creates this file |

## Diagnostics

- **Runtime log:** `docker compose logs api 2>&1 | grep "shapes.*rules triples"` — shows shapes and rules triple counts per model load. A non-zero rules count confirms rules are flowing into validation.
- **Code verification:** `grep -n "advanced=True" backend/app/services/validation.py` — confirms SHACL-AF flag is set.
- **Failure signal:** If lint panel shows 0 warnings on objects that should violate rules, check the model_shapes_loader log line — a rules count of 0 means rules graphs are missing from the triplestore.

## Deviations

None.

## Known Issues

- Pre-existing test failure in `tests/test_jira_sync_engine.py::TestComputeStatus::test_no_errors_returns_success` — unrelated `_compute_status` import error from linear-sync engine refactoring. Not caused by this task.

## Files Created/Modified

- `backend/app/services/models.py` — `model_shapes_loader()` now fetches and merges rules graphs alongside shapes graphs
- `backend/app/services/validation.py` — `validate()` now passes `advanced=True` to `pyshacl.validate()`
- `.gsd/milestones/M030/slices/S01/S01-PLAN.md` — Added diagnostic verification steps (pre-flight fix)
- `.gsd/milestones/M030/slices/S01/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
