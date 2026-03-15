---
estimated_steps: 5
estimated_files: 3
---

# T03: Integration Test and Edge Case Hardening

**Slice:** S05 — Interactive Dashboards — Cross-View Context
**Milestone:** M006

## Description

Add edge case unit tests for VALUES injection and dashboard context wiring. Verify the full test suite passes with zero regressions. Run conflict marker check.

## Steps

1. Add edge case tests to `backend/tests/test_values_injection.py`:
   - Test: query with multiple nested `{ }` blocks in WHERE (subqueries, OPTIONAL groups) — VALUES still placed correctly
   - Test: var_name with special characters rejected (dots, hyphens, spaces)
   - Test: very long IRI (500+ chars) still works
   - Test: IRI with unicode characters passes validation and injects correctly
   - Test: `inject_values_binding` called with query that has no WHERE clause — returns unchanged

2. Add context passthrough tests to `backend/tests/test_dashboard.py`:
   - Test: render_block for view-embed without context config produces no data-listens/data-emits attributes
   - Test: round-trip: create dashboard with emits_context/listens_to_context in block config, retrieve it, verify config preserved

3. Run full backend test suite: `cd backend && .venv/bin/pytest -x -q`

4. Run conflict marker check: `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"`

5. Verify all syntax is valid: `find backend/app -name "*.py" -exec python3 -c "import ast; ast.parse(open('{}').read())" \;`

## Must-Haves

- [ ] Edge case tests cover: nested braces, invalid var_name, no WHERE clause, unicode IRI
- [ ] Full test suite passes (599+ existing + new tests)
- [ ] Zero conflict markers in committed files

## Verification

- `cd backend && .venv/bin/pytest -x -q` — all tests pass
- `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` — returns empty
- Test count increased by 10+ from baseline (599)

## Inputs

- T01 output: `inject_values_binding()` function and basic tests
- T02 output: render_block data attribute wiring and template changes

## Expected Output

- `backend/tests/test_values_injection.py` — extended with 5+ edge case tests
- `backend/tests/test_dashboard.py` — extended with 2+ context config tests
- All tests passing, zero regressions, zero conflict markers

## Observability Impact

This task adds tests only — no runtime behavior changes. The new tests exercise
existing logging paths:
- `inject_values_binding` WARNING logs for rejected var_name/IRI are triggered by edge case tests (visible in pytest captured output with `-s`)
- No new runtime signals, endpoints, or diagnostic surfaces introduced
- Future agents: run `pytest -k test_values_injection -v` to see edge case coverage; run `pytest -k TestDashboardContextConfigRoundTrip -v` for context config round-trip verification
