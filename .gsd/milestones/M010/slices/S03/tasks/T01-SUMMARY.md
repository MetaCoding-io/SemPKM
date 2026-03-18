---
id: T01
parent: S03
milestone: M010
provides:
  - Proxy query-string forwarding fix (platform bug affecting all app fragment requests)
  - Three-panel reader.html shell with htmx lazy-load triggers
  - Complete CSS Grid layout for RSS reader scoped under .rss-reader
  - reader.js with markdown rendering, Lucide refresh, and j/k keyboard navigation
key_files:
  - backend/app/apps/proxy.py
  - backend/tests/test_app_proxy.py
  - apps/rss-reader/frontend/templates/reader.html
  - apps/rss-reader/frontend/static/styles.css
  - apps/rss-reader/frontend/static/reader.js
  - apps/rss-reader/manifest.yaml
key_decisions: []
patterns_established:
  - reader.js IIFE pattern with htmx:afterSwap scoped to #rss-reading-pane for markdown rendering
  - CSS scoped entirely under .rss-reader to avoid workspace conflicts
observability_surfaces:
  - "htmx load triggers on #rss-feed-sidebar and #rss-article-list-content fire on page load — 404/502 in Network tab means routes not wired yet"
  - "feedsChanged custom event on document.body triggers sidebar refresh — testable via new CustomEvent('feedsChanged')"
  - "renderMarkdownBody() failures show raw markdown instead of rendered HTML — check browser console"
duration: 12m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Fix proxy query-string forwarding + build reader shell, CSS, and reader.js

**Fixed platform proxy dropping query strings from app requests; built three-panel reader shell with CSS Grid layout, htmx lazy-load triggers, and reader.js for markdown/icon/keyboard handling**

## What Happened

Fixed a platform-level bug in `AppProxy.forward()` where `target_url` was built without appending `request.url.query`, causing all parametrized fragment requests (e.g. `/_fragments/article-list?feed_iri=...`) to silently lose their query parameters. The fix is a two-line conditional append after the URL construction.

Created the reader.html three-panel shell using CSS Grid with htmx `hx-get` + `hx-trigger="load"` on the feed sidebar and article list content panels. The sidebar also listens for `feedsChanged from:body` to auto-refresh after subscribe/unsubscribe actions.

Wrote complete styles.css (~350 lines) with CSS Grid layout (240px sidebar, 320px article list, 1fr reading pane), article items with read/unread states, feed items with unread badges and error indicators, star button with filled/unfilled states, reading pane typography, empty states, and status feedback classes. All selectors scoped under `.rss-reader` and all colors use `var(--color-*)` theme tokens.

Created reader.js as an IIFE with three features: (1) `htmx:afterSwap` listener scoped to `#rss-reading-pane` that finds `<script type="text/plain" id="md-source-*">` elements and calls `renderMarkdownBody()`, (2) `htmx:afterSwap` listener for `lucide.createIcons()` on any swap within the reader container, (3) `j`/`k` keyboard navigation for article list traversal.

Updated manifest.yaml to include `reader.js` in the `frontend.js` array.

## Verification

- `pytest tests/test_app_proxy.py -v` — 3/3 tests pass (query-string forwarding, no-query baseline, token injection)
- `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — 88/88 S01/S02 tests pass, zero regressions
- `ast.parse` on `apps/rss-reader/app.py` — syntax OK
- All 6 grep-based verification checks pass (proxy fix, reader.html htmx triggers, CSS scoping, manifest.yaml, reader.js markdown hook)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_app_proxy.py -v` | 0 | ✅ pass | 0.18s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` | 0 | ✅ pass | 0.33s |
| 3 | `python -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <0.1s |
| 4 | `grep "request.url.query" backend/app/apps/proxy.py` | 0 | ✅ pass | <0.1s |
| 5 | `grep 'hx-get="/_fragments/feed-sidebar"' apps/rss-reader/frontend/templates/reader.html` | 0 | ✅ pass | <0.1s |
| 6 | `grep "rss-reader" apps/rss-reader/frontend/static/styles.css` | 0 | ✅ pass | <0.1s |
| 7 | `grep "reader.js" apps/rss-reader/manifest.yaml` | 0 | ✅ pass | <0.1s |
| 8 | `grep "renderMarkdownBody" apps/rss-reader/frontend/static/reader.js` | 0 | ✅ pass | <0.1s |

### Slice-level checks (T01 is intermediate — partial passes expected)

| # | Slice Check | Status | Notes |
|---|-------------|--------|-------|
| 1 | `pytest tests/test_rss_reader_ui.py -v` — ≥20 tests | ⬜ pending | Test file created in T04 |
| 2 | `pytest tests/test_app_proxy.py -v` — proxy tests pass | ✅ pass | 3/3 pass |
| 3 | `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — S01/S02 regression | ✅ pass | 88/88 pass |
| 4 | `ast.parse app.py` — syntax OK | ✅ pass | |
| 5 | `manifest.yaml` includes `reader.js` | ✅ pass | |

## Diagnostics

- **Proxy fix:** `grep "request.url.query" backend/app/apps/proxy.py` confirms the fix. Run proxy tests to verify behavior.
- **htmx load triggers:** On page load, `#rss-feed-sidebar` fires `GET /_fragments/feed-sidebar` and `#rss-article-list-content` fires `GET /_fragments/article-list`. Until T02 wires the route handlers, these will 404 — visible in browser DevTools Network tab.
- **feedsChanged event:** After subscribe/unsubscribe, dispatch `new CustomEvent('feedsChanged')` on `document.body` to trigger sidebar refresh.
- **reader.js markdown:** After htmx swaps reading pane content, look for `<script type="text/plain" id="md-source-*">` elements. If `renderMarkdownBody()` fails, raw markdown is visible; check browser console for errors.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/proxy.py` — Added query-string forwarding (2 lines after target_url construction)
- `backend/tests/test_app_proxy.py` — New test file with 3 tests (query-string, no-query baseline, token injection)
- `apps/rss-reader/frontend/templates/reader.html` — Replaced stub with three-panel CSS Grid shell + htmx triggers
- `apps/rss-reader/frontend/static/styles.css` — Complete reader CSS (~350 lines) scoped under .rss-reader
- `apps/rss-reader/frontend/static/reader.js` — New IIFE with markdown rendering, Lucide refresh, j/k keyboard nav
- `apps/rss-reader/manifest.yaml` — Added reader.js to frontend.js array
