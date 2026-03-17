---
estimated_steps: 5
estimated_files: 2
---

# T04: Unit tests for all reader UI route handlers

**Slice:** S03 — Reader UI (split-pane layout)
**Milestone:** M010

## Description

Create `backend/tests/test_rss_reader_ui.py` with ≥20 unit tests covering all route handlers added in T02 and T03. Tests mock the SDK context (graph.query, commands.execute, render_template) and verify SPARQL query construction, template rendering calls, star/read toggle logic, and edge cases. Also add one test to `backend/tests/test_app_proxy.py` for the query-string forwarding fix from T01.

**Key testing pattern:** Use `importlib.util.spec_from_file_location` to import from `apps/rss-reader/app.py` (see KNOWLEDGE.md — the module name `app` collides with `backend/app/`). Import route handler functions by their function name after loading the module. The route handlers are async functions decorated with `@rss_reader_app.route()` — to test them, create mock Request objects with `app.state.ctx` containing mock graph/commands clients.

## Steps

1. **Set up test file and import helpers** — Create `backend/tests/test_rss_reader_ui.py`:
   - Use `importlib.util.spec_from_file_location("rss_reader_app", path)` to load app.py
   - Create helper functions:
     - `_make_mock_ctx()` — returns a mock with `graph.query` (AsyncMock), `commands.execute` (AsyncMock), `commands.bulk` (AsyncMock context manager), `render_template` (Mock returning HTML string)
     - `_make_mock_request(query_params=None, form_data=None)` — returns a mock Request with `app.state.ctx`, `query_params`, and async `form()` method
     - `_make_sparql_result(bindings)` — wraps binding dicts in `{"results": {"bindings": [...]}}`

2. **Feed sidebar tests** (~5 tests):
   - `test_feed_sidebar_queries_subscriptions` — verify SPARQL query contains GROUP BY and COUNT for unread
   - `test_feed_sidebar_passes_feeds_to_template` — verify render_template called with feed list containing correct fields
   - `test_feed_sidebar_empty_feeds` — verify renders with empty feeds list when no bindings
   - `test_feed_sidebar_error_count_parsing` — verify error_count parsed as int from SPARQL string
   - `test_feed_sidebar_title_fallback` — verify URL used as title when title is absent

3. **Article list tests** (~6 tests):
   - `test_article_list_no_filter` — all articles returned, SPARQL has no FILTER clause
   - `test_article_list_filter_by_feed` — SPARQL contains FILTER for feed_iri
   - `test_article_list_filter_unread` — SPARQL requires isRead false
   - `test_article_list_filter_starred` — SPARQL requires isStarred true
   - `test_article_list_date_formatting` — ISO 8601 dates formatted as human-readable
   - `test_article_list_empty` — no articles renders empty state

4. **Reading pane + action tests** (~10 tests):
   - `test_reading_pane_with_body` — article with body passes body content to template
   - `test_reading_pane_fallback_to_description` — no body → uses dcterms:description
   - `test_reading_pane_no_content` — no body and no description → passes None for body
   - `test_reading_pane_no_article_iri` — returns empty state HTML when no article_iri param
   - `test_toggle_star_on` — calls object.patch with isStarred=True when current is false
   - `test_toggle_star_off` — calls object.patch with isStarred=False when current is true
   - `test_toggle_star_returns_button` — returns rendered star-button.html template
   - `test_toggle_read_marks_read` — calls object.patch with isRead=True
   - `test_mark_all_read_patches_all` — queries unread articles and patches each to read
   - `test_unsubscribe_calls_service` — calls feed_service.unsubscribe with correct IRI

5. **Proxy query-string test** — Add one test to `backend/tests/test_app_proxy.py`:
   - `test_forward_preserves_query_string` — mock request with `url.query = "feed_iri=urn:test&filter=unread"`, verify the httpx client was called with a URL containing `?feed_iri=urn:test&filter=unread`

## Must-Haves

- [ ] ≥20 tests in `test_rss_reader_ui.py`
- [ ] Tests cover all 7 route handlers: feed-sidebar, article-list, article-reading-pane, toggle-star, toggle-read, mark-all-read, unsubscribe
- [ ] Edge cases tested: empty feeds, empty articles, missing body, missing title, no article_iri
- [ ] Star toggle tests verify correct object.patch call with toggled boolean value
- [ ] Proxy query-string test added to `test_app_proxy.py`
- [ ] All tests pass: `cd backend && python -m pytest tests/test_rss_reader_ui.py tests/test_app_proxy.py -v`
- [ ] Zero regressions on S01/S02 tests

## Verification

- `cd backend && python -m pytest tests/test_rss_reader_ui.py -v` — ≥20 tests pass
- `cd backend && python -m pytest tests/test_app_proxy.py -v` — all tests pass including new query-string test
- `cd backend && python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — zero regressions
- `grep -c "def test_" backend/tests/test_rss_reader_ui.py` — ≥20

## Inputs

- `apps/rss-reader/app.py` — from T02/T03, all route handlers implemented
- `apps/rss-reader/services/feed_service.py` — `unsubscribe()` function signature
- `backend/tests/test_rss_feed_parser.py` — reference for `importlib.util.spec_from_file_location` import pattern and mock helpers
- `backend/tests/test_feed_service.py` — reference for mock ctx pattern (`_make_mock_ctx`, `_make_sparql_binding`)
- `backend/tests/test_app_proxy.py` — existing proxy test patterns (pytest-asyncio, mocked httpx.AsyncClient)
- KNOWLEDGE.md: "App module import collision in tests" — use `spec_from_file_location` with unique module name

## Observability Impact

- **Test coverage signals:** `pytest tests/test_rss_reader_ui.py -v` reports per-test pass/fail for all 7 route handlers. A future agent can run this to confirm all UI route logic is intact.
- **Inspection surface:** `grep -c "def test_" backend/tests/test_rss_reader_ui.py` returns ≥20, confirming coverage breadth.
- **Failure visibility:** Any route handler regression (SPARQL query structure, template args, star/read toggle logic, HX-Trigger headers) will surface as a named test failure.
- **Proxy coverage:** `test_forward_preserves_query_string` in `test_app_proxy.py` catches query-string forwarding regressions.

## Expected Output

- `backend/tests/test_rss_reader_ui.py` — ≥20 unit tests for reader UI route handlers
- `backend/tests/test_app_proxy.py` — one new test for query-string forwarding (appended to existing file)
