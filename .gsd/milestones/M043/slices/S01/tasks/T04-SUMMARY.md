---
id: T04
parent: S01
milestone: M043
key_files:
  - backend/tests/test_sparql_injection_regression.py
  - backend/app/views/router.py
  - backend/app/vfs/mount_router.py
key_decisions:
  - Added early safe_iri() validation at parameter extraction point in views/router.py rather than relying on deep-call-chain ValueError — defense-in-depth: reject bad input as early as possible, return clean 400 with audit logging
  - Wrapped all IRI-field safe_iri() calls in mount_router create_mount() in a single try/except block rather than individual per-field validation — keeps the code concise while catching any IRI field injection
duration: ""
verification_result: passed
completed_at: 2026-03-25T08:44:02.423Z
blocker_discovered: false
---

# T04: Add 18 SPARQL injection regression tests covering all 5 audit findings (F-006 through F-010), plus fix early-validation gaps in views/router.py and vfs/mount_router.py

**Add 18 SPARQL injection regression tests covering all 5 audit findings (F-006 through F-010), plus fix early-validation gaps in views/router.py and vfs/mount_router.py**

## What Happened

Created `backend/tests/test_sparql_injection_regression.py` with 18 tests covering all 5 SPARQL injection findings from the M042 security audit:

**F-006 (7 tests):** Views `type` parameter injection — tests table, card, graph, and data endpoints with the exact audit payload (`x> . ?s ?p ?o } #`), plus angle-bracket breakout, comment injection, and a positive test confirming valid IRIs are not over-blocked.

**F-007 (3 tests):** Apps `iri` parameter injection — tests right-pane-sections with the audit payload, newline injection, and curly-brace WHERE block escape.

**F-008 (3 tests):** VFS mount write injection — tests create-mount with injected `group_by_property`, `type_filter`, and `scope_query` fields using the exact audit payload that would write arbitrary triples.

**F-009 (3 tests):** Favorites stored injection — tests toggle endpoint with the audit payload, angle-bracket breakout, and backslash-quote breakout.

**F-010 (2 tests):** Events search escape breakout — verifies the backslash-quote payload (`\" )) . ?s ?p ?o } #`) is safely escaped by `sparql_escape_string()` and doesn't cause SPARQL breakout. Also verifies tab/CR characters are properly escaped.

**Additional fixes discovered during test writing:**

1. `views/router.py` `generic_view()` and `generic_view_data()` had no early `type_iri` validation — `safe_iri()` was called deep inside `build_dynamic_query()` but the ValueError was uncaught, producing 500 instead of 400. Added try/except with `safe_iri()` validation right after the type parameter extraction, returning 400 with a warning log.

2. `vfs/mount_router.py` `create_mount()` called `safe_iri()` on body fields inline during triple construction without try/except — ValueError became 500. Wrapped all safe_iri calls in a try/except block that raises HTTPException(400) with a descriptive message. Also removed duplicate scope_query/type_filter blocks that existed outside the try/except.

3. Added explicit warning-level logging to mount_router's ValueError handler for security monitoring consistency.

## Verification

All 18 regression tests pass. 84 total SPARQL-related tests pass (66 builder + 18 regression). Full test suite: 5,231 pass, 118 pre-existing failures (CalDAV, sync engines — unrelated). LSP diagnostics show only pre-existing type warnings. Each audit finding has at least one test using the exact exploit payload from the M042 findings report.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_injection_regression.py -v` | 0 | ✅ pass | 780ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py tests/test_sparql_injection_regression.py -v` | 0 | ✅ pass | 820ms |
| 3 | `cd backend && .venv/bin/python -m pytest tests/ -v --ignore=tests/test_caldav_field_mapper.py --ignore=tests/test_caldav_sync_engine.py --ignore=tests/test_notion_executor.py (5231 passed, 118 pre-existing failures)` | 1 | ✅ pass (no new failures) | 38700ms |


## Deviations

Added early type_iri validation in views/router.py generic_view() and generic_view_data(), plus ValueError handling in vfs/mount_router.py create_mount(). These were gaps where safe_iri() was called deep in the call chain without try/except, causing 500 instead of 400. The task plan focused on tests but these fixes were necessary for the tests to verify 400 responses as specified.

## Known Issues

RuntimeWarning about unawaited coroutine in test teardown (from unittest.mock's AsyncMock) — cosmetic, does not affect test correctness.

## Files Created/Modified

- `backend/tests/test_sparql_injection_regression.py`
- `backend/app/views/router.py`
- `backend/app/vfs/mount_router.py`
