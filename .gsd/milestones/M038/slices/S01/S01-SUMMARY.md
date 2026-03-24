---
id: S01
milestone: M038
outcome: success
tasks_completed: 4
tasks_total: 4
verification: passed
completed_at: 2026-03-23
---

# S01: Mental Model + Podcast Sources — Summary

## What This Slice Delivered

A complete media-scheduler Mental Model and App Platform app that lets users subscribe to podcast RSS feeds and discover episodes as MediaItem objects. The model defines three OWL classes (MediaSource, MediaItem, MediaCategory), SHACL shapes with enum constraints (sourceType: podcast/youtube/spotify; status: queued/playing/completed/skipped/saved), and ViewSpecs for table/card browsing. The app registers with the App Platform, exposes 6 fragment routes, and includes a `poll-sources` scheduled task that parses RSS feeds via feedparser, deduplicates by deterministic IRI, and bulk-creates MediaItem objects.

## Key Artifacts

| File | Purpose |
|------|---------|
| `models/media-scheduler/manifest.yaml` | Model manifest (v1.0.0, 3 types, icons) |
| `models/media-scheduler/ontology/media-scheduler.jsonld` | OWL ontology: 3 classes, 15 properties |
| `models/media-scheduler/shapes/media-scheduler.jsonld` | SHACL shapes with PropertyGroups, sh:in enums |
| `models/media-scheduler/views/media-scheduler.jsonld` | 3 ViewSpecs (2 table + 1 card) |
| `apps/media-scheduler/manifest.yaml` | App manifest: poll-sources task (15m), permissions, UI page |
| `apps/media-scheduler/app.py` | Entrypoint: 6 routes + poll-sources task handler |
| `apps/media-scheduler/services/podcast_service.py` | Pure functions: IRI minting, feed parsing, duration parsing, subscription CRUD |
| `apps/media-scheduler/frontend/templates/` | 4 Jinja2 templates: main, sources-list, items-list, add-source |
| `apps/media-scheduler/frontend/static/styles.css` | App CSS with 44 workspace theme variable references |
| `backend/tests/test_media_scheduler.py` | 64 unit tests across 13 classes |

## Patterns Established

- **Namespace:** `urn:sempkm:model:media-scheduler:` with `ms:` prefix. App IRI minting: `urn:sempkm:app:media-scheduler:source-{sha256}` and `item-{sha256}`.
- **Poll task structure:** SPARQL source query → conditional GET (ETag/Last-Modified) → feedparser parse → dedup against existing IRIs → bulk create → state update. Identical structure to rss-reader's poll-feeds.
- **Source type filtering:** `FILTER(?sourceType = "podcast")` in the poll SPARQL query ensures YouTube/Spotify sources get separate poll tasks in S03/S04.
- **htmx proxy prefix:** All template htmx URLs use `/app/media-scheduler/` prefix per KNOWLEDGE.md rule.
- **importlib-based testing:** App module loaded via `importlib.util.spec_from_file_location` with feedparser mocked at `sys.modules` level. Poll-sources tests must patch on the app module (`_app_mod`), not the service module, because the app's fallback import binds its own function references.
- **Soft-delete via sourceType:** Unsubscribe sets `sourceType="inactive"` rather than adding a separate boolean — reuses the existing sh:in enum.
- **MAX_INITIAL_ITEMS = 50:** Cap per source per poll cycle prevents flooding on first poll of prolific feeds.

## What Downstream Slices Need to Know

- **S02 (Rules + Plan):** MediaSource and MediaItem types are in the triplestore. The `poll-sources` task populates items. Rules engine should query `ms:MediaItem` objects filtered by source type and status. `ms:MediaCategory` exists but has no seed data — S02 can use it for rule-based categorization.
- **S03 (YouTube):** The `sourceType` sh:in enum already includes "youtube". Add a separate poll task (e.g., `poll-youtube`) that queries sources with `FILTER(?sourceType = "youtube")`. Reuse the deterministic IRI minting pattern (`mint_item_iri(source_iri, video_id)`). YouTube items use `ms:enclosureUrl` for the video URL.
- **S04 (Spotify):** Same pattern as S03. `sourceType` includes "spotify". Spotify items don't have RSS feeds — the poll task queries the Spotify API directly. OAuth tokens go in StateClient per D346.
- **S05 (Context):** The `/_fragments/current-suggestion` endpoint doesn't exist yet — S05 creates it. The app subscribes to context SSE events; the rules engine evaluates against context and selects from available MediaItems.

## Verification Results

| Check | Result |
|-------|--------|
| `cd backend && python -m pytest tests/test_media_scheduler.py -v` | ✅ 64/64 passed (0.31s) |
| Model manifest YAML valid with modelId=media-scheduler | ✅ pass |
| Ontology contains MediaSource, MediaItem, MediaCategory classes | ✅ pass |
| App manifest validates: appId=media-scheduler, 1 task, poll-sources | ✅ pass |
| htmx URLs all use `/app/media-scheduler/` proxy prefix | ✅ pass |

## Decisions Made

- D351: Flat sh:in enum for sourceType, not OWL subclasses
- D352: Media scheduler owns its model, does not extend rss-feeds
- T01: gist:FormattedContent as MediaItem superclass (matches rss-feeds Article pattern)
- T02: sourceType="inactive" for soft-delete unsubscribe
- T03: feedparser used directly (no JSON Feed dispatch — podcast feeds are always XML/RSS)

## Known Issues

- No MEDIA-01 through MEDIA-10 requirements in REQUIREMENTS.md yet — referenced in roadmap but not defined. Future slices should create them.
- Badge status colors use hardcoded hex (youtube red, spotify green) since no matching workspace theme variables exist.
