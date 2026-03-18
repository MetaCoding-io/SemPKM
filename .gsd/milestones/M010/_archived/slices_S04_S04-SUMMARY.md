---
id: S04
parent: M010
milestone: M010
provides:
  - rightPane "Related Articles" section showing articles sharing tags/feed with focused object
  - Custom rss:Article read renderer replacing default SHACL form in object browser
  - "Mark All as Read" command palette entry with context-aware response (command palette vs reader UI)
  - Navigate command enrichment with appId/pageId for dockview tab opening (platform-wide fix)
  - 21 new unit tests (19 RSS reader + 2 navigate enrichment)
requires:
  - slice: S02
    provides: FeedService, article/subscription data in triplestore, SPARQL query patterns
  - slice: S03
    provides: Reader UI template patterns, _sparql_bool/_format_date/_sparql_int helpers, star-button template, reader.css/reader.js
affects:
  - S06
key_files:
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/related-articles.html
  - apps/rss-reader/frontend/templates/article-read-renderer.html
  - backend/app/browser/apps.py
  - frontend/static/js/workspace.js
  - backend/tests/test_rss_reader_ui.py
  - backend/tests/test_app_views_commands.py
key_decisions:
  - Related articles SPARQL uses UNION of feedSource match and bpkm:tags match (LIMIT 10, self-exclusion FILTER)
  - Article read renderer omits fire-and-forget mark-read (object browser context != reader context)
  - Command palette context detection via HX-Target header == "#modal-container"
  - Navigate command page matching uses exact equality (page.path == cmd.path)
patterns_established:
  - Right pane fragment handler pattern: receive ?iri= param, SPARQL query, render template with articles list
  - Custom object renderer fragment: receive ?iri= param, reuse SPARQL shape, render without reader-specific triggers
  - Command palette context detection via HX-Target header for branching response format
  - Navigate command enrichment: iterate manifest pages, match path, add appId+pageId to JSON
observability_surfaces:
  - SPARQL errors in related-articles/renderer handlers logged as warnings, rendered as <div class="rss-error">
  - data-article-iri attributes on related-articles list items for test automation
  - HX-Trigger: articleStateChanged, feedsChanged on mark-all-read command palette response
  - /api/apps/commands JSON includes appId/pageId fields (inspectable via DevTools or curl)
drill_down_paths:
  - .gsd/milestones/M010/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S04/tasks/T03-SUMMARY.md
duration: ~40m
verification_result: passed
completed_at: 2026-03-17
---

# S04: Workspace contributions + custom renderer

**Wired RSS Reader into the workspace integration layer: right pane "Related Articles" section, custom Article read renderer in object browser, "Mark All as Read" in command palette, and fixed navigate commands to open as dockview tabs instead of leaving the SPA.**

## What Happened

Three tasks, all completed with zero regressions:

**T01 — Manifest + route handlers + templates.** Updated `manifest.yaml` with three new workspace contributions: `rightPane` entry (related-articles, priority 60, targets all types), `objectRenderers` entry (type `urn:sempkm:model:rss-feeds:Article`, read mode), and `mark-all-read` in `commandPalette` (actionType: post). Added two new route handlers in `app.py`: `/_fragments/related-articles` queries articles sharing the same feedSource or bpkm:tags as the focused object (UNION pattern, LIMIT 10, self-exclusion), and `/_fragments/article-read-renderer` fetches article properties using the same SPARQL shape as the reading pane but without fire-and-forget mark-read behavior. Created corresponding templates (`related-articles.html` with `data-article-iri` attributes, `article-read-renderer.html` with markdown rendering and star button). Updated `mark_all_read_route()` to detect command palette context via `HX-Target == "#modal-container"` and return a confirmation div with `rss-success` class instead of sidebar HTML.

**T02 — Navigate command fix (platform-wide).** Enhanced `commands_list()` in `apps.py` to iterate `manifest.ui.pages` for navigate commands — when `page.path == cmd.path`, the JSON response gains `appId` and `pageId` fields. Updated `_loadAppCommandEntries()` in `workspace.js` to check for `cmd.appId` and call `openAppPageTab()` instead of `window.location.href`. This fixes "Open RSS Reader" (and any future app navigate commands) to open as dockview tabs within the workspace SPA.

**T03 — Unit tests.** Added 19 new tests to `test_rss_reader_ui.py`: TestRelatedArticles (7 tests — SPARQL structure, template args, empty/missing IRI, no results, SPARQL error, self-exclusion), TestArticleReadRenderer (9 tests — query, template args, missing/empty IRI, not-found, correct template, star state, body fallback, SPARQL error), TestMarkAllReadContext (3 tests — command palette context, zero-article edge case, reader context). Extended `_make_mock_request()` helper to accept `headers` dict for testing request-header-dependent branching. The 2 navigate enrichment tests were added in T02.

## Verification

All slice-level checks passed:

- `pytest tests/test_rss_reader_ui.py -v` → **62 passed** (43 S03 + 19 S04, zero regressions)
- `pytest tests/test_app_views_commands.py -v` → **15 passed** (13 existing + 2 new, zero regressions)
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` → syntax OK
- `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` → valid YAML
- `objectRenderers[0].type` is `urn:sempkm:model:rss-feeds:Article` (full IRI, under `ui.objectRenderers`)
- Navigate command JSON includes `appId` and `pageId` when path matches an app page (verified by test)
- `rss-error` class returned from Python handlers on SPARQL failure (verified by tests + grep)
- `rss-success` class returned from `mark_all_read_route()` when HX-Target is `#modal-container` (verified by test)
- `openAppPageTab` dispatched in JS for navigate commands with `appId` (3 occurrences in workspace.js)

## Requirements Advanced

- RSS-03 — Custom Article read renderer implemented and tested. `rss:Article` objects opened from the object browser now display the custom reader layout instead of the default SHACL form. (oa:Annotation renderer deferred to M011 with RSS-04.)
- RSS-06 — "Related Articles" right pane section, "Mark All as Read" command palette entry, and "Open RSS Reader" navigate command now functional. "Unread Articles" and "Starred Articles" workspace views were already delivered in S03.

## Requirements Validated

- None fully validated yet — runtime E2E verification deferred to S06.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Plan mentioned "Subscribe to Feed..." command palette entry as part of the demo, but this was already implemented in S02/S03. S04 only added the new contributions (rightPane, objectRenderers, mark-all-read context detection, navigate fix).
- `rss-error` divs are returned from Python handler code (not Jinja templates) — the plan's grep verification step expected them in template files. Tests verify the handler behavior directly.

## Known Limitations

- Related articles fragment queries only by feedSource and bpkm:tags — doesn't discover semantic similarity or shared edges beyond these two predicates.
- Article read renderer doesn't auto-mark articles as read (deliberate — object browser context differs from reader context where users expect that behavior).
- Navigate command enrichment uses exact path equality, not prefix matching. If an app's command path doesn't exactly match a page path in the manifest, it falls through to `window.location.href`.

## Follow-ups

- S06 E2E tests should verify: right pane "Related Articles" appears when viewing an object, custom renderer loads for Article objects, "Mark All as Read" command palette entry works, "Open RSS Reader" opens a dockview tab.

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — Added rightPane, objectRenderers, and mark-all-read commandPalette entries under ui.contributions
- `apps/rss-reader/app.py` — Added BPKM_TAGS constant, RELATED_ARTICLES_SPARQL, related_articles_fragment(), article_read_renderer_fragment(); updated mark_all_read_route() with command palette detection
- `apps/rss-reader/frontend/templates/related-articles.html` — New template for right pane related articles section
- `apps/rss-reader/frontend/templates/article-read-renderer.html` — New template for custom Article read renderer
- `backend/app/browser/apps.py` — Enhanced commands_list() navigate branch with appId/pageId enrichment
- `frontend/static/js/workspace.js` — Updated _loadAppCommandEntries() navigate handler to call openAppPageTab()
- `backend/tests/test_rss_reader_ui.py` — Added 19 new tests (TestRelatedArticles, TestArticleReadRenderer, TestMarkAllReadContext) + headers param on _make_mock_request()
- `backend/tests/test_app_views_commands.py` — Added 2 navigate enrichment tests

## Forward Intelligence

### What the next slice should know
- The manifest now has all workspace contributions wired. S05 (OPML + settings) is independent of S04's work — it adds to the subscribe dialog and settings page, not workspace contributions.
- S06 should test the right pane, custom renderer, command palette entries, and dockview tab opening as part of the E2E lifecycle spec.

### What's fragile
- Command palette context detection relies on `HX-Target == "#modal-container"` — if the command palette's htmx target changes, mark-all-read will return sidebar HTML instead of a confirmation message. The 3 TestMarkAllReadContext tests will catch this.
- Navigate command enrichment uses exact `page.path == cmd.path` matching — if an app's manifest has a page path that doesn't exactly match the command's path, the fix won't fire and the old `window.location.href` behavior returns.

### Authoritative diagnostics
- `pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles or TestArticleReadRenderer or TestMarkAllReadContext"` — isolates all 19 S04-specific tests
- `pytest tests/test_app_views_commands.py -v -k "navigate"` — isolates the 2 navigate enrichment tests
- `curl localhost:8000/api/apps/commands | jq '.[] | select(.appId)'` — verifies navigate enrichment at runtime

### What assumptions changed
- Plan assumed `objectRenderers` would be a top-level manifest key. Actual structure is `ui.objectRenderers[]` — nested under `ui` alongside pages and contributions. The platform's `_get_renderer_override()` reads from the correct path.
