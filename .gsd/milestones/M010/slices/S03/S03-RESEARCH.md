# S03: Reader UI (split-pane layout) — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

S03 builds the RSS Reader's standalone split-pane UI — the Level 1 app page that users see when they click "RSS Reader" in the APPS sidebar. The slice is straightforward application of known patterns: htmx fragments rendered by Jinja2 via the SDK, SPARQL queries for data, and CSS within the app's own `styles.css`. All infrastructure is proven — S01 proved fragment serving via proxy, S02 proved the data pipeline and subscribe dialog, and the test-app E2E validates the full proxy→fragment chain.

The reader consists of three visual panels inside a single fragment: a feed sidebar (list of subscriptions with unread counts), an article list (title/date/source filtered by selected feed), and a reading pane (article body rendered as markdown). Star toggle and mark-read/unread are `object.patch` calls. All interactions are htmx fragment swaps within the reader container — no full-page reloads.

**Primary risk:** The platform proxy (`AppProxy.forward()`) builds `target_url` without the request's query string — `target_url = f"http://localhost/{path}"` drops any `?key=value` params. The reader UI needs query parameters for sub-fragment requests (e.g., `/_fragments/article-list?feed_iri=...`). This requires a one-line proxy fix (append `request.url.query`) or a workaround using POST bodies with `hx-vals` for all parametrized requests. The proxy fix is the clean solution and benefits all apps.

## Recommendation

### Fix the proxy, then build the UI

1. **Fix AppProxy query-string forwarding** — one-line change in `proxy.py` to append `request.url.query` to `target_url`. This is a platform bug that affects all apps using query params through the proxy chain. Add a unit test proving query params round-trip.

2. **Build UI top-down: reader shell → feed sidebar → article list → reading pane → actions.** Each is a separate template and route handler in app.py. The shell template loads the three panels; each panel loads its content via `hx-get` with `hx-trigger="load"`. Feed clicks swap the article list. Article clicks swap the reading pane.

3. **Use platform CSS variables** (`--color-bg`, `--color-surface`, `--color-border`, etc.) for all styling. The reader CSS lives in `apps/rss-reader/frontend/static/styles.css` and is loaded by the platform's `app_page.html` wrapper via `<link>` tags from the manifest's `frontend.css` array.

4. **Mark-read on article open** — When a user clicks an article, the reading pane loads AND an `object.patch` sets `rss:isRead = true`. This is a fire-and-forget htmx request using `hx-trigger="load"` on a hidden element inside the reading pane template.

5. **Star toggle** — A button in the reading pane header toggles `rss:isStarred` via `hx-post` to a toggle route. Response swaps just the star button with updated state.

### Approach: Pure htmx, no client-side JS framework

The reader UI uses the same htmx patterns as the rest of SemPKM — fragment loading, `hx-swap`, `hx-trigger`, `hx-target`. No React, no client-side routing. The only JS needed is for markdown rendering (call `window.renderMarkdownBody()` from `markdown-render.js` which is already loaded in the workspace page).

**Important:** The app's JS file needs to invoke `renderMarkdownBody()` after htmx swaps in article content. Use `htmx.on("htmx:afterSwap", ...)` scoped to the reading pane container.

## Implementation Landscape

### Key Files

**Existing (read, do not modify unless noted):**

- `backend/app/apps/proxy.py` — `AppProxy.forward()` **needs query-string fix** (line ~87: append `?{request.url.query}` to `target_url` when query string is non-empty)
- `backend/app/templates/browser/app_page.html` — Platform wrapper that loads app CSS, the fragment via `hx-get`, and app JS. This is the entry point when the user opens "RSS Reader" from the sidebar.
- `backend/sdk/sempkm_app_sdk/context.py` — `render_template()` uses Jinja2 `FileSystemLoader` on `frontend/templates/`. Templates get `**context` kwargs.
- `backend/sdk/sempkm_app_sdk/app.py` — `App.route()` decorator registers FastAPI routes. Handlers receive `Request`, access `request.app.state.ctx` for SDK context.
- `frontend/static/js/markdown-render.js` — `window.renderMarkdownBody(sourceId, targetId)` renders markdown from a source element into a target. Already loaded in workspace page.
- `frontend/static/css/theme.css` — CSS variable definitions (`--color-bg`, `--color-surface`, `--color-border`, `--color-text`, `--color-text-muted`, `--color-accent`, etc.)
- `apps/rss-reader/services/feed_service.py` — `subscribe()`, `unsubscribe()`, SPARQL constants. S03 adds no new service functions — queries are inline SPARQL in route handlers.

**Modify:**

- `apps/rss-reader/app.py` — Add ~8 new route handlers for the reader UI fragments: feed sidebar, article list, article reading pane, star toggle, mark read/unread, mark all read, feed detail/unsubscribe. Remove the stub `reader_fragment` route and replace with the real implementation.
- `apps/rss-reader/frontend/templates/reader.html` — Replace stub with the split-pane shell that loads the three panels via htmx.
- `apps/rss-reader/frontend/templates/unread-view.html` — Replace stub with actual unread articles list (shared template with article-list, filtered by `isRead=false`).
- `apps/rss-reader/frontend/templates/starred-view.html` — Replace stub with actual starred articles list (filtered by `isStarred=true`).
- `apps/rss-reader/frontend/static/styles.css` — Replace placeholder with full reader CSS (split-pane layout, feed sidebar, article list items, reading pane typography).
- `apps/rss-reader/manifest.yaml` — Add `reader.js` to `frontend.js` array.

**Create:**

- `apps/rss-reader/frontend/templates/feed-sidebar.html` — Feed list with unread counts, subscribe button, error indicators.
- `apps/rss-reader/frontend/templates/article-list.html` — Article items with title, date, source name, read/unread indicator.
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — Article header (title, author, date, star button, original link) + markdown body.
- `apps/rss-reader/frontend/templates/star-button.html` — Micro-template for just the star button (swap target for toggle).
- `apps/rss-reader/frontend/static/reader.js` — htmx afterSwap handler for markdown rendering, keyboard shortcuts (j/k for next/prev article).
- `backend/tests/test_rss_reader_ui.py` — Unit tests for the new route handlers (SPARQL queries, response shapes, edge cases).

### Route handlers needed

| Route | Method | Purpose | Params |
|-------|--------|---------|--------|
| `/_fragments/reader` | GET | Split-pane shell | none |
| `/_fragments/feed-sidebar` | GET | Feed list with unread counts | none |
| `/_fragments/article-list` | GET | Articles for a feed (or all) | `?feed_iri=`, `?filter=` (unread/starred/all) |
| `/_fragments/article-reading-pane` | GET | Single article body | `?article_iri=` |
| `/_fragments/toggle-star` | POST | Toggle star state | form: `article_iri` |
| `/_fragments/toggle-read` | POST | Toggle read state | form: `article_iri` |
| `/_fragments/mark-all-read` | POST | Mark all articles in a feed as read | form: `feed_iri` |
| `/_fragments/unsubscribe` | POST | Soft-delete a subscription | form: `feed_iri` |

### SPARQL queries needed

1. **Feed sidebar** — subscriptions with unread counts:
```sparql
SELECT ?sub ?feedUrl ?title (COUNT(?unread) AS ?unreadCount) WHERE {
  ?sub a <urn:sempkm:model:rss-feeds:FeedSubscription> .
  ?sub <urn:sempkm:model:rss-feeds:feedUrl> ?feedUrl .
  OPTIONAL { ?sub <http://purl.org/dc/terms/title> ?title }
  OPTIONAL {
    ?unread a <urn:sempkm:model:rss-feeds:Article> .
    ?unread <urn:sempkm:model:rss-feeds:feedSource> ?sub .
    ?unread <urn:sempkm:model:rss-feeds:isRead> false .
  }
} GROUP BY ?sub ?feedUrl ?title
```

2. **Article list** — articles for a specific feed or all, ordered by date:
```sparql
SELECT ?article ?title ?created ?isRead ?isStarred ?author ?feedTitle WHERE {
  ?article a <urn:sempkm:model:rss-feeds:Article> .
  ?article <urn:sempkm:model:rss-feeds:feedSource> ?sub .
  OPTIONAL { ?article <http://purl.org/dc/terms/title> ?title }
  OPTIONAL { ?article <http://purl.org/dc/terms/created> ?created }
  OPTIONAL { ?article <urn:sempkm:model:rss-feeds:isRead> ?isRead }
  OPTIONAL { ?article <urn:sempkm:model:rss-feeds:isStarred> ?isStarred }
  OPTIONAL { ?article <urn:sempkm:model:rss-feeds:author> ?author }
  OPTIONAL { ?sub <http://purl.org/dc/terms/title> ?feedTitle }
  # FILTER for specific feed_iri injected conditionally
} ORDER BY DESC(?created) LIMIT 100
```

3. **Article body** — single article with body text:
```sparql
SELECT ?title ?link ?author ?created ?isStarred ?isRead ?body ?feedTitle WHERE {
  <{article_iri}> <http://purl.org/dc/terms/title> ?title .
  OPTIONAL { <{article_iri}> <urn:sempkm:model:rss-feeds:link> ?link }
  OPTIONAL { <{article_iri}> <urn:sempkm:model:rss-feeds:author> ?author }
  OPTIONAL { <{article_iri}> <http://purl.org/dc/terms/created> ?created }
  OPTIONAL { <{article_iri}> <urn:sempkm:model:rss-feeds:isStarred> ?isStarred }
  OPTIONAL { <{article_iri}> <urn:sempkm:model:rss-feeds:isRead> ?isRead }
  OPTIONAL { <{article_iri}> <urn:sempkm:body> ?body }
  OPTIONAL {
    <{article_iri}> <urn:sempkm:model:rss-feeds:feedSource> ?sub .
    ?sub <http://purl.org/dc/terms/title> ?feedTitle .
  }
}
```

### Build Order

1. **Proxy fix** — Fix `AppProxy.forward()` to forward query string. Add one unit test. This unblocks all parametrized fragment requests for ALL apps, not just the reader. (~5 min)

2. **Reader shell + CSS** — Replace stub `reader.html` with the three-panel layout div structure. Write the full `styles.css` with CSS Grid/flexbox for the split-pane layout. The shell uses `hx-get` + `hx-trigger="load"` to load each panel on first render. (~15 min)

3. **Feed sidebar** — Route handler queries subscriptions with unread counts via SPARQL. Template renders feed list items with click handlers (`hx-get` to swap article list). Subscribe button opens the existing subscribe dialog. Error indicators shown when `errorCount > 0`. (~15 min)

4. **Article list** — Route handler queries articles filtered by feed_iri (optional) and filter mode (all/unread/starred). Template renders article items with title, relative date, source, read/unread visual state. Clicking an article loads the reading pane. (~15 min)

5. **Reading pane + markdown** — Route handler queries single article properties + body. Template renders article header (title, author, date, link, star button) and body markdown. Uses `window.renderMarkdownBody()` for client-side markdown rendering. Fire-and-forget mark-read on load. (~15 min)

6. **Star toggle + read toggle** — Two POST route handlers that `object.patch` the article and return updated button/indicator HTML. Star toggle swaps just the star button. Read toggle swaps the article list item indicator. (~10 min)

7. **Unread/starred views** — Replace view stubs with real filtered article lists. These use the same article-list template but with preset filters. (~10 min)

8. **reader.js** — htmx `afterSwap` handler for markdown rendering, keyboard nav (j/k for article navigation). (~10 min)

9. **Unit tests** — Test the route handler SPARQL queries, template rendering, star/read toggle logic, and edge cases (no feeds, no articles, missing body). (~15 min)

### Verification Approach

**Unit tests (pytest):**
- Route handler tests with mocked ctx.graph.query() and ctx.commands.execute()
- Test feed sidebar SPARQL returns correct structure and unread counts
- Test article list with/without feed filter, with/without starred/unread filter
- Test reading pane returns article body and metadata
- Test star toggle calls object.patch with correct properties, returns updated button
- Test mark-all-read patches all articles for a feed
- Test edge cases: no subscriptions, no articles, article with no body
- Test proxy query-string forwarding (in existing proxy test file)
- Target: ≥20 new tests

**Manual verification (Docker stack):**
- Navigate to `/app/rss-reader/` — see the split-pane layout
- Feed sidebar shows subscriptions with unread counts
- Click a feed → article list filters to that feed's articles
- Click an article → reading pane shows title, author, date, body
- Star button toggles star state, persists on reload
- Mark read/unread updates visual state in article list
- "Unread Articles" and "Starred Articles" views show filtered content

## Constraints

- **No client-side routing** — All navigation is htmx fragment swaps within the reader container. The URL stays at `/app/rss-reader/` (or whatever the platform maps to the reader page).
- **App CSS loaded once** — The platform's `app_page.html` loads `styles.css` via `<link>` before the fragment. CSS must not conflict with workspace styles. All selectors should be scoped under `.rss-reader` or similar prefix.
- **Markdown rendering is client-side** — Article bodies stored as markdown via `body.set`. The reading pane template embeds raw markdown in a `<script type="text/plain">` tag. Client-side JS calls `renderMarkdownBody()` after htmx swap. This matches the existing workspace pattern.
- **App `render_template()` uses Jinja2 with autoescape=True** — All template variables are auto-escaped by default. Safe HTML needs `|safe` filter. The markdown source element uses `<script type="text/plain">` which doesn't need escaping.
- **Article body might be absent** — Not all articles have body text (depends on whether `body.set` was called during poll-feeds). The reading pane should show the feed-provided summary (`dcterms:description`) or a "No content available — visit original" fallback.
- **Proxy query-string bug** — `AppProxy.forward()` doesn't forward query params. Must be fixed or worked around. The fix is a one-line change: `if request.url.query: target_url += f"?{request.url.query}"`.

## Common Pitfalls

- **Markdown rendering after htmx swap** — `renderMarkdownBody()` must be called AFTER the reading pane fragment is swapped into the DOM. Use `htmx.on("htmx:afterSwap", callback)` scoped to the reading pane container, or use `hx-on::after-swap` attribute on the reading pane div.
- **Lucide icon initialization** — The workspace calls `lucide.createIcons()` on page load, but htmx-swapped content won't have icons rendered. Either call `lucide.createIcons()` after each swap, or use inline SVGs in templates. Inline SVGs are simpler — copy the SVG paths from Lucide's icon set for the ~5 icons needed (star, star-off, check, circle, rss).
- **CSS variable availability** — App CSS is loaded inside the workspace page, which has all theme variables in scope. Use `var(--color-*)` tokens directly — they're available.
- **SPARQL boolean values** — RDF4J returns boolean literals as `"true"^^xsd:boolean` or `"false"^^xsd:boolean`. The SPARQL binding value will be the string `"true"` or `"false"`. Compare as strings in templates: `{% if isStarred == "true" %}`.
- **Date formatting** — Articles store `dcterms:created` as ISO 8601 strings. For display, either format server-side in the route handler before passing to the template, or use a simple Jinja2 filter. Relative dates ("2 hours ago") would need JS — use absolute dates for simplicity.

## Open Risks

- **Proxy query-string fix scope** — The fix touches platform code (`backend/app/apps/proxy.py`), which is nominally "read-only during M010." However, this is a bug fix that enables correct app functionality, not a feature addition. The fix is minimal (one line + one test) and required for any app using query params through the proxy.
- **Article body rendering quality** — If `body.set` was never called for an article (S01's poll-feeds doesn't call `body.set` — it stores the summary in `dcterms:description`), the reading pane falls back to the description. The full content extraction pipeline (S02's `extract_article_content()`) needs to be wired into the poll-feeds flow. This is a data availability issue, not a UI issue — the UI should handle both cases gracefully.

## Sources

- `apps/test-app/` — Canonical SDK app patterns (manifest, templates, route handlers)
- `backend/app/apps/proxy.py` — Platform proxy (query-string bug location)
- `backend/app/templates/browser/app_page.html` — Platform wrapper for app pages
- `frontend/static/css/theme.css` — CSS variable definitions
- `frontend/static/js/markdown-render.js` — Client-side markdown rendering
