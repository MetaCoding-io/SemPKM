---
id: T04
parent: S03
milestone: M010
provides:
  - 43 unit tests covering all 7 reader UI route handlers, edge cases, and helper functions
  - Proxy query-string forwarding test (already existed from T01, verified passing)
key_files:
  - backend/tests/test_rss_reader_ui.py
key_decisions:
  - Used flat helper functions (_feed_binding, _article_binding, _reading_pane_binding) over pytest fixtures for binding construction — simpler, more explicit, no fixture dependency chains
patterns_established:
  - _make_mock_request(ctx, query_params, form_data) pattern for testing Starlette route handlers with async form() mocking
  - pytest.MonkeyPatch.context() for patching module-level imports (unsubscribe) in async test functions
observability_surfaces:
  - `pytest tests/test_rss_reader_ui.py -v` — 43 named tests covering feed sidebar, article list, reading pane, star/read toggles, mark-all-read, unsubscribe, and helper functions
duration: 8m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T04: Unit tests for all reader UI route handlers

**Created 43 unit tests covering all 7 reader UI route handlers with mocked SDK context, verifying SPARQL construction, template rendering, star/read toggle logic, and edge cases.**

## What Happened

Created `backend/tests/test_rss_reader_ui.py` with 43 tests organized into 8 test classes:

- **TestFeedSidebar** (6 tests): SPARQL query structure (GROUP BY/COUNT), template args, empty feeds, error count parsing, title fallback to URL, SPARQL error handling
- **TestArticleList** (7 tests): No filter, feed_iri filter, unread filter, starred filter, date formatting, empty state, active_filter/active_feed passthrough
- **TestReadingPane** (6 tests): Body present, description fallback, no content (None), no article_iri (empty state), article not found, md_id passthrough
- **TestToggleStar** (4 tests): Star on (false→true), star off (true→false), returns star-button.html with HX-Trigger, missing IRI 400
- **TestToggleRead** (3 tests): Default marks read, toggle=true flips, missing IRI 400
- **TestMarkAllRead** (4 tests): Batch-patches all unread, skips when none unread, filters by feed_iri, returns sidebar
- **TestUnsubscribe** (3 tests): Calls feed_service.unsubscribe, missing IRI 400, returns sidebar with feedsChanged trigger
- **TestHelpers** (10 tests): _format_date, _sparql_bool, _sparql_int with valid/invalid/None inputs

The proxy query-string test (`test_forward_preserves_query_string`) already existed in `test_app_proxy.py` from T01 — verified it passes.

## Verification

- `pytest tests/test_rss_reader_ui.py -v` — **43 passed** in 0.42s
- `pytest tests/test_app_proxy.py -v` — **25 passed** (includes query-string test)
- `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — **77 passed**, zero regressions
- `grep -c "def test_" backend/tests/test_rss_reader_ui.py` — **43** (≥20 required)
- `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK
- `manifest.yaml` includes `reader.js` in `frontend.js` array — confirmed

**Slice-level verification (all checks pass — this is the final task):**
- ✅ ≥20 tests covering all route handlers
- ✅ Proxy tests pass with query-string forwarding test
- ✅ Zero regressions on S01/S02 tests
- ✅ app.py syntax OK
- ✅ manifest.yaml includes reader.js

## Diagnostics

- Run `pytest tests/test_rss_reader_ui.py -v` for named pass/fail per route handler
- Run `pytest tests/test_rss_reader_ui.py -k "star"` to isolate star toggle tests
- Run `grep -c "def test_" backend/tests/test_rss_reader_ui.py` to confirm coverage breadth

## Deviations

- Plan called for adding a proxy query-string test to `test_app_proxy.py` — it already existed from T01 execution, so no new test was added there. Verified it passes.
- Plan estimated ~20 tests; delivered 43 for more thorough coverage including helper function tests and additional edge cases.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_rss_reader_ui.py` — **created**, 43 unit tests for all 7 reader UI route handlers
- `.gsd/milestones/M010/slices/S03/tasks/T04-PLAN.md` — added Observability Impact section
- `.gsd/milestones/M010/slices/S03/S03-PLAN.md` — marked T04 as `[x]`
