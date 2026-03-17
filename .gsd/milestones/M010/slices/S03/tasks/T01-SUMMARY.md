---
id: T01
parent: S03
milestone: M010
provides:
  - Proxy query-string forwarding fix (platform-wide)
  - RSS Reader three-panel shell HTML (reader.html)
  - Complete CSS layout for reader UI (styles.css)
  - Client-side reader.js (markdown rendering, Lucide icons, keyboard nav)
  - manifest.yaml updated with reader.js
key_files:
  - backend/app/apps/proxy.py
  - backend/tests/test_app_proxy.py
  - apps/rss-reader/frontend/templates/reader.html
  - apps/rss-reader/frontend/static/styles.css
  - apps/rss-reader/frontend/static/reader.js
  - apps/rss-reader/manifest.yaml
key_decisions:
  - Used `data-md-source` / `data-md-target` attribute convention for markdown rendering hook in reader.js — T02/T03 templates must include these attributes on the source script and target div elements
patterns_established:
  - Existing proxy tests needed `mock_request.url = MagicMock(query=None)` added after the proxy fix — any new proxy test must set `.url.query` on mock requests
  - reader.js keyboard nav (j/k) wraps around the list and skips when an input is focused
observability_surfaces:
  - htmx `hx-trigger="load"` on sidebar and article-list fires on page load — network requests visible in DevTools
  - `feedsChanged from:body` custom event triggers sidebar refresh — testable via `document.body.dispatchEvent(new CustomEvent('feedsChanged'))`
  - reader.js logs nothing but errors surface in browser console from markdown-render.js if source/target elements are missing
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Fix proxy query-string forwarding + build reader shell, CSS, and reader.js

**Fixed platform proxy dropping query strings and built the complete RSS Reader three-panel shell (HTML + CSS + JS).**

## What Happened

1. **Proxy fix:** Added two lines in `AppProxy.forward()` to append `request.url.query` to `target_url` when present. This is a platform-wide bug fix that affected all apps relying on query parameters through the proxy chain. Added two new tests: one proving query strings are preserved, one confirming no trailing `?` when query is absent. Updated 5 existing mock requests to set `.url.query = None` so they remain correct with the new code path.

2. **reader.html:** Replaced the placeholder with a three-panel CSS Grid layout. The feed sidebar auto-loads via `hx-get="/_fragments/feed-sidebar"` on page load and re-fetches on the `feedsChanged` custom event. The article list loads via `hx-get="/_fragments/article-list"`. The reading pane shows a placeholder until an article is selected.

3. **styles.css:** Wrote ~330 lines of CSS covering the complete reader layout: feed sidebar (240px), article list (320px), flexible reading pane. All selectors scoped under `.rss-reader`. Includes feed item hover/active states, unread count badges, article list with read/unread styling, star button states, reading pane typography with generous line-height, blockquote/code styling, status classes (rss-success/error/info), empty states, and a loading spinner.

4. **reader.js:** Created an IIFE with three concerns: (a) `htmx:afterSwap` listener scoped to `#rss-reading-pane` that calls `renderMarkdownBody()` using `data-md-source`/`data-md-target` attribute convention, (b) Lucide icon refresh after any swap in the reader container, (c) j/k keyboard navigation for article list with wrap-around and input-field guard.

5. **manifest.yaml:** Added `reader.js` to the `frontend.js` array.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_app_proxy.py -v` — **25 passed** (including 2 new query-string tests)
- `grep "request.url.query" backend/app/apps/proxy.py` — fix present ✓
- `grep 'hx-get="/_fragments/feed-sidebar"' apps/rss-reader/frontend/templates/reader.html` — ✓
- `grep -c ".rss-reader" apps/rss-reader/frontend/static/styles.css` — 69 occurrences ✓
- `grep "reader.js" apps/rss-reader/manifest.yaml` — ✓
- `grep "renderMarkdownBody" apps/rss-reader/frontend/static/reader.js` — ✓
- `ast.parse` on `apps/rss-reader/app.py` — syntax OK ✓
- S01/S02 regression: `test_rss_feed_parser.py` + `test_feed_service.py` — **77 passed** ✓

### Slice-level verification status (T01 of 4):
- [ ] `test_rss_reader_ui.py` ≥20 tests — not yet (T04 creates this)
- [x] `test_app_proxy.py` — all pass including query-string test
- [x] S01/S02 tests — zero regressions (77 passed)
- [x] `ast.parse` on `app.py` — OK
- [x] `manifest.yaml` includes `reader.js`
- [ ] HX-Trigger headers on route handlers — not yet (T02/T03)

## Diagnostics

- Proxy: `grep "request.url.query" backend/app/apps/proxy.py` to verify the fix is present
- Reader shell: Open RSS Reader page in browser, check Network tab for `/_fragments/feed-sidebar` and `/_fragments/article-list` requests on load
- CSS: Inspect `.rss-reader` container — should be a 3-column grid filling available height
- JS: Open console, dispatch `new CustomEvent('feedsChanged')` on `document.body` to trigger sidebar refresh

## Deviations

- Added `mock_request.url = MagicMock(query=None)` to 5 existing proxy tests — without this, `MagicMock(spec=Request).url.query` returns a truthy Mock object, causing the new `if request.url.query:` check to append garbage to URLs in existing tests. This is a necessary fix, not optional.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/proxy.py` — 2-line fix appending query string to target_url
- `backend/tests/test_app_proxy.py` — 2 new tests + 5 existing tests patched with `.url.query = None`
- `apps/rss-reader/frontend/templates/reader.html` — Three-panel layout shell with htmx triggers
- `apps/rss-reader/frontend/static/styles.css` — Complete reader CSS (~330 lines, scoped under .rss-reader)
- `apps/rss-reader/frontend/static/reader.js` — IIFE with markdown rendering, Lucide icons, j/k keyboard nav
- `apps/rss-reader/manifest.yaml` — Added reader.js to frontend.js array
- `.gsd/milestones/M010/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
