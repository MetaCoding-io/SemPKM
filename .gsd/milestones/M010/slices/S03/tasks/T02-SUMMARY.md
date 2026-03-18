---
id: T02
parent: S03
milestone: M010
provides:
  - "/_fragments/feed-sidebar route handler with SPARQL GROUP BY unread counts"
  - "/_fragments/article-list route handler with feed_iri and filter query params"
  - "feed-sidebar.html template with unread badges, error indicators, subscribe button"
  - "article-list.html template with filter tabs and read/unread visual state"
  - "_format_date() server-side date formatting helper"
  - "_build_article_list_sparql() dynamic SPARQL builder with IRI sanitization"
key_files:
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/feed-sidebar.html
  - apps/rss-reader/frontend/templates/article-list.html
  - apps/rss-reader/frontend/static/styles.css
key_decisions:
  - "Boolean normalization in route handler (Python bools to template, not SPARQL string comparisons)"
  - "IRI sanitization via angle-bracket/backslash stripping rather than full URL encoding to avoid breaking URN syntax"
patterns_established:
  - "SPARQL binding → Python dict normalization pattern: extract .get('field', {}).get('value', default), cast types, pass clean dicts to templates"
  - "Filter tab pattern: hx-get with preserved active_feed and active_filter as query params for stateless filter switching"
observability_surfaces:
  - "data-feed-iri attributes on feed list items (inspectable via document.querySelectorAll('[data-feed-iri]'))"
  - "data-article-iri, data-read, data-starred attributes on article items"
  - ".rss-feed-error-indicator elements visible when feed has errors"
  - ".rss-empty-state divs with descriptive text for empty feeds/articles"
  - "SPARQL failures render as <div class='rss-error'> fragments instead of HTTP 500"
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Build feed sidebar and article list route handlers + templates

**Added feed-sidebar and article-list fragment route handlers with SPARQL queries, Jinja2 templates with filter tabs/unread badges/error indicators, and server-side date formatting**

## What Happened

Added two new route handlers to `apps/rss-reader/app.py`:

1. **`feed_sidebar_fragment`** — Runs a SPARQL query with `GROUP BY` + `COUNT` to fetch all FeedSubscription objects with their unread article counts. Parses SPARQL bindings into clean Python dicts with properly typed fields (ints for counts, strings for titles). Renders `feed-sidebar.html`.

2. **`article_list_fragment`** — Reads `feed_iri` and `filter` query params. Builds SPARQL dynamically via `_build_article_list_sparql()` — adds `FILTER(?sub = <iri>)` when filtering by feed, adds required `isRead false` or `isStarred true` triples for unread/starred filters. Normalizes SPARQL boolean strings to Python bools before template rendering. Formats dates server-side via `_format_date()`. Renders `article-list.html`.

Created two Jinja2 templates:

- **`feed-sidebar.html`** — "All Feeds" item at top, loop over feeds with unread badges (hidden when 0), error indicator dots when `error_count > 0`, subscribe button. Empty state with "No feeds yet" message and subscribe CTA.

- **`article-list.html`** — Filter tab bar (All/Unread/Starred) preserving active feed context. Article items with title, source, author, date, read/unread CSS classes. Data attributes for testing. Empty states vary by active filter.

Added CSS for filter tabs (`.rss-filter-btn`) and article count indicator (`.rss-article-count`) to `styles.css`.

## Verification

- `ast.parse` on `app.py` — syntax OK
- Both templates have balanced Jinja2 blocks (5/5 and 13/13 opens/closes)
- Both templates contain `hx-get` attributes for htmx navigation
- SPARQL queries use correct type IRIs from constants (`ARTICLE_TYPE`, `SUBSCRIPTION_TYPE`, `RSS_NS`)
- Feed sidebar SPARQL uses `GROUP BY` with `COUNT` for unread counts
- `_format_date` tested with ISO datetimes, date-only strings, None, empty, and invalid inputs
- 3/3 proxy tests pass, 88/88 S01/S02 tests pass (zero regressions)
- `data-feed-iri`, `data-article-iri`, `data-read`, `data-starred` attributes present in templates
- `.rss-feed-error-indicator` present in feed-sidebar template

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `grep "feed-sidebar" apps/rss-reader/app.py` | 0 | ✅ pass | <1s |
| 3 | `grep "article-list" apps/rss-reader/app.py` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_app_proxy.py -v` | 0 | ✅ pass (3/3) | 0.19s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` | 0 | ✅ pass (88/88) | 0.33s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` | — | ⏳ expected fail (T04 creates this file) | — |

## Diagnostics

- **Feed sidebar errors:** `document.querySelectorAll('.rss-feed-error-indicator')` lists feeds with errors
- **Feed list items:** `document.querySelectorAll('[data-feed-iri]')` returns all rendered feeds
- **Article list items:** `document.querySelectorAll('[data-article-iri]')` returns all rendered articles
- **Active filter:** Check URL query params in Network tab for `/_fragments/article-list?filter=...&feed_iri=...`
- **SPARQL failures:** Route handlers catch exceptions and return `<div class="rss-error">` fragments
- **Empty states:** Visible as `.rss-empty-state` divs when no feeds/articles exist

## Deviations

- Added CSS for filter tabs and article count indicator to `styles.css` — these weren't in T01's CSS since they're new UI patterns specific to T02's templates.
- Feed sidebar template uses `active_feed` variable for All Feeds highlight even though it's not passed from the route handler (it defaults to None/falsy which is correct for initial load). Active-feed highlighting for specific feeds will be handled client-side in reader.js per the plan note.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/app.py` — Added `_format_date()` helper, `FEED_SIDEBAR_SPARQL` constant, `_build_article_list_sparql()` builder, `feed_sidebar_fragment()` and `article_list_fragment()` route handlers
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — New template: feed list with unread badges, error indicators, subscribe button, empty state
- `apps/rss-reader/frontend/templates/article-list.html` — New template: filter tabs, article items with read/unread state, data attributes, empty states
- `apps/rss-reader/frontend/static/styles.css` — Added `.rss-filter-btn` and `.rss-article-count` CSS rules
