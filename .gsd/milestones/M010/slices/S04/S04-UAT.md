# S04: Workspace contributions + custom renderer — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S04 is contract-verified via 73 unit tests (56 RSS reader UI + 17 app views/commands). Live runtime E2E testing is explicitly deferred to S06. All workspace contributions are manifest-declared and route-handler-backed — artifacts can be inspected directly.

## Preconditions

- M010 worktree exists at `.gsd/worktrees/M010/`
- Backend venv functional at `.gsd/worktrees/M010/backend/.venv/`
- `apps/rss-reader/manifest.yaml` and `apps/rss-reader/app.py` exist in worktree
- All unit tests pass: `pytest tests/test_rss_reader_ui.py tests/test_app_views_commands.py -v`

## Smoke Test

Run `cd .gsd/worktrees/M010/backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles or TestArticleReadRenderer or TestMarkAllReadContext"` — should report 19 passed in <1s.

## Test Cases

### 1. Manifest declares all three workspace contributions

1. `python3 -c "import yaml, json; m=yaml.safe_load(open('.gsd/worktrees/M010/apps/rss-reader/manifest.yaml')); print(json.dumps(m['ui']['contributions'], indent=2))"`
2. **Expected:** JSON shows `rightPane` array with "related-articles" entry, `commandPalette` array containing "mark-all-read" entry with `actionType: "post"`, and existing entries preserved.

### 2. Manifest declares Article object renderer with full IRI

1. `python3 -c "import yaml; m=yaml.safe_load(open('.gsd/worktrees/M010/apps/rss-reader/manifest.yaml')); print(m['ui']['objectRenderers'][0])"`
2. **Expected:** `{'type': 'urn:sempkm:model:rss-feeds:Article', 'modes': {'read': 'article-read-renderer'}}` — type is the full IRI, not a short name.

### 3. Related articles handler returns empty state for blank IRI

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_empty_iri_returns_empty_state and TestRelatedArticles"`
2. **Expected:** Test passes — handler returns `rss-empty-state` div when no IRI provided.

### 4. Related articles SPARQL uses UNION for feedSource and shared tags

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_queries_by_iri_with_union_pattern"`
2. **Expected:** Test passes — SPARQL query contains UNION with both `feedSource` and `bpkm:tags` branches, and FILTER excludes the focused IRI itself.

### 5. Related articles passes article list to template

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_passes_articles_to_template and TestRelatedArticles"`
2. **Expected:** Test passes — template receives `articles` list with `iri`, `title`, `date`, `feed_title` fields parsed from SPARQL bindings.

### 6. Related articles SPARQL error returns error fragment

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_sparql_error_returns_error_fragment and TestRelatedArticles"`
2. **Expected:** Test passes — SPARQL exception results in `rss-error` div, not a 500 crash.

### 7. Article read renderer queries by IRI

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_queries_article_by_iri and TestArticleReadRenderer"`
2. **Expected:** Test passes — SPARQL query filters by the provided IRI with correct Article type.

### 8. Article read renderer includes star state

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_includes_star_state and TestArticleReadRenderer"`
2. **Expected:** Test passes — template args include `is_starred` boolean parsed from SPARQL binding.

### 9. Article read renderer falls back to description when no body

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_falls_back_to_description_when_no_body and TestArticleReadRenderer"`
2. **Expected:** Test passes — when `body` binding is empty, `description` is used as fallback content.

### 10. Mark-all-read command palette context returns success message

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_command_palette_context_returns_success_message"`
2. **Expected:** Test passes — when HX-Target is `#modal-container`, response contains `rss-success` class div with article count, not sidebar HTML.

### 11. Mark-all-read command palette triggers both events

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_command_palette_context_triggers_both_events"`
2. **Expected:** Test passes — HX-Trigger header contains both `articleStateChanged` and `feedsChanged`.

### 12. Mark-all-read reader context returns sidebar

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_reader_context_returns_sidebar"`
2. **Expected:** Test passes — without HX-Target `#modal-container`, response returns sidebar HTML with only `articleStateChanged` trigger.

### 13. Navigate command enrichment adds appId/pageId for app pages

1. Run: `pytest tests/test_app_views_commands.py -v -k "test_navigate_matching_app_page_includes_appid_pageid"`
2. **Expected:** Test passes — navigate command JSON includes `appId` and `pageId` when cmd.path matches a manifest page.

### 14. Navigate command omits appId/pageId for non-app paths

1. Run: `pytest tests/test_app_views_commands.py -v -k "test_navigate_non_matching_path_omits_appid_pageid"`
2. **Expected:** Test passes — navigate command JSON for external/admin paths has no `appId` or `pageId` fields.

### 15. JS handler calls openAppPageTab for navigate with appId

1. `grep -A4 'cmd.appId' .gsd/worktrees/M010/frontend/static/js/workspace.js | head -10`
2. **Expected:** Code shows `if (cmd.appId) { openAppPageTab(cmd.appId, cmd.pageId, cmd.title); }` — SPA tab opening instead of `window.location.href`.

### 16. Related articles template has data-article-iri attributes

1. `grep 'data-article-iri' .gsd/worktrees/M010/apps/rss-reader/frontend/templates/related-articles.html`
2. **Expected:** Template element includes `data-article-iri="{{ article.iri }}"` for test automation targeting.

### 17. Related articles template dispatches open-object event

1. `grep 'sempkm:open-object' .gsd/worktrees/M010/apps/rss-reader/frontend/templates/related-articles.html`
2. **Expected:** onclick handler dispatches `sempkm:open-object` custom event with `detail: {iri: ...}`.

## Edge Cases

### Empty state for article read renderer with missing IRI

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_no_iri_returns_empty_state and TestArticleReadRenderer"`
2. **Expected:** Returns `rss-reading-pane-empty` div — same pattern as S03's reading pane.

### Article not found in read renderer

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_article_not_found and TestArticleReadRenderer"`
2. **Expected:** SPARQL returns no bindings → error message rendered, not a crash.

### No related articles found

1. Run: `pytest tests/test_rss_reader_ui.py -v -k "test_no_results_template_receives_empty_list"`
2. **Expected:** Template receives empty articles list → empty state rendered gracefully.

### All existing S03 tests still pass

1. Run: `cd .gsd/worktrees/M010/backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "not TestRelatedArticles and not TestArticleReadRenderer and not TestMarkAllReadContext"`
2. **Expected:** 37 tests pass — zero regressions from S04 changes to app.py.

## Failure Signals

- Any test failure in `test_rss_reader_ui.py` or `test_app_views_commands.py`
- `rss-error` appearing in success-path test assertions (should only appear in error-path tests)
- Missing `appId` or `pageId` in navigate command JSON for app page paths
- `window.location.href` still used for app page navigates in workspace.js (should use `openAppPageTab`)
- `objectRenderers[0].type` not being the full IRI `urn:sempkm:model:rss-feeds:Article`
- SPARQL query in related-articles missing UNION or FILTER NOT EXISTS for self-exclusion

## Requirements Proved By This UAT

- RSS-06 (partial) — Related Articles right pane and Mark All as Read command palette verified via unit tests
- RSS-03 (partial) — Custom Article read renderer contract verified; runtime dispatch deferred to S06
- APP-08 (partial) — Right pane section and command palette entries verified at contract level
- APP-09 (partial) — Object renderer override manifest declaration verified; runtime dispatch deferred to S06

## Not Proven By This UAT

- Live runtime behavior (platform rendering right pane sections, dispatching to custom renderer, command palette integration) — deferred to S06 E2E tests
- Visual rendering quality (typography, layout, star button styling) — requires human UAT
- Performance with large article sets (related articles SPARQL with many tags/feeds)
- Cross-browser compatibility of openAppPageTab() dockview tab creation

## Notes for Tester

- All tests run in <1s with mocked SDK context — no Docker or triplestore required
- The `rss-error` class is generated in Python route handler code, not in Jinja2 templates — grep the `.py` file, not `.html` templates
- T02's navigate fix is platform-wide (all apps benefit), not RSS-specific. Future app E2E tests should also verify this behavior.
- The existing S03 mark-all-read tests (TestMarkAllRead class) test the core functionality; S04's TestMarkAllReadContext tests specifically cover the command palette vs reader context branching added in this slice.
