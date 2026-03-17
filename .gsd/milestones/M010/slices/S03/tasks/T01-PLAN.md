---
estimated_steps: 6
estimated_files: 6
---

# T01: Fix proxy query-string forwarding + build reader shell, CSS, and reader.js

**Slice:** S03 — Reader UI (split-pane layout)
**Milestone:** M010

## Description

Fix the platform proxy's query-string forwarding bug (which drops `?key=value` params from all app fragment requests), then build the reader UI's structural foundation: the three-panel shell template, the full CSS layout, and the reader.js client-side helper. This task produces the visual frame that T02/T03 fill with data-driven content.

The proxy fix is a platform bug that affects ALL apps using query parameters through the proxy chain (`AppProxy.forward()` builds `target_url` without appending `request.url.query`). It must be fixed before T02's `/_fragments/article-list?feed_iri=...` requests can work.

## Steps

1. **Fix proxy query-string forwarding** — In `backend/app/apps/proxy.py`, find line ~87 where `target_url = f"http://localhost/{path}"`. After that line, add: `if request.url.query: target_url += f"?{request.url.query}"`. This preserves query parameters when forwarding requests to app unix sockets. Add one test in `backend/tests/test_app_proxy.py` that verifies query params are forwarded (mock the httpx client, check that the `url` kwarg contains the query string).

2. **Replace reader.html with split-pane shell** — Replace the stub in `apps/rss-reader/frontend/templates/reader.html` with a three-panel layout using CSS Grid. Structure:
   ```html
   <div class="rss-reader" id="rss-reader-container">
     <div class="rss-feed-sidebar" id="rss-feed-sidebar"
          hx-get="/_fragments/feed-sidebar"
          hx-trigger="load, feedsChanged from:body"
          hx-swap="innerHTML">
       <div class="tree-empty">Loading feeds...</div>
     </div>
     <div class="rss-article-list" id="rss-article-list">
       <div class="rss-article-list-header">
         <h3>All Articles</h3>
       </div>
       <div id="rss-article-list-content"
            hx-get="/_fragments/article-list"
            hx-trigger="load"
            hx-swap="innerHTML">
         <div class="tree-empty">Loading articles...</div>
       </div>
     </div>
     <div class="rss-reading-pane" id="rss-reading-pane">
       <div class="rss-reading-pane-empty">
         <p>Select an article to read</p>
       </div>
     </div>
   </div>
   ```
   Note: Feed sidebar listens for `feedsChanged from:body` to auto-refresh after subscribe/unsubscribe.

3. **Write full styles.css** — Replace the placeholder CSS with a complete reader layout. Key rules:
   - `.rss-reader` — CSS Grid: `grid-template-columns: 240px 320px 1fr; height: 100%; overflow: hidden;`
   - `.rss-feed-sidebar` — left panel with border-right, overflow-y auto, background surface-recessed
   - `.rss-article-list` — center panel with border-right, overflow-y auto
   - `.rss-reading-pane` — right panel with overflow-y auto, max-width for readability
   - Article list items: `.rss-article-item` with hover state, active state, read/unread styling (unread = bold title)
   - Feed items: `.rss-feed-item` with unread count badge, active highlight, error indicator
   - Star button: `.rss-star-btn` with filled/unfilled SVG state
   - Reading pane typography: clean serif/sans-serif stack for article body, generous line-height
   - All colors use `var(--color-*)` tokens from theme.css
   - Scope everything under `.rss-reader` to avoid conflicts with workspace styles
   - Status classes: `.rss-success`, `.rss-error`, `.rss-info` for subscribe dialog fragments (keep from S02)
   - Empty states: `.rss-reading-pane-empty`, `.rss-empty-state`

4. **Create reader.js** — Client-side JS for:
   - `htmx:afterSwap` listener scoped to `#rss-reading-pane` that calls `window.renderMarkdownBody()` on the markdown source/target elements inside the reading pane
   - `htmx:afterSwap` listener that calls `lucide.createIcons()` if lucide is available (for any htmx-swapped content in the reader)
   - Keyboard navigation: `j`/`k` keys for next/prev article in the article list (find `.rss-article-item.active` then click next/prev sibling)
   - The JS should be wrapped in an IIFE to avoid polluting global scope

5. **Update manifest.yaml** — Add `reader.js` to the `frontend.js` array:
   ```yaml
   frontend:
     staticDir: "frontend/static"
     css:
       - "styles.css"
     js:
       - "reader.js"
   ```

6. **Verify** — Run `cd backend && python -m pytest tests/test_app_proxy.py -v` to confirm proxy tests pass. Check `ast.parse` on app.py (no changes to app.py in this task). Confirm reader.html contains `hx-get="/_fragments/feed-sidebar"`. Confirm manifest.yaml includes reader.js.

## Must-Haves

- [ ] Proxy `AppProxy.forward()` appends query string to target_url when present
- [ ] New proxy test verifies query params are forwarded to app subprocess
- [ ] reader.html defines three-panel layout with htmx lazy-load triggers for feed sidebar and article list
- [ ] styles.css provides complete CSS Grid layout with theme variable usage, scoped under `.rss-reader`
- [ ] reader.js handles markdown rendering after htmx swap and Lucide icon refresh
- [ ] manifest.yaml includes `reader.js` in `frontend.js` array

## Verification

- `cd backend && python -m pytest tests/test_app_proxy.py -v` — all tests pass including new query-string test
- `grep "request.url.query" backend/app/apps/proxy.py` — the fix is present
- `grep "hx-get=\"/_fragments/feed-sidebar\"" apps/rss-reader/frontend/templates/reader.html` — shell loads sidebar
- `grep "rss-reader" apps/rss-reader/frontend/static/styles.css` — CSS scoped correctly
- `grep "reader.js" apps/rss-reader/manifest.yaml` — JS registered
- `grep "renderMarkdownBody" apps/rss-reader/frontend/static/reader.js` — markdown rendering wired

## Observability Impact

- **Proxy query-string fix:** After this fix, `target_url` in `AppProxy.forward()` will include `?key=value` when present. A future agent can verify by grepping `request.url.query` in `proxy.py` or running the dedicated proxy test. If this fix is missing, ALL parametrized fragment requests (e.g. `/_fragments/article-list?feed_iri=...`) will silently lose their query params, causing empty or wrong results.
- **reader.html htmx triggers:** The `hx-trigger="load"` on `#rss-feed-sidebar` and `#rss-article-list-content` fire HTTP requests on page load. If the proxy or route handlers aren't wired, these will produce 404/502 errors visible in browser DevTools Network tab. The `feedsChanged from:body` trigger on the sidebar enables auto-refresh after subscribe/unsubscribe — testable by dispatching `new CustomEvent('feedsChanged')` on `document.body`.
- **reader.js post-swap hooks:** After htmx swaps content into `#rss-reading-pane`, the `htmx:afterSwap` listener calls `renderMarkdownBody()`. If this fails, raw markdown will be visible instead of rendered HTML. Check browser console for errors from `markdown-render.js`.

## Inputs

- `backend/app/apps/proxy.py` — line ~87, `target_url = f"http://localhost/{path}"` needs query-string append
- `backend/tests/test_app_proxy.py` — existing proxy test patterns to follow (pytest-asyncio, mocked httpx)
- `apps/rss-reader/frontend/templates/reader.html` — current stub to replace
- `apps/rss-reader/frontend/static/styles.css` — current placeholder to replace
- `apps/rss-reader/manifest.yaml` — current manifest with empty js array
- `frontend/static/css/theme.css` — CSS variable names to reference (--color-bg, --color-surface, --color-border, --color-text, --color-text-muted, --color-accent, --color-surface-recessed, --color-surface-hover, etc.)
- `frontend/static/js/markdown-render.js` — `window.renderMarkdownBody(sourceId, targetId)` is the function to call after htmx swap. It reads markdown from a source element and renders into a target element.

## Expected Output

- `backend/app/apps/proxy.py` — one-line query-string forwarding fix
- `backend/tests/test_app_proxy.py` — one new test for query-string forwarding
- `apps/rss-reader/frontend/templates/reader.html` — three-panel shell with htmx triggers
- `apps/rss-reader/frontend/static/styles.css` — complete reader CSS (~200 lines)
- `apps/rss-reader/frontend/static/reader.js` — markdown/icon/keyboard handler (~60 lines)
- `apps/rss-reader/manifest.yaml` — updated with reader.js in js array
