---
id: T04
parent: S02
milestone: M010
provides:
  - POST /_fragments/subscribe route — creates feed subscription from form data, returns HTML result fragment
  - GET /_fragments/discover-feeds route — discovers feeds from website URL via HTML link tags
  - Working subscribe-dialog.html htmx form with URL input, title input, discover button, subscribe button
key_files:
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/subscribe-dialog.html
  - backend/tests/test_feed_service.py
key_decisions:
  - Discover-feeds route accepts both `url` and `feed_url` query params to align with htmx hx-include which sends the input's name attribute
  - Discover-feeds pre-fill uses onclick JS to set input value (lightweight, no htmx round-trip needed)
  - Subscribe success emits HX-Trigger feedsChanged header for downstream UI refresh
patterns_established:
  - HTML fragment routes return CSS-classed divs (rss-success, rss-error, rss-info) as structured result signals
  - HX-Trigger header pattern for cross-component communication in htmx apps
observability_surfaces:
  - POST subscribe returns rss-success/rss-error/rss-info CSS-classed fragments — inspectable via browser DevTools
  - GET discover-feeds returns discovered feed count or error fragment
  - HX-Trigger feedsChanged header on successful subscription — observable in browser network tab
duration: 12m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T04: Wire subscribe route, feed discovery endpoint, and working dialog template

**Added POST subscribe route, GET discover-feeds route, and working htmx subscribe dialog — closes S02 user-facing loop for feed subscription by URL**

## What Happened

Added two new route handlers to `apps/rss-reader/app.py`:

1. **POST `/_fragments/subscribe`** — reads `feed_url` and `title` from form body, calls `subscribe()` from feed_service, returns HTML fragments with CSS classes (`rss-success`, `rss-error`, `rss-info`) indicating outcome. On success, includes `HX-Trigger: feedsChanged` header for downstream UI components.

2. **GET `/_fragments/discover-feeds`** — reads URL from query params, fetches the page via `ctx.http.get()`, calls `discover_feeds_from_html()`, and renders a list of discovered feeds with "Use this feed" buttons that pre-fill the subscribe form's URL input.

Updated `subscribe-dialog.html` from the S01 stub to a working htmx form with feed URL input, optional title input, discover button (triggers GET discover-feeds), and subscribe button (triggers POST subscribe). Two result divs (`#discover-result`, `#subscribe-result`) receive the HTML fragments from the respective routes.

Added `subscribe` and `discover_feeds_from_html` to the app.py import block (both normal import and spec_from_file_location fallback paths).

Wrote 4 new contract tests in `TestSubscribeRouteContract`: subscribe-new-url, subscribe-duplicate, discover-with-multiple-feeds, and discover-no-feeds.

## Verification

- 50 tests pass in test_feed_service.py (≥37 required) — 4 new tests added
- 38 tests pass in test_rss_feed_parser.py — zero S01 regressions
- app.py syntax valid (ast.parse OK)
- feed_service.py syntax valid (ast.parse OK)
- subscribe-dialog.html is non-empty and starts with `<div`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_feed_service.py -v` | 0 | ✅ pass (50 tests) | 0.35s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v` | 0 | ✅ pass (38 tests) | 0.27s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `test -s apps/rss-reader/frontend/templates/subscribe-dialog.html` | 0 | ✅ pass | <1s |

## Diagnostics

- **Subscribe route outcomes:** Inspect `<div class="rss-success|rss-error|rss-info">` in the `#subscribe-result` container after form submission.
- **Discover route outcomes:** Inspect `<div class="rss-discovered-feeds">` or `<div class="rss-info|rss-error">` in the `#discover-result` container.
- **HX-Trigger header:** On successful subscription, check network tab for `HX-Trigger: feedsChanged` response header.
- **Feed discovery count:** The discover response includes "Found N feed(s):" text showing how many feeds were extracted.

## Deviations

- Discover-feeds route reads both `url` and `feed_url` query params (`request.query_params.get("url") or request.query_params.get("feed_url")`) since htmx `hx-include="#feed-url-input"` sends the input's `name` attribute (`feed_url`), not `url`. Plan specified only `url` param.
- Added 4 new tests instead of 3 (added a no-feeds empty case alongside the multi-feed case).

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/app.py` — added POST subscribe route, GET discover-feeds route, updated imports for subscribe + discover_feeds_from_html
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — replaced S01 stub with working htmx form (URL input, title input, discover button, subscribe button, result divs)
- `backend/tests/test_feed_service.py` — added TestSubscribeRouteContract class with 4 contract tests (50 total)
