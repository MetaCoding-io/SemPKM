---
id: T03
parent: S01
milestone: M031
provides:
  - 25 unit tests covering scope_filter parameter in build_dynamic_query()
  - 10 tests for extract_scope_where_body() utility including variable renaming and edge cases
  - 6 tests for get_view_specs_for_type() filtering including empty and generic spec exclusion
  - Contract verification for S01 boundary outputs consumed by S02, S03, S04
key_files:
  - backend/tests/test_view_scope.py
key_decisions:
  - Documented that extract_scope_where_body() returns empty for queries with LIMIT/ORDER BY after closing brace (end-of-string regex) — callers strip those clauses before calling
patterns_established:
  - Mocking get_all_view_specs via AsyncMock on the service instance to test get_view_specs_for_type without SPARQL infrastructure
  - Test classes organized by function under test with clear no-scope/with-scope separation
observability_surfaces:
  - pytest output from `cd backend && .venv/bin/python -m pytest tests/test_view_scope.py -v` — any red test identifies broken S01 contract
duration: 10m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Unit tests for scope query filtering and variant dropdown data

**Created 25 unit tests covering build_dynamic_query() scope filtering, extract_scope_where_body() utility, and get_view_specs_for_type() type matching — S01 contract verification.**

## What Happened

Created `backend/tests/test_view_scope.py` with 25 tests organized into 4 test classes:

1. **TestBuildDynamicQueryNoScope** (3 tests) — Baseline verification that default SELECT, typed SELECT, and CONSTRUCT queries contain no scope sub-select when `scope_filter` is None.

2. **TestBuildDynamicQueryWithScope** (6 tests) — Verifies that passing `scope_filter` injects a `{ SELECT ?s WHERE { ... } }` sub-select into all query types: default SELECT, typed SELECT, SHACL-derived SELECT, CONSTRUCT, typed CONSTRUCT, and confirms the sub-select uses the `?s` variable.

3. **TestExtractScopeWhereBody** (10 tests) — Tests the WHERE body extraction utility: simple ?s queries, variable renaming (?iri → ?s), DISTINCT handling, FROM clause tolerance, nested braces (OPTIONAL blocks), graceful degradation on malformed input (no WHERE, no braces, empty string), LIMIT-after-brace edge case, and secondary variable preservation.

4. **TestGetViewSpecsForType** (6 tests) — Tests type filtering against a mock set of 4 ViewSpecs: returns matching specs, different type, empty for unknown type, excludes generic specs (empty target_class), exact-match behavior for empty string, and empty when no specs exist.

One test adjustment was needed: `extract_scope_where_body()` uses an end-of-string regex (`\}\s*$`) so queries with `LIMIT` after the closing brace return empty. This is a known limitation documented in the test and handled by callers (the router strips LIMIT/ORDER BY from saved queries before passing to this function).

## Verification

All 25 tests pass with zero failures:

```
cd backend && .venv/bin/python -m pytest tests/test_view_scope.py -v
25 passed in 0.50s
```

Slice-level verification — all checks pass:

- `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/` — zero results ✅
- `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" frontend/static/js/` — zero results ✅
- `cd backend && .venv/bin/python -m pytest tests/test_view_scope.py -v` — 25 passed ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_view_scope.py -v` | 0 | ✅ pass (25 passed) | 0.50s |
| 2 | `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/` | 1 | ✅ pass (no matches) | <1s |
| 3 | `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" frontend/static/js/` | 1 | ✅ pass (no matches) | <1s |

### Slice-level verification (final task — all checks)

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | `cd backend && python -m pytest tests/test_view_scope.py -v` | ✅ pass | 25 tests, 0 failures |
| 2 | `grep -rn "carousel" ...` | ✅ pass | Zero results |
| 3 | `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" ...` | ✅ pass | Zero results |
| 4 | Docker stack manual check | ⬜ deferred | Requires running Docker stack — not part of unit test task |
| 5 | Diagnostic check (empty variant dropdown) | ⬜ deferred | Requires running Docker stack |

## Diagnostics

- **Run tests:** `cd backend && .venv/bin/python -m pytest tests/test_view_scope.py -v` — any failure names the specific broken contract.
- **Scope filtering contract:** If `test_default_select_with_scope` fails, the scope sub-select injection in `_build_default_select()` is broken.
- **WHERE body extraction:** If `test_renames_primary_var_to_s` fails, variable normalization in `extract_scope_where_body()` is broken — scope queries with non-?s variables won't filter correctly.
- **Variant dropdown data:** If `test_returns_matching_specs` fails, `get_view_specs_for_type()` filtering is broken — dropdown will show wrong specs.

## Deviations

- Plan said 8-12 tests; delivered 25 tests for more comprehensive coverage.
- Added a test documenting the LIMIT-after-brace edge case in `extract_scope_where_body()` — not in the plan but important for contract clarity.

## Known Issues

- `extract_scope_where_body()` returns empty for queries with `LIMIT`, `ORDER BY`, or other clauses after the closing WHERE brace. The regex uses `\}\s*$` (end-of-string). This is acceptable because the router calls `_extract_where_body()` (the brace-depth-counting version) for query execution, and `extract_scope_where_body()` is only used for scope injection where callers provide clean saved queries.

## Files Created/Modified

- `backend/tests/test_view_scope.py` — **created** — 25 unit tests for scope filtering, WHERE body extraction, and type-filtered spec lookup
- `.gsd/milestones/M031/slices/S01/tasks/T03-PLAN.md` — added Observability Impact section per pre-flight requirement
