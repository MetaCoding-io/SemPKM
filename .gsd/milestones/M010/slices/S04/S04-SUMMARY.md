---
id: S04
parent: M010
milestone: M010
provides:
  - Right pane "Related Articles" fragment with UNION SPARQL (same feedSource OR shared tags)
  - Custom rss:Article read renderer replacing default SHACL form in object browser
  - Mark-all-read command palette entry with HX-Target context detection
  - Navigate command enrichment with appId/pageId for SPA dockview tab opening
  - 19 new unit tests (56 total in test_rss_reader_ui.py, 17 total in test_app_views_commands.py)
requires:
  - slice: S02
    provides: FeedService patterns, article/feed data in triplestore, SPARQL query patterns
  - slice: S03
    provides: Reader UI template patterns, _sparql_bool()/_format_date()/_sparql_int() helpers, star-button template
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
  - D183: Navigate command enrichment — commands_list() iterates manifest.ui.pages comparing page.path == cmd.path; on match adds appId/pageId to JSON response. JS handler branches on cmd.appId to call openAppPageTab() instead of window.location.href
  - Related articles use UNION SPARQL: same feedSource OR shared bpkm:tags, self-excluded via FILTER
  - Article read renderer omits fire-and-forget mark-read — object browser context is read-only browsing, not reader workflow
  - Command palette context detected via HX-Target header matching #modal-container
patterns_established:
  - Right pane fragment pattern: receives ?iri param, queries triplestore, returns complete HTML including empty/error states
  - Command palette POST handlers detect context via HX-Target header to branch between command palette (confirmation message) and reader UI (sidebar refresh) responses
  - Navigate command enrichment: platform-wide pattern for commands_list() to add appId/pageId when path matches an app page, enabling SPA tab opening for all future apps
observability_surfaces:
  - SPARQL errors in related-articles and article-read-renderer logged as warnings, rendered as <div class="rss-error"> fragments
  - data-article-iri attributes on related article items for test automation targeting
  - HX-Trigger headers (articleStateChanged, feedsChanged) on mark-all-read command palette response
  - Navigate command JSON at /api/apps/commands includes appId/pageId fields when path matches an app page (inspectable via DevTools or curl)
drill_down_paths:
  - .gsd/milestones/M010/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S04/tasks/T03-SUMMARY.md
duration: 33m
verification_result: passed
completed_at: 2026-03-18
---

# S04: Workspace contributions + custom renderer

**Wired RSS Reader into workspace integration layer: right pane "Related Articles" section, custom rss:Article read renderer, mark-all-read command palette entry with context detection, and navigate command SPA fix — all with 19 new unit tests**

## What Happened

Three tasks delivered the full workspace contribution layer for the RSS Reader app:

**T01 (manifest + route handlers)** added three workspace contributions to `manifest.yaml`: a `rightPane` "Related Articles" section, an `objectRenderers` entry for `urn:sempkm:model:rss-feeds:Article` with custom read renderer, and a `mark-all-read` command palette entry with `actionType: "post"`. Two new route handlers were added to `app.py`:

- `/_fragments/related-articles` queries articles sharing the same feedSource or bpkm:tags as the focused object using a UNION SPARQL pattern, limited to 10 results ordered by creation date descending, self-excluded via FILTER.
- `/_fragments/article-read-renderer` reuses the reading pane SPARQL pattern but omits the fire-and-forget mark-read trigger since the object browser is a browsing context, not the reader workflow.

The existing `mark_all_read_fragment()` was updated to detect command palette context via `HX-Target: #modal-container` header — returns a `<div class="rss-success">` confirmation message with both `articleStateChanged` and `feedsChanged` HX-Trigger headers when called from the command palette, while preserving the existing sidebar-refresh behavior for the reader UI.

**T02 (navigate fix)** solved the "Open RSS Reader" command palette entry navigating away from the workspace SPA. Two surgical edits: in `commands_list()` (apps.py), navigate commands whose path matches an app page now include `appId` and `pageId` in the JSON response. In `_loadAppCommandEntries()` (workspace.js), the navigate handler checks `cmd.appId` and calls `openAppPageTab()` when present, falling back to `window.location.href` for non-app paths. This is a platform-wide fix — all future apps with navigate commands benefit automatically.

**T03 (unit tests)** added 19 tests across three new test classes: TestRelatedArticles (7 tests covering UNION SPARQL structure, self-exclusion, empty/error states), TestArticleReadRenderer (9 tests covering query, template, body fallback, star state, empty/error states), and TestMarkAllReadContext (3 tests covering command palette vs reader UI context branching). Two navigate enrichment tests were already added by T02.

## Verification

- `pytest tests/test_rss_reader_ui.py -v` — **56 passed** (37 existing S03 + 19 new S04), 0.36s
- `pytest tests/test_app_views_commands.py -v` — **17 passed** (15 existing + 2 new navigate tests), 0.31s
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` — valid YAML
- `objectRenderers[0].type` is the full IRI `urn:sempkm:model:rss-feeds:Article` in manifest
- Navigate command JSON includes `appId` and `pageId` when path matches an app page
- `rss-error` in route handlers for related-articles (line 1309) and article-read-renderer (line 1370) confirms error-state HTML is rendered on SPARQL failure
- `rss-success` class in mark-all-read when HX-Target is `#modal-container` (line 1062)
- `openAppPageTab` wired in navigate branch of `_loadAppCommandEntries` in workspace.js

## Requirements Advanced

- RSS-06 — "Related Articles" right pane section, "Mark All as Read" command palette entry now functional. "Unread Articles" and "Starred Articles" workspace views were already shipped in S03. Only remaining workspace contribution gap: "Subscribe to Feed..." dialog (already in manifest, handler exists from S01)
- RSS-03 — Custom `rss:Article` read renderer replaces default SHACL form when opening an article from the object browser. `oa:Annotation` renderer deferred to M011 alongside RSS-04.
- APP-08 — Right pane sections (Related Articles) now work alongside Relations/Lint for app-contributed content. Command palette entries registered with ninja-keys via app manifest.
- APP-09 — Object renderer override for Article type via objectRenderers manifest declaration. Platform dispatches to app fragment instead of default SHACL form.

## Requirements Validated

- None moved to validated — full validation requires S06 E2E tests proving end-to-end runtime behavior

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Plan estimated 43 existing S03 tests; actual count was 37. The plan likely counted from a different branch state. All 37 pass with zero regressions.
- Navigate enrichment tests were added in T02 (not T03 as planned), since they naturally belong with the implementation. T03 verified they exist and pass — no duplicates added.
- `rss-error` class appears in route handler Python code (HTMLResponse strings), not in the Jinja2 templates. The templates render the happy path; error states are returned directly from the route handler before reaching templates. The plan's grep check targets were slightly off but the functionality is correct.

## Known Limitations

- Related Articles right pane queries the triplestore directly — no caching. High-frequency object switching could generate many SPARQL queries.
- Article read renderer does not mark articles as read when viewed from the object browser. This is intentional (browsing context vs reader workflow) but may surprise users who expect consistent behavior.
- "Subscribe to Feed..." command palette dialog handler exists from S01 but was not the focus of S04. It works but isn't tested in S04's scope.

## Follow-ups

- S06 should add E2E tests for: opening an Article from object browser shows custom renderer (not SHACL form), right pane shows Related Articles when viewing any object, "Mark All as Read" command palette entry works, "Open RSS Reader" opens as dockview tab (not full navigation).

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — Added `rightPane`, `objectRenderers`, and `mark-all-read` command palette entry under `ui.contributions`
- `apps/rss-reader/app.py` — Added `related_articles_fragment()` and `article_read_renderer_fragment()` route handlers; updated `mark_all_read_fragment()` with command palette context detection
- `apps/rss-reader/frontend/templates/related-articles.html` — New template for right pane related articles with `data-article-iri` attributes and `sempkm:open-object` custom events
- `apps/rss-reader/frontend/templates/article-read-renderer.html` — New template for custom Article read renderer with markdown rendering support and star button
- `backend/app/browser/apps.py` — Enhanced `commands_list()` to add `appId`/`pageId` for navigate commands matching app pages
- `frontend/static/js/workspace.js` — Updated navigate handler in `_loadAppCommandEntries()` to call `openAppPageTab()` when `cmd.appId` present
- `backend/tests/test_rss_reader_ui.py` — Added 3 test classes (19 tests): TestRelatedArticles, TestArticleReadRenderer, TestMarkAllReadContext
- `backend/tests/test_app_views_commands.py` — Added 2 navigate enrichment tests + AppPage import

## Forward Intelligence

### What the next slice should know
- S04 did not write user guide docs or E2E tests — those are explicitly deferred to S06 per the milestone roadmap
- The `ui.contributions` key in manifest.yaml nests rightPane/views/commandPalette under `contributions`, while `objectRenderers` is at the `ui` level directly. The platform reads both paths — be aware of this when writing E2E assertions
- The navigate command enrichment (appId/pageId) is a platform-wide fix in apps.py, not RSS-specific. E2E tests should verify it works for any app with navigate commands.

### What's fragile
- The command palette context detection relies on `HX-Target: #modal-container` header — if the platform changes how it calls command palette POST endpoints, the context branching will break silently (returning sidebar HTML instead of confirmation message)
- Related Articles UNION SPARQL has no index optimization — performance depends on triplestore query planning for large article sets

### Authoritative diagnostics
- `pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles or TestArticleReadRenderer or TestMarkAllReadContext"` — isolates all S04-specific tests (19 tests)
- `curl /api/apps/commands | jq '.[] | select(.actionType=="navigate")'` — confirms navigate entries have appId/pageId fields

### What assumptions changed
- Plan assumed 43 existing tests from S03; actual was 37. No functional impact — all pass with zero regressions.
- Plan expected `rss-error` class to appear in HTML templates; it's in Python route handler code instead. Same behavior, different location.
