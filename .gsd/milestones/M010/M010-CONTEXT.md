---
depends_on: [M009]
---

# M010: RSS Reader & Hypothesis App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

The first app built on SemPKM's app platform (M009). An RSS/Atom feed reader with Hypothesis annotation sync — subscribe to feeds, read articles in a clean reader interface, highlight and annotate via Hypothesis, and have everything stored as first-class RDF objects in the knowledge graph. Includes two new Mental Models (`rss-feeds`, `web-annotations`) and the full app implementation exercising all three levels of frontend integration.

This milestone validates the app platform end-to-end with a real, useful application. It's the proof-of-concept that M009's infrastructure works for non-trivial use cases: background polling, bulk ingestion, external API integration, custom object renderers, workspace contributions, and command palette actions.

## Why This Milestone

The RSS Reader was the motivating use case for the entire app platform design. The research document (`docs/research/rss-reader-hypothesis-integration.md`) concluded "very feasible" and mapped all integration points. Without a real app, the platform is untested infrastructure — the RSS Reader forces every subsystem to work together under realistic load (dozens of feeds, hundreds of articles, periodic sync).

The user gets immediate value: a reading workflow integrated with their knowledge graph. Articles, highlights, and annotations are RDF objects — linkable to Concepts, searchable, explorable in views and the spatial canvas.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open "RSS Reader" from the [Apps] sidebar section and see a split-pane reader interface (feed list + article list + reading pane)
- Subscribe to RSS/Atom/JSON feeds via URL or feed discovery (paste a website URL, find its feed)
- Import existing subscriptions from an OPML file
- See articles appear automatically as feeds are polled (configurable interval, default 15m)
- Read articles in a clean, distraction-free renderer (custom object renderer for `rss:Article`)
- Star articles, mark as read/unread
- Connect their Hypothesis account and see annotations sync automatically
- View highlights and annotations inline alongside articles
- See "Unread Articles", "Starred Articles", and "Highlights" as view contributions in the workspace
- See "Related Articles" in the right pane when viewing any object (finds articles linking to the same concepts)
- Use Ctrl+K → "Subscribe to Feed..." to quickly add a new subscription
- Use Ctrl+K → "Mark All as Read" to clear the unread count
- Configure poll interval, Hypothesis API token, reader preferences in app settings
- See articles as browsable objects in the object browser (typed by shared `rss-feeds` model)
- Create edges from articles to Concepts, Notes, Projects — full knowledge graph integration

### Entry point / environment

- Entry point: `http://localhost:3000/app/rss-reader/` (reader interface), `http://localhost:3000/workspace` (contributions)
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore, external RSS feeds, Hypothesis API (optional)

## Completion Class

- Contract complete means: feed parsing handles RSS 2.0, Atom 1.0, and JSON Feed; articles have correct RDF types and properties; Hypothesis sync maps annotations to W3C Web Annotation vocabulary; bulk ingestion uses EventStore.commit_bulk()
- Integration complete means: articles appear in object browser, are searchable via FTS, display in table/cards/graph views, render with custom reader when opened, and survive platform restart
- Operational complete means: feed polling runs reliably on schedule, handles feed errors gracefully (timeout, 404, malformed XML), and Hypothesis sync cursor persists across restarts

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User subscribes to 3+ real RSS feeds, articles appear within one poll cycle
- User opens an article and sees the custom reader renderer (not default SHACL form)
- User stars an article, the state persists across page reload
- User imports an OPML file with 10+ feeds, all subscriptions appear
- Hypothesis sync pulls annotations and creates `oa:Annotation` objects linked to articles
- "Unread Articles" view in the workspace shows correct filtered results
- Articles appear in object browser under their RDF type, searchable via Ctrl+K
- Admin > Applications > RSS Reader shows task history with successful poll/sync runs

## Risks and Unknowns

- **Feed parsing edge cases** — Real-world RSS feeds are notoriously messy (invalid XML, mixed encodings, non-standard extensions). `feedparser` handles most cases but some feeds will fail. Need graceful error handling and per-feed error tracking.
- **Content extraction quality** — `trafilatura` extracts article body from HTML. Quality varies by site. Some sites block bots. Need fallback to feed-provided summary when extraction fails.
- **Hypothesis API rate limits** — Unknown rate limit policy. Need to respect `Retry-After` headers and implement backoff.
- **Article deduplication** — Feeds sometimes update articles (changed title, corrected content). Need to detect updates vs. new articles using GUID/link as stable identifier.
- **Data volume** — 20 feeds × 10 articles/day × 365 days = 73k articles/year. Each article is ~5 triples + body. Should be fine for RDF4J but worth monitoring triplestore size.

## Existing Codebase / Prior Art

- `docs/research/rss-reader-hypothesis-integration.md` — Comprehensive feasibility research (feed parsing, content extraction, Hypothesis API, RDF data model, implementation phases)
- `.gsd/design/APP-PLATFORM-DESIGN.md` § 13 — Concrete RSS Reader manifest example
- `.gsd/design/APP-PLATFORM-DESIGN.md` § 6 — SDK usage examples with RSS Reader code
- `backend/app/events/store.py` — EventStore (apps use via SDK CommandClient)
- `backend/app/commands/handlers/` — Command handler implementations (object.create, body.set, etc.)
- `apps/test-app/` — M009's test app as SDK usage reference

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- New requirements: RSS-01 through RSS-08 (feed management, polling, reader UI, article rendering, starring, Hypothesis sync, OPML import, workspace contributions)
- Validates: APP-01 through APP-14 from M009 (platform exercised end-to-end by a real app)

## Scope

### In Scope

**Mental Models (2 new models):**
- `rss-feeds` model: `rss:FeedSubscription`, `rss:Article`, `rss:ReadActivity` types with OWL ontology, SHACL shapes, ViewSpecs, and seed data. `browserVisible: false` on internal types (ReadActivity).
- `web-annotations` model: `oa:Annotation`, `oa:TextQuoteSelector` types following W3C Web Annotation vocabulary. Shared model — usable by any app that creates annotations.

**App Backend:**
- `RSSReaderApp` class with lifecycle hooks
- `FeedService` — subscription management, feed parsing (feedparser), content extraction (trafilatura), feed discovery (feedfinder2)
- `HypothesisService` — API client, annotation sync with cursor-based pagination, W3C Web Annotation mapping
- Task handlers: `poll-feeds` (check all subscriptions for new articles), `sync-hypothesis` (pull new annotations)
- Route handlers for all fragment endpoints

**App Frontend:**
- Reader UI: split-pane layout (feed sidebar + article list + reading pane)
- Feed subscription management (add/remove/edit, OPML import)
- Article reading experience (clean typography, star toggle, mark read)
- Hypothesis annotation display (inline highlights)
- App settings page (poll interval, Hypothesis token, reader preferences)
- Custom CSS (`reader.css`) + JS (`reader.js`)

**Frontend Integration (all 3 levels):**
- Level 1: RSS Reader standalone page in [Apps] sidebar
- Level 2: "Unread Articles", "Starred Articles", "Highlights" views; "Related Articles" right pane; "Subscribe to Feed...", "Mark All as Read", "Open RSS Reader" command palette entries
- Level 3: Custom `rss:Article` read renderer, custom `oa:Annotation` read renderer

**Data Flow:**
- Feed polling creates `rss:Article` objects via bulk EventStore
- Article bodies stored via `body.set` command (markdown-converted from HTML)
- Star/read state stored via `object.patch`
- Hypothesis annotations create `oa:Annotation` objects linked to articles via edges
- All data in `urn:sempkm:current` — browsable, searchable, linkable

### Out of Scope / Non-Goals

- Podcast/audio feed support
- Social reader features (sharing, commenting on articles)
- Full-text RSS search (beyond platform FTS)
- Hypothesis group annotations (personal annotations only for v1)
- Feed recommendations / discovery beyond URL paste
- Export to Pocket/Instapaper/etc.
- Mobile-optimized reader layout (responsive is fine, dedicated mobile is not)

## Technical Constraints

- App runs as subprocess using M009's app platform (SDK, unix socket IPC)
- All data writes go through SDK `CommandClient` → EventStore (no direct SPARQL writes)
- Feed polling and Hypothesis sync are platform-scheduled tasks (not app-managed timers)
- External HTTP goes through SDK `HttpClient` (network permissions enforced)
- Frontend is htmx fragments — no React, no full-page app rendering
- Dependencies installed in app's isolated venv (`feedparser`, `trafilatura`, `feedfinder2`, `opml`)

## Integration Points

- **App Platform (M009)** — All platform subsystems exercised: manifest, lifecycle, SDK, scheduler, permissions, admin, 3-level frontend
- **EventStore** — Bulk mode for feed ingestion, standard mode for user actions (star, read)
- **Object Browser** — Articles appear as typed objects (rss:Article), searchable via FTS
- **Views System** — Articles browsable in Table/Cards/Graph generic views
- **Command Palette** — Subscribe and mark-all-read actions
- **Right Pane** — Related articles shown on any focused object
- **Settings** — Hypothesis token, poll interval, reader preferences
- **Admin** — RSS Reader app detail with task history and data stats

## Open Questions

- **Article body storage format** — Store as markdown (converted from HTML via trafilatura) or as sanitized HTML? Markdown is consistent with SemPKM's body format but loses some formatting. HTML preserves fidelity but needs sanitization. Current thinking: markdown for body.set (consistent), original HTML in app state graph for the custom renderer.
- **Feed error UI** — How to surface feed errors to users? A badge on the feed sidebar entry? A separate "Feed Health" section in settings? Current thinking: error indicator on the feed entry + last error message in feed detail.
- **Annotation linking** — When a Hypothesis annotation targets a URL that matches a known article, create an edge. But what about annotations on arbitrary web pages (not from subscribed feeds)? Current thinking: import all annotations, link to articles when possible, leave unlinked ones as standalone Annotation objects.
