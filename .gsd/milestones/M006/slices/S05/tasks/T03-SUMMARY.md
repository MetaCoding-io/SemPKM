---
id: T03
parent: S05
milestone: M006
provides:
  - 12 edge case tests for inject_values_binding (nested braces, subqueries, invalid var names, unicode IRIs, long IRIs, no WHERE clause)
  - 3 context config round-trip tests for dashboard service (create/retrieve/update preserve emits_context and listens_to_context)
key_files:
  - backend/tests/test_values_injection.py
  - backend/tests/test_dashboard.py
key_decisions:
  - Tests exercise existing _validate_iri boundary via inject_values_binding rather than testing _validate_iri directly — keeps tests at the public API surface
patterns_established:
  - Edge case test naming: test_{what}_{condition} e.g. test_var_name_rejects_dot
observability_surfaces:
  - none (test-only task — no runtime changes)
duration: 10m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Integration Test and Edge Case Hardening

**Added 15 edge case tests across values injection and dashboard context config — 631 total tests passing, zero regressions, zero conflict markers.**

## What Happened

Extended `test_values_injection.py` with 12 new edge case tests covering:
- Nested brace handling (OPTIONAL+UNION, subqueries with inner WHERE)
- Variable name rejection (dots, hyphens, spaces, SPARQL injection attempts)
- Long IRIs (500+ chars)
- Unicode IRIs (Latin accented, CJK characters)
- No WHERE clause (DESCRIBE, CONSTRUCT without WHERE)

Extended `test_dashboard.py` with 3 new tests in `TestDashboardContextConfigRoundTrip`:
- Create → retrieve round-trip preserves emits_context and listens_to_context
- Update name doesn't clobber block context config
- view-embed without context config produces no data-listens/data-emits attributes

## Verification

- `cd backend && .venv/bin/pytest -x -q` → **631 passed** (up from 599 baseline, +32 total from S05)
- `grep -rn "^<<<<<<< " backend/ frontend/` → **empty** (zero conflict markers)
- `find backend/app -name "*.py" -exec python3 -c "import ast; ast.parse(open('{}').read())" \;` → **zero syntax errors**

### Slice-level verification status (intermediate task):
- ✅ `test_values_injection.py` — VALUES placement, IRI rejection, no-op, variable naming, edge cases
- ✅ `test_dashboard.py` — context_iri passthrough, round-trip config, no-context-no-attrs
- ⏭️ E2E browser test — deferred to T04
- ✅ 0 conflict markers
- ⏭️ Diagnostic failure path (invalid IRI with running stack) — covered by unit tests; live verification deferred to T04

## Diagnostics

Run specific test groups:
- `pytest -k test_values_injection -v` — all VALUES injection tests
- `pytest -k TestDashboardContextConfigRoundTrip -v` — context config round-trip tests
- `pytest -k "nested" -v` — nested brace edge cases specifically

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_values_injection.py` — added 12 edge case tests (nested braces, var name rejection, long/unicode IRIs, no WHERE clause)
- `backend/tests/test_dashboard.py` — added `TestDashboardContextConfigRoundTrip` class with 3 tests
- `.gsd/milestones/M006/slices/S05/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M006/slices/S05/S05-PLAN.md` — marked T03 as `[x]`
