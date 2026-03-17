---
estimated_steps: 8
estimated_files: 6
---

# T03: Build reading pane + star/read/unsubscribe action handlers + workspace views

**Slice:** S03 — Reader UI (split-pane layout)
**Milestone:** M010

## Description

Build the reading pane (right panel) that displays article content with markdown rendering, plus the action handlers (star toggle, read toggle, mark-all-read, unsubscribe) that mutate article/subscription state. Also replace the workspace view stubs (Unread Articles, Starred Articles) with real filtered article lists.

This task completes all user-facing interactivity for the reader UI. After this, the full read→star→mark-read flow works end-to-end (pending data in the triplestore).

**Important patterns:**
- Article bodies are stored as markdown via `body.set`. The body is accessible via the `urn:sempkm:body` predicate in SPARQL. Embed raw markdown in `<script type="text/plain" id="md-source-...">` for `renderMarkdownBody()`.
- `renderMarkdownBody(sourceId, targetId)` is already loaded in the workspace page (from `markdown-render.js`). reader.js (from T01) calls it after htmx swap.
- Star/read toggles use `object.patch` via `ctx.commands.execute("object.patch", {...})`.
- Unsubscribe uses `feed_service.unsubscribe()` (soft-delete, sets isActive=False).

## Steps

1. **Add `/_fragments/article-reading-pane` GET route handler** in `apps/rss-reader/app.py`:
   - Reads `article_iri` from query params
   - If no `article_iri`, return the empty state HTML: `<div class="rss-reading-pane-empty"><p>Select an article to read</p></div>`
   - SPARQL query for the single article:
     ```sparql
     SELECT ?title ?link ?author ?created ?isStarred ?isRead ?body ?feedTitle ?description WHERE {
       <{article_iri}> a <urn:sempkm:model:rss-feeds:Article> .
       OPTIONAL { <{article_iri}> <http://purl.org/dc/terms/title> ?title }
       OPTIONAL { <{article_iri}> <urn:sempkm:model:rss-feeds:link> ?link }
       OPTIONAL { <{article_iri}> <urn:sempkm:model:rss-feeds:author> ?author }
       OPTIONAL { <{article_iri}> <http://purl.org/dc/terms/created> ?created }
       OPTIONAL { <{article_iri}> <urn:sempkm:model:rss-feeds:isStarred> ?isStarred }
       OPTIONAL { <{article_iri}> <urn:sempkm:model:rss-feeds:isRead> ?isRead }
       OPTIONAL { <{article_iri}> <urn:sempkm:body> ?body }
       OPTIONAL { <{article_iri}> <http://purl.org/dc/terms/description> ?description }
       OPTIONAL {
         <{article_iri}> <urn:sempkm:model:rss-feeds:feedSource> ?sub .
         ?sub <http://purl.org/dc/terms/title> ?feedTitle .
       }
     }
     ```
   - Parse bindings into an article dict with Python booleans for is_starred/is_read
   - Format the `created` date as human-readable
   - Determine body content: use `body` if present, fall back to `description`, or `None`
   - Generate a unique ID suffix for the markdown source/target elements (e.g., hash of article_iri)
   - Render `article-reading-pane.html` with article data and md_source_id/md_target_id

2. **Create `apps/rss-reader/frontend/templates/article-reading-pane.html`**:
   - Article header: title (h1), author, formatted date, feed source name
   - Original link: `<a href="{{ article.link }}" target="_blank" rel="noopener">View Original</a>`
   - Star button: include `star-button.html` template with current star state
   - Article body:
     - If body content exists: `<script type="text/plain" id="md-source-{{ md_id }}">{{ body }}</script>` + `<div id="md-target-{{ md_id }}" class="rss-article-body"></div>`
     - If no body: `<div class="rss-article-body"><p class="rss-no-content">No full content available. <a href="{{ article.link }}" target="_blank">Visit the original article</a>.</p></div>`
   - Fire-and-forget mark-read (when article is currently unread):
     ```html
     {% if not article.is_read %}
     <div hx-post="/_fragments/toggle-read"
          hx-vals='{"article_iri": "{{ article.iri }}"}'
          hx-trigger="load"
          hx-swap="none"
          style="display:none"></div>
     {% endif %}
     ```
   - Note: The markdown `<script>` tag content does NOT need Jinja2 escaping because `<script type="text/plain">` content is treated as raw text by HTML parsers. However, if using `{{ body }}` inside it, Jinja2 autoescape will escape `<` and `>`. Use `{{ body | safe }}` since the markdown content doesn't contain user-hostile HTML (it's server-generated from trafilatura or feed summaries).

3. **Create `apps/rss-reader/frontend/templates/star-button.html`** — micro-template for just the star button:
   ```html
   <button class="rss-star-btn {% if is_starred %}starred{% endif %}"
           hx-post="/_fragments/toggle-star"
           hx-vals='{"article_iri": "{{ article_iri }}"}'
           hx-target="closest .rss-star-btn"
           hx-swap="outerHTML"
           title="{% if is_starred %}Unstar{% else %}Star{% endif %} article">
     {% if is_starred %}
     <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
     {% else %}
     <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
     {% endif %}
   </button>
   ```
   Uses inline SVG (Lucide star icon paths) — filled when starred, outline when not. `hx-swap="outerHTML"` replaces just this button on toggle.

4. **Add `/_fragments/toggle-star` POST route handler**:
   - Reads `article_iri` from form body
   - SPARQL query current `isStarred` value: `SELECT ?val WHERE { <{iri}> <rss:isStarred> ?val }`
   - Toggle: if current is "true", patch to false; otherwise patch to true
   - `await ctx.commands.execute("object.patch", {"iri": article_iri, "properties": {f"{RSS_NS}isStarred": new_value}})`
   - Return `HTMLResponse(ctx.render_template("star-button.html", article_iri=article_iri, is_starred=new_value))`

5. **Add `/_fragments/toggle-read` POST route handler**:
   - Reads `article_iri` from form body
   - Patches `isRead` to `true` (mark-read on article open is always "mark as read")
   - If an explicit `toggle` param is present, query current value and flip it
   - `await ctx.commands.execute("object.patch", {"iri": article_iri, "properties": {f"{RSS_NS}isRead": new_value}})`
   - Return `HTMLResponse("")` with status 200 (fire-and-forget, no visual update needed for the reading pane)
   - Add `HX-Trigger: articleStateChanged` header to signal article list refresh

6. **Add `/_fragments/mark-all-read` POST route handler**:
   - Reads `feed_iri` from form body (optional — if absent, mark all articles across all feeds)
   - SPARQL query for all unread article IRIs (optionally filtered by feed):
     ```sparql
     SELECT ?article WHERE {
       ?article a <urn:sempkm:model:rss-feeds:Article> .
       ?article <urn:sempkm:model:rss-feeds:isRead> false .
       # FILTER(?sub = <feed_iri>) if feed_iri provided
     }
     ```
   - Batch patch each to `isRead: true` via `ctx.commands.bulk()` (or individual patches if count is small)
   - Return the updated feed sidebar fragment (call the feed sidebar SPARQL and render)

7. **Add `/_fragments/unsubscribe` POST route handler**:
   - Reads `feed_iri` from form body
   - Calls `unsubscribe(ctx, feed_iri)` from `services.feed_service`
   - Returns updated feed sidebar fragment with `HX-Trigger: feedsChanged`

8. **Replace unread-view.html and starred-view.html stubs**:
   - `unread-view.html`: Replace stub with a container that loads articles filtered by unread:
     ```html
     <div class="rss-workspace-view" id="rss-unread-view">
       <h3>Unread Articles</h3>
       <div hx-get="/_fragments/article-list?filter=unread"
            hx-trigger="load"
            hx-swap="innerHTML">
         <div class="tree-empty">Loading unread articles...</div>
       </div>
     </div>
     ```
   - `starred-view.html`: Same pattern with `?filter=starred`
   - Both views reuse the `/_fragments/article-list` endpoint with filter params, which T02 already supports. Articles in these views link to the full reader page (or if opened from workspace, just show the list without the reading pane).

## Must-Haves

- [ ] Reading pane shows article header (title, author, date, link) and markdown-rendered body
- [ ] Reading pane falls back to description or "no content" message when body is absent
- [ ] Star toggle button flips between filled/outline star via object.patch
- [ ] Mark-as-read fires automatically on article open (fire-and-forget hidden div)
- [ ] Mark-all-read patches all unread articles for a feed
- [ ] Unsubscribe calls feed_service.unsubscribe and refreshes sidebar
- [ ] Unread and Starred workspace views load filtered article lists
- [ ] Star button uses inline SVG (not Lucide data-lucide attribute) for immediate rendering

## Verification

- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `grep "toggle-star" apps/rss-reader/app.py` — route handler exists
- `grep "toggle-read" apps/rss-reader/app.py` — route handler exists
- `grep "mark-all-read" apps/rss-reader/app.py` — route handler exists
- `grep "unsubscribe" apps/rss-reader/app.py` — route handler exists
- `grep "article-reading-pane" apps/rss-reader/app.py` — route handler exists
- Templates exist: article-reading-pane.html, star-button.html
- unread-view.html contains `filter=unread`, starred-view.html contains `filter=starred`

## Observability Impact

- **HX-Trigger headers:** `articleStateChanged` emitted after toggle-read/toggle-star; `feedsChanged` emitted after unsubscribe. These drive htmx-driven UI refresh in the reader shell.
- **Data attributes on reading pane:** `data-article-iri`, `data-starred`, `data-read` on the pane root for test/diagnostic inspection.
- **SPARQL error fragments:** All route handlers return `<div class="rss-error">` HTML on SPARQL failure, visible in both UI and curl diagnostics.
- **Inspection commands:**
  - `curl /_fragments/article-reading-pane?article_iri=<IRI>` — returns full reading pane HTML
  - `curl -X POST /_fragments/toggle-star -d article_iri=<IRI>` — returns updated star button
  - `curl -X POST /_fragments/toggle-read -d article_iri=<IRI>` — returns empty with HX-Trigger header
  - `curl -X POST /_fragments/mark-all-read -d feed_iri=<IRI>` — returns updated sidebar
  - `curl -X POST /_fragments/unsubscribe -d feed_iri=<IRI>` — returns updated sidebar
- **Failure visibility:** Mark-all-read logs individual patch failures but continues best-effort. Unsubscribe returns error fragment on failure.

## Inputs

- `apps/rss-reader/app.py` — from T02, has feed sidebar and article list routes; constants ARTICLE_TYPE, SUBSCRIPTION_TYPE, RSS_NS
- `apps/rss-reader/services/feed_service.py` — `unsubscribe(ctx, subscription_iri)` function for soft-delete
- `apps/rss-reader/frontend/templates/reader.html` — from T01, defines `#rss-reading-pane` as swap target
- `apps/rss-reader/frontend/static/styles.css` — from T01, defines `.rss-star-btn`, `.rss-article-body`, `.rss-reading-pane-empty` classes
- `apps/rss-reader/frontend/static/reader.js` — from T01, handles `htmx:afterSwap` to call `renderMarkdownBody()` on elements inside `#rss-reading-pane`
- S01 Forward Intelligence: `_mint_article_iri()` pattern, bulk command pattern `async with ctx.commands.bulk()`
- S02 Summary: `unsubscribe()` does soft-delete via `object.patch` setting `isActive=False`

## Expected Output

- `apps/rss-reader/app.py` — 5 new route handlers: article-reading-pane, toggle-star, toggle-read, mark-all-read, unsubscribe
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — reading pane with markdown body and fire-and-forget mark-read
- `apps/rss-reader/frontend/templates/star-button.html` — star toggle micro-template with inline SVG
- `apps/rss-reader/frontend/templates/unread-view.html` — workspace view loading filtered articles
- `apps/rss-reader/frontend/templates/starred-view.html` — workspace view loading filtered articles
