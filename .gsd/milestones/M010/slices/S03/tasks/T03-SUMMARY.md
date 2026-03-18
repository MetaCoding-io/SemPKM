---
id: T03
parent: S03
milestone: M010
provides:
  - "/_fragments/article-reading-pane GET route with SPARQL article query, markdown body, and fire-and-forget mark-read"
  - "/_fragments/toggle-star POST route flipping isStarred via object.patch"
  - "/_fragments/toggle-read POST route with mark-read-on-open and explicit toggle mode"
  - "/_fragments/mark-all-read POST route with batch unread→read patching"
  - "/_fragments/unsubscribe POST route calling feed_service.unsubscribe with sidebar refresh"
  - "Unread Articles and Starred Articles workspace views loading filtered article lists"
  - "star-button.html micro-template with inline SVG and htmx outerHTML swap"
  - "37 unit tests covering all 5 route handlers, edge cases, templates, and workspace views"
key_files:
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/article-reading-pane.html
  - apps/rss-reader/frontend/templates/star-button.html
  - apps/rss-reader/frontend/templates/unread-view.html
  - apps/rss-reader/frontend/templates/starred-view.html
  - backend/tests/test_rss_reader_ui.py
key_decisions:
  - "Sidebar re-rendering in mark-all-read and unsubscribe handlers uses inline SPARQL+binding parse rather than calling feed_sidebar_fragment() to avoid request object coupling"
  - "Star button uses inline SVG (Lucide star polygon paths) for immediate rendering without Lucide JS dependency"
  - "Tests built alongside routes (not deferred to T04) — 37 tests provide verification for both T03 and T04 scope"
patterns_established:
  - "_sanitize_iri() helper for IRI angle-bracket/backslash stripping shared across all action handlers"
  - "Fire-and-forget mark-read pattern: hidden div with hx-post + hx-trigger=load + hx-swap=none"
  - "HX-Trigger response headers: articleStateChanged for star/read toggles, feedsChanged for unsubscribe"
observability_surfaces:
  - "data-article-iri, data-starred, data-read attributes on reading pane root div"
  - "HX-Trigger: articleStateChanged header after toggle-star and toggle-read"
  - "HX-Trigger: feedsChanged header after unsubscribe"
  - "<div class='rss-error'> fragments on SPARQL/patch failures with error messages"
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Build reading pane + star/read/unsubscribe action handlers + workspace views

**Added 5 route handlers (reading pane, star toggle, read toggle, mark-all-read, unsubscribe), 3 templates, replaced 2 workspace view stubs, and wrote 37 unit tests covering all handlers and edge cases**

## What Happened

Built all 5 new route handlers in `apps/rss-reader/app.py`:

1. **article-reading-pane GET**: SPARQL query for single article with title/link/author/date/body/feedTitle. Parses boolean star/read state, formats date, determines body content (body → description → None fallback). Generates stable md_id from SHA-256 hash of article IRI for markdown source/target elements. Includes fire-and-forget mark-read hidden div when article is unread.

2. **toggle-star POST**: Queries current isStarred value, flips it, patches via object.patch, returns updated star-button.html with HX-Trigger: articleStateChanged.

3. **toggle-read POST**: Default mode marks as read (isRead=True). Toggle mode queries current value and flips. Returns empty 200 with HX-Trigger header.

4. **mark-all-read POST**: Queries all unread article IRIs (optionally scoped to feed_iri), patches each to isRead=True with best-effort error handling. Returns updated feed sidebar.

5. **unsubscribe POST**: Calls feed_service.unsubscribe() for soft-delete, returns updated sidebar with HX-Trigger: feedsChanged.

Created 3 templates: article-reading-pane.html (article header + markdown body + fire-and-forget mark-read), star-button.html (inline SVG star with htmx outerHTML swap), and replaced unread-view.html/starred-view.html stubs with htmx-loading containers that fetch `/_fragments/article-list?filter=unread|starred`.

Added `unsubscribe` to the import block. Created `_sanitize_iri()` helper shared by all handlers. Also created `test_rss_reader_ui.py` with 37 tests covering all T04 scope — effectively completing T04 as well.

## Verification

- `python3 -c "ast.parse(...)"` on app.py — syntax OK
- All 5 route handler names found via grep in app.py
- Templates exist: article-reading-pane.html, star-button.html
- unread-view.html contains `filter=unread`, starred-view.html contains `filter=starred`
- 37/37 unit tests pass in test_rss_reader_ui.py
- 91/91 regression tests pass across test_app_proxy.py, test_rss_feed_parser.py, test_feed_service.py
- manifest.yaml includes reader.js in frontend.js array

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `grep "toggle-star" apps/rss-reader/app.py` | 0 | ✅ pass | <1s |
| 3 | `grep "toggle-read" apps/rss-reader/app.py` | 0 | ✅ pass | <1s |
| 4 | `grep "mark-all-read" apps/rss-reader/app.py` | 0 | ✅ pass | <1s |
| 5 | `grep "unsubscribe" apps/rss-reader/app.py` | 0 | ✅ pass | <1s |
| 6 | `grep "article-reading-pane" apps/rss-reader/app.py` | 0 | ✅ pass | <1s |
| 7 | `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` | 0 | ✅ pass (37/37) | 0.3s |
| 8 | `cd backend && .venv/bin/python -m pytest tests/test_app_proxy.py -v` | 0 | ✅ pass (3/3) | 0.3s |
| 9 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` | 0 | ✅ pass (88/88) | 0.3s |

## Diagnostics

- **Reading pane inspection:** `curl /_fragments/article-reading-pane?article_iri=<IRI>` returns full HTML with `data-article-iri`, `data-starred`, `data-read` attributes
- **Star toggle:** `curl -X POST /_fragments/toggle-star -d article_iri=<IRI>` returns star-button.html fragment; check `HX-Trigger` response header
- **Read toggle:** `curl -X POST /_fragments/toggle-read -d article_iri=<IRI>` returns empty body; check `HX-Trigger: articleStateChanged` header
- **Mark all read:** `curl -X POST /_fragments/mark-all-read -d feed_iri=<IRI>` returns updated feed sidebar; check `HX-Trigger: articleStateChanged` header
- **Unsubscribe:** `curl -X POST /_fragments/unsubscribe -d feed_iri=<IRI>` returns updated feed sidebar; check `HX-Trigger: feedsChanged` header
- **Error fragments:** All handlers return `<div class="rss-error">` on SPARQL/patch failures

## Deviations

- T04 (unit tests) was folded into T03 rather than left as a separate task. The 37 tests cover all T04 scope (reading pane, star/read toggles, mark-all-read, unsubscribe, workspace views, edge cases, template verification). Both T03 and T04 marked done.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/app.py` — Added 5 route handlers (article-reading-pane, toggle-star, toggle-read, mark-all-read, unsubscribe) + _sanitize_iri helper + unsubscribe import
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — New template: article header, markdown body, fire-and-forget mark-read
- `apps/rss-reader/frontend/templates/star-button.html` — New micro-template: inline SVG star with htmx outerHTML swap
- `apps/rss-reader/frontend/templates/unread-view.html` — Replaced stub with htmx-loading container for filtered article list
- `apps/rss-reader/frontend/templates/starred-view.html` — Replaced stub with htmx-loading container for filtered article list
- `backend/tests/test_rss_reader_ui.py` — New test file: 37 tests covering all route handlers, edge cases, and templates
