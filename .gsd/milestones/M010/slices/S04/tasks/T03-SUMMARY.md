---
id: T03
parent: S04
milestone: M010
provides:
  - TestRelatedArticles class (7 tests) covering SPARQL structure, template args, empty/missing IRI, no results, error, self-exclusion
  - TestArticleReadRenderer class (9 tests) covering query, template args, missing/empty IRI, not-found, correct template, star state, body fallback, SPARQL error
  - TestMarkAllReadContext class (3 tests) covering command palette vs reader context branching
  - Navigate enrichment tests (2 tests, added in T02) verified passing
key_files:
  - backend/tests/test_rss_reader_ui.py
  - backend/tests/test_app_views_commands.py
key_decisions:
  - Separated mark-all-read context tests into own TestMarkAllReadContext class rather than adding to existing TestMarkAllRead, for clarity
  - Reused _reading_pane_binding() helper for renderer tests since the SPARQL shape is nearly identical
  - Added headers parameter to _make_mock_request() to support HX-Target context detection
patterns_established:
  - _make_mock_request() now accepts headers dict for testing request header-dependent branching
  - _related_article_binding() helper for related-articles SPARQL results
observability_surfaces:
  - pytest -v output shows test counts per class for regression detection
  - pytest -k "TestRelatedArticles or TestArticleReadRenderer" isolates S04-specific tests
duration: ~15 min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Unit tests for S04 fragments and navigate fix

**Added 19 new tests covering related-articles, article-read-renderer, and mark-all-read context detection; all 77 tests pass with zero regressions.**

## What Happened

Added three new test classes to `test_rss_reader_ui.py`:

1. **TestRelatedArticles** (7 tests): Verifies SPARQL query contains focused IRI and UNION pattern for feedSource/tags matching, self-exclusion FILTER, articles passed to `related-articles.html` template, empty/missing IRI returns empty state, no results passes empty list, and SPARQL error returns `rss-error` fragment.

2. **TestArticleReadRenderer** (9 tests): Verifies SPARQL query fetches article properties, template receives article dict with `is_starred`, body, and `md_id`, uses `article-read-renderer.html` template, missing/empty IRI returns error, not-found returns message, body falls back to description, and SPARQL error returns error fragment.

3. **TestMarkAllReadContext** (3 tests): Verifies `HX-Target: #modal-container` returns `rss-success` message with both `articleStateChanged` and `feedsChanged` triggers (command palette context), zero-article edge case, and absence of HX-Target returns sidebar HTML (reader context).

The navigate enrichment tests (2 tests) were already added in T02 and verified passing.

Updated `_make_mock_request()` to accept an optional `headers` dict for testing request-header-dependent branching.

## Verification

- `pytest tests/test_rss_reader_ui.py -v` → **62 passed** (43 existing + 19 new)
- `pytest tests/test_app_views_commands.py -v` → **15 passed** (13 existing + 2 navigate enrichment)
- `pytest tests/test_rss_reader_ui.py tests/test_app_views_commands.py -v` → **77 passed, 0 failures**
- Slice checks:
  - `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` → syntax OK ✓
  - `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` → valid YAML ✓
  - `objectRenderers[0].type` = `urn:sempkm:model:rss-feeds:Article` in manifest ✓
  - Navigate command JSON includes `appId`/`pageId` when path matches app page (verified by test) ✓
  - `mark_all_read_route()` returns `rss-success` when `HX-Target` is `#modal-container` (verified by test) ✓
  - `rss-error` HTML is returned from Python handlers on SPARQL failure (verified by tests, not in templates) ✓

## Diagnostics

- Run `pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles"` to isolate related-articles tests
- Run `pytest tests/test_rss_reader_ui.py -v -k "TestArticleReadRenderer"` to isolate renderer tests
- Run `pytest tests/test_rss_reader_ui.py -v -k "TestMarkAllReadContext"` to isolate context detection tests
- Failures pinpoint which handler contract broke: SPARQL structure, template name, template args, response body, or HTTP headers

## Deviations

- Plan specified ≥5 TestRelatedArticles tests; delivered 7 (added no_iri_param test for missing param entirely, distinct from empty param)
- Plan specified ≥4 TestArticleReadRenderer tests; delivered 9 (added empty_iri, body_fallback, and sparql_error tests)
- Plan noted `rss-error` should be in template HTML files; actually the error divs are returned directly from Python handlers, not in Jinja templates. Tests verify the handler behavior correctly.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_rss_reader_ui.py` — Added imports for `related_articles_fragment`, `article_read_renderer_fragment`, `RELATED_ARTICLES_SPARQL`, `BPKM_TAGS`; added `headers` param to `_make_mock_request()`; added `_related_article_binding()` helper; added `TestRelatedArticles` (7 tests), `TestArticleReadRenderer` (9 tests), `TestMarkAllReadContext` (3 tests)
- `backend/tests/test_app_views_commands.py` — No changes (navigate enrichment tests already present from T02)
- `.gsd/milestones/M010/slices/S04/tasks/T03-PLAN.md` — Added Observability Impact section
