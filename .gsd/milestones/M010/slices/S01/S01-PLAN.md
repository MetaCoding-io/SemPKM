# S01: Platform fix + Mental Model + App data pipeline

**Goal:** SDK IRI prefix bug fixed with tests. `rss-feeds` model installed in triplestore (Article, FeedSubscription types visible). `rss-reader` app skeleton installs, starts, and the `poll-feeds` task creates real articles from a test feed via bulk EventStore. Articles visible in object browser.
**Demo:** Install rss-feeds model → install rss-reader app → trigger poll-feeds → articles appear in object browser with Article type.

## Must-Haves

- `CommandClient._check_iri_prefix()` whitelists model namespace IRIs (`urn:sempkm:model:*`), standard vocabularies (`http://`, `https://`), and user-types (`urn:sempkm:user-types:*`) — only enforces prefix on `urn:sempkm:app:*` and `urn:sempkm:data:*`
- Unit tests proving model type IRIs pass validation, standard vocab IRIs pass, and foreign app IRIs are still blocked
- `models/rss-feeds/` Mental Model with OWL ontology defining `rss:Article` and `rss:FeedSubscription` classes, SHACL shapes for form generation, ViewSpecs for articles table view
- `apps/rss-reader/manifest.yaml` with correct dependencies, permissions, tasks, and UI stubs
- `apps/rss-reader/app.py` with `poll-feeds` task handler that parses RSS feeds via feedparser and creates articles via `ctx.commands.bulk()`
- Unit tests proving feedparser entry → article RDF mapping and bulk command assembly

## Proof Level

- This slice proves: integration (SDK → bulk EventStore → triplestore)
- Real runtime required: yes (Docker stack for integration verification)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_iri_prefix_fix.py -v` — IRI prefix whitelist tests pass (≥8 tests)
- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — feed parsing + article mapping tests pass (≥10 tests)
- `python -c "from backend.app.models.manifest import parse_manifest; from pathlib import Path; parse_manifest(Path('models/rss-feeds'))"` — model manifest validates
- `python -c "from backend.app.apps.manifest import parse_app_manifest; parse_app_manifest('apps/rss-reader/manifest.yaml')"` — app manifest validates
- Docker integration: install model → install app → trigger poll-feeds → articles queryable via SPARQL `SELECT * WHERE { ?s a <urn:sempkm:model:rss-feeds:Article> }`
- Diagnostic: `cd backend && python -m pytest tests/test_iri_prefix_fix.py::TestIRIPrefixWhitelist::test_foreign_app_iri_blocked -v` — verify PermissionError message includes both the offending IRI and the required prefix string (failure-path check)

## Observability / Diagnostics

- Runtime signals: `poll-feeds` task logs article count created per run, feed parse errors logged with feed URL
- Inspection surfaces: Admin > Applications > RSS Reader shows task history with `poll-feeds` runs; triplestore SPARQL query for Article instances
- Failure visibility: Task run status (success/error) in `app_task_runs` SQLite table with error message, IRI prefix PermissionError includes offending IRI and required prefix in message
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `backend/sdk/sempkm_app_sdk/clients/commands.py` (IRI prefix fix), `backend/app/events/store.py` (commit_bulk), `backend/app/commands/router.py` (/api/commands/bulk endpoint), `backend/app/apps/manager.py` (app lifecycle), Mental Model manifest schema
- New wiring introduced in this slice: `models/rss-feeds/` model archive, `apps/rss-reader/` app directory with all artifacts
- What remains before the milestone is truly usable end-to-end: S02 (feed service, content extraction), S03 (reader UI), S04 (workspace contributions), S05 (OPML), S06 (E2E tests)

## Tasks

- [x] **T01: Fix SDK IRI prefix validation to whitelist model and standard namespace IRIs** `est:45m`
  - Why: The current `_check_iri_prefix()` rejects ALL `http://`/`https://` IRIs (they can never start with `urn:sempkm:app:{appId}:`) and all `urn:sempkm:model:*` IRIs. This makes it impossible for any app to reference model-defined types in `object.create` params — the #1 platform risk for M010. Decision D171 specifies the fix.
  - Files: `backend/sdk/sempkm_app_sdk/clients/commands.py`, `backend/tests/test_iri_prefix_fix.py`
  - Do: Rewrite `_check_iri_prefix()` to only enforce prefix on `urn:sempkm:app:*` and `urn:sempkm:data:*` namespaces. IRIs starting with `urn:sempkm:model:*`, `urn:sempkm:user-types:*`, `http://`, or `https://` pass through unchecked. Write new unit test file with ≥8 tests covering: model type IRI passes, standard vocab IRI passes, user-types IRI passes, own app IRI passes, foreign app IRI blocked, data namespace IRI blocked, nested params scanning still works, non-IRI strings still ignored.
  - Verify: `cd backend && python -m pytest tests/test_iri_prefix_fix.py -v` — all tests pass. Existing `test_app_permissions.py` tests still pass (run both).
  - Done when: `_check_iri_prefix()` accepts `urn:sempkm:model:rss-feeds:Article` as a param value for app `rss-reader`, rejects `urn:sempkm:app:other-app:thing`, and all existing permission tests still pass.

- [x] **T02: Create rss-feeds Mental Model with Article and FeedSubscription types** `est:1h`
  - Why: The RSS Reader app needs model-defined types for Article and FeedSubscription. These must exist as a standalone Mental Model (per RSS-07) following the exact patterns of `basic-pkm`. The model must be installable independently of the app.
  - Files: `models/rss-feeds/manifest.yaml`, `models/rss-feeds/ontology/rss-feeds.jsonld`, `models/rss-feeds/shapes/rss-feeds.jsonld`, `models/rss-feeds/views/rss-feeds.jsonld`, `models/rss-feeds/seed/rss-feeds.jsonld`
  - Do: Create the model directory structure. Define OWL classes `rss:Article` (properties: title, link, author, published date, summary, feedSource, isRead, isStarred) and `rss:FeedSubscription` (properties: feedUrl, title, siteUrl, lastPolled, errorCount, etag, lastModified). Align to gist where appropriate (Article → gist:FormattedContent). SHACL shapes for both types with property groups. ViewSpec for Articles table. Manifest with icons (rss icon for Article, antenna icon for FeedSubscription). No seed data needed.
  - Verify: `python -c "from backend.app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('models/rss-feeds')); print(f'OK: {m.modelId} v{m.version}')"` — prints `OK: rss-feeds v1.0.0`. Ontology, shapes, views JSON-LD files parse as valid JSON.
  - Done when: `models/rss-feeds/` directory validates against ManifestSchema, contains well-formed OWL ontology with Article and FeedSubscription classes, SHACL shapes with ≥5 properties each, and at least one ViewSpec.

- [x] **T03: Create rss-reader app skeleton with poll-feeds task handler** `est:1h30m`
  - Why: This is the core deliverable — an app that uses feedparser to parse RSS feeds and creates articles via `ctx.commands.bulk()`, proving the full SDK → EventStore data pipeline. It follows the `test-app` patterns exactly.
  - Files: `apps/rss-reader/manifest.yaml`, `apps/rss-reader/app.py`, `apps/rss-reader/requirements.txt`, `apps/rss-reader/frontend/templates/main.html`, `apps/rss-reader/frontend/templates/reader.html`, `apps/rss-reader/frontend/static/styles.css`
  - Do: Create manifest with: appId `rss-reader`, dependency on `rss-feeds` model `>=1.0.0`, permissions for `object.create`, `edge.create`, `body.set`, SPARQL read, backgroundTasks, network access to `*` (for fetching feeds). Declare `poll-feeds` task with 5m interval. Declare UI pages (main reader page). Create `app.py` with `RSSReaderApp` — route handlers for reader fragments, `poll-feeds` task handler. The poll-feeds handler: queries existing FeedSubscription objects via SPARQL, for each subscription fetches the feed via feedparser, for each new entry creates an Article object via `ctx.commands.bulk()` with type `urn:sempkm:model:rss-feeds:Article`. Include `requirements.txt` with `feedparser>=6.0`. Create minimal frontend templates.
  - Verify: `python -c "from backend.app.apps.manifest import parse_app_manifest; m = parse_app_manifest('apps/rss-reader/manifest.yaml'); print(f'OK: {m.appId} v{m.version}, tasks: {[t.id for t in m.tasks]}')"` — manifest validates with poll-feeds task. `python -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('Syntax OK')"` — app code parses.
  - Done when: `apps/rss-reader/` directory has valid manifest, syntactically correct app.py with poll-feeds task handler that uses feedparser and ctx.commands.bulk(), requirements.txt, and minimal templates.

- [x] **T04: Unit tests for feed parsing pipeline and article creation** `est:45m`
  - Why: Proves the data path contract without requiring a running Docker stack. Tests the feed entry → article mapping, IRI minting, bulk command assembly, and error handling — giving S02 a solid foundation to extend.
  - Files: `backend/tests/test_rss_feed_parser.py`
  - Do: Write ≥10 unit tests covering: RSS 2.0 entry parsing produces correct article dict, Atom entry parsing produces correct article dict, entry with missing fields handled gracefully, article IRI minted from feed URL + entry ID, duplicate detection via article IRI, bulk command assembly with correct type IRI and properties, feedparser error handling (malformed XML), poll-feeds task flow with mocked SDK clients (mock ctx.commands.bulk, mock ctx.graph.query for subscriptions). Import and test the feed parsing functions from `apps/rss-reader/app.py` directly (add `sys.path` for apps dir).
  - Verify: `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — all ≥10 tests pass.
  - Done when: All tests pass, covering RSS 2.0 and Atom feed entry parsing, article IRI generation, bulk command assembly, and error paths.

## Files Likely Touched

- `backend/sdk/sempkm_app_sdk/clients/commands.py`
- `backend/tests/test_iri_prefix_fix.py`
- `backend/tests/test_rss_feed_parser.py`
- `models/rss-feeds/manifest.yaml`
- `models/rss-feeds/ontology/rss-feeds.jsonld`
- `models/rss-feeds/shapes/rss-feeds.jsonld`
- `models/rss-feeds/views/rss-feeds.jsonld`
- `models/rss-feeds/seed/rss-feeds.jsonld`
- `apps/rss-reader/manifest.yaml`
- `apps/rss-reader/app.py`
- `apps/rss-reader/requirements.txt`
- `apps/rss-reader/frontend/templates/main.html`
- `apps/rss-reader/frontend/templates/reader.html`
- `apps/rss-reader/frontend/static/styles.css`
