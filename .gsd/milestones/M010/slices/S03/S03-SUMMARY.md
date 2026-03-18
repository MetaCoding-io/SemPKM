---
id: S03
parent: M010
milestone: M010
provides:
  - "Split-pane RSS Reader UI with feed sidebar, article list, and reading pane via htmx fragments"
  - "8 route handlers in app.py replacing stubs (feed-sidebar, article-list, reading-pane, toggle-star, toggle-read, mark-all-read, unsubscribe, subscribe-dialog)"
  - "CSS Grid layout (240px | 320px | 1fr) scoped under .rss-reader with theme tokens"
  - "reader.js IIFE with markdown rendering, Lucide refresh, j/k keyboard nav"
  - "Star toggle, mark-as-read on open, mark-all-read, unsubscribe actions"
  - "Unread Articles and Starred Articles workspace views with preset filters"
  - "Platform proxy query-string forwarding fix"
  - "37 unit tests covering all route handlers and edge cases"
requires:
  - slice: S01
    provides: "Installed rss-feeds model with type IRIs, working app process on UDS, ctx.render_template()"
  - slice: S02
    provides: "subscribe/unsubscribe functions from feed_service, SUBSCRIPTIONS_WITH_STATE_SPARQL"
affects:
  - S04 (reader UI template patterns, reader.css/reader.js, fragment endpoints)
  - S06 (complete reader UI with stable CSS selectors for E2E testing)
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
  - "IRI sanitization via angle-bracket/backslash stripping to prevent SPARQL injection"
  - "Star button uses inline SVG for immediate rendering without Lucide JS dependency"
  - "Fire-and-forget mark-read via hidden div with hx-post + hx-trigger=load + hx-swap=none"
  - "Sidebar re-rendering in mark-all-read/unsubscribe uses inline SPARQL to avoid request object coupling"
patterns_established:
  - "reader.js htmx:afterSwap scoped to #rss-reading-pane for markdown rendering"
  - "CSS scoped under .rss-reader with var(--color-*) theme tokens"
  - "SPARQL binding → Python dict normalization pattern"
  - "Filter tab pattern with preserved active_feed and active_filter query params"
  - "_sanitize_iri() shared across all action handlers"
  - "HX-Trigger headers: articleStateChanged for star/read, feedsChanged for unsubscribe"
observability_surfaces:
  - "data-feed-iri, data-article-iri, data-starred, data-read attributes on HTML elements"
  - "HX-Trigger response headers (articleStateChanged, feedsChanged)"
  - "<div class='rss-error'> fragments on SPARQL/patch failures"
  - ".rss-empty-state divs for empty feeds/articles/selection"
drill_down_paths:
  - .gsd/milestones/M010/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M010/slices/S03/tasks/T04-SUMMARY.md
duration: ~60m across 4 tasks
verification_result: passed
completed_at: 2026-03-18
---

# S03: Reader UI (split-pane layout)

**Functional split-pane RSS reader with feed sidebar, article list, reading pane, star/read toggles, mark-all-read, unsubscribe, workspace views, and 37 unit tests — all driven by htmx fragment swaps against SPARQL data**

## What Happened

**T01** fixed a platform bug in `AppProxy.forward()` where query strings were silently dropped from proxied app requests — blocking all parametrized fragment requests. Built the reader.html three-panel shell using CSS Grid with htmx lazy-load triggers, complete styles.css (~350 lines) scoped under `.rss-reader`, and reader.js as an IIFE with markdown rendering, Lucide icon refresh, and j/k keyboard navigation.

**T02** added the two navigation route handlers. `feed_sidebar_fragment` runs a SPARQL GROUP BY/COUNT query for subscriptions with unread counts. `article_list_fragment` builds dynamic SPARQL via `_build_article_list_sparql()` with optional feed_iri and filter params. Both normalize SPARQL bindings into clean Python dicts with properly typed fields before template rendering. Created feed-sidebar.html (unread badges, error indicators, subscribe button) and article-list.html (filter tabs, read/unread visual state).

**T03** built the reading pane and all 5 action handlers. Reading pane queries a single article, determines body content (body → description → None fallback), generates a stable md_id for markdown elements, and fires mark-read via a hidden div with `hx-post + hx-trigger="load" + hx-swap="none"`. Star toggle flips isStarred via object.patch and returns inline SVG star button. Mark-all-read patches each unread article with best-effort error handling. Unsubscribe calls feed_service.unsubscribe() for soft-delete. Workspace view stubs replaced with htmx-loading containers fetching filtered article lists.

**T04** was folded into T03 — 37 unit tests written alongside route handlers using mocked SDK clients with Starlette TestClient.

## Verification

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | `pytest tests/test_rss_reader_ui.py -v` — ≥20 tests | ✅ 37/37 pass | 0.33s |
| 2 | `pytest tests/test_app_proxy.py -v` — proxy tests | ✅ 3/3 pass | 0.20s |
| 3 | `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — S01/S02 regression | ✅ 88/88 pass | 0.35s |
| 4 | `ast.parse(app.py)` — syntax OK | ✅ pass | |
| 5 | `manifest.yaml` includes `reader.js` | ✅ pass | grep verified |
| 6 | HX-Trigger headers verified in unit tests | ✅ pass | articleStateChanged + feedsChanged |

## Requirements Advanced

- **RSS-02** — Reader UI split-pane layout implemented with all controls. Needs Docker UAT for full validation.

## Requirements Validated

None — RSS-02 requires live Docker stack UAT.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- T04 folded into T03 for faster iteration — tests written alongside route handlers.

## Known Limitations

- No live Docker stack verification — all tests use mocked SDK clients.
- Mark-all-read is sequential (individual patches, not bulk EventStore batch).
- Date formatting is basic ("Mar 17, 2026"), no relative dates.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/apps/proxy.py` — Query-string forwarding fix
- `backend/tests/test_app_proxy.py` — 3 proxy tests
- `backend/tests/test_rss_reader_ui.py` — 37 tests across 6 classes
- `apps/rss-reader/app.py` — 8 route handlers + helpers
- `apps/rss-reader/manifest.yaml` — reader.js in frontend.js
- `apps/rss-reader/frontend/templates/reader.html` — Three-panel shell
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — Feed list with badges
- `apps/rss-reader/frontend/templates/article-list.html` — Filter tabs + articles
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — Article display + mark-read
- `apps/rss-reader/frontend/templates/star-button.html` — Inline SVG star
- `apps/rss-reader/frontend/templates/unread-view.html` — Filtered article container
- `apps/rss-reader/frontend/templates/starred-view.html` — Filtered article container
- `apps/rss-reader/frontend/static/styles.css` — Complete reader CSS
- `apps/rss-reader/frontend/static/reader.js` — Markdown/Lucide/keyboard IIFE

## Forward Intelligence

### What the next slice should know
- S04: article-list.html already supports `filter=unread|starred` — workspace views reuse the same endpoint.
- S04: reading pane uses `renderMarkdownBody()` from platform — custom Article renderer should follow same pattern.
- S04: reader.js listens for `feedsChanged` and `articleStateChanged` events — command palette actions should dispatch these.
- S06: All HTML fragments have `data-feed-iri`, `data-article-iri`, `data-starred`, `data-read` attributes for E2E assertions.

### What's fragile
- Feed sidebar SPARQL GROUP BY/COUNT tested only with mocked results, not real RDF4J.
- Markdown rendering chain: reader.js scoped to `#rss-reading-pane` looking for `md-source-*` elements — template changes break silently.

### Authoritative diagnostics
- `pytest tests/test_rss_reader_ui.py -v` — 37 tests are ground truth for route handler behavior.
- Browser DevTools Network tab — htmx fragments at `/_fragments/*`, check HX-Trigger headers.

### What assumptions changed
- T04 as separate task was unnecessary — tests written alongside handlers in T03.
