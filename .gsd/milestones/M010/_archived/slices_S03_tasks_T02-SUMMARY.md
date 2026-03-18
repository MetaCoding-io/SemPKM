---
id: T02
parent: S03
milestone: M010
provides:
  - Feed sidebar route handler with SPARQL unread counts (/_fragments/feed-sidebar)
  - Article list route handler with feed/filter query params (/_fragments/article-list)
  - feed-sidebar.html template with unread badges, error indicators, subscribe button
  - article-list.html template with filter tabs and read/unread styling
  - _format_date, _sparql_bool, _sparql_int helper functions
  - FEED_SIDEBAR_SPARQL constant with GROUP BY/COUNT aggregation
  - CSS for filter tabs in styles.css
key_files:
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/feed-sidebar.html
  - apps/rss-reader/frontend/templates/article-list.html
  - apps/rss-reader/frontend/static/styles.css
key_decisions:
  - IRI sanitization via regex (re.sub removing angle brackets and unsafe chars) rather than urllib.parse.quote — keeps the IRI readable in SPARQL and avoids double-encoding
  - SPARQL boolean/int normalization done in route handler via _sparql_bool/_sparql_int helpers — templates receive native Python types, no string comparisons needed
  - Filter tabs use pill-style buttons with active state CSS — matches workspace UI patterns
patterns_established:
  - _sparql_bool(value, default) and _sparql_int(value, default) helpers for SPARQL binding normalization — use these in T03 route handlers too
  - _format_date(iso_str) handles ISO 8601 with Z suffix and various timezone formats — reuse for any date display
  - article-list.html preserves active_feed in filter tab hx-get URLs so feed filtering persists across filter changes
  - Jinja2 `| urlencode` filter used on all IRI values in hx-get URL query params
observability_surfaces:
  - /_fragments/feed-sidebar returns HTML with data-feed-iri attributes on each feed item — inspect via document.querySelectorAll('[data-feed-iri]')
  - /_fragments/article-list returns HTML with data-article-iri, data-read, data-starred attributes — inspect via document.querySelectorAll('[data-article-iri]')
  - SPARQL failures caught and rendered as <div class="rss-error"> fragments with error message — visible in DOM
  - Feed error indicators shown as .rss-feed-error-indicator elements with title attribute containing the error text
  - Empty states render as .rss-empty-state divs — testable via document.querySelector('.rss-empty-state')
duration: 10m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Build feed sidebar and article list route handlers + templates

**Added two SPARQL-driven htmx fragment endpoints and Jinja2 templates for feed sidebar navigation (with unread badges) and filtered article list.**

## What Happened

1. **FEED_SIDEBAR_SPARQL constant** — Added a SPARQL query using `GROUP BY` with `COUNT(?unread)` to aggregate unread article counts per feed subscription. Includes `OPTIONAL` clauses for `errorCount` and `lastError` fields for error state display.

2. **Helper functions** — Added three pure helpers:
   - `_format_date(iso_str)` — parses ISO 8601 strings (handles Z suffix) and formats as "Mar 17, 2026"
   - `_sparql_bool(value, default)` — converts SPARQL string booleans to Python bools
   - `_sparql_int(value, default)` — converts SPARQL string integers to Python ints

3. **`feed_sidebar_fragment()` route handler** — Queries all FeedSubscription objects via `FEED_SIDEBAR_SPARQL`, parses bindings into feed dicts with `{iri, url, title, unread_count, error_count, last_error}`, renders `feed-sidebar.html`. SPARQL errors caught and returned as `<div class="rss-error">` fragments.

4. **`article_list_fragment()` route handler** — Reads optional `feed_iri` and `filter` query params. Builds dynamic SPARQL with injected FILTER clause for feed IRI and required triples for unread/starred filters. IRI sanitized via `re.sub` to prevent SPARQL injection. Parses bindings with boolean normalization and date formatting before template rendering.

5. **feed-sidebar.html** — "All Feeds" item at top, loop over feeds with unread badges (hidden when 0), error indicators (red dot with tooltip), subscribe button at bottom linking to existing subscribe dialog. Empty state when no feeds.

6. **article-list.html** — Filter tabs (All/Unread/Starred) as pill buttons preserving current `feed_iri`. Article items with unread class for bold styling, metadata (source, author, date), star indicator. `hx-get` targets reading pane for article click. Empty states vary by filter mode. Article count indicator.

7. **CSS additions** — Added filter tab styles (`.rss-filter-tab`, `.rss-article-count`, `.rss-article-item-author`) to styles.css.

## Verification

- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — **syntax OK** ✓
- `grep "feed-sidebar" apps/rss-reader/app.py` — route handler exists ✓
- `grep "article-list" apps/rss-reader/app.py` — route handler exists ✓
- `grep "GROUP BY" apps/rss-reader/app.py` — SPARQL aggregation present ✓
- Both templates parse as valid Jinja2 ✓
- Both templates contain `hx-get` attributes for htmx navigation ✓
- `data-feed-iri` and `data-article-iri` attributes present in templates ✓
- Empty states in both templates ✓
- `_format_date` and `_sparql_bool` used in route handlers ✓
- S01/S02 tests: **77 passed** — zero regressions ✓
- Proxy tests: **25 passed** ✓

### Slice-level verification status (T02 of 4):
- [ ] `test_rss_reader_ui.py` ≥20 tests — not yet (T04 creates this)
- [x] `test_app_proxy.py` — all pass (25 passed)
- [x] S01/S02 tests — zero regressions (77 passed)
- [x] `ast.parse` on `app.py` — OK
- [x] `manifest.yaml` includes `reader.js`
- [ ] HX-Trigger headers on route handlers — partially (T03 adds star/read/unsubscribe triggers)

## Diagnostics

- Feed sidebar: `curl /_fragments/feed-sidebar` returns HTML with `data-feed-iri` attributes; count with `document.querySelectorAll('[data-feed-iri]').length`
- Article list: `curl /_fragments/article-list?filter=unread` returns filtered articles; `document.querySelectorAll('[data-article-iri]').length` for count
- Error state: Force SPARQL error → handler logs warning and returns `<div class="rss-error">` fragment
- Empty state: No subscriptions → sidebar shows `.rss-empty-state`; no articles → list shows `.rss-empty-state`

## Deviations

- Removed unused `from urllib.parse import quote` that was initially added — IRI sanitization uses `re.sub` instead.
- Added CSS for filter tabs, article count, and article author to styles.css — these weren't called out in the plan but are required for the template markup to render correctly.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/app.py` — Added FEED_SIDEBAR_SPARQL, _format_date, _sparql_bool, _sparql_int, feed_sidebar_fragment(), article_list_fragment(); added `import re`
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — New template: feed list with unread badges, error indicators, subscribe button, empty state
- `apps/rss-reader/frontend/templates/article-list.html` — New template: filter tabs, article items with read/unread/starred state, empty states
- `apps/rss-reader/frontend/static/styles.css` — Added filter tab, article count, and article author CSS rules
- `.gsd/milestones/M010/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
