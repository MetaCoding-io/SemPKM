---
id: T03
parent: S04
milestone: M010
provides:
  - 19 new unit tests covering related-articles, article-read-renderer, and mark-all-read context detection
  - TestRelatedArticles (7 tests): SPARQL structure, UNION pattern, self-exclusion, empty state, error handling
  - TestArticleReadRenderer (9 tests): query, template, body fallback, star state, empty/error states
  - TestMarkAllReadContext (3 tests): command palette vs reader UI context branching
key_files:
  - backend/tests/test_rss_reader_ui.py
key_decisions:
  - Navigate enrichment tests already existed from T02 — no duplicates added to test_app_views_commands.py
patterns_established:
  - _make_related_article_bindings() helper for building related-articles SPARQL result mocks
  - TestMarkAllReadContext separated from TestMarkAllRead to isolate S04's context-branching behavior
observability_surfaces:
  - "pytest tests/test_rss_reader_ui.py -v -k TestRelatedArticles" isolates right pane tests
  - "pytest tests/test_rss_reader_ui.py -v -k TestArticleReadRenderer" isolates custom renderer tests
  - "pytest tests/test_rss_reader_ui.py -v -k TestMarkAllReadContext" isolates context detection tests
duration: 8 minutes
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Unit tests for S04 fragments and navigate fix

**Added 19 unit tests for S04's related-articles fragment, article-read-renderer fragment, and mark-all-read command palette context detection — all pass with zero regressions**

## What Happened

Added three new test classes to `test_rss_reader_ui.py`:

1. **TestRelatedArticles** (7 tests) — covers the right-pane related-articles handler: empty/blank IRI returns `rss-empty-state`, SPARQL query uses UNION pattern for feedSource OR shared tags, FILTER excludes the focused IRI, articles list passed to `related-articles.html` template, empty results template, and SPARQL error returns `rss-error` fragment.

2. **TestArticleReadRenderer** (9 tests) — covers the object browser custom renderer: missing/blank IRI returns `rss-reading-pane-empty`, SPARQL queries by IRI with correct type, article-not-found returns error message, renders `article-read-renderer.html` template with article dict + body + md_id, includes `is_starred` state, SPARQL error returns `rss-error`, and body falls back to description when empty.

3. **TestMarkAllReadContext** (3 tests) — covers the T01 command palette context branching: HX-Target `#modal-container` returns `rss-success` message (not sidebar), HX-Trigger includes both `articleStateChanged` and `feedsChanged`; without HX-Target returns sidebar HTML with only `articleStateChanged`.

Navigate enrichment tests (`test_navigate_matching_app_page_includes_appid_pageid` and `test_navigate_non_matching_path_omits_appid_pageid`) already existed from T02 — verified they still pass.

## Verification

- `pytest tests/test_rss_reader_ui.py -v` — 56 passed (37 existing + 19 new)
- `pytest tests/test_app_views_commands.py -v` — 17 passed (all existing, zero regressions)
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` — valid YAML

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_rss_reader_ui.py -v` | 0 | ✅ pass | 0.41s |
| 2 | `pytest tests/test_app_views_commands.py -v` | 0 | ✅ pass | 0.31s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` | 0 | ✅ pass | <1s |
| 5 | `pytest -k "TestRelatedArticles or TestArticleReadRenderer or TestMarkAllReadContext" -v` | 0 | ✅ pass (19 selected) | 0.27s |

## Diagnostics

- `pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles or TestArticleReadRenderer"` — isolates S04-specific handler tests
- `pytest tests/test_rss_reader_ui.py -v -k "TestMarkAllReadContext"` — isolates command palette context branching tests
- Test failures pinpoint: SPARQL query structure (UNION, FILTER), template name, template args, response body content, and HTTP headers

## Deviations

- Navigate enrichment tests (Step 4) were already present in `test_app_views_commands.py` from T02 — no duplicates added. The plan anticipated these might need to be written, but T02 already included them.
- Existing test count was 37 (not 43 as the plan estimated) — the plan likely counted tests from a different branch state. All 37 still pass with zero regressions.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_rss_reader_ui.py` — Added `TestRelatedArticles` (7 tests), `TestArticleReadRenderer` (9 tests), `TestMarkAllReadContext` (3 tests), plus `_make_related_article_bindings()` helper and `BPKM_TAGS` constant import
