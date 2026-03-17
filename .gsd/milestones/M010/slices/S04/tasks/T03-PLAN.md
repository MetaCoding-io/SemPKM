---
estimated_steps: 5
estimated_files: 2
---

# T03: Unit tests for S04 fragments and navigate fix

**Slice:** S04 — Workspace contributions + custom renderer
**Milestone:** M010

## Description

Add unit tests for all new S04 code: the two new app fragment route handlers (related-articles, article-read-renderer), the mark-all-read command palette context detection, and the navigate command enrichment with `appId`/`pageId`. Tests follow S03's established patterns: `_make_mock_request()` for app route handlers, `TestClient` for platform API endpoints.

**Relevant skills:** `test` — for test pattern reference if needed.

## Steps

1. **Add related-articles handler tests** to `backend/tests/test_rss_reader_ui.py`:
   Create a new `TestRelatedArticles` class with tests:
   - `test_related_articles_queries_by_iri` — verifies SPARQL query contains the focused IRI and UNION pattern (same feed source OR shared tags)
   - `test_related_articles_passes_articles_to_template` — verifies articles list is constructed from bindings and passed to `render_template("related-articles.html", ...)`
   - `test_related_articles_empty_iri` — when `?iri=` is empty, returns empty state HTML
   - `test_related_articles_no_results` — when SPARQL returns empty bindings, template receives empty articles list
   - `test_related_articles_sparql_error` — when `ctx.graph.query` raises, returns `<div class="rss-error">` fragment
   - `test_related_articles_excludes_self` — SPARQL query contains `FILTER(?article != <{iri}>)` to exclude the focused object

   Use the existing `_make_mock_request(ctx, query_params={"iri": "urn:test:article:1"})` pattern. Mock `ctx.graph.query` to return appropriate bindings. Assert on `ctx.render_template` call args.

2. **Add article-read-renderer handler tests** to `backend/tests/test_rss_reader_ui.py`:
   Create a new `TestArticleReadRenderer` class with tests:
   - `test_renderer_queries_article` — verifies SPARQL query fetches article properties for the given IRI
   - `test_renderer_passes_article_and_body_to_template` — verifies template args include article dict, body content, and md_id
   - `test_renderer_no_iri` — when `?iri=` is missing, returns error/empty state
   - `test_renderer_article_not_found` — when SPARQL returns empty bindings, returns "not found" message
   - `test_renderer_uses_correct_template` — verifies template name is `"article-read-renderer.html"`
   - `test_renderer_includes_star_state` — article dict contains `is_starred` field

   Follow the same pattern as `TestReadingPane` tests from S03.

3. **Add mark-all-read context detection test** to `backend/tests/test_rss_reader_ui.py`:
   Add to existing `TestMarkAllRead` class (or create new test):
   - `test_mark_all_read_command_palette_context` — when request has `HX-Target: #modal-container` header, response body contains a success message (not sidebar HTML), and response has `HX-Trigger` header with both `articleStateChanged` and `feedsChanged`
   - `test_mark_all_read_reader_context` — when request does NOT have `HX-Target: #modal-container`, response returns feed sidebar HTML (existing behavior)

   Use `_make_mock_request()` with headers dict to simulate HX-Target header.

4. **Add navigate command enrichment tests** to `backend/tests/test_app_views_commands.py`:
   Add to existing `TestCommandsAPI` class:
   - `test_navigate_command_with_app_page_includes_app_id` — create a manifest with a page at `/reader` and a navigate command pointing to `/reader`. Verify the JSON response includes `appId` and `pageId` fields.
   - `test_navigate_command_without_app_page_has_no_app_id` — create a manifest with a navigate command pointing to `/some/external/path` that doesn't match any page. Verify `appId` and `pageId` are NOT in the JSON response. (The existing `test_navigate_command_format` test already covers this with `/admin/apps/nav-app/settings` but add an explicit assertion for absent keys.)

   Use the existing `_make_manifest()` and `_create_test_app()` helpers. The `_make_manifest` helper may need a `pages` parameter added — or construct the manifest with pages directly.

5. **Run all tests and verify zero regressions**:
   - `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` — all tests pass (S03's 43 + new ≥11)
   - `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v` — all tests pass (existing + new ≥2)
   - Total new tests ≥15

## Must-Haves

- [ ] `TestRelatedArticles` class with ≥5 tests covering SPARQL structure, template args, empty state, self-exclusion, and error handling
- [ ] `TestArticleReadRenderer` class with ≥4 tests covering query, template args, missing IRI, and not-found
- [ ] Mark-all-read context detection has ≥2 tests (command palette vs reader context)
- [ ] Navigate command enrichment has ≥2 tests (page match vs no match)
- [ ] All S03 tests (43) still pass — zero regressions
- [ ] All existing command tests still pass — zero regressions
- [ ] Total new tests ≥15

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` — reports ≥54 passed (43 existing + ≥11 new)
- `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v` — reports ≥13 passed (11 existing + ≥2 new)
- `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py tests/test_app_views_commands.py -v` — all pass, zero failures

## Inputs

- `backend/tests/test_rss_reader_ui.py` — S03's 43-test file. Key patterns to follow:
  - `_make_mock_ctx()` creates a mock with `ctx.graph.query`, `ctx.render_template`, `ctx.commands.execute`, `ctx.commands.bulk`
  - `_make_mock_request(ctx, query_params, form_data)` creates a Starlette-like Request mock with async `form()` method
  - `_reading_pane_binding(...)` helper creates SPARQL result bindings for articles
  - Tests are organized by handler into classes like `TestFeedSidebar`, `TestArticleList`, `TestReadingPane`, etc.
  - Each test typically: (1) sets up mock ctx, (2) creates mock request with params, (3) awaits the handler, (4) asserts on ctx.graph.query call (SPARQL structure), ctx.render_template call (template name, args), or response body

- `backend/tests/test_app_views_commands.py` — 11-test file with `_make_manifest()`, `_make_command()`, `_create_test_app()` helpers. Tests use `TestClient(app).get("/api/apps/commands")` to hit the commands_list endpoint and assert on JSON response.

- `apps/rss-reader/app.py` — T01's new route handlers: `related_articles_fragment()` and `article_read_renderer_fragment()`, plus updated `mark_all_read_route()`

- `backend/app/browser/apps.py` — T02's enhanced `commands_list()` with `appId`/`pageId` enrichment

**Key testing patterns from S03:**
- Mock `ctx.graph.query` as `AsyncMock(return_value=_make_sparql_result([...bindings...]))`
- Mock `ctx.render_template` as `MagicMock(return_value="<html>...")`
- Assert SPARQL query structure by inspecting `ctx.graph.query.call_args[0][0]`
- Assert template args by inspecting `ctx.render_template.call_args`

## Observability Impact

- **Test coverage signal:** `pytest tests/test_rss_reader_ui.py -v` output shows test count per class. Future agents can verify coverage by class: `TestRelatedArticles` (≥5), `TestArticleReadRenderer` (≥4), `TestMarkAllRead` (≥6), navigate enrichment (≥2).
- **Regression detection:** Any code change to `related_articles_fragment`, `article_read_renderer_fragment`, `mark_all_read_route` (context branching), or `commands_list` (navigate enrichment) will trigger test failures visible in pytest output.
- **Failure visibility:** Tests assert on SPARQL query structure, template name, template args, response body content, and HTTP headers — failures pinpoint exactly which contract broke.
- **Inspection:** `pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles or TestArticleReadRenderer"` isolates S04-specific tests.

## Expected Output

- `backend/tests/test_rss_reader_ui.py` — expanded with `TestRelatedArticles` (≥5 tests), `TestArticleReadRenderer` (≥4 tests), and mark-all-read context tests (≥2 tests)
- `backend/tests/test_app_views_commands.py` — expanded with navigate enrichment tests (≥2 tests)
