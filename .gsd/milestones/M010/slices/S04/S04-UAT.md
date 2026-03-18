# S04: Workspace contributions + custom renderer — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All features are contract-tested via unit tests with mocked SDK context. Live runtime verification is deferred to S06 E2E tests. This UAT validates the artifacts (manifest structure, route handler behavior, template content, JS wiring) can be confirmed without a running Docker stack.

## Preconditions

- Working directory: `.gsd/worktrees/M010`
- Backend venv active: `cd backend && source .venv/bin/activate`
- All S03 test infrastructure in place (conftest, mock helpers)

## Smoke Test

Run the full S04 test suite to confirm everything works:
```
cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py tests/test_app_views_commands.py -v
```
**Expected:** 56 + 17 = 73 tests pass, 0 failures.

## Test Cases

### 1. Manifest declares all three workspace contributions

1. Load manifest: `python3 -c "import yaml, json; m=yaml.safe_load(open('apps/rss-reader/manifest.yaml')); print(json.dumps(m['ui']['contributions'], indent=2))"`
2. **Expected:** `rightPane` array contains entry with `fragment: "related-articles"` and `label: "Related Articles"`
3. **Expected:** `commandPalette` array contains entry with `id: "mark-all-read"` and `actionType: "post"`
4. **Expected:** `commandPalette` array contains entry with `id: "open-reader"` and `actionType: "navigate"` and `path: "/reader"`

### 2. Manifest declares Article object renderer with full IRI

1. Load manifest: `python3 -c "import yaml; m=yaml.safe_load(open('apps/rss-reader/manifest.yaml')); print(m['ui']['objectRenderers'][0])"`
2. **Expected:** `type` is `urn:sempkm:model:rss-feeds:Article` (full IRI, not QName)
3. **Expected:** `modes` includes `read` with a `fragment` path

### 3. Related articles handler — SPARQL UNION pattern

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles::test_queries_by_iri_with_union_pattern"`
2. **Expected:** Test passes, confirming the SPARQL query uses UNION with both feedSource and bpkm:tags match paths

### 4. Related articles handler — self-exclusion

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles::test_excludes_self_from_results"`
2. **Expected:** Test passes, confirming the focused object's own IRI is excluded via FILTER

### 5. Related articles handler — empty/error states

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles and (empty_iri or blank_iri or error)"`
2. **Expected:** 3 tests pass — empty IRI returns `rss-empty-state`, blank IRI returns `rss-empty-state`, SPARQL error returns `rss-error`

### 6. Article read renderer — renders article with correct template

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestArticleReadRenderer::test_renders_article_with_correct_template"`
2. **Expected:** Test passes, confirming template is `article-read-renderer.html` (not `reading-pane.html`)

### 7. Article read renderer — includes star state

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestArticleReadRenderer::test_includes_star_state"`
2. **Expected:** Test passes, confirming `is_starred` is extracted from SPARQL results and passed to template

### 8. Article read renderer — body falls back to description

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestArticleReadRenderer::test_falls_back_to_description"`
2. **Expected:** Test passes, confirming body uses `description` value when `content` is empty

### 9. Mark-all-read command palette context detection

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestMarkAllReadContext::test_command_palette_context_returns_success_message"`
2. **Expected:** When `HX-Target: #modal-container` is set, response contains `rss-success` class
3. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestMarkAllReadContext::test_reader_context_returns_sidebar"`
4. **Expected:** Without `HX-Target` header, response returns sidebar HTML (not success message)

### 10. Mark-all-read triggers both events from command palette

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestMarkAllReadContext::test_command_palette_context_triggers_both_events"`
2. **Expected:** HX-Trigger response header contains both `articleStateChanged` and `feedsChanged`

### 11. Navigate command enrichment — app page match

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v -k "test_navigate_matching_app_page_includes_appid_pageid"`
2. **Expected:** Navigate command JSON entry includes `appId` and `pageId` fields when path matches an app page

### 12. Navigate command enrichment — non-matching path

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v -k "test_navigate_non_matching_path_omits_appid_pageid"`
2. **Expected:** Navigate command JSON entry does NOT include `appId` or `pageId` when path doesn't match any app page

### 13. JS handler wires openAppPageTab for navigate commands

1. Run: `grep -A5 'cmd.appId' frontend/static/js/workspace.js | head -10`
2. **Expected:** When `cmd.appId` exists, handler calls `openAppPageTab(cmd.appId, cmd.pageId, cmd.title)` instead of `window.location.href`

### 14. Error states render rss-error class in both new handlers

1. Run: `grep -c 'rss-error' apps/rss-reader/app.py`
2. **Expected:** Count includes lines for related-articles and article-read-renderer error paths
3. Verify specific lines: `grep -n 'rss-error.*related\|rss-error.*article' apps/rss-reader/app.py`
4. **Expected:** Lines ~1111 (related articles) and ~1172 (article renderer) present

### 15. Templates exist with correct structure

1. Check related-articles template: `cat apps/rss-reader/frontend/templates/related-articles.html | head -20`
2. **Expected:** Contains `data-article-iri` attributes and `rss-empty-state` class for empty state
3. Check article-read-renderer template: `cat apps/rss-reader/frontend/templates/article-read-renderer.html | head -20`
4. **Expected:** Contains `data-md-source` / `data-md-target` attributes for markdown rendering

## Edge Cases

### Empty IRI parameter on related articles

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles::test_empty_iri_returns_empty_state"`
2. **Expected:** Returns `rss-empty-state` HTML, no SPARQL query executed

### Missing article in read renderer

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestArticleReadRenderer::test_article_not_found"`
2. **Expected:** Returns error message HTML (not a 500 crash)

### SPARQL failure in both new handlers

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles::test_sparql_error or TestArticleReadRenderer::test_sparql_error"`
2. **Expected:** Both return `rss-error` div fragment (graceful degradation, no stack trace in response)

### Navigate command for non-app path

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v -k "test_navigate_non_matching"`
2. **Expected:** No `appId`/`pageId` in JSON — command falls through to `window.location.href`

## Failure Signals

- `pytest tests/test_rss_reader_ui.py` fails → route handler or template regression
- `pytest tests/test_app_views_commands.py` fails → navigate enrichment regression
- `rss-error` class missing from handler error paths → SPARQL errors will return unformatted text
- `openAppPageTab` not in JS navigate branch → "Open RSS Reader" navigates away from workspace SPA
- Manifest missing `objectRenderers` → articles open with default SHACL form, not reader layout
- Manifest missing `rightPane` contribution → "Related Articles" section won't appear in workspace right pane

## Requirements Proved By This UAT

- **RSS-06** (partial) — "Related Articles" right pane, "Mark All as Read" command palette, "Open RSS Reader" navigate-to-tab all have contract tests proving handler behavior
- **RSS-03** (partial) — Custom `rss:Article` read renderer declared in manifest and handler implemented with tests
- **APP-08** (partial) — Right pane section and command palette POST contributions proven via unit tests
- **APP-09** (partial) — Object renderer override for Article type declared and handler tested

## Not Proven By This UAT

- Live runtime behavior: fragments rendering in actual browser, dockview tab creation, right pane section loading
- Platform dispatch: `_get_renderer_override()` actually routing to the app fragment for Article objects
- Platform rendering: `right_pane_sections.html` actually loading the related-articles fragment
- Visual appearance: article reader styling, star button interaction in custom renderer context
- All deferred to S06 E2E tests with live Docker stack

## Notes for Tester

- All tests run in <1s total — they use mocked SDK context, no Docker needed
- The 37→56 test count increase (19 new) matches the S04 plan's ≥15 target
- Navigate enrichment tests are in a separate file (`test_app_views_commands.py`) — don't forget to run both test files
- The command palette context detection relies on the HX-Target header value `#modal-container` — this is the platform's standard modal target, not an RSS-reader-specific value
