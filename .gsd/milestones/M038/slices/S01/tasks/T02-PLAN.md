---
estimated_steps: 5
estimated_files: 6
skills_used: []
---

# T02: Scaffold media-scheduler app with podcast CRUD

**Slice:** S01 — Mental Model + Podcast Sources
**Milestone:** M038

## Description

Create the `media-scheduler` app directory under `apps/` following the exact pattern established by `apps/rss-reader/`. This task creates the app manifest, entrypoint module, requirements file, and podcast subscription service with pure helper functions. The app registers with the App Platform via `manifest.yaml`, exposes fragment routes for the UI, and provides podcast feed subscription management.

Key patterns to follow from `apps/rss-reader/`:
- `manifest.yaml` declares appId, dependencies (model: media-scheduler), permissions (commands, sparql, network, backgroundTasks), one scheduled task (poll-sources), and a UI page
- `app.py` creates an `App("media-scheduler")` instance, registers routes via `@media_scheduler_app.route()`, and uses `ctx.render_template()` for HTML responses
- `services/podcast_service.py` contains pure functions (testable without SDK) for IRI minting and entry conversion, plus SDK-dependent functions for subscribe/unsubscribe

The app's IRI namespace is `urn:sempkm:app:media-scheduler:` and uses the model namespace `urn:sempkm:model:media-scheduler:` for type IRIs.

## Steps

1. Create `apps/media-scheduler/manifest.yaml` based on the `apps/rss-reader/manifest.yaml` pattern:
   - `appId: "media-scheduler"`, `name: "Media Scheduler"`, `version: "0.1.0"`
   - `dependencies.models: [{id: "media-scheduler", version: ">=1.0.0"}]`
   - `permissions: {commands: ["object.create", "object.patch", "edge.create"], sparql: {read: true}, backgroundTasks: true, network: ["*"], settings: true}`
   - `tasks: [{id: "poll-sources", description: "Poll media sources for new content", interval: "15m", configurable: true}]`
   - `ui.pages: [{id: "scheduler", path: "/scheduler", label: "Media Scheduler", icon: "radio", nav: "apps", fragment: "main"}]`
   - `settings: [{key: "maxItemsPerPoll", label: "Max items per poll", inputType: "number", default: "50"}]`

2. Create `apps/media-scheduler/requirements.txt` listing `feedparser>=6.0` (the only external dependency for S01 — Spotify/YouTube clients come in later slices).

3. Create `apps/media-scheduler/services/__init__.py` (empty) and `apps/media-scheduler/services/podcast_service.py` with:
   - Constants: `MEDIA_SOURCE_TYPE`, `MEDIA_ITEM_TYPE`, `MS_NS` (model namespace)
   - `mint_source_iri(feed_url: str) -> str` — deterministic IRI via SHA-256 of feed URL, returns `urn:sempkm:app:media-scheduler:source-{hash}`
   - `mint_item_iri(source_iri: str, episode_id: str) -> str` — deterministic IRI via SHA-256 of source_iri + episode_id, returns `urn:sempkm:app:media-scheduler:item-{hash}`
   - `entry_to_media_item(entry: dict, source_iri: str) -> dict` — converts a feedparser entry dict to an object.create params dict. Maps: title → dcterms:title, link → ms:enclosureUrl (prefer enclosure URL from `entry.enclosures[0].href` if present, fall back to entry.link), published_parsed → dcterms:created, summary → dcterms:description, entry.id/entry.link → ms:externalId. Sets ms:status to "queued", ms:mediaSource to source_iri. Extracts duration from `itunes_duration` if present.
   - `get_existing_item_iris(graph_client, source_iri: str) -> set[str]` — SPARQL query returning existing MediaItem IRIs for a given source (for dedup)
   - `subscribe_podcast(ctx, feed_url: str, title: str | None) -> dict` — checks for existing source via SPARQL, creates MediaSource via object.create with sourceType="podcast", returns `{"status": "created"|"duplicate", "iri": ...}`
   - `unsubscribe_source(ctx, source_iri: str) -> dict` — patches source to mark inactive
   - `update_source_state(ctx, source_iri, ...)` — updates lastPolled, etag, errorCount, lastError on the MediaSource object
   - `SOURCES_WITH_STATE_SPARQL` — query for all active MediaSource objects with their polling state

4. Create `apps/media-scheduler/app.py` with:
   - `media_scheduler_app = App("media-scheduler")`
   - Import podcast_service functions (with the same `try/except ModuleNotFoundError` fallback pattern used by rss-reader for importlib-based loading in test contexts)
   - Route `/_fragments/main` — renders main.html template
   - Route `/_fragments/sources` (GET) — queries all MediaSource objects via SPARQL, renders sources-list.html
   - Route `/_fragments/sources/add-podcast` (POST) — reads feed_url from form, calls subscribe_podcast(), returns success/error/duplicate HTML fragment with HX-Trigger: sourcesChanged
   - Route `/_fragments/sources/remove` (POST) — reads source_iri from form, calls unsubscribe_source(), returns updated sources list
   - Route `/_fragments/items` (GET) — queries MediaItem objects (optionally filtered by source_iri query param), renders items-list.html
   - Startup/shutdown lifecycle hooks (logging only, same as rss-reader)

5. Create `apps/media-scheduler/frontend/templates/` directory (templates will be created in T04, but the directory must exist for the Jinja2 loader). Create a minimal placeholder `main.html` so the `/_fragments/main` route doesn't crash: `<div class="media-scheduler"><h2>Media Scheduler</h2><p>Loading...</p></div>`.

## Must-Haves

- [ ] App manifest validates via `parse_app_manifest()` with appId `media-scheduler`
- [ ] `mint_source_iri()` is deterministic: same feed_url always produces same IRI
- [ ] `mint_item_iri()` is deterministic: same source_iri + episode_id always produces same IRI
- [ ] `entry_to_media_item()` maps feedparser fields to correct RDF properties with ms: namespace
- [ ] `subscribe_podcast()` checks for duplicates before creating
- [ ] `app.py` registers 5 routes: main, sources list, add-podcast, remove source, items list
- [ ] `poll-sources` task declared in manifest with 15m interval

## Verification

- `python -c "from app.apps.manifest import parse_app_manifest; m=parse_app_manifest('apps/media-scheduler/manifest.yaml'); assert m.appId=='media-scheduler' and len(m.tasks)==1 and m.tasks[0].id=='poll-sources'"` passes
- The podcast_service pure functions are importable and callable (verified in T04 tests, but can be smoke-tested here with a Python one-liner)

## Observability Impact

- **New signals:** `media_scheduler_app` registers 5 fragment routes — each logs warnings on SPARQL failure and info on successful subscribe/unsubscribe via structured `logger.warning()` / `logger.info()` calls. `podcast_service.py` logs IRI minting and subscription state changes at debug/info levels.
- **Inspection:** A future agent can verify the app loaded correctly by checking `app._routes` length (should be 5). SPARQL query `SOURCES_WITH_STATE_SPARQL` can be used to inspect all active MediaSource objects with their polling state.
- **Failure visibility:** Subscribe/unsubscribe route handlers return HTML fragments with `.ms-error` class on failure, making errors visible in both UI and test assertions. Source state (errorCount, lastError) is persisted via `update_source_state()`.

## Inputs

- `models/media-scheduler/manifest.yaml` — model type IRIs referenced in podcast_service constants
- `models/media-scheduler/ontology/media-scheduler.jsonld` — property IRIs used in entry_to_media_item mapping
- `apps/rss-reader/manifest.yaml` — reference pattern for app manifest
- `apps/rss-reader/app.py` — reference pattern for App() entrypoint, routes, feedparser import fallback
- `apps/rss-reader/services/feed_service.py` — reference pattern for subscription management functions

## Expected Output

- `apps/media-scheduler/manifest.yaml` — validated app manifest
- `apps/media-scheduler/app.py` — app entrypoint with 5 fragment routes
- `apps/media-scheduler/requirements.txt` — feedparser dependency
- `apps/media-scheduler/services/__init__.py` — empty package init
- `apps/media-scheduler/services/podcast_service.py` — pure functions + SDK subscription management
- `apps/media-scheduler/frontend/templates/main.html` — minimal placeholder template
