---
id: T04
parent: S03
milestone: M010
provides:
  - "37 unit tests in test_rss_reader_ui.py covering all 5 route handlers, workspace views, and edge cases"
  - "Verification that all S03 route handlers return correct HTTP status codes, HX-Trigger headers, and error fragments"
key_files:
  - backend/tests/test_rss_reader_ui.py
key_decisions:
  - "T04 folded into T03 — tests written alongside route handlers for faster iteration and immediate verification"
patterns_established:
  - "importlib.util.spec_from_file_location pattern for importing app.py in test context (avoids backend/app/ package collision)"
  - "Starlette TestClient with mocked AppContext (graph.query, commands.execute, render_template) for route handler testing"
observability_surfaces:
  - "pytest -v output shows 37 named test cases organized by handler class (TestArticleReadingPane, TestToggleStar, TestToggleRead, TestMarkAllRead, TestUnsubscribe, TestWorkspaceViews)"
  - "Test assertions verify HX-Trigger response headers (articleStateChanged, feedsChanged) — these headers drive UI refresh in production"
  - "Template existence checks verify all 4 new templates are on disk with expected content markers"
duration: 0m (folded into T03)
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T04: Unit tests for all reader UI route handlers

**37 unit tests covering all S03 route handlers, edge cases, template verification, and workspace views — delivered as part of T03**

## What Happened

T04 was fully completed within T03's execution. The 37 tests in `test_rss_reader_ui.py` cover the complete T04 scope:

- **TestArticleReadingPane** (11 tests): empty state, article not found, body rendering, description fallback, no content, star/read parsing, SPARQL errors, IRI sanitization, md_id presence
- **TestToggleStar** (6 tests): missing IRI, star/unstar toggle, HX-Trigger header, SPARQL/patch errors
- **TestToggleRead** (6 tests): missing IRI, mark-read-on-open, HX-Trigger header, toggle mode (both directions), patch errors
- **TestMarkAllRead** (6 tests): no unread articles, batch marking, feed scoping, HX-Trigger header, SPARQL errors, partial patch failure (best-effort)
- **TestUnsubscribe** (4 tests): missing feed_iri, successful unsubscribe with feed_service call, HX-Trigger header, unsubscribe errors
- **TestWorkspaceViews** (4 tests): unread-view.html filter=unread, starred-view.html filter=starred, star-button.html with SVG, reading pane template structure

## Verification

- 37/37 tests pass in 0.33s
- All tests use mocked SDK clients — no Docker stack required
- Tests verify HTTP status codes, response body content, HX-Trigger headers, and object.patch call arguments

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` | 0 | ✅ pass (37/37) | 0.33s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_app_proxy.py -v` | 0 | ✅ pass (3/3) | 0.20s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` | 0 | ✅ pass (88/88) | 0.35s |

## Diagnostics

- **Run tests**: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` — all 37 should pass in <1s
- **Check coverage by class**: The test output groups by class name (TestArticleReadingPane, TestToggleStar, etc.) — if any handler breaks, the class name identifies which route
- **Inspect mock calls**: Tests verify `mock_ctx.commands.execute.call_args` for correct object.patch payloads — add `print(mock_ctx.commands.execute.call_args_list)` for debugging
- **Template checks**: TestWorkspaceViews reads template files from disk — if a template is missing or renamed, these fail with clear FileNotFoundError

## Deviations

T04 was folded into T03 rather than being a separate execution unit. All 37 tests were written alongside the route handlers for faster iteration.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_rss_reader_ui.py` — 37 tests across 6 test classes (created in T03, verified here)
