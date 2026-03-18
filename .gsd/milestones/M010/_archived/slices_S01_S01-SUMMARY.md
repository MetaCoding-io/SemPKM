---
id: S01
parent: M010
milestone: M010
provides:
  - Fixed SDK IRI prefix validation — model namespace, standard vocab, and user-type IRIs pass through unchecked
  - rss-feeds Mental Model v1.0.0 with Article and FeedSubscription OWL classes, SHACL shapes, and ViewSpec
  - rss-reader app skeleton with poll-feeds task handler creating articles via bulk EventStore
  - Proven data pipeline: feedparser → entry_to_article → ctx.commands.bulk() → Article objects in triplestore
requires:
  - slice: M009/S05
    provides: SDK IRI prefix validation (D168), bulk EventStore (commit_bulk), permission enforcement
  - slice: M009/S02
    provides: App SDK (sempkm-app-sdk package), AppContext with scoped clients
affects:
  - S02 (feed service consumes entry_to_article, bulk command pattern, rss-feeds model types)
  - S03 (reader UI consumes installed model type IRIs, app process serving fragments)
  - S04 (workspace contributions consume article/subscription data in triplestore)
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
  - "D171: IRI prefix enforcement narrowed to urn:sempkm:app:* and urn:sempkm:data:* only — everything else passes through"
  - "D174: Article subClassOf gist:FormattedContent; FeedSubscription has no gist superclass"
  - "D175: FeedSubscription has browserVisible: false — managed by the app, not cluttering object browser"
  - "Article IRI pattern: urn:sempkm:app:rss-reader:article-{sha256(feed_url+entry_id)} — deterministic, dedup-friendly"
patterns_established:
  - "IRI prefix check is a 2-line startswith guard on urn:sempkm:app: and urn:sempkm:data: — simpler than a whitelist cascade"
  - "RSS model uses dcterms:title/dcterms:created/dcterms:description for standard properties; rss:-prefixed for domain-specific only"
  - "Bulk command pattern: async with ctx.commands.bulk(summary, source) as batch → batch.add() per article"
  - "importlib.util.spec_from_file_location for importing app modules that collide with backend package names"
observability_surfaces:
  - "PermissionError message includes both the offending IRI and the required prefix string"
  - "poll-feeds task logs per-feed: 'Polled {url}: N new articles created'"
  - "poll-feeds returns summary dict: {feeds_polled: N, articles_created: M}"
  - "parse_manifest(Path('models/rss-feeds')) validates model structure with field-level ValidationError details"
drill_down_paths:
  - .gsd/milestones/M010/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M010/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M010/slices/S01/tasks/T04-SUMMARY.md
duration: 65m
verification_result: passed
completed_at: 2026-03-17
---

# S01: Platform fix + Mental Model + App data pipeline

**Fixed the SDK IRI prefix bug (D171), created the rss-feeds Mental Model with Article/FeedSubscription types, built the rss-reader app skeleton with a poll-feeds task handler, and proved the full feedparser → bulk EventStore → triplestore data pipeline with 36 unit tests.**

## What Happened

This slice delivered four coordinated tasks that together retire the highest risk in M010 — the IRI prefix enforcement bug — and prove the complete data pipeline from RSS feed to triplestore Article objects.

**T01 (IRI prefix fix):** Rewrote `_check_iri_prefix()` in the SDK's CommandClient. The old implementation rejected ALL IRIs that didn't start with `urn:sempkm:app:{appId}:`, blocking any app from referencing model-defined types or standard vocabularies. The new implementation only enforces prefix checking on `urn:sempkm:app:*` and `urn:sempkm:data:*` — the two namespaces where apps create new IRIs needing scoping. Model types (`urn:sempkm:model:*`), user-types (`urn:sempkm:user-types:*`), standard vocabs (`http://`, `https://`), and other URN schemes pass through unchecked. 13 new tests + 4 updated existing tests, zero regressions against 33 permission tests.

**T02 (rss-feeds Mental Model):** Created `models/rss-feeds/` following the `basic-pkm` patterns exactly. OWL ontology defines `rss:Article` (9 properties, subClassOf gist:FormattedContent) and `rss:FeedSubscription` (8 properties). SHACL shapes with 5 property groups for form generation. Articles Table ViewSpec with SPARQL query. FeedSubscription marked `browserVisible: false` to keep the object browser clean.

**T03 (rss-reader app skeleton):** Created `apps/rss-reader/` following the `test-app` patterns. The manifest declares dependency on rss-feeds model, permissions for object/edge/body operations, SPARQL read, background tasks, and network wildcard. The `poll-feeds` async task handler queries existing FeedSubscription objects via SPARQL, parses each feed with feedparser, deduplicates articles via SHA-256 IRI hashing, and bulk-creates Article objects. Pure helper functions (`entry_to_article`, `parse_feed`, `get_existing_article_iris`, `_mint_article_iri`) are importable for unit testing.

**T04 (unit tests):** 23 tests covering RSS 2.0 and Atom entry mapping, IRI determinism and SHA-256 verification, duplicate detection via SPARQL mock, bulk command assembly, error handling (bozo feeds, empty feeds), date parsing, and constant validation. Used `importlib.util.spec_from_file_location` to avoid module name collision between `apps/rss-reader/app.py` and `backend/app/`.

## Verification

All slice-level verification checks pass:

- ✅ `cd backend && python -m pytest tests/test_iri_prefix_fix.py -v` — **13/13 tests passed** (≥8 required)
- ✅ `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — **23/23 tests passed** (≥10 required)
- ✅ `cd backend && python -m pytest tests/test_app_permissions.py -v` — **33/33 tests passed** (no regressions)
- ✅ `parse_manifest(Path('models/rss-feeds'))` — rss-feeds v1.0.0 with 2 icons
- ✅ `parse_app_manifest('apps/rss-reader/manifest.yaml')` — rss-reader v1.0.0, tasks: ['poll-feeds'], dependency: rss-feeds >=1.0.0
- ✅ All 3 JSON-LD files parse as valid JSON (ontology: 16 items, shapes: 7 items, views: 1 item)
- ✅ `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK
- ✅ Diagnostic: `test_foreign_app_iri_blocked` verifies PermissionError message includes both offending IRI and required prefix
- ⏳ Docker integration (install model → install app → trigger poll-feeds → articles queryable) — requires running stack, deferred to S06 E2E

**Total new tests: 36** (13 IRI prefix + 23 feed parser)

## Requirements Advanced

- RSS-01 — poll-feeds task handler created with feedparser parsing, dedup, and bulk article creation. Subscription query and per-feed polling loop implemented. Content extraction and configurable interval deferred to S02.
- RSS-07 — rss-feeds Mental Model created with Article and FeedSubscription types, OWL ontology, SHACL shapes, and ViewSpec. Model validates via parse_manifest(). Independent of app installation.

## Requirements Validated

- None fully validated in this slice (no runtime integration proof yet — deferred to S06 E2E tests).

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T01 produced 13 tests instead of planned 11 (2 extra: `test_urn_uuid_passes`, `test_own_data_namespace_still_blocked`).
- T03 added `_time_struct_to_iso()` and `_mint_article_iri()` as separate helpers (plan implied inline logic).
- T04 used `importlib.util.spec_from_file_location` instead of `sys.path.insert` due to module name collision with `backend/app/` package — this pattern is now documented in KNOWLEDGE.md.

## Known Limitations

- Docker integration not verified — install model → install app → trigger poll-feeds → articles queryable requires a running Docker stack. This will be proven in S06 E2E tests.
- `entry._feed_url` is set as a side effect on feedparser entry objects by the poll-feeds handler before calling `entry_to_article`. Works correctly but is slightly impure.
- No seed data for the rss-feeds model — the model installs with empty types. FeedSubscriptions are created by the app's subscribe flow (S02).
- Frontend templates are stubs — reader UI built in S03.

## Follow-ups

- S02 must build `FeedService.subscribe()` to create FeedSubscription objects (the poll-feeds handler queries them but doesn't create them).
- S02 should add trafilatura for full article content extraction (current implementation uses feed-provided summaries only).
- S03 builds the actual reader UI using the stub templates created here.
- S06 must run Docker integration verification (the one verification check this slice deferred).

## Files Created/Modified

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — rewrote `_check_iri_prefix()` with D171 enforcement scope
- `backend/tests/test_iri_prefix_fix.py` — 13 IRI prefix whitelist tests
- `backend/tests/test_app_permissions.py` — 4 existing tests updated for new enforcement scope
- `backend/tests/test_rss_feed_parser.py` — 23 feed parsing pipeline tests
- `models/rss-feeds/manifest.yaml` — Mental Model manifest (rss-feeds v1.0.0, 2 icons)
- `models/rss-feeds/ontology/rss-feeds.jsonld` — OWL ontology (Article, FeedSubscription, 13 properties)
- `models/rss-feeds/shapes/rss-feeds.jsonld` — SHACL shapes (5 property groups)
- `models/rss-feeds/views/rss-feeds.jsonld` — Articles Table ViewSpec
- `apps/rss-reader/manifest.yaml` — App manifest (poll-feeds task, rss-feeds dependency, permissions)
- `apps/rss-reader/app.py` — App module (poll-feeds handler, entry_to_article, parse_feed, dedup)
- `apps/rss-reader/requirements.txt` — feedparser>=6.0
- `apps/rss-reader/frontend/templates/*.html` — 5 stub templates (main, reader, unread, starred, subscribe)
- `apps/rss-reader/frontend/static/styles.css` — placeholder styles

## Forward Intelligence

### What the next slice should know
- `entry_to_article()` is a pure function — it takes a feedparser entry and returns a dict with all Article properties. S02's `FeedService` should call it directly, not rewrite the mapping logic.
- The poll-feeds handler expects FeedSubscription objects to already exist in the triplestore (queries via SPARQL). S02 must create the subscription creation flow before poll-feeds can work end-to-end.
- The `_mint_article_iri(feed_url, entry_id)` function produces deterministic IRIs. S02's dedup logic should rely on this — don't add a second dedup mechanism.
- The model namespace is `urn:sempkm:model:rss-feeds:` with prefix `rss`. All type IRIs use this namespace. Constants are defined in `app.py` as `ARTICLE_TYPE`, `SUBSCRIPTION_TYPE`, `RSS_NS`.

### What's fragile
- `entry._feed_url` side effect — the poll-feeds handler sets `entry._feed_url = feed_url` on each feedparser entry before calling `entry_to_article`. If callers forget this, `entry_to_article` falls back to `feed_iri` for the feed URL. S02 should set `_feed_url` explicitly in `FeedService` too.
- The rss-feeds model has no seed data. If the model install process strictly requires a seed file, it will fail. Currently `manifest.seed` is null and `parse_manifest()` handles this — but verify at install time.

### Authoritative diagnostics
- `cd backend && python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py -v` — 36 tests prove the IRI prefix fix and feed parsing pipeline. If any regress, check `_check_iri_prefix()` in commands.py and `entry_to_article()` in app.py.
- `parse_manifest(Path('models/rss-feeds'))` and `parse_app_manifest('apps/rss-reader/manifest.yaml')` — these are the definitive manifest validation checks.

### What assumptions changed
- The IRI prefix fix was simpler than anticipated — only 2 lines of `startswith` checks instead of a whitelist cascade. The original assumption was a complex routing table; reality is a clean guard clause.
- feedparser entry objects support attribute access (getattr) for normalized fields, not just dict access. Tests use `SimpleNamespace` to mock this pattern accurately.
