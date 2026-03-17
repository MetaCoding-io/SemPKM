# M010: RSS Reader & Hypothesis App — Research

**Date:** 2026-03-17
**Status:** Complete
**Researcher:** auto-mode

## Summary

M010 is the first real application built on M009's app platform. The platform infrastructure is proven (372 tests, E2E spec with 28 assertions, test-app exercising all 6 SDK contribution types). The RSS Reader exercises every platform subsystem under realistic conditions: subprocess lifecycle, SDK clients (commands, graph, state, settings, http), bulk EventStore, task scheduling, 3-level frontend integration, and two new Mental Models.

The primary risk is **scope breadth** — this milestone spans two Mental Models, a substantial backend (feed parsing, content extraction, Hypothesis sync, OPML import), a complete reader UI, and all three frontend integration levels. The research document (`docs/research/rss-reader-hypothesis-integration.md`) is comprehensive and well-aligned with the platform design. The recommended approach is to **prove the data pipeline first** (model → ingest → query) before building the UI, and to **defer Hypothesis sync to late in the build** since it's an optional integration that doesn't block core reader functionality.

The codebase imposes clear contracts: apps mint IRIs with `urn:sempkm:app:{appId}:` prefix, all writes go through SDK CommandClient (which enforces command whitelist and IRI prefix), tasks are platform-scheduled HTTP invocations, and all UI is htmx fragments proxied through UDS. The test-app (`apps/test-app/`) is the canonical SDK usage reference and should be followed for structural patterns.

## Recommendation

### Build Order: Data-First, UI-Last

1. **Mental Models first** — `rss-feeds` and `web-annotations` models are prerequisites for everything else. They define the types, shapes, and views that the app produces data into. Models are independently installable and testable.

2. **App skeleton + feed ingestion second** — `RSSReaderApp` class with the `poll-feeds` task handler. Proves the full data path: feedparser → object.create via SDK CommandClient → bulk EventStore → articles in triplestore. This is the highest-risk integration point (subprocess ↔ platform ↔ triplestore).

3. **Reader UI third** — Split-pane layout as a Level 1 standalone page. The UI needs data to display, so it depends on (2). This is the largest single slice by code volume but lowest risk (htmx patterns are established, test-app proves fragment loading).

4. **Workspace contributions fourth** — Level 2 (views, right pane, command palette) and Level 3 (custom object renderers). These are the platform integration proof points but need both data (2) and UI patterns (3) in place.

5. **Hypothesis sync fifth** — Optional integration that creates `oa:Annotation` objects. Can be deferred or descoped without blocking the core reader. Depends on the `web-annotations` model from (1).

6. **OPML import sixth** — Enhancement feature. Simple XML parsing + batch subscription creation. Low risk, low dependency.

7. **Polish, E2E tests, and docs last** — Standing requirements: Playwright tests and user guide.

### Approach: Lean on Existing Patterns

The codebase has strong conventions that should be followed:

- **App structure**: Copy `apps/test-app/` as the starting template. Same manifest.yaml shape, same `frontend/templates/` + `frontend/static/` layout, same decorator-based handler registration.
- **Mental Model structure**: Copy `models/basic-pkm/` as the template. Same `manifest.yaml` + `ontology/` + `shapes/` + `views/` + `seed/` layout. Use JSON-LD for all artifacts.
- **SDK patterns**: The test-app's `app.py` demonstrates all patterns. Use `ctx.commands.bulk()` for feed ingestion. Use `ctx.graph.query()` for reading. Use `ctx.state.get/set()` for sync cursors and polling metadata. Use `ctx.http.get()` for feed fetching and Hypothesis API calls.
- **Frontend patterns**: htmx fragments with `hx-get`, `hx-trigger="load"`, `hx-swap="innerHTML"`. No React, no client-side routing. Templates rendered via `ctx.render_template()`.

## Implementation Landscape

### Key Files

**Platform (existing, read-only during M010):**
- `backend/app/apps/manager.py` — AppManager: install/start/stop lifecycle. M010 uses this as-is.
- `backend/app/apps/scheduler.py` — AppScheduler: task invocation loop. `poll-feeds` and `sync-hypothesis` tasks are triggered here.
- `backend/app/apps/proxy.py` — AppProxy: UDS forwarding. All RSS Reader UI requests go through this.
- `backend/app/apps/registry.py` — AppRegistry: manifest cache, right pane contributions, renderer lookup. RSS Reader's manifest registers here.
- `backend/app/apps/manifest.py` — AppManifestSchema: manifest validation. RSS Reader manifest must validate against this.
- `backend/app/browser/apps.py` — Frontend integration endpoints: explorer, right pane sections, views, command palette.
- `backend/app/browser/objects.py` — `_get_renderer_override()` dispatches to app-provided renderer fragments.
- `backend/sdk/sempkm_app_sdk/` — Full SDK package. RSS Reader imports `App`, `AppContext`, and uses all 5 clients.
- `backend/app/events/store.py` — `commit_bulk()` for batch article ingestion.

**New files (M010 creates):**

- `models/rss-feeds/manifest.yaml` — Model manifest
- `models/rss-feeds/ontology/rss-feeds.jsonld` — OWL classes: FeedSubscription, Article, ReadActivity
- `models/rss-feeds/shapes/rss-feeds.jsonld` — SHACL shapes for form generation
- `models/rss-feeds/views/rss-feeds.jsonld` — ViewSpecs (optional — generic views may suffice)
- `models/rss-feeds/seed/rss-feeds.jsonld` — Optional seed data
- `models/web-annotations/manifest.yaml` — Model manifest
- `models/web-annotations/ontology/web-annotations.jsonld` — OWL classes: Annotation, TextQuoteSelector (W3C OA vocabulary)
- `models/web-annotations/shapes/web-annotations.jsonld` — SHACL shapes
- `apps/rss-reader/manifest.yaml` — App manifest (all permissions, tasks, UI contributions)
- `apps/rss-reader/requirements.txt` — feedparser, trafilatura, listparser (or opml)
- `apps/rss-reader/app.py` — RSSReaderApp class with all handlers
- `apps/rss-reader/services/feed_service.py` — Feed parsing, discovery, content extraction
- `apps/rss-reader/services/hypothesis_service.py` — Hypothesis API client and sync logic
- `apps/rss-reader/frontend/templates/*.html` — All fragment templates
- `apps/rss-reader/frontend/static/css/reader.css` — Reader styling
- `apps/rss-reader/frontend/static/js/reader.js` — Reader interactivity

### Build Order

1. **Mental Models** — Prove first because they define the type IRIs that everything else references. Install into running stack, verify types appear in object browser (or are hidden via `browserVisible: false`).

2. **App skeleton + poll-feeds task** — Prove that feedparser can run inside an app subprocess venv, that `ctx.commands.bulk()` creates articles in the triplestore, and that the scheduler triggers the task. This is the critical path — if bulk ingestion through UDS→proxy→EventStore doesn't work, nothing else matters.

3. **Reader UI (Level 1)** — Standalone page with feed sidebar + article list + reading pane. Proves htmx fragment loading via the proxy chain. Article rendering uses the existing markdown renderer (marked + DOMPurify).

4. **Star/read state + feed management** — User actions (star, mark read, subscribe, unsubscribe) via `object.patch` and `object.create`. Feed discovery via httpx.

5. **Level 2+3 contributions** — Views ("Unread Articles", "Starred Articles", "Highlights"), right pane ("Related Articles"), command palette ("Subscribe to Feed...", "Mark All as Read"), and custom object renderers for `rss:Article` and `oa:Annotation`.

6. **Hypothesis sync** — API client, cursor-based pagination, annotation-to-article linking. The `sync-hypothesis` task handler.

7. **OPML import** — File upload endpoint, XML parsing, batch subscription creation.

8. **E2E tests + docs** — Playwright spec covering full lifecycle. User guide chapter.

### Verification Approach

- **Unit tests**: Each service (FeedService, HypothesisService) should have pure-function tests for parsing, content extraction, and RDF mapping — no Docker dependency. Target: 50+ tests.
- **Integration tests**: App subprocess round-trip tests (similar to `apps/test-app/` pattern) proving SDK ↔ platform data flow.
- **Stack verification**: After each major slice, verify in the running Docker stack:
  - Models installed: `GET /admin/models` shows `rss-feeds` and `web-annotations`
  - App installed: `GET /admin/apps` shows `rss-reader` with status `running`
  - Task execution: `GET /admin/apps/rss-reader` shows task history with `poll-feeds` runs
  - Data present: SPARQL query returns articles from triplestore
  - UI works: Navigate to `/app/rss-reader/` and see the reader interface
- **E2E tests**: Playwright spec covering: install → subscribe to feed → poll triggers → article appears → open article → star article → workspace views show data → admin shows task history → uninstall.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| RSS/Atom/JSON Feed parsing | `feedparser` 6.x | Handles malformed feeds gracefully, built-in ETag/Last-Modified support, massive community knowledge base. BSD license. |
| Content extraction (reader mode) | `trafilatura` | Best F1 score (0.958) across diverse pages, outputs Markdown directly (matches SemPKM body format), falls back to readability-lxml internally. Apache 2.0. |
| OPML import | `listparser` | Handles OPML + other subscription formats. Simpler than stdlib XML parsing for edge cases. MIT license. |
| Feed discovery from website URL | httpx + BeautifulSoup/lxml | feedfinder2 is an option but the logic is ~50 lines. httpx is already a dependency. |
| Hypothesis API | httpx (direct) | The API is simple REST (5 endpoints). A thin wrapper is cleaner than pulling in `python-hypothesis` which adds its own dependencies. |
| W3C Web Annotation RDF | Standard `oa:` vocabulary | The W3C Web Annotation Data Model maps directly to RDF. No custom vocabulary needed. |

## Constraints

- **IRI prefix enforcement**: All IRIs created by the app must start with `urn:sempkm:app:rss-reader:`. The SDK's `CommandClient._check_iri_prefix()` enforces this recursively. IRIs for articles, subscriptions, activities, and annotations must follow this pattern. Exception: type IRIs come from the shared model (e.g., `urn:sempkm:model:rss-feeds:Article`) — the app references but doesn't create these.

- **Command whitelist**: The manifest declares permitted commands. RSS Reader needs: `object.create`, `object.patch`, `edge.create`, `edge.patch`, `body.set`. Any command not in this list will raise `PermissionError`.

- **Network domain enforcement**: `HttpClient._check_domain()` validates every outbound URL against `permissions.network[]`. RSS feeds can be anywhere → needs `"*"` wildcard. Hypothesis needs `"*.hypothes.is"`. The manifest must declare both.

- **Object renderer type matching uses full IRIs (D165)**: The manifest's `objectRenderers[].type` must be a full IRI like `urn:sempkm:model:rss-feeds:Article`, not a prefixed name like `rss:Article`. The registry does exact string comparison.

- **Model dependency checking is NOT enforced at install time**: The manifest declares model dependencies but `AppManager.install()` only checks platform version. Model presence must be validated manually or by convention (documenting that `rss-feeds` and `web-annotations` must be installed before the app).

- **Task handlers receive empty body by default**: The scheduler's `_post_task()` sends a POST with no body. Task handlers should not depend on request body content. Context comes from the state graph.

- **All UI is htmx fragments**: No full-page rendering from the app. The platform provides `base.html` chrome. App fragments are loaded into dockview tabs via htmx `hx-get` + `hx-swap="innerHTML"`.

- **Settings stored as string key/value pairs**: `SettingsClient` stores everything as strings in the state graph. Complex values (e.g., per-feed configuration) need JSON serialization or separate state keys.

- **Bulk EventStore limit**: `commit_bulk()` enforces a 1000-operation limit per batch. Feed polling with 100+ articles per feed may need multiple batches.

- **App dependencies installed via `/bin/uv`**: The Docker image has `uv` pre-installed. `requirements.txt` is installed into the app's isolated venv. trafilatura has C dependencies (lxml) — these must be available in the Docker image or installable via uv.

## Common Pitfalls

- **trafilatura's dependency tree is large** — It pulls in lxml, courlan, htmldate, and several other packages (~15 transitive deps). The Docker image must have C build tools or pre-built wheels available. If venv install fails, the app won't start. **Mitigation**: Test `uv pip install trafilatura` in a fresh venv inside the Docker container before coding.

- **feedparser runs synchronously** — It uses urllib internally and blocks the event loop. Since the app runs in its own subprocess, this is acceptable for v1 (the platform's event loop is not affected). But the app's own uvicorn event loop will block during feed parsing. **Mitigation**: Use `asyncio.to_thread(feedparser.parse, url)` for the parse call, or accept the blocking since task handlers aren't concurrent anyway.

- **IRI prefix mismatch between model types and app-created instances** — The model defines types like `urn:sempkm:model:rss-feeds:Article`. The app creates instances like `urn:sempkm:app:rss-reader:article:{uuid}`. The `rdf:type` triple references the model IRI. The `_check_iri_prefix()` only checks IRI-valued strings, and standard vocabulary IRIs (http://, https://) are checked but model IRIs (`urn:sempkm:model:...`) will also be checked. **Mitigation**: Verify that `object.create` command handler treats the `type` field as a reference IRI that doesn't get prefix-checked, or that the platform's command handler resolves types differently. Looking at the SDK code, `_check_iri_prefix` checks all IRI-like strings recursively — this means `type: "urn:sempkm:model:rss-feeds:Article"` in command params will fail because it doesn't start with `urn:sempkm:app:rss-reader:`. **This is a known SDK constraint** — investigate how the test-app handles type references. The test-app creates objects with type `urn:sempkm:test:TestRenderedType` which also doesn't match the app prefix. The platform's command handler on the platform side processes the command — the SDK's prefix check may need an exception for `rdf:type` or `type` field values. **This needs investigation during the first implementation slice**.

- **Article deduplication** — Feeds repost or update articles. Must use a stable identifier (GUID from feed or canonical URL) to detect duplicates. Query the triplestore before creating to avoid duplicates. **Mitigation**: Store `dcterms:identifier` with the feed-provided GUID and do a SPARQL ASK before bulk creating.

- **Conditional GET metadata persistence** — ETag and Last-Modified values must survive across poll cycles. Store in the app's state graph (`ctx.state.set("feed:{feed_id}:etag", value)`). State graph is not event-sourced — direct SPARQL CRUD — which is correct for ephemeral polling metadata.

- **Timezone handling in feed dates** — feedparser normalizes dates to `time.struct_time` (UTC). Convert to ISO 8601 `xsd:dateTime` for RDF storage. Use `datetime.fromtimestamp(calendar.timegm(struct_time), tz=timezone.utc).isoformat()`.

- **Content sanitization** — Article HTML from feeds must be sanitized before storage and rendering. trafilatura handles this for extracted content, but feed-provided HTML summaries need explicit sanitization. The frontend already has DOMPurify for markdown rendering — use it for article display. For storage, convert to markdown via trafilatura or store sanitized HTML.

## Open Risks

- **IRI prefix enforcement for type references**: The SDK's `_check_iri_prefix()` checks ALL IRI-like strings in command params recursively. When creating an `object.create` command with `type: "urn:sempkm:model:rss-feeds:Article"`, this IRI doesn't start with `urn:sempkm:app:rss-reader:` and would be rejected. This is the **highest-risk unknown** in the milestone. Possible resolutions: (a) the platform command handler pre-processes the type before forwarding to EventStore, bypassing the SDK check; (b) the SDK has an exception for well-known param keys; (c) we need to modify the SDK to whitelist model namespace IRIs. **Must be investigated and resolved in the first implementation slice.**

- **trafilatura install in Docker** — trafilatura has heavy C dependencies (lxml, etc.). If the Docker image lacks build essentials or pre-built wheels, `uv pip install trafilatura` will fail inside the app venv. May need a Dockerfile change to add `build-essential` or use a binary wheel cache. If this is a blocker, fall back to using feed-provided summaries only (skip full content extraction for v1).

- **Hypothesis API rate limits** — Rate limit policy is not well-documented. The sync task runs every 15m by default. If annotation volume is high, may hit limits. **Mitigation**: Implement exponential backoff on 429 responses, respect `Retry-After` headers.

- **State graph SPARQL for polling metadata** — The StateClient stores key/value pairs via SPARQL INSERT/DELETE against the app's state graph. With 50+ feeds, each with ETag + Last-Modified + nextPollTime + errorCount, that's 200+ state keys. StateClient's simple key/value model may be inefficient for this scale. **Mitigation**: Consider storing per-feed metadata as a single JSON blob per feed, or accept the per-key overhead since RDF4J handles 200 triples trivially.

- **Article body storage format** — The M010-CONTEXT.md flags this as an open question. Recommendation: store as markdown via `body.set` (consistent with SemPKM body format). For the custom reader renderer, fetch the markdown body and render it with marked.js (already loaded). If the feed provides rich HTML, convert to markdown via trafilatura before storing.

## Requirements Analysis

### Table Stakes (RSS-01 through RSS-08)

All 8 requirements are well-scoped and realistic:

- **RSS-01 (feed subscription + polling)**: Core functionality. The platform scheduler handles timing. feedparser handles parsing. Bulk EventStore handles ingestion. Clear path.
- **RSS-02 (reader UI)**: Standard htmx split-pane layout. Established patterns from workspace UI.
- **RSS-03 (custom renderers)**: Level 3 integration proven by test-app. Full IRI type matching per D165.
- **RSS-04 (Hypothesis sync)**: Optional but declared as core-capability. Should be descoped to enhancement or built as a late slice.
- **RSS-05 (OPML import)**: Simple enhancement. listparser + batch subscribe.
- **RSS-06 (workspace contributions)**: Level 2 integration proven by test-app. 3 views + 1 right pane + 3 command palette entries.
- **RSS-07 (Mental Models)**: Two new models following established pattern.
- **RSS-08 (feed discovery + content extraction)**: Enhancement. trafilatura + URL probing.

### Candidate Requirements (not yet in REQUIREMENTS.md)

These behaviors are implied by the milestone context but not explicitly tracked:

- **RSS-09 (Feed error tracking)**: Per-feed error indicator in sidebar. M010-CONTEXT mentions this. Should be explicit.
- **RSS-10 (Article deduplication)**: GUID-based dedup during ingestion. Essential for correctness but not stated.
- **RSS-11 (Conditional GET)**: ETag/Last-Modified support to avoid redundant downloads. Essential for production quality.
- **RSS-12 (App settings page)**: Configure poll interval, Hypothesis token, reader preferences. Declared in manifest design but not a requirement.

### Scope Observation

RSS-04 (Hypothesis sync) is classified as `core-capability` but it's an **optional integration** — the reader works perfectly without it. Consider:
- Keep it as core-capability if Hypothesis is the motivating use case
- Reclassify as enhancement if the reader itself is the primary deliverable
- Either way, build it as a late slice so the reader ships independently

## Sources

- `docs/research/rss-reader-hypothesis-integration.md` — Comprehensive feasibility research (feed parsing, content extraction, Hypothesis API, RDF data model, implementation phases)
- `.gsd/design/APP-PLATFORM-DESIGN.md` — App platform architecture, especially §3 (manifest), §6 (SDK), §7 (frontend integration), §13 (RSS Reader manifest example)
- `apps/test-app/` — Canonical SDK usage reference (manifest, app.py, templates, static assets)
- `backend/sdk/sempkm_app_sdk/` — SDK source (App class, AppContext, 5 clients, runner)
- `backend/app/apps/` — Platform-side app infrastructure (manager, scheduler, proxy, registry, manifest schema)
- `models/basic-pkm/` — Reference Mental Model structure (manifest.yaml, ontology, shapes, views, seed)
- W3C Web Annotation Data Model — https://www.w3.org/TR/annotation-model/
- feedparser docs — https://pythonhosted.org/feedparser/
- trafilatura docs — https://trafilatura.readthedocs.io/

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| RSS/feedparser | tiangong-ai/skills@ai-tech-rss-fetch | available (133 installs) — generic, not project-specific |
| trafilatura | none | no skills found |
| Hypothesis API | none | no relevant skills found |
| W3C Web Annotation | none | standard vocabulary, no skill needed |

No skills are recommended for installation — the technologies are well-documented and the codebase has strong conventions to follow.
