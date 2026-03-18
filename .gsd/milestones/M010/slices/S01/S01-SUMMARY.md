---
id: S01
parent: M010
milestone: M010
provides:
  - "Fixed SDK IRI prefix validation (D179): apps can reference model types, standard vocabs, and user-types in commands"
  - "rss-feeds Mental Model v1.0.0 with Article (9 properties) and FeedSubscription (8 properties) OWL classes, SHACL shapes, ViewSpecs, SavedQueries"
  - "rss-reader app skeleton with poll-feeds task handler creating articles via ctx.commands.bulk()"
  - "51 unit tests (13 IRI prefix + 38 feed parser) proving the data pipeline contract"
requires:
  - slice: M009/S05
    provides: "CommandClient._check_iri_prefix() to fix, bulk EventStore API, permission enforcement"
  - slice: M009/S02
    provides: "App SDK (sempkm-app-sdk) with App class, route/task decorators, AppContext with scoped clients"
affects:
  - S02
  - S03
key_files:
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/tests/test_iri_prefix_fix.py
  - backend/tests/test_rss_feed_parser.py
  - models/rss-feeds/manifest.yaml
  - models/rss-feeds/ontology/rss-feeds.jsonld
  - models/rss-feeds/shapes/rss-feeds.jsonld
  - models/rss-feeds/views/rss-feeds.jsonld
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/app.py
  - apps/rss-reader/requirements.txt
key_decisions:
  - "D179: IRI prefix enforcement scoped to urn:sempkm:app:* and urn:sempkm:data:* only — model/user-types/http(s) pass through"
  - "D180: Article IRI minted via SHA-256 of (feed_iri + entry_id) — stable across URL redirects"
  - "D181: FeedSubscription browserVisible: false — managed by app, not cluttering object browser"
  - "rss namespace prefix: rss: → urn:sempkm:model:rss-feeds:"
  - "Article subClassOf gist:FormattedContent; shared dcterms properties (title, created, description)"
  - "seed: null in manifest — no seed data for app-populated models"
patterns_established:
  - "_check_iri_prefix() whitelist: pass-through for model/user-types/http(s), enforce only on app/data namespaces"
  - "Pure helper functions (entry_to_article, _mint_article_iri) with zero SDK dependency — importable and testable directly"
  - "importlib.util.spec_from_file_location for testing app modules that collide with backend/app/ package"
  - "poll-feeds task: SPARQL query for subscriptions → feedparser per feed → dedup → bulk create articles"
  - "RSS model follows basic-pkm ontology/shapes/views pattern exactly for new Mental Model creation"
observability_surfaces:
  - "PermissionError from _check_iri_prefix() includes offending IRI and required prefix"
  - "poll-feeds task returns {feeds_polled: N, articles_created: M} and logs per-feed stats"
  - "parse_manifest(Path('models/rss-feeds')) validates model; parse_app_manifest('apps/rss-reader/manifest.yaml') validates app"
drill_down_paths:
  - .gsd/milestones/M010/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M010/slices/S01/tasks/T04-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-18
---

# S01: Platform fix + Mental Model + App data pipeline

**Fixed the SDK IRI prefix validation bug blocking all cross-namespace references, built the rss-feeds Mental Model with Article and FeedSubscription types, and created the rss-reader app skeleton with a poll-feeds task handler that parses RSS feeds and bulk-creates articles via the SDK — all proved by 51 unit tests.**

## What Happened

This slice retired the #1 platform risk for M010 and established the complete data pipeline from feed parsing through to article creation in the triplestore.

**T01 — IRI prefix fix (D179).** The SDK's `_check_iri_prefix()` was rejecting every IRI that didn't match the app's own `urn:sempkm:app:{appId}:` prefix. This made it impossible for any app to reference model-defined types like `urn:sempkm:model:rss-feeds:Article`. The fix rewrites the method to only enforce prefix on `urn:sempkm:app:*` (foreign app namespaces) and `urn:sempkm:data:*`. Model types, user-types, and standard vocabularies (http/https) now pass through unchecked. 13 unit tests cover every branch including error message content.

**T02 — rss-feeds Mental Model.** Created `models/rss-feeds/` following the basic-pkm reference pattern exactly. OWL ontology defines `rss:Article` (subClassOf `gist:FormattedContent`, 9 properties including title, link, author, published, isRead, isStarred) and `rss:FeedSubscription` (8 properties including feedUrl, lastPolled, etag, errorCount). SHACL shapes with 7 PropertyGroups for form generation. Two ViewSpecs (articles table, articles card) and two SavedQueries (unread articles, starred articles). FeedSubscription has `browserVisible: false` (D181) since it's app-managed.

**T03 — rss-reader app skeleton.** Created `apps/rss-reader/` following test-app patterns. The `poll-feeds` task handler queries FeedSubscription objects via SPARQL, parses each feed with feedparser, deduplicates articles against existing IRIs in the triplestore, and bulk-creates new Article objects via `ctx.commands.bulk()`. Article IRIs use SHA-256 of `feed_iri + entry_id` (D180) for stable deduplication. Pure helper functions (`entry_to_article`, `_mint_article_iri`) are designed for direct import by tests — zero SDK dependency. Manifest declares rss-feeds model ≥1.0.0 dependency, object.create/object.patch/edge.create/body.set permissions, 5m poll interval, and UI stubs for reader page, views, and command palette entries.

**T04 — 38 unit tests.** Comprehensive test coverage for the data pipeline: RSS 2.0 and Atom entry mapping, IRI determinism (7 tests), date parsing, duplicate detection, bulk command assembly, error handling (bozo feeds, empty feeds, no subscriptions), and full poll-feeds task flow with mocked SDK clients. Uses `importlib.util.spec_from_file_location` to load the rss-reader's `app.py` without name collision with `backend/app/`.

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `cd backend && uv run python -m pytest tests/test_iri_prefix_fix.py -v` — 13 IRI prefix tests | ✅ 13/13 passed (0.22s) |
| 2 | `cd backend && uv run python -m pytest tests/test_rss_feed_parser.py -v` — 38 feed parser tests | ✅ 38/38 passed (0.28s) |
| 3 | `test_foreign_app_iri_blocked` diagnostic — PermissionError includes IRI and prefix | ✅ passed |
| 4 | `parse_manifest(Path('models/rss-feeds'))` — model manifest validates | ✅ rss-feeds v1.0.0 |
| 5 | `parse_app_manifest('apps/rss-reader/manifest.yaml')` — app manifest validates | ✅ rss-reader v1.0.0, tasks: ['poll-feeds'] |
| 6 | JSON-LD integrity — ontology (16), shapes (9), views (4) @graph entries | ✅ all parse as valid JSON |
| 7 | `ast.parse(open('apps/rss-reader/app.py').read())` — syntax check | ✅ Syntax OK |
| 8 | Docker integration (model install → app install → poll → SPARQL query) | ⏳ deferred to S02 integration |

## Requirements Advanced

- RSS-01 — poll-feeds task handler parses feeds and creates articles via bulk EventStore; polling interval declared in manifest. Feed subscription/error-tracking properties defined in model. Full end-to-end data pipeline unit-tested. Missing: live Docker integration, subscription management UI, error indicator UI.
- RSS-07 — rss-feeds model created with Article and FeedSubscription types, OWL ontology, SHACL shapes, ViewSpecs, and SavedQueries. Model validates against ManifestSchema and is installable independently. Missing: web-annotations model (deferred to M011 per roadmap).
- APP-05 — IRI prefix enforcement fix proven by 13 unit tests. Model namespace IRIs, standard vocabularies, and user-types now pass validation. Foreign app IRIs still blocked.

## Requirements Validated

- None newly validated — all requirements advanced are partial; full validation requires Docker integration (S02+) or complete UI (S03+).

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T01 plan expected `test_app_permissions.py` to exist in the worktree for regression testing — it doesn't. No regression was possible, but the new tests cover the same IRI prefix paths more thoroughly.
- T03 uses `feed_iri` (not `feed_url`) for article IRI hashing — more stable for dedup since URLs can redirect but IRIs are canonical. Plan implied feed_url.
- T04 wrote 38 tests (vs plan's ≥10 minimum) — extra coverage strengthens the contract at no cost.
- T02 added bonus ViewSpec (articles card) and two SavedQueries (unread/starred) beyond the plan's minimum — useful for S03/S04 downstream.

## Known Limitations

- **No Docker integration proof yet.** The full pipeline (model install → app install → poll-feeds → articles in triplestore) has only been unit-tested with mocked SDK clients. Real integration testing requires the Docker stack, which S02 will prove.
- **Frontend templates are stubs.** The 5 HTML templates in `apps/rss-reader/frontend/templates/` contain minimal placeholder content. S03 builds the real reader UI.
- **feedparser not installed in backend venv.** It was installed ad-hoc for T03/T04 testing. In Docker, it installs from the app's `requirements.txt` during app installation.

## Follow-ups

- S02 must prove the Docker integration path: install rss-feeds model → install rss-reader app → trigger poll-feeds → articles queryable in triplestore.
- S02 needs to extend `FeedService` with subscription management using the patterns established here (SPARQL query for subscriptions, object.create for new subscriptions).
- S03 can use the stub templates as starting points and the SavedQueries (unread/starred) for workspace views.

## Files Created/Modified

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — Added `_check_iri_prefix()` method with namespace whitelist; updated `_check_permissions()` to delegate
- `backend/tests/test_iri_prefix_fix.py` — New: 13 tests covering all IRI prefix whitelist branches and error messages
- `backend/tests/test_rss_feed_parser.py` — New: 38 tests covering feed entry mapping, IRI minting, date parsing, dedup, bulk assembly, error handling, and task flow
- `models/rss-feeds/manifest.yaml` — New: model manifest with Article and FeedSubscription type definitions, icons, prefixes
- `models/rss-feeds/ontology/rss-feeds.jsonld` — New: OWL ontology with 2 classes and 13 properties
- `models/rss-feeds/shapes/rss-feeds.jsonld` — New: SHACL shapes with 7 PropertyGroups for form generation
- `models/rss-feeds/views/rss-feeds.jsonld` — New: 2 ViewSpecs (table/card) and 2 SavedQueries (unread/starred)
- `apps/rss-reader/manifest.yaml` — New: app manifest with dependencies, permissions, tasks, UI declarations
- `apps/rss-reader/app.py` — New: core app with poll-feeds task handler, pure helper functions, stub routes
- `apps/rss-reader/requirements.txt` — New: feedparser>=6.0 dependency
- `apps/rss-reader/frontend/templates/main.html` — New: main page stub
- `apps/rss-reader/frontend/templates/reader.html` — New: reader page stub
- `apps/rss-reader/frontend/templates/unread-view.html` — New: unread articles view stub
- `apps/rss-reader/frontend/templates/starred-view.html` — New: starred articles view stub
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — New: subscribe dialog with htmx form
- `apps/rss-reader/frontend/static/styles.css` — New: placeholder CSS

## Forward Intelligence

### What the next slice should know
- `entry_to_article()` and `_mint_article_iri()` are pure functions with zero SDK dependency — import them directly from `apps/rss-reader/app.py` for extending or testing.
- The model's SHACL shapes define `isRead` and `isStarred` as `xsd:boolean` with defaults `false` — S02/S03 can use `object.patch` to toggle these.
- The SavedQueries in `views/rss-feeds.jsonld` use SPARQL with `FILTER(?isRead = false)` and `FILTER(?isStarred = true)` — these work immediately once articles exist in the triplestore.
- The manifest declares permissions for `object.create`, `object.patch`, `edge.create`, `body.set`, SPARQL read, backgroundTasks, and network access to `*` — this is the maximal set for feed operations.

### What's fragile
- **importlib pattern for testing app modules** — `backend/tests/test_rss_feed_parser.py` uses `importlib.util.spec_from_file_location` to avoid the `backend/app/` name collision. If the test file is moved or `apps/rss-reader/app.py` is renamed, the hardcoded path will break. This is documented as Knowledge Pattern #2.
- **feedparser in backend test venv** — feedparser was pip-installed into the backend venv for testing. It's not in `pyproject.toml` dependencies. If the venv is recreated, run `pip install feedparser` again, or add it to dev dependencies.

### Authoritative diagnostics
- `cd backend && uv run python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py -v` — runs all 51 S01 tests in <0.5s. Any failure here means a regression.
- `_check_iri_prefix()` is the single method that gates IRI validation — check `backend/sdk/sempkm_app_sdk/clients/commands.py` for the whitelist logic.

### What assumptions changed
- Plan assumed `test_app_permissions.py` existed in the worktree — it doesn't. The IRI prefix fix tests are self-contained and don't depend on that file.
- Plan assumed D171 was the decision ID for the IRI prefix fix — D171 was already taken (AppManager restart counts). The actual decision IDs are D179/D180/D181.
