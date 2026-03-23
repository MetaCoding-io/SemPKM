---
estimated_steps: 4
estimated_files: 2
skills_used:
  - test
---

# T04: Unit tests for OKR + Decision Matrix pipelines

**Slice:** S03 — OKR Progress + Decision Matrix Weighted Scoring
**Milestone:** M036

## Description

Write comprehensive unit tests for both renderer pipelines, following the exact `test_quadrant.py` / `test_bmc.py` pattern. These tests pin the server-side computation logic: OKR progress percentages (including edge cases like division by zero and over-target clamping) and Decision Matrix weighted scoring (including tie handling and missing scores). Uses the same `_make_property()`, `_make_form()`, `_build_service()` helper pattern.

## Steps

1. **test_okr.py helpers** — Create `backend/tests/test_okr.py`. Import `pytest`, `AsyncMock`, `MagicMock`, `PropertyShape`, `NodeShapeForm`, `ShapesService`, `ViewSpecService`. Copy the `_make_property()`, `_make_form()`, `_build_service()` helpers from `test_quadrant.py` (they're identical — creates PropertyShape/NodeShapeForm with given parameters, builds ViewSpecService with mocked dependencies).

2. **test_okr.py test classes** — Write 3 test classes with ≥15 tests total:
   - `TestDetectOkrStructure` (~6 tests): happy path finds currentValue + targetValue decimal properties and belongsToObjective ObjectProperty; prefers path containing "currentvalue"/"targetvalue"; rejects non-decimal datatypes; returns None when no decimal properties; handles shapes_service=None; handles get_form_for_type raising exception.
   - `TestBuildOkrSelect` (~4 tests): basic query structure with type filter; OPTIONAL bindings for currentValue/targetValue/unit/objective; scope_filter sub-select inclusion; no objective join when objective_path is None.
   - `TestExecuteOkrQuery` (~8 tests): progress computation 50/100=50%, 0/0=0% (div-by-zero), 120/100=100% (clamped), negative current=-10/100=0% (clamped at 0); grouping by objective (2 objectives each with 2 KRs); objective-level progress = average of child KR progress; ungrouped KRs (no objective link); empty results; error handling (query raises exception); deduplication by IRI.

3. **test_decision_matrix.py helpers** — Create `backend/tests/test_decision_matrix.py`. Same imports and helpers. The `_build_service()` helper may need adjustment for Decision Matrix queries that return score+alt+crit bindings rather than simple property bindings.

4. **test_decision_matrix.py test classes** — Write 3 test classes with ≥15 tests total:
   - `TestDetectDecisionMatrixStructure` (~5 tests): happy path finds weight/value decimal properties and alternative/criterion ObjectProperties on Score shape; prefers paths containing "weight"/"value"; handles missing ObjectProperties; returns None when no qualifying properties; handles exception.
   - `TestBuildDecisionMatrixSelect` (~4 tests): basic query with 3-type join (Score→Alternative, Score→Criterion); criterion weight included; scope_filter sub-select; non-OPTIONAL joins (scores without both references are excluded).
   - `TestExecuteDecisionMatrixQuery` (~8 tests): weighted scoring Σ(weight×value) for 3 alternatives; correct ranking order (highest first); tie handling (same weighted_score gets same rank); single alternative; empty results; error handling; missing score for one criterion (partial scoring); criteria list extraction.

## Must-Haves

- [ ] `test_okr.py` with ≥15 tests covering detection, query building, and computation edge cases
- [ ] `test_decision_matrix.py` with ≥15 tests covering detection, query building, and scoring
- [ ] OKR progress edge cases: 0/0=0%, over-target clamped to 100%, negative clamped to 0%
- [ ] Decision Matrix scoring: Σ(weight × value) computed correctly, ranking by descending score
- [ ] Both test files use `_make_property()`, `_make_form()`, `_build_service()` helper pattern
- [ ] All tests pass: `cd backend && .venv/bin/python -m pytest tests/test_okr.py tests/test_decision_matrix.py -v`

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_okr.py -v` — all tests pass, ≥15 tests
- `cd backend && .venv/bin/python -m pytest tests/test_decision_matrix.py -v` — all tests pass, ≥15 tests
- `cd backend && .venv/bin/python -m pytest tests/test_okr.py tests/test_decision_matrix.py -v` — combined run, 0 failures
- `grep -c 'def test_' backend/tests/test_okr.py` — ≥15
- `grep -c 'def test_' backend/tests/test_decision_matrix.py` — ≥15

## Inputs

- `backend/tests/test_quadrant.py` — reference test pattern (649 lines) with helpers and test structure
- `backend/tests/test_bmc.py` — reference test pattern (711 lines)
- `backend/app/views/service.py` — T02 output with OKR + Decision Matrix service methods to test
- `backend/app/services/shapes.py` — PropertyShape and NodeShapeForm dataclass definitions

## Expected Output

- `backend/tests/test_okr.py` — ≥15 unit tests for OKR detection, query building, and progress computation
- `backend/tests/test_decision_matrix.py` — ≥15 unit tests for Decision Matrix detection, query building, and weighted scoring

## Observability Impact

- **Test coverage signal:** `cd backend && .venv/bin/python -m pytest tests/test_okr.py tests/test_decision_matrix.py -v` — tests pin the detection, query building, and computation logic for both renderer pipelines. Regressions in progress clamping, weighted scoring, tie handling, or SHACL detection will be caught here.
- **Inspection:** `grep -c 'def test_' backend/tests/test_okr.py` (≥15) and `grep -c 'def test_' backend/tests/test_decision_matrix.py` (≥15) confirm test density.
- **Failure visibility:** Test names encode the edge case being verified (e.g., `test_div_by_zero`, `test_tie_handling`, `test_negative_current_clamped_to_0`) — failure output immediately identifies which computation path broke.
