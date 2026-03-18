---
id: S03
parent: M010
milestone: M010
provides:
  - Split-pane RSS reader UI with feed sidebar, article list, and reading pane (CSS Grid layout)
  - 8 htmx fragment route handlers (feed-sidebar, article-list, article-reading-pane, toggle-star, toggle-read, mark-all-read, unsubscribe, workspace views)
  - Platform proxy query-string forwarding fix (AppProxy.forward() was dropping ?params)
  - Star toggle and mark-read via object.patch with HX-Trigger response headers for UI refresh
  - Unread Articles and Starred Articles workspace view stubs with filtered article lists
  - reader.js with htmx:afterSwap markdown rendering, Lucide icon refresh, j/k keyboard nav
  - Complete reader CSS (~560 lines) scoped under .rss-reader using theme variables
requires:
  - slice: S01
    provides: Installed rss-feeds model with type IRIs, working app process on UDS, ctx.render_template()
  - slice: S02
    provides: FeedService with subscribe/unsubscribe, feed_service import in app.py
affects:
  - S04 (workspace contributions + custom renderer — consumes template patterns, reader.css/js, fragment endpoints)
  - S06 (E2E tests — consumes stable CSS selectors and data attributes for assertions)
key_files:
  - backend/app/apps/proxy.py
  - backend/tests/test_app_proxy.py
  - backend/tests/test_rss_reader_ui.py
  - apps/rss-reader/app.py
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/frontend/templates/reader.html
  - apps/rss-reader/frontend/templates/feed-sidebar.html
  - apps/rss-reader/frontend/templates/article-list.html
  - apps/rss-reader/frontend/templates/article-reading-pane.html
  - apps/rss-reader/frontend/templates/star-button.html
  - apps/rss-reader/frontend/templates/unread-view.html
  - apps/rss-reader/frontend/templates/starred-view.html
  - apps/rss-reader/frontend/static/styles.css
  - apps/rss-reader/frontend/static/reader.js
key_decisions:
  - "Star button uses inline SVG (Lucide star polygon paths) for immediate rendering without Lucide JS dependency"
  - "Sidebar re-rendering in mark-all-read and unsubscribe handlers uses inline SPARQL+binding parse rather than calling feed_sidebar_fragment() to avoid request object coupling"
  - "IRI sanitization via angle-bracket/backslash stripping — shared _sanitize_iri() helper across all action handlers"
patterns_established:
  - "SPARQL binding → Python dict normalization: extract .get('field', {}).get('value', default), cast types, pass clean dicts to templates"
  - "Filter tab pattern: hx-get with preserved active_feed and active_filter as query params for stateless filter switching"
  - "Fire-and-forget mark-read: hidden div with hx-post + hx-trigger=load + hx-swap=none auto-marks articles read on open"
  - "reader.js IIFE with htmx:afterSwap scoped to #rss-reading-pane for markdown rendering"
  - "CSS scoped entirely under .rss-reader to prevent workspace style conflicts"
observability_surfaces:
  - "HX-Trigger: articleStateChanged — emitted after star/read toggles for UI refresh"
  - "HX-Trigger: feedsChanged — emitted after unsubscribe and mark-all-read for sidebar refresh"
  - "data-feed-iri, data-article-iri, data-starred, data-read attributes on DOM elements for testing"
  - "<div class='rss-error'> fragments returned on SPARQL/patch failures with descriptive error messages"
  - "feedsChanged custom event on document.body triggers sidebar refresh"
drill_down_paths:
  - .gsd/milestones/M010/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T04-SUMMARY.md
duration: 47m
verification_result: passed
completed_at: 2026-03-18
---

# S03: Reader UI (split-pane layout)

**Split-pane RSS reader with feed sidebar, article list, reading pane, star/read toggles, mark-all-read, unsubscribe — all driven by htmx fragment swaps with 56 unit tests and zero S01/S02 regressions**

## What Happened

This slice built the complete reader UI for the RSS Reader app across 4 tasks (T03 absorbed T04's test scope).

**T01 — Platform fix + shell + CSS + JS:** Fixed a platform-level bug in `AppProxy.forward()` where query strings were silently dropped from all proxied app requests — a blocker for any parametrized fragment endpoint. Built the three-panel `reader.html` shell using CSS Grid (240px sidebar / 320px article list / 1fr reading pane) with htmx `hx-trigger="load"` for lazy panel population. Created `styles.css` (~560 lines) scoped entirely under `.rss-reader` using `var(--color-*)` theme tokens — covers feed items, article items with read/unread states, star button states, reading pane typography, filter tabs, empty states, and error indicators. Created `reader.js` as an IIFE with `htmx:afterSwap` markdown rendering (scoped to `#rss-reading-pane`), Lucide icon refresh, and `j`/`k` keyboard article navigation.

**T02 — Feed sidebar + article list:** Added `/_fragments/feed-sidebar` GET route with SPARQL `GROUP BY + COUNT` for unread counts per subscription, and `/_fragments/article-list` GET route with dynamic SPARQL built by `_build_article_list_sparql()` supporting `feed_iri` and `filter` (all/unread/starred) query params. Created `feed-sidebar.html` (feed list with unread badges, error indicator dots, subscribe button) and `article-list.html` (filter tab bar preserving context, article items with title/source/date/read state). Established the SPARQL binding → Python dict normalization pattern used by all subsequent handlers.

**T03 — Reading pane + actions + workspace views + tests:** Added 5 action route handlers: reading pane (SPARQL article query with markdown body in `<script type="text/plain">` for client-side rendering, fire-and-forget mark-read via hidden hx-post div), star toggle (query current → flip → patch → return updated button), read toggle (mark-read-on-open default + explicit toggle mode), mark-all-read (batch SPARQL query + per-article patch with best-effort error handling), unsubscribe (calls `feed_service.unsubscribe()` for soft-delete). Created `star-button.html` with inline SVG star paths for framework-independent rendering. Replaced `unread-view.html` and `starred-view.html` stubs with htmx containers loading `/_fragments/article-list?filter=unread|starred`. Wrote 56 unit tests covering all handlers, edge cases, templates, and workspace views.

**T04 — Tests (folded into T03):** All 56 unit tests were written alongside the route handlers for immediate verification rather than deferred to a separate pass.

## Verification

| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | `pytest tests/test_rss_reader_ui.py -v` — ≥20 tests | ✅ 56/56 pass | 0.38s, 8 test classes |
| 2 | `pytest tests/test_app_proxy.py -v` — proxy tests pass | ✅ 3/3 pass | query-string, no-query, token injection |
| 3 | `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — S01/S02 regression | ✅ 88/88 pass | 0.34s, zero regressions |
| 4 | `ast.parse(app.py)` — syntax OK | ✅ pass | 1418 lines, no syntax errors |
| 5 | `manifest.yaml` includes `reader.js` in frontend.js | ✅ pass | grep confirms |
| 6 | HX-Trigger headers present | ✅ confirmed | articleStateChanged + feedsChanged in app.py |
| 7 | Data attributes in templates | ✅ confirmed | data-feed-iri, data-article-iri, data-starred, data-read |
| 8 | Error fragments present | ✅ confirmed | `<div class="rss-error">` in route handlers and templates |
| 9 | Proxy query-string fix | ✅ confirmed | `request.url.query` appended in proxy.py line 64-65 |

## Requirements Advanced

- **RSS-02** (Reader UI with split-pane layout) — All UI components built: feed sidebar with unread counts, article list with filter tabs, reading pane with markdown rendering, star toggle, mark read/unread. Waiting on S04 for workspace contributions and S06 for E2E to reach validated.

## Requirements Validated

- None (RSS-02 needs live Docker verification + E2E coverage in S06 to be validated)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **T04 folded into T03** — The test task was completed alongside route handler development rather than as a separate execution unit. This produced 56 tests instead of the planned ≥20, exceeding the target.
- **Additional route handlers beyond S03 plan** — The actual app.py grew to 1418 lines, including some route handlers (related-articles, article-read-renderer, mark-all-read context variants) that overlap with S04 scope. These were tested in T03's expanded test suite.

## Known Limitations

- **No live Docker verification** — All testing is unit-level with mocked SDK contexts. The UI has not been verified running against a real triplestore. Typography, layout responsiveness, and htmx swap behavior need UAT.
- **Active feed highlight is client-side** — The feed sidebar template doesn't receive the current active_feed from the route handler on initial load (defaults to None). Active-feed highlighting for specific feeds relies on client-side JS in reader.js.
- **Mark-all-read is sequential** — Each article is patched individually in a loop. For feeds with hundreds of unread articles, this could be slow. A bulk patch SDK method would be more efficient.

## Follow-ups

- S04 consumes the template patterns and fragment endpoints for workspace contributions and custom renderer
- S06 uses data attributes (data-feed-iri, data-article-iri, data-starred, data-read) for E2E Playwright selectors
- Typography UAT needed on real articles with varying content length and formatting

## Files Created/Modified

- `backend/app/apps/proxy.py` — 2-line query-string forwarding fix (lines 64-65)
- `backend/tests/test_app_proxy.py` — 3 tests for proxy query-string behavior
- `backend/tests/test_rss_reader_ui.py` — 56 tests across 8 test classes
- `apps/rss-reader/app.py` — 8+ route handlers, _format_date, _sanitize_iri, _build_article_list_sparql
- `apps/rss-reader/manifest.yaml` — reader.js added to frontend.js array
- `apps/rss-reader/frontend/templates/reader.html` — Three-panel CSS Grid shell with htmx lazy-load triggers
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — Feed list with unread badges and error indicators
- `apps/rss-reader/frontend/templates/article-list.html` — Filter tabs and article items with read/unread state
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — Article header + markdown body + mark-read trigger
- `apps/rss-reader/frontend/templates/star-button.html` — Inline SVG star with htmx outerHTML swap
- `apps/rss-reader/frontend/templates/unread-view.html` — Workspace view loading filtered article list
- `apps/rss-reader/frontend/templates/starred-view.html` — Workspace view loading filtered article list
- `apps/rss-reader/frontend/static/styles.css` — ~560 lines scoped under .rss-reader
- `apps/rss-reader/frontend/static/reader.js` — IIFE: markdown rendering, Lucide refresh, j/k keyboard nav

## Forward Intelligence

### What the next slice should know
- The reader UI has stable CSS selectors and data attributes ready for E2E testing: `[data-feed-iri]`, `[data-article-iri]`, `[data-starred]`, `[data-read]`, `.rss-filter-btn`, `.rss-empty-state`
- HX-Trigger headers (`articleStateChanged`, `feedsChanged`) are the primary UI refresh mechanism — S04 workspace contributions should listen for these events
- The `_build_article_list_sparql()` function already supports `filter` param (all/unread/starred) — S04 workspace views can reuse this endpoint directly
- S03 already replaced the workspace view stubs (unread-view.html, starred-view.html) — S04 may need to enhance these rather than create new ones

### What's fragile
- **SPARQL binding normalization** — Every route handler manually extracts and casts SPARQL binding values. A shared helper would reduce duplication but doesn't exist yet. New handlers must follow the `.get('field', {}).get('value', default)` pattern carefully.
- **Inline SVG in star-button.html** — The star icon uses hardcoded SVG path data from Lucide. If Lucide updates the star icon shape, it won't auto-update. This is intentional (no JS dependency) but worth noting.

### Authoritative diagnostics
- `pytest tests/test_rss_reader_ui.py -v` — 56 tests verify all route handler logic, SPARQL queries, edge cases, and template existence. If a handler breaks, the test class name identifies which route.
- `grep "HX-Trigger" apps/rss-reader/app.py` — Shows all UI refresh trigger points. Missing triggers = stale UI after actions.
- `document.querySelectorAll('[data-article-iri]')` in browser console — Lists all rendered articles with their IRIs.

### What assumptions changed
- **Test count exceeded plan** — Plan required ≥20 tests; actual is 56. The extra coverage comes from testing additional routes that were built alongside S03's core handlers.
- **T04 was not a separate execution unit** — Tests were written in T03, making T04 a no-op verification step rather than a separate development phase.
