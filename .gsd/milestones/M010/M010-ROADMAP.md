# M010: RSS Reader App

**Vision:** The first real application on SemPKM's app platform — an RSS/Atom feed reader that subscribes to feeds, polls for new articles, and presents them in a clean split-pane reader UI. Articles are first-class RDF objects, browsable in the object browser, searchable via FTS, and linkable to Concepts, Notes, and Projects. The milestone validates M009's app platform end-to-end with realistic load: background polling, bulk ingestion, custom object renderers, workspace contributions, and command palette actions.

## Success Criteria

- User installs the `rss-feeds` Mental Model and `rss-reader` app from the admin portal
- User subscribes to 3+ real RSS/Atom feeds by URL
- Articles appear within one poll cycle (no manual trigger needed beyond initial install)
- User opens an article and sees the custom reader renderer (clean typography, not default SHACL form)
- User stars an article; the star persists across page reload
- User marks articles as read/unread; unread count updates in feed sidebar
- "Unread Articles" and "Starred Articles" workspace views show correct filtered results
- Articles appear in the object browser under their RDF type, searchable via Ctrl+K
- User imports an OPML file with 5+ feeds; all subscriptions appear
- Admin > Applications > RSS Reader shows task history with successful `poll-feeds` runs
- Feed errors (404, timeout, malformed XML) display per-feed error indicators, not app crashes

## Key Risks / Unknowns

- **IRI prefix enforcement blocks type references** — The SDK's `_check_iri_prefix()` rejects ALL `urn:` IRIs that don't start with `urn:sempkm:app:{appId}:`. This means `object.create` with `type: "urn:sempkm:model:rss-feeds:Article"` will raise `PermissionError`. The test-app never calls `commands.execute()` with real params — this path is untested. This is a platform bug that must be fixed before any app can create typed objects.

- **trafilatura install in Docker** — The Docker image is `python:3.12-slim` with only `curl` installed. trafilatura depends on lxml (C extension). Pre-built wheels exist for Linux x86_64/Python 3.12 but installation in the app venv via `uv pip install` has not been proven inside the container.

- **Feed parsing reliability** — Real-world RSS feeds are messy (invalid XML, mixed encodings, non-standard dates). feedparser handles most cases but edge cases will surface with real feeds.

## Proof Strategy

- **IRI prefix enforcement** → retire in S01 by fixing `_check_iri_prefix()` to whitelist model and standard namespace IRIs, proving with a unit test that `object.create` succeeds with a model type IRI
- **trafilatura install** → retire in S02 by including trafilatura in requirements.txt and verifying the app installs and starts in the Docker container. If it fails, fall back to feed-provided summaries only (trafilatura becomes optional)
- **Feed parsing reliability** → retire in S02 by parsing 3+ real feeds (RSS 2.0, Atom 1.0, JSON Feed) and asserting article count > 0 in unit tests

## Verification Classes

- Contract verification: pytest unit tests for feed parsing, content extraction, RDF mapping, IRI prefix fix, OPML parsing; target 80+ new tests
- Integration verification: real app subprocess round-trip (model install → app install → poll-feeds task → articles in triplestore)
- Operational verification: feed polling runs on schedule, handles feed errors gracefully, articles survive platform restart
- UAT / human verification: reader UI usability (typography, star toggle, feed sidebar navigation)

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slice deliverables complete (S01–S06)
- `rss-feeds` Mental Model installable independently and defines Article, FeedSubscription types
- `rss-reader` app installs, starts, serves reader UI, creates articles via bulk EventStore, runs poll-feeds on schedule
- Reader UI displays articles with custom renderer, star toggle works, mark read/unread works
- Workspace views (Unread, Starred) and command palette entries (Subscribe, Mark All Read) functional
- OPML import creates subscriptions from uploaded file
- Admin portal shows RSS Reader with task history, logs, lifecycle actions
- Playwright E2E tests cover install → subscribe → poll → read → star → workspace views → admin → uninstall
- User guide documents RSS Reader for users
- Success criteria re-checked against live Docker stack behavior

## Requirement Coverage

- Covers: RSS-01 (feed subscription + polling), RSS-02 (reader UI), RSS-03 (custom renderers — Article only), RSS-05 (OPML import), RSS-06 (workspace contributions), RSS-07 (rss-feeds model only), RSS-08 (feed discovery + content extraction)
- Deferred to M011: RSS-04 (Hypothesis sync), RSS-07 partial (web-annotations model)
- Orphan risks: none — RSS-03 for `oa:Annotation` renderer deferred alongside RSS-04

## Slices

- [x] **S01: Platform fix + Mental Model + App data pipeline** `risk:high` `depends:[]`
  > After this: SDK IRI prefix bug fixed with tests. `rss-feeds` model installed in triplestore (Article, FeedSubscription types visible). `rss-reader` app skeleton installs, starts, and the `poll-feeds` task creates real articles from a test feed via bulk EventStore. Articles visible in object browser.

- [x] **S02: Feed service + content extraction + feed management** `risk:medium` `depends:[S01]`
  > After this: User subscribes to feeds by URL, feed discovery finds feeds from website URLs, trafilatura extracts full article content, conditional GET (ETag/Last-Modified) avoids redundant downloads, per-feed error tracking reports failures. Unit tests cover RSS 2.0, Atom 1.0, and JSON Feed formats.

- [x] **S03: Reader UI (split-pane layout)** `risk:low` `depends:[S01]`
  > After this: RSS Reader standalone page shows split-pane layout — feed sidebar with unread counts, article list with title/date/source, and reading pane with clean markdown-rendered article body. Star toggle and mark read/unread controls work. All via htmx fragments.

- [x] **S04: Workspace contributions + custom renderer** `risk:low` `depends:[S02,S03]`
  > After this: "Unread Articles" and "Starred Articles" views in workspace Views section. "Related Articles" in right pane. "Subscribe to Feed...", "Mark All as Read", "Open RSS Reader" in command palette. Custom `rss:Article` read renderer replaces default SHACL form when opening an article from the object browser.

- [x] **S05: OPML import + app settings** `risk:low` `depends:[S02]`
  > After this: User uploads an OPML file and subscriptions are created for all feeds in it. App settings page configures poll interval and reader preferences. Feed categories from OPML preserved as tags.

- [x] **S06: E2E tests + user guide** `risk:low` `depends:[S03,S04,S05]`
  > After this: Playwright E2E spec covers full lifecycle (install model → install app → subscribe → poll → read article → star → workspace views → admin task history → uninstall). User guide Chapter 32 documents RSS Reader setup and usage.

## Boundary Map

### S01 → S02

Produces:
- Fixed `CommandClient._check_iri_prefix()` — model namespace IRIs (`urn:sempkm:model:*`), standard vocabulary IRIs (`http://`, `https://`), and `rdf:type` references pass validation
- `models/rss-feeds/` — Mental Model with OWL ontology (`rss:FeedSubscription`, `rss:Article`), SHACL shapes, manifest.yaml
- `apps/rss-reader/manifest.yaml` — complete manifest with permissions, tasks, UI stubs
- `apps/rss-reader/app.py` — RSSReaderApp skeleton with `poll-feeds` task handler that creates articles via `ctx.commands.bulk()`
- Proven data path: feedparser → object.create via SDK → bulk EventStore → articles queryable in triplestore

### S01 → S03

Produces:
- Installed `rss-feeds` model with type IRIs for Article and FeedSubscription
- Working app process serving fragments on UDS
- Template rendering via `ctx.render_template()`

### S02 → S04

Produces:
- `FeedService` with subscription management, feed parsing, content extraction, feed discovery
- Feed and article data in triplestore (subscriptions, articles with bodies, read/star state)
- App state storage patterns (ETag, poll timestamps, error counts via `ctx.state`)

### S02 → S05

Produces:
- `FeedService.subscribe()` method for creating subscriptions programmatically
- Feed subscription creation pattern (object.create with FeedSubscription type)

### S03 → S04

Produces:
- Reader UI template patterns (article list rendering, reading pane, fragment endpoints)
- `reader.css` and `reader.js` with established styling patterns

### S03 → S06

Produces:
- Complete reader UI with stable CSS selectors for E2E testing

### S04 → S06

Produces:
- Workspace contributions with stable UI for E2E assertions
- Custom renderer with stable fragment endpoint

### S05 → S06

Produces:
- OPML import UI with file upload endpoint
- Settings page with configurable poll interval
