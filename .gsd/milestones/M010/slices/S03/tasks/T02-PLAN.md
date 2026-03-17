---
estimated_steps: 6
estimated_files: 3
---

# T02: Build feed sidebar and article list route handlers + templates

**Slice:** S03 — Reader UI (split-pane layout)
**Milestone:** M010

## Description

Build the two navigation panels of the reader UI: the feed sidebar (left) showing subscriptions with unread counts and error indicators, and the article list (center) showing articles filtered by feed and state. Both are htmx fragment endpoints with SPARQL queries and Jinja2 templates.

**Skill note:** This task modifies `apps/rss-reader/app.py` which has import collision issues with `backend/app/`. See KNOWLEDGE.md for the `importlib.util.spec_from_file_location` pattern.

## Steps

1. **Add `/_fragments/feed-sidebar` GET route handler** in `apps/rss-reader/app.py`. The handler:
   - Runs a SPARQL query to get all FeedSubscription objects with unread counts:
     ```sparql
     SELECT ?sub ?feedUrl ?title ?errorCount ?lastError (COUNT(?unread) AS ?unreadCount) WHERE {
       ?sub a <urn:sempkm:model:rss-feeds:FeedSubscription> .
       ?sub <urn:sempkm:model:rss-feeds:feedUrl> ?feedUrl .
       OPTIONAL { ?sub <http://purl.org/dc/terms/title> ?title }
       OPTIONAL { ?sub <urn:sempkm:model:rss-feeds:errorCount> ?errorCount }
       OPTIONAL { ?sub <urn:sempkm:model:rss-feeds:lastError> ?lastError }
       OPTIONAL {
         ?unread a <urn:sempkm:model:rss-feeds:Article> .
         ?unread <urn:sempkm:model:rss-feeds:feedSource> ?sub .
         ?unread <urn:sempkm:model:rss-feeds:isRead> false .
       }
     } GROUP BY ?sub ?feedUrl ?title ?errorCount ?lastError
     ```
   - Parses bindings into a list of feed dicts: `{iri, url, title, unread_count, error_count, last_error}`
   - Passes feeds list to `ctx.render_template("feed-sidebar.html", feeds=feeds)`
   - Returns `HTMLResponse`

2. **Add `/_fragments/article-list` GET route handler** in `apps/rss-reader/app.py`. The handler:
   - Reads query params: `feed_iri` (optional — filters to specific feed), `filter` (optional — "unread", "starred", or "all" default)
   - Builds SPARQL query dynamically:
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
       # Dynamic FILTER clauses injected here
     } ORDER BY DESC(?created) LIMIT 100
     ```
   - When `feed_iri` is provided: add `FILTER(?sub = <{feed_iri}>)` (escape the IRI properly)
   - When `filter=unread`: add `?article <urn:sempkm:model:rss-feeds:isRead> false .` as a required triple
   - When `filter=starred`: add `?article <urn:sempkm:model:rss-feeds:isStarred> true .` as a required triple
   - Format dates server-side: parse ISO 8601 `created` strings and format as "Mar 17, 2026" or similar human-readable format. Use a helper function `_format_date(iso_str)` that returns the formatted string or empty string.
   - Passes articles list to `ctx.render_template("article-list.html", articles=articles, active_feed=feed_iri, active_filter=filter_mode)`
   - Returns `HTMLResponse`

3. **Create `apps/rss-reader/frontend/templates/feed-sidebar.html`** — Jinja2 template:
   - "All Feeds" item at top with `hx-get="/_fragments/article-list"` + `hx-target="#rss-article-list-content"` + `hx-swap="innerHTML"` (loads all articles)
   - Loop over feeds: each feed item has:
     - Feed title (or URL fallback)
     - Unread count badge (hidden when 0): `<span class="rss-unread-badge">{{ feed.unread_count }}</span>`
     - `hx-get="/_fragments/article-list?feed_iri={{ feed.iri }}"` + `hx-target="#rss-article-list-content"` + `hx-swap="innerHTML"`
     - Error indicator when `feed.error_count > 0`: small warning icon or red dot
     - `data-feed-iri="{{ feed.iri }}"` for testing
   - Subscribe button at bottom: opens the existing subscribe dialog (`hx-get="/_fragments/subscribe-dialog"` + `hx-target="#rss-reading-pane"` + `hx-swap="innerHTML"`)
   - Empty state when no feeds: "No feeds yet. Subscribe to get started."
   - Active feed highlight: add `.active` class when `feed.iri` matches some marker (client-side via JS in reader.js, or `hx-on::after-request` adding active class)

4. **Create `apps/rss-reader/frontend/templates/article-list.html`** — Jinja2 template:
   - Filter tabs at top: "All" / "Unread" / "Starred" — each with `hx-get="/_fragments/article-list?filter=all|unread|starred"` (preserve current `feed_iri` if set)
   - Loop over articles: each article item has:
     - Title (bold if unread: `{% if article.is_read != "true" %}font-weight: bold{% endif %}` or CSS class `.unread`)
     - Date (formatted by server) and source feed title
     - Author if present
     - `hx-get="/_fragments/article-reading-pane?article_iri={{ article.iri }}"` + `hx-target="#rss-reading-pane"` + `hx-swap="innerHTML"`
     - `data-article-iri="{{ article.iri }}"` for testing
     - CSS class `.rss-article-item`
   - Empty state: "No articles found." (or "No unread articles" / "No starred articles" depending on filter)
   - Article count indicator: "Showing N articles"

5. **Handle SPARQL boolean values** — In the route handler, normalize SPARQL boolean values before passing to template. SPARQL returns `"true"` or `"false"` as strings. In the route handler, convert: `is_read = binding.get("isRead", {}).get("value", "false") == "true"` and pass Python booleans to the template. This avoids `{% if article.is_read == "true" %}` string comparisons in templates.

6. **Verify** — Check that `ast.parse(open('apps/rss-reader/app.py').read())` succeeds. Verify templates parse as valid Jinja2 (no unclosed blocks). Verify SPARQL queries use correct type IRIs: `urn:sempkm:model:rss-feeds:Article`, `urn:sempkm:model:rss-feeds:FeedSubscription`, and property IRIs from the rss-feeds model.

## Must-Haves

- [ ] `/_fragments/feed-sidebar` route returns feed list with unread counts from SPARQL
- [ ] `/_fragments/article-list` route supports optional `feed_iri` and `filter` query params
- [ ] Feed sidebar template shows feeds with unread badges, error indicators, and subscribe button
- [ ] Article list template shows articles with read/unread visual state and filter tabs
- [ ] Dates formatted server-side as human-readable strings
- [ ] Empty states handled for no feeds and no articles
- [ ] SPARQL boolean values normalized to Python bools before template rendering

## Verification

- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `grep "feed-sidebar" apps/rss-reader/app.py` — route handler exists
- `grep "article-list" apps/rss-reader/app.py` — route handler exists
- Both templates exist and contain `hx-get` attributes for navigation
- Feed sidebar SPARQL uses `GROUP BY` with `COUNT` for unread counts

## Inputs

- `apps/rss-reader/app.py` — existing app with S01/S02 routes, constants (ARTICLE_TYPE, SUBSCRIPTION_TYPE, RSS_NS)
- `apps/rss-reader/services/feed_service.py` — subscribe/unsubscribe functions (not called in this task but the patterns are reference)
- `apps/rss-reader/frontend/templates/reader.html` — from T01, defines `#rss-article-list-content` and `#rss-reading-pane` as swap targets
- `apps/rss-reader/frontend/static/styles.css` — from T01, defines CSS classes for feed items, article items, badges, etc.
- S01 Summary: constants are `ARTICLE_TYPE = "urn:sempkm:model:rss-feeds:Article"`, `SUBSCRIPTION_TYPE = "urn:sempkm:model:rss-feeds:FeedSubscription"`, `RSS_NS = "urn:sempkm:model:rss-feeds:"`
- S02 Summary: subscribe dialog at `/_fragments/subscribe-dialog` exists and works; `HX-Trigger: feedsChanged` emitted on successful subscribe

## Observability Impact

- **New signals:** `/_fragments/feed-sidebar` and `/_fragments/article-list` return HTML fragments with `data-feed-iri` and `data-article-iri` attributes — inspectable via `document.querySelectorAll('[data-feed-iri]')` and `document.querySelectorAll('[data-article-iri]')`.
- **Inspection:** Feed sidebar errors visible via `.rss-feed-error-indicator` elements. SPARQL failures return `<div class="rss-error">` fragments. Filter state visible in article-list URL query params.
- **Failure visibility:** Empty states rendered as `.rss-empty-state` divs with descriptive text. SPARQL query failures caught and rendered as error fragments rather than HTTP 500s.
- **Diagnostic commands:** `grep "feed_sidebar_fragment\|article_list_fragment" apps/rss-reader/app.py` to confirm route handlers exist. Browser DevTools Network tab shows `/_fragments/feed-sidebar` and `/_fragments/article-list` requests with status 200.

## Expected Output

- `apps/rss-reader/app.py` — two new route handlers: `feed_sidebar_fragment()` and `article_list_fragment()`
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — feed list template with unread badges and error indicators
- `apps/rss-reader/frontend/templates/article-list.html` — article list template with filter tabs and read/unread styling
