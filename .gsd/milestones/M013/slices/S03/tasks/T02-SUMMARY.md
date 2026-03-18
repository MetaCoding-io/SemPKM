---
id: T02
parent: S03
milestone: M013
provides:
  - 18 unit tests covering all context-query code paths including graceful degradation
key_files:
  - backend/tests/test_api_surface.py
key_decisions:
  - Added graceful degradation tests beyond T02-PLAN's 6 required tests — SPARQL failure, FTS failure, label resolution failure, and type resolution failure each verified independently
patterns_established:
  - Degradation test pattern: override one mock to raise, verify the other result sources still return data
  - SPARQL escape helper has its own test class (TestSparqlEscapeStr) for input sanitization coverage
observability_surfaces:
  - pytest -v -k "context_query or sparql_escape" shows 18 test names confirming each code path
duration: 10m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Unit tests for context-query endpoint

**Added 9 tests (4 graceful degradation + 5 SPARQL escape helper) on top of T01's 9, totaling 18 context-query-related tests covering all code paths**

## What Happened

T01 already wrote 9 tests covering the 6 required paths (URL match, keyword match, title match, empty results, validation 400, auth 401, deduplication, type info enrichment, Bearer token auth). T02 extended coverage with:

1. **Graceful degradation tests** (4 new): Verified that each independent exception-catching stage in the endpoint works correctly — SPARQL URL match failure still returns FTS results, FTS failure still returns URL results, label resolution failure falls back to IRI as label, type resolution failure returns type_iri/type_label as None.

2. **SPARQL escape helper tests** (5 new, `TestSparqlEscapeStr`): Verified `_sparql_escape_str` correctly escapes double quotes, backslashes, newlines, and combined special characters — critical for injection prevention in the URL matching SPARQL query.

## Verification

- `cd backend && .venv/bin/pytest tests/test_api_surface.py -v -k "context_query or sparql_escape"` — 18 passed
- `cd backend && .venv/bin/pytest tests/test_api_surface.py -v` — 62 passed (no regressions)
- Python AST parse check on test file — OK

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `.venv/bin/pytest tests/test_api_surface.py -v -k "context_query or sparql_escape"` | 0 | ✅ pass | 0.80s |
| 2 | `.venv/bin/pytest tests/test_api_surface.py -v` | 0 | ✅ pass | 1.41s |
| 3 | `python3 -c "import ast; ast.parse(open('tests/test_api_surface.py').read())"` | 0 | ✅ pass | <1s |

### Slice-level checks (intermediate task — partial expected)

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Unit tests `-k "context_query"` | ✅ pass | 13/13 context-query + 5 sparql_escape |
| 2 | curl URL match against Docker | ⏳ pending | Requires Docker stack |
| 3 | curl keyword match against Docker | ⏳ pending | Requires Docker stack |
| 4 | E2E Playwright tests | ⏳ pending | T03 |
| 5 | docs/guide/31-api-surface.md | ⏳ pending | T04 |
| 6 | curl empty body → 400 (failure-path) | ⏳ pending | Requires Docker stack |

## Diagnostics

- **Test coverage map**: URL match, keyword match, title match, empty results, validation (400), auth (401), dedup, type enrichment, Bearer auth, SPARQL failure degradation, FTS failure degradation, label failure degradation, type failure degradation, plus 5 SPARQL escape edge cases
- **How to inspect**: `pytest tests/test_api_surface.py -v -k "context_query or sparql_escape"` — each test name indicates the code path it validates

## Deviations

- Added 4 graceful degradation tests and 5 SPARQL escape tests beyond the plan's minimum 6 — these exercise the independent exception-catching pattern documented in T01's patterns.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_api_surface.py` — Added 4 degradation tests in TestContextQueryEndpoint and 5 helper tests in TestSparqlEscapeStr
- `.gsd/milestones/M013/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (preflight fix)
