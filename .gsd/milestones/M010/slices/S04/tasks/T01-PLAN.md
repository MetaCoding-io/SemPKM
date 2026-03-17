---
estimated_steps: 7
estimated_files: 4
---

# T01: Add right pane, custom renderer, and mark-all-read command to manifest + app

**Slice:** S04 — Workspace contributions + custom renderer
**Milestone:** M010

## Description

Add the three workspace contributions to the RSS Reader: a "Related Articles" right pane section, a custom `rss:Article` object renderer, and a "Mark All as Read" command palette entry. This involves manifest changes and two new route handlers + templates in `app.py`, plus a small tweak to the existing `mark_all_read_route()` to detect when it's called from the command palette (vs the reader UI).

**Relevant skills:** None required — this is Python route handlers + Jinja2 templates following established patterns.

## Steps

1. **Update `manifest.yaml`** — Add three new sections under `ui.contributions`:
   - `rightPane` array with one entry: `id: "related-articles"`, `label: "Related Articles"`, `icon: "newspaper"`, `fragment: "related-articles"`, `targetTypes: ["*"]`, `priority: 60`
   - `objectRenderers` array with one entry: `type: "urn:sempkm:model:rss-feeds:Article"`, `modes.read: "article-read-renderer"` (D165: must be full IRI, not `rss:Article`)
   - Add `mark-all-read` entry to the existing `commandPalette` array: `id: "mark-all-read"`, `label: "Mark All as Read"`, `keywords: ["rss", "mark", "read", "unread"]`, `actionType: "post"`, `endpoint: "/_fragments/mark-all-read"`

2. **Add `/_fragments/related-articles` route handler** in `app.py`:
   - GET handler receiving `?iri=<encoded_iri>` query param (URL-encoded by the platform)
   - Build SPARQL query finding articles that share the same `feedSource` or `bpkm:tags` as the focused IRI, excluding the focused IRI itself, limited to 10, ordered by `dcterms:created DESC`
   - Handle empty IRI → return empty state HTML
   - Handle SPARQL error → return `<div class="rss-error">` message
   - Parse bindings using existing `_format_date()` helper
   - Render `related-articles.html` template with articles list

3. **Create `related-articles.html` template**:
   - If no articles: render `<div class="rss-empty-state">No related articles found</div>`
   - Otherwise: render a list of articles with `data-article-iri` attributes, each showing title, date, and feed source
   - Each article item should be clickable (using htmx or an onclick that calls `openTab` with the article IRI)
   - Use existing `.rss-*` CSS classes from `styles.css` for consistent styling

4. **Add `/_fragments/article-read-renderer` route handler** in `app.py`:
   - GET handler receiving `?iri=<encoded_iri>` query param
   - Reuse the same SPARQL query pattern as `article_reading_pane_fragment()` (single article with title, link, author, created, isStarred, body, description, feedTitle)
   - **Do NOT** include the fire-and-forget mark-read `<div>` — this is for the object browser, not the reader
   - **Do** include the star button via `{% include "star-button.html" %}`
   - **Do** use `data-md-source`/`data-md-target` for markdown rendering (platform's `object_tab_app.html` loads app JS)
   - Handle missing IRI and article-not-found cases with error messages

5. **Create `article-read-renderer.html` template**:
   - Similar structure to `article-reading-pane.html` but:
     - No fire-and-forget mark-read trigger
     - The platform's `object_tab_app.html` already provides the outer toolbar (label, type badge, favorite, edit toggle) — this fragment only needs the article content area
   - Include article header (title, meta, star button), markdown body, and "no content" fallback
   - Use `data-md-source`/`data-md-target` attributes with unique IDs for markdown rendering

6. **Update `mark_all_read_route()`** to detect command palette context:
   - Check `request.headers.get("HX-Target")` — if it's `#modal-container`, the call came from the command palette
   - When from command palette: after marking articles read, return a short success/confirmation HTML message (e.g., `<div class="rss-success">Marked N articles as read</div>`) with `HX-Trigger: articleStateChanged, feedsChanged` headers
   - When from reader UI (existing behavior): return the updated feed sidebar HTML as before
   - This ensures the command palette shows a meaningful confirmation instead of rendering sidebar HTML into the modal container

7. **Validate syntax**:
   - `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"`
   - `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"`

## Must-Haves

- [ ] `manifest.yaml` has `rightPane` with `related-articles` entry
- [ ] `manifest.yaml` has `objectRenderers` with `type: "urn:sempkm:model:rss-feeds:Article"` (full IRI) and `modes.read: "article-read-renderer"`
- [ ] `manifest.yaml` has `mark-all-read` in `commandPalette` with `actionType: "post"` and `endpoint: "/_fragments/mark-all-read"`
- [ ] `/_fragments/related-articles` route exists and queries triplestore for related articles
- [ ] `/_fragments/article-read-renderer` route exists and renders article content without mark-read trigger
- [ ] `related-articles.html` template exists with `data-article-iri` attributes for testability
- [ ] `article-read-renderer.html` template uses `data-md-source`/`data-md-target` for markdown rendering
- [ ] `mark_all_read_route()` returns confirmation message when `HX-Target` is `#modal-container`
- [ ] Both `.py` and `.yaml` files parse without syntax errors

## Verification

- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` — valid YAML
- Grep `objectRenderers` in manifest → type is `urn:sempkm:model:rss-feeds:Article`
- Grep `related-articles` in manifest → present in `rightPane`
- Grep `mark-all-read` in manifest → present in `commandPalette`

## Inputs

- `apps/rss-reader/manifest.yaml` — current manifest with views and commandPalette (subscribe-feed, open-reader)
- `apps/rss-reader/app.py` — current app with S03's route handlers, helpers (`_sparql_bool`, `_format_date`, `_sparql_int`), and constants (`ARTICLE_TYPE`, `RSS_NS`)
- `apps/rss-reader/frontend/templates/article-reading-pane.html` — reference template for reading pane layout, `data-md-source`/`data-md-target` pattern, star button inclusion
- `apps/rss-reader/frontend/templates/star-button.html` — self-replacing star button component
- `apps/test-app/manifest.yaml` — reference for `rightPane` and `objectRenderers` syntax
- `apps/test-app/app.py` — reference for renderer fragment handler pattern (`read_renderer_fragment`)

**Key constraints from research:**
- objectRenderers type MUST be full IRI `urn:sempkm:model:rss-feeds:Article` (D165 — registry does exact string comparison)
- Right pane fragment receives `?iri=<encoded_iri>` — platform URL-encodes it
- Right pane uses `hx-trigger="toggle once"` — fragment must return complete HTML
- mark-all-read via command palette sends POST; response renders into `#modal-container`
- The SPARQL for related articles uses UNION: same feedSource OR shared tags (via `urn:sempkm:model:basic-pkm:tags`)
- For non-Article objects with no tags, the result will be empty — render empty state

## Observability Impact

- **New signals:** `/_fragments/related-articles` and `/_fragments/article-read-renderer` log SPARQL errors via `logger.warning()` and return `<div class="rss-error">` HTML fragments on failure. `mark_all_read_route()` returns `<div class="rss-success">Marked N articles as read</div>` when invoked from command palette (HX-Target: `#modal-container`).
- **Inspection:** `data-article-iri` attributes on related-articles list items enable test automation targeting. HX-Trigger headers (`articleStateChanged`, `feedsChanged`) on mark-all-read response enable downstream UI refresh.
- **Failure visibility:** Empty `?iri=` param → empty state HTML. SPARQL errors → `rss-error` div. Article not found → `rss-reading-pane-empty` div with "Article not found" message.

## Expected Output

- `apps/rss-reader/manifest.yaml` — updated with rightPane, objectRenderers, and mark-all-read commandPalette entry
- `apps/rss-reader/app.py` — two new route handlers (`related_articles_fragment`, `article_read_renderer_fragment`), updated `mark_all_read_route()`
- `apps/rss-reader/frontend/templates/related-articles.html` — new template for right pane related articles
- `apps/rss-reader/frontend/templates/article-read-renderer.html` — new template for custom Article renderer
