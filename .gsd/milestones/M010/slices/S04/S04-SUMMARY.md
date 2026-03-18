---
id: S04
parent: M010
milestone: M010
provides:
  - Right pane "Related Articles" fragment with UNION SPARQL (feedSource OR shared tags)
  - Custom rss:Article read renderer replacing default SHACL form in object browser
  - Mark-all-read command palette entry with context-aware response (modal vs sidebar)
  - Navigate command enrichment — appId/pageId in JSON response for dockview tab opening
  - 19 new unit tests (56 total in test_rss_reader_ui.py, 17 in test_app_views_commands.py)
requires:
  - slice: S02
    provides: FeedService subscription management, article data in triplestore
  - slice: S03
    provides: Reader UI template patterns, reading pane SPARQL structure, star-button template
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
  - Related articles use UNION SPARQL — same feedSource OR shared bpkm:tags (D183)
  - Command palette context detected via HX-Target header matching #modal-container (D183)
  - Navigate enrichment — exact path matching adds appId/pageId to JSON (D183)
patterns_established:
  - Right pane fragments receive ?iri param and return complete HTML including empty/error states
  - Command palette POST handlers detect context via HX-Target header for response branching
  - commands_list() enriches navigate entries with appId/pageId when path matches app page; JS branches on cmd.appId
observability_surfaces:
  - SPARQL errors in related-articles and renderer handlers logged as warnings, rendered as <div class="rss-error">
  - data-article-iri attributes on related article items for test automation
  - Navigate command JSON in /api/apps/commands includes appId/pageId fields (inspectable via DevTools/curl)
  - HX-Trigger headers (articleStateChanged, feedsChanged) on mark-all-read command palette response
drill_down_paths:
  - .gsd/milestones/M010/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S04/tasks/T03-SUMMARY.md
duration: 33m
verification_result: passed
completed_at: 2026-03-18
---

# S04: Workspace contributions + custom renderer

**Wired RSS Reader into the workspace integration layer: right pane "Related Articles" section, custom Article read renderer in the object browser, mark-all-read command palette entry, and navigate-to-dockview-tab fix for all app page commands**

## What Happened

Three tasks completed the slice in ~33 minutes total, all passing verification on first attempt.

**T01 (15m)** added the three workspace contributions to the RSS Reader manifest and implemented their route handlers. The `rightPane` contribution registers a "Related Articles" section that queries articles sharing the same `feedSource` or `bpkm:tags` as the focused object using a UNION SPARQL pattern, limited to 10 results. The `objectRenderers` entry declares `urn:sempkm:model:rss-feeds:Article` as the type for custom rendering, with a read-mode fragment that reuses the reading pane SPARQL pattern but omits the fire-and-forget mark-read trigger (since it renders in the object browser, not the reader UI). The `mark-all-read` command palette entry uses `actionType: "post"` — the handler detects command palette invocation via `HX-Target: #modal-container` and returns a confirmation message with both `articleStateChanged` and `feedsChanged` HX-Trigger headers, while preserving the existing sidebar-refresh behavior for the reader UI. Two HTML templates were created: `related-articles.html` with clickable items dispatching `sempkm:open-object` events, and `article-read-renderer.html` with markdown rendering attributes and star button.

**T02 (10m)** fixed the "Open RSS Reader" command (and all future app navigate commands) to stay within the workspace SPA. In `commands_list()`, after building a navigate command entry, the code now iterates `manifest.ui.pages` to check if the command path matches any page. On match, `appId` and `pageId` are added to the JSON. In `_loadAppCommandEntries()`, the navigate branch checks `cmd.appId` — if present, it calls `openAppPageTab()` for a dockview tab; if absent, it falls through to the original `window.location.href`. Two new tests verified the enrichment logic.

**T03 (8m)** added 19 unit tests across three test classes. `TestRelatedArticles` (7 tests) covers SPARQL UNION structure, self-exclusion, empty/error states. `TestArticleReadRenderer` (9 tests) covers query structure, template rendering, body fallback to description, star state, empty/error states. `TestMarkAllReadContext` (3 tests) covers the HX-Target branching between command palette and reader UI contexts.

## Verification

All slice-level checks pass:

| Check | Result |
|-------|--------|
| `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | ✅ pass |
| `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` | ✅ pass |
| `pytest tests/test_rss_reader_ui.py -v` — 56 passed (37 S03 + 19 S04) | ✅ pass |
| `pytest tests/test_app_views_commands.py -v` — 17 passed (15 existing + 2 new) | ✅ pass |
| `objectRenderers[0].type` is `urn:sempkm:model:rss-feeds:Article` | ✅ pass |
| `rightPane` has `related-articles` fragment | ✅ pass |
| `commandPalette` has `mark-all-read` with `actionType: "post"` | ✅ pass |
| `rss-error` in related-articles and article-read-renderer handlers | ✅ pass |
| `rss-success` class in mark-all-read when HX-Target is `#modal-container` | ✅ pass |
| `openAppPageTab` wired in JS navigate branch | ✅ pass |

## Requirements Advanced

- **RSS-06** — "Related Articles" right pane section and "Mark All as Read" command palette entry now functional. Workspace views (Unread, Starred) were already delivered in S03. "Open RSS Reader" navigate command now opens dockview tab correctly.
- **RSS-03** — Custom `rss:Article` read renderer registered in manifest and implemented as fragment handler. Opening an Article from the object browser will show the clean reader layout instead of the default SHACL form.
- **APP-08** — Right pane section contribution proven end-to-end with real RSS Reader manifest + handler. Command palette POST action proven with context-aware response.
- **APP-09** — Object renderer override declared in manifest for `urn:sempkm:model:rss-feeds:Article` with read-mode custom fragment.

## Requirements Validated

- none (RSS-03, RSS-06, APP-08, APP-09 remain active — full validation requires S06 E2E tests with live Docker stack)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Plan estimated 43 existing S03 tests; actual count was 37. The plan likely counted from a different branch state. All 37 pass with zero regressions.
- `test_app_views_commands.py` didn't exist in the worktree — copied from main repo in T02. T03 confirmed no duplicates needed since T02 already added the navigate enrichment tests.
- Manifest structure uses `ui.contributions.rightPane` (not `ui.rightPane` as some references implied). This matches the platform's manifest schema correctly.

## Known Limitations

- Related articles SPARQL uses a simple UNION strategy (same feed OR shared tags). No semantic similarity or graph traversal — this is intentional for v1.
- Article read renderer omits fire-and-forget mark-read. Articles opened via the object browser won't auto-mark as read (by design — the mark-read trigger belongs in the reader UI flow).
- Navigate enrichment only works for exact path matches. Deep-link paths with parameters (e.g., `/reader?feed=xyz`) won't match and will fall through to `window.location.href`.

## Follow-ups

- S06 E2E tests should verify: (1) right pane "Related Articles" appears when viewing any object, (2) opening an rss:Article shows custom renderer, (3) "Mark All as Read" works from command palette, (4) "Open RSS Reader" opens dockview tab.

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — Added `rightPane`, `objectRenderers`, and `mark-all-read` command palette entry
- `apps/rss-reader/app.py` — Added `related_articles_fragment()` and `article_read_renderer_fragment()` route handlers; updated `mark_all_read_fragment()` with command palette context detection
- `apps/rss-reader/frontend/templates/related-articles.html` — New template for right pane related articles
- `apps/rss-reader/frontend/templates/article-read-renderer.html` — New template for custom Article read renderer
- `backend/app/browser/apps.py` — Enhanced `commands_list()` with appId/pageId enrichment for navigate commands
- `frontend/static/js/workspace.js` — Updated navigate handler to call `openAppPageTab()` when `cmd.appId` present
- `backend/tests/test_rss_reader_ui.py` — Added 19 new tests (TestRelatedArticles, TestArticleReadRenderer, TestMarkAllReadContext)
- `backend/tests/test_app_views_commands.py` — Copied from main repo, added 2 navigate enrichment tests

## Forward Intelligence

### What the next slice should know
- The manifest now has all workspace contributions declared. S05 (OPML import + settings) can add its own settings page as another `ui.pages` entry without touching the contributions block.
- The `openAppPageTab()` pattern in workspace.js is now the standard way to handle navigate commands for app pages. S06 E2E tests should verify this opens a dockview tab (no URL change).
- `mark_all_read_fragment()` has dual-path behavior: HX-Target `#modal-container` → confirmation message; no HX-Target → sidebar refresh. E2E tests should test both paths.

### What's fragile
- Navigate enrichment depends on exact `page.path == cmd.path` matching — if an app manifest defines a navigate command with a path that includes query parameters or doesn't exactly match a page path, the enrichment won't fire and the command will do a full-page navigation instead of opening a dockview tab.
- Related articles SPARQL assumes `bpkm:tags` is the tag predicate. If a model uses `schema:keywords` instead, tag-based matching won't find related articles.

### Authoritative diagnostics
- `pytest tests/test_rss_reader_ui.py -v -k "TestRelatedArticles or TestArticleReadRenderer or TestMarkAllReadContext"` — isolates all S04 tests (19 tests, ~0.3s)
- `curl /api/apps/commands | jq '.[] | select(.actionType=="navigate")'` — shows appId/pageId enrichment on live stack
- Browser DevTools Network tab filtering for `related-articles` and `article-read-renderer` shows fragment requests with ?iri= parameters

### What assumptions changed
- Plan assumed 43 existing S03 tests — actual count is 37. Not a correctness issue, just a count discrepancy from different branch states.
- Plan assumed `test_app_views_commands.py` existed in worktree — it didn't and had to be copied from main repo.
