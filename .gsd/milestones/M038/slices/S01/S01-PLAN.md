# S01: Mental Model + Podcast Sources

**Goal:** User installs the media-scheduler Mental Model, opens the Media Scheduler app from the sidebar, subscribes to a podcast RSS feed, and sees discovered episodes listed as MediaItem objects.
**Demo:** Navigate to the Media Scheduler app page, add a podcast RSS feed URL, trigger poll-sources, and observe MediaItem objects created in the triplestore with episode metadata (title, duration, enclosure URL, publication date).

## Must-Haves

- `media-scheduler` Mental Model installable via model management with MediaSource, MediaItem, and MediaCategory types
- SHACL shapes for all types enabling form-based creation and validation
- `media-scheduler` app scaffold with App SDK entrypoint, manifest, and scheduled task declaration
- Podcast feed subscription CRUD: add feed URL, list active sources, remove source
- `poll-sources` scheduled task that parses RSS feeds via feedparser, deduplicates by episode GUID, and creates MediaItem objects via CommandClient
- Basic app UI page accessible from the [Apps] sidebar showing sources and discovered items
- Deterministic IRI minting for MediaSource (SHA-256 of feed URL) and MediaItem (SHA-256 of source IRI + episode ID)

## Proof Level

- This slice proves: contract + integration (model installs, app runs, polling creates real RDF objects)
- Real runtime required: yes (Docker stack for triplestore + app platform)
- Human/UAT required: no (pytest unit tests cover pure logic; integration verified via Docker in S07)

## Verification

- `cd backend && python -m pytest tests/test_media_scheduler.py -v` — unit tests for feed parsing, IRI minting, entry-to-media-item conversion, dedup logic, manifest validation
- `python -c "import yaml; m=yaml.safe_load(open('models/media-scheduler/manifest.yaml')); assert m['modelId']=='media-scheduler'"` — model manifest parseable
- `python -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); assert any(n.get('@id','').endswith('MediaSource') for n in d['@graph'])"` — ontology contains MediaSource class
- `python -c "from app.apps.manifest import parse_app_manifest; m=parse_app_manifest('apps/media-scheduler/manifest.yaml'); assert m.appId=='media-scheduler'"` — app manifest validates

## Observability / Diagnostics

- Runtime signals: structured logging in poll-sources task with `feeds_polled`, `items_created` counts; per-feed error tracking via `ms:errorCount` and `ms:lastError` properties
- Inspection surfaces: SPARQL query for MediaSource listing with poll state; app task run history in `app_task_runs` table
- Failure visibility: feed-level error count + last error message persisted on MediaSource object; poll task returns summary dict logged by scheduler
- Redaction constraints: none (no secrets in media metadata)

## Integration Closure

- Upstream surfaces consumed: App Platform SDK (`sempkm_app_sdk`), feedparser library, model install infrastructure (`models/` directory convention)
- New wiring introduced in this slice: `apps/media-scheduler/` app directory with manifest + entrypoint; `models/media-scheduler/` model directory with ontology + shapes + views
- What remains before the milestone is truly usable end-to-end: S02 (rules engine + daily plan), S03 (YouTube), S04 (Spotify), S05 (context-driven adaptation + mobile), S06 (stats + polish), S07 (integration verification)

## Tasks

- [x] **T01: Create media-scheduler Mental Model** `est:45m`
  - Why: All other tasks depend on the RDF types — MediaSource, MediaItem, MediaCategory — being defined with proper ontology classes, SHACL shapes, and view specs.
  - Files: `models/media-scheduler/manifest.yaml`, `models/media-scheduler/ontology/media-scheduler.jsonld`, `models/media-scheduler/shapes/media-scheduler.jsonld`, `models/media-scheduler/views/media-scheduler.jsonld`
  - Do: Create model directory with manifest.yaml (following rss-feeds pattern), JSON-LD ontology defining 3 owl:Classes (MediaSource, MediaItem, MediaCategory) with properties (sourceType enum, feedUrl, enclosureUrl, duration, status enum, etc.), SHACL NodeShapes with PropertyGroups for form generation, and ViewSpecs for table/card views. MediaSource.sourceType uses sh:in [podcast, youtube, spotify]. MediaItem.status uses sh:in [queued, playing, completed, skipped, saved].
  - Verify: `python -c "import yaml; m=yaml.safe_load(open('models/media-scheduler/manifest.yaml')); assert m['modelId']=='media-scheduler'"` and `python -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); types=[n['@id'] for n in d['@graph'] if n.get('@type')=='owl:Class']; assert 'ms:MediaSource' in types and 'ms:MediaItem' in types"`
  - Done when: All 4 model files exist, are valid JSON-LD/YAML, define the 3 types with SHACL shapes, and icons are declared in the manifest.

- [x] **T02: Scaffold media-scheduler app with podcast CRUD** `est:1h`
  - Why: The app needs to register with the App Platform, expose fragment routes for the UI, and handle podcast feed subscription management. This establishes the app entrypoint that the scheduler and proxy will operate on.
  - Files: `apps/media-scheduler/manifest.yaml`, `apps/media-scheduler/app.py`, `apps/media-scheduler/requirements.txt`, `apps/media-scheduler/services/__init__.py`, `apps/media-scheduler/services/podcast_service.py`
  - Do: Create app manifest (following rss-reader pattern) with appId `media-scheduler`, model dependency on `media-scheduler`, permissions for commands + sparql + network + backgroundTasks, one scheduled task `poll-sources` at 15m interval, and a UI page. Create app.py with App("media-scheduler") entrypoint, fragment routes for sources list and add-podcast form. Create podcast_service.py with pure functions: `mint_source_iri(feed_url)`, `mint_item_iri(source_iri, episode_id)`, `entry_to_media_item(entry, source_iri)` converting feedparser entries to MediaItem create params, and `subscribe_podcast(ctx, feed_url, title)` for creating MediaSource objects. Reuses feedparser pattern from rss-reader but with media-scheduler namespace IRIs.
  - Verify: `python -c "from app.apps.manifest import parse_app_manifest; m=parse_app_manifest('apps/media-scheduler/manifest.yaml'); assert m.appId=='media-scheduler' and len(m.tasks)==1 and m.tasks[0].id=='poll-sources'"` passes
  - Done when: App manifest validates, app.py imports cleanly, podcast_service.py defines the 4 core functions, and fragment routes are registered.

- [ ] **T03: Implement poll-sources task and episode discovery** `est:1h`
  - Why: The scheduled task is the core integration point — it polls podcast RSS feeds, parses episodes, deduplicates against existing items, and creates MediaItem objects. Without this, the app can store sources but never discovers content.
  - Files: `apps/media-scheduler/app.py`, `apps/media-scheduler/services/podcast_service.py`
  - Do: Implement `@media_scheduler_app.task("poll-sources")` handler that queries all MediaSource objects with sourceType="podcast", calls feedparser for each, converts entries to MediaItem params via `entry_to_media_item()`, deduplicates against existing items via SPARQL query, and bulk-creates new items via CommandClient. Handle conditional GET (ETag/Last-Modified) for efficiency. Track poll state on MediaSource (lastPolled, errorCount, lastError). Cap initial imports to 50 items per source. Add source removal route (`/_fragments/sources/remove`).
  - Verify: `cd backend && python -m pytest tests/test_media_scheduler.py -v -k "poll"` — tests verify poll task queries sources, parses feed, deduplicates, creates items, and updates source state
  - Done when: poll-sources task handler is complete with error handling, dedup, conditional GET, and bulk creation; source state updates work.

- [ ] **T04: App UI templates + unit tests** `est:1h`
  - Why: Closes the slice by providing the user-visible surface (app page with sources and items lists) and comprehensive unit tests proving the pure logic and manifest are correct.
  - Files: `apps/media-scheduler/frontend/templates/main.html`, `apps/media-scheduler/frontend/templates/sources-list.html`, `apps/media-scheduler/frontend/templates/items-list.html`, `apps/media-scheduler/frontend/templates/add-source.html`, `apps/media-scheduler/frontend/static/styles.css`, `backend/tests/test_media_scheduler.py`
  - Do: Create Jinja2 templates for the main app page (two-column layout: sources sidebar + items list), sources list fragment (htmx-powered with add/remove), items list fragment showing discovered episodes with title/date/duration/source, and add-source dialog form. Create `test_media_scheduler.py` with tests covering: manifest validation, IRI minting determinism, entry_to_media_item conversion (title, enclosure URL, published date, duration extraction), dedup logic (existing IRIs skipped), feed error handling, and source state updates. Follow the `test_rss_settings.py` pattern for importing app module via `importlib.util.spec_from_file_location`.
  - Verify: `cd backend && python -m pytest tests/test_media_scheduler.py -v` — all tests pass
  - Done when: All templates render valid HTML, tests pass covering pure functions and manifest, and the main page fragment route returns HTML.

## Files Likely Touched

- `models/media-scheduler/manifest.yaml`
- `models/media-scheduler/ontology/media-scheduler.jsonld`
- `models/media-scheduler/shapes/media-scheduler.jsonld`
- `models/media-scheduler/views/media-scheduler.jsonld`
- `apps/media-scheduler/manifest.yaml`
- `apps/media-scheduler/app.py`
- `apps/media-scheduler/requirements.txt`
- `apps/media-scheduler/services/__init__.py`
- `apps/media-scheduler/services/podcast_service.py`
- `apps/media-scheduler/frontend/templates/main.html`
- `apps/media-scheduler/frontend/templates/sources-list.html`
- `apps/media-scheduler/frontend/templates/items-list.html`
- `apps/media-scheduler/frontend/templates/add-source.html`
- `apps/media-scheduler/frontend/static/styles.css`
- `backend/tests/test_media_scheduler.py`
