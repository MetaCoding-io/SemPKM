---
estimated_steps: 7
estimated_files: 8
---

# T03: Create rss-reader app skeleton with poll-feeds task handler

**Slice:** S01 — Platform fix + Mental Model + App data pipeline
**Milestone:** M010

## Description

Creates the `rss-reader` application following the `apps/test-app/` patterns. The app has a `poll-feeds` task that queries existing FeedSubscription objects via SPARQL, fetches each feed using feedparser, and creates Article objects via `ctx.commands.bulk()`. This proves the full SDK → bulk EventStore → triplestore data pipeline.

The task handler functions should be structured so feed parsing logic is importable and testable by T04's test file.

## Steps

1. Create `apps/rss-reader/manifest.yaml`:
   ```yaml
   appId: "rss-reader"
   name: "RSS Reader"
   version: "1.0.0"
   description: "RSS/Atom feed reader that subscribes to feeds, polls for new articles, and presents them in a clean reader UI."
   author:
     name: "SemPKM"
   license: "MIT"

   dependencies:
     platform: ">=0.1.0"
     models:
       - id: "rss-feeds"
         version: ">=1.0.0"

   permissions:
     commands:
       - "object.create"
       - "object.patch"
       - "edge.create"
       - "body.set"
     sparql:
       read: true
     backgroundTasks: true
     network:
       - "*"

   backend:
     entrypoint: "app:rss_reader_app"
     requirements: "requirements.txt"

   tasks:
     - id: "poll-feeds"
       description: "Poll subscribed RSS/Atom feeds for new articles"
       interval: "5m"
       configurable: true
       retryPolicy:
         maxRetries: 2
         backoffMultiplier: 2
         maxBackoff: "5m"

   frontend:
     staticDir: "frontend/static"
     css:
       - "styles.css"
     js: []

   ui:
     pages:
       - id: "reader"
         path: "/reader"
         label: "RSS Reader"
         icon: "rss"
         nav: "apps"
         fragment: "reader"
     contributions:
       views:
         - id: "unread-articles"
           label: "Unread Articles"
           icon: "mail"
           fragment: "unread-view"
         - id: "starred-articles"
           label: "Starred Articles"
           icon: "star"
           fragment: "starred-view"
       commandPalette:
         - id: "subscribe-feed"
           label: "Subscribe to Feed..."
           keywords: ["rss", "feed", "subscribe", "atom"]
           actionType: "dialog"
           fragment: "subscribe-dialog"
         - id: "open-reader"
           label: "Open RSS Reader"
           keywords: ["rss", "reader", "feeds", "articles"]
           actionType: "navigate"
           path: "/reader"
   ```

2. Create `apps/rss-reader/requirements.txt`:
   ```
   feedparser>=6.0
   ```

3. Create `apps/rss-reader/app.py` with the following structure:

   **Module-level constants:**
   - `ARTICLE_TYPE = "urn:sempkm:model:rss-feeds:Article"`
   - `SUBSCRIPTION_TYPE = "urn:sempkm:model:rss-feeds:FeedSubscription"`
   - `RSS_NS = "urn:sempkm:model:rss-feeds:"`
   - App instance: `rss_reader_app = App("rss-reader")`

   **Helper functions (importable by test file):**
   - `parse_feed(feed_url: str) -> dict` — wraps `feedparser.parse(feed_url)`, returns parsed feed dict
   - `entry_to_article(entry: dict, feed_iri: str, app_id: str) -> dict` — converts a feedparser entry to an article params dict suitable for `object.create`:
     - Mints article IRI: `urn:sempkm:app:rss-reader:article-{hash}` where hash = SHA-256 of feed_url + entry.id (or entry.link as fallback)
     - Maps: entry.title → dcterms:title, entry.link → rss:link, entry.author → rss:author, entry.published_parsed → dcterms:created (ISO 8601), entry.summary → dcterms:description, feed_iri → rss:feedSource, entry.id → rss:articleId
     - Returns dict with `iri`, `type`, and `properties` keys
   - `get_existing_article_iris(graph_client, feed_iri: str) -> set[str]` — queries triplestore for existing article IRIs from a given feed (for dedup)

   **Task handler:**
   - `@rss_reader_app.task("poll-feeds")` decorated function
   - Queries all FeedSubscription objects via `ctx.graph.query()` SPARQL
   - For each subscription: parses feed, gets existing articles for dedup, creates new articles via `ctx.commands.bulk()`
   - Logs count of new articles created per feed
   - Returns summary dict `{"feeds_polled": N, "articles_created": M}`

   **Route handlers (stubs for now — S03 builds the real UI):**
   - `/_fragments/reader` — minimal reader page placeholder
   - `/_fragments/unread-view` — stub view fragment
   - `/_fragments/starred-view` — stub view fragment
   - `/_fragments/subscribe-dialog` — stub dialog fragment

   **Lifecycle hooks:**
   - `@rss_reader_app.on_startup` — logs startup
   - `@rss_reader_app.on_shutdown` — logs shutdown

4. Create `apps/rss-reader/frontend/templates/main.html`:
   ```html
   <div class="rss-reader-main">
     <h2>RSS Reader</h2>
     <p>Feed reader coming soon. Use the command palette to subscribe to feeds.</p>
   </div>
   ```

5. Create `apps/rss-reader/frontend/templates/reader.html` — same stub content.

6. Create stub templates for view and dialog fragments:
   - `apps/rss-reader/frontend/templates/unread-view.html`
   - `apps/rss-reader/frontend/templates/starred-view.html`
   - `apps/rss-reader/frontend/templates/subscribe-dialog.html`

7. Create `apps/rss-reader/frontend/static/styles.css` — minimal placeholder styles.

**Important constraints:**
- The `entry_to_article()` function MUST be a standalone pure function (no SDK dependency) so T04 can import and test it directly.
- Article IRI minting MUST use SHA-256 hash of (feed_url + entry_id) for deterministic, dedup-friendly IRIs.
- The poll-feeds handler MUST use `ctx.commands.bulk()` (not individual `execute()` calls) for performance per the bulk EventStore design (APP-11).
- The `type` field in object.create params MUST use the full IRI `urn:sempkm:model:rss-feeds:Article` — this is the pattern that T01's IRI prefix fix enables.

## Must-Haves

- [ ] `apps/rss-reader/manifest.yaml` validates against `AppManifestSchema`
- [ ] `app.py` has `rss_reader_app = App("rss-reader")` instance
- [ ] `poll-feeds` task handler queries subscriptions, parses feeds, creates articles via bulk
- [ ] `entry_to_article()` is a standalone pure function importable by tests
- [ ] Article IRIs use deterministic SHA-256 hash
- [ ] Article type uses full IRI `urn:sempkm:model:rss-feeds:Article`
- [ ] `requirements.txt` includes feedparser
- [ ] All fragment routes have stub templates

## Verification

- `python -c "from backend.app.apps.manifest import parse_app_manifest; m = parse_app_manifest('apps/rss-reader/manifest.yaml'); print(f'OK: {m.appId} v{m.version}, tasks: {[t.id for t in m.tasks]}')"` — prints OK with poll-feeds task
- `python -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('Syntax OK')"` — no syntax errors
- `python -c "import sys; sys.path.insert(0, 'apps/rss-reader'); from app import entry_to_article; print('Import OK')"` — function is importable

## Observability Impact

- Signals added/changed: `poll-feeds` task logs `"Polled {feed_url}: {N} new articles"` per feed and returns `{"feeds_polled": N, "articles_created": M}` summary
- How a future agent inspects this: Admin > Applications > RSS Reader > task history shows poll-feeds runs with result JSON
- Failure state exposed: Feed parse errors logged with feed URL, subscription error count incremented

## Inputs

- `apps/test-app/` — reference implementation for app structure (manifest, app.py, templates)
- `apps/test-app/manifest.yaml` — pattern for manifest fields
- `apps/test-app/app.py` — pattern for route handlers, task handlers, lifecycle hooks
- `backend/sdk/sempkm_app_sdk/app.py` — App class API (decorators, build_asgi_app)
- `backend/sdk/sempkm_app_sdk/context.py` — AppContext API (commands, graph, state, settings)
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — CommandClient.bulk() context manager API
- T01 output: fixed `_check_iri_prefix()` that allows model type IRIs
- T02 output: `models/rss-feeds/` model with type IRIs

## Expected Output

- `apps/rss-reader/manifest.yaml` — complete app manifest
- `apps/rss-reader/app.py` — app with poll-feeds task, stub routes, helper functions
- `apps/rss-reader/requirements.txt` — feedparser dependency
- `apps/rss-reader/frontend/templates/*.html` — 5 stub template files
- `apps/rss-reader/frontend/static/styles.css` — placeholder styles
