---
id: T04
parent: S01
milestone: M036
provides:
  - 28 unit tests covering quadrant axis detection, SPARQL query building, Eisenhower labelling, and result grouping
key_files:
  - backend/tests/test_quadrant.py
key_decisions: []
patterns_established:
  - Quadrant test follows kanban test structure exactly — same _make_property/_make_form/_build_service helpers, same mock AsyncMock(return_value={"results":{"bindings":[...]}}) pattern
observability_surfaces:
  - Test file itself is the observability surface — `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` shows per-test pass/fail with descriptive names
  - Failure in any test pinpoints which quadrant pipeline stage broke (axis detection, query building, labelling, or grouping)
duration: 12m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T04: Quadrant backend unit tests

**Added 28 unit tests for quadrant axis detection, query building, Eisenhower labelling, and result grouping — all pass.**

## What Happened

Created `backend/tests/test_quadrant.py` with 5 test classes (28 tests total):

1. **TestDetectQuadrantAxes** (9 tests) — validates `_detect_quadrant_axes()` finds two SHACL properties with exactly 2 `sh:in` values, prefers "urgency"/"importance" keywords case-insensitively, falls back to first two candidates when no keyword match, rejects properties with 3+ values, rejects single-candidate shapes, and handles None/exception from shapes service.

2. **TestBuildQuadrantSelect** (4 tests) — validates `_build_quadrant_select()` produces correct SPARQL with type filter and two non-OPTIONAL axis bindings, scope filter injection as sub-select, and absence of scope clause when None.

3. **TestQuadrantLabel** (5 tests) — validates `_quadrant_label()` returns Eisenhower-specific labels (Do First, Schedule, Delegate, Eliminate) for high/low combinations and generic "Name: val / Name: val" fallback for non-Eisenhower values.

4. **TestExecuteQuadrantQuery** (10 tests) — validates `execute_quadrant_query()` groups items into 4 quadrant buckets, places mismatched axis values in Unclassified bucket, follows x×y iteration order, deduplicates subjects, returns empty buckets on no results, includes axes metadata, handles query failures gracefully, falls back to local name when label binding absent, handles multiple items in same quadrant, and uses generic labels for non-standard values.

## Verification

1. `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — 28 passed, 0 failures, 0 errors in 0.56s
2. `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v --tb=short 2>&1 | tail -5` — confirms 28 passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` | 0 | ✅ pass | 0.56s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v --tb=short 2>&1 \| tail -5` | 0 | ✅ pass | 0.52s |

## Diagnostics

- **Run all quadrant tests:** `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v`
- **Run a specific class:** `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py::TestDetectQuadrantAxes -v`
- **Run with coverage:** `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py --cov=app.views.service --cov-report=term-missing`

## Deviations

- Added Observability Impact section to T04-PLAN.md per pre-flight requirement — test files are their own observability surface (named assertions pinpoint which pipeline stage broke).

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_quadrant.py` — 28 unit tests for quadrant axis detection, SPARQL query building, Eisenhower labelling, and result grouping
- `.gsd/milestones/M036/slices/S01/S01-PLAN.md` — Marked T04 as [x] done
