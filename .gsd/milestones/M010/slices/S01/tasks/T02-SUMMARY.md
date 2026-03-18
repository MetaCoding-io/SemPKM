---
id: T02
parent: S01
milestone: M010
provides:
  - "rss-feeds Mental Model with Article and FeedSubscription OWL classes, SHACL shapes, and ViewSpecs"
key_files:
  - models/rss-feeds/manifest.yaml
  - models/rss-feeds/ontology/rss-feeds.jsonld
  - models/rss-feeds/shapes/rss-feeds.jsonld
  - models/rss-feeds/views/rss-feeds.jsonld
key_decisions:
  - "rss namespace prefix: rss: → urn:sempkm:model:rss-feeds:"
  - "FeedSubscription browserVisible: false — managed by app, not cluttering object browser"
  - "Article subClassOf gist:FormattedContent; FeedSubscription has no gist superclass"
  - "Shared dcterms properties (title, created, description) used on Article; rss-namespaced properties for feed-specific fields"
patterns_established:
  - "RSS model follows basic-pkm ontology/shapes/views pattern exactly for new Mental Model creation"
  - "seed: null in manifest — no seed data file needed for app-populated models"
observability_surfaces:
  - "parse_manifest(Path('models/rss-feeds')) validates manifest; raises ValidationError on failure"
  - "JSON-LD files loadable via json.load(); @graph arrays contain class/property/shape/view definitions"
  - "Admin > Models shows rss-feeds v1.0.0 after installation; SPARQL query for owl:Class in rss namespace confirms ontology loaded"
duration: 8m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Create rss-feeds Mental Model with Article and FeedSubscription types

**Created rss-feeds Mental Model with Article (9 properties) and FeedSubscription (8 properties) types, SHACL shapes with property groups, and articles table/card ViewSpecs.**

## What Happened

Built the complete `models/rss-feeds/` directory following the `basic-pkm` reference implementation pattern exactly:

1. **manifest.yaml** — Defines model metadata, `rss:` prefix → `urn:sempkm:model:rss-feeds:`, two icon definitions (Article=newspaper/#f59e0b, FeedSubscription=rss/#3b82f6). FeedSubscription has `browserVisible: false` since it's app-managed. `seed: null` since articles are created by the RSS reader app, not seeded.

2. **ontology/rss-feeds.jsonld** — OWL ontology with 2 classes and 13 properties. `rss:Article` (subClassOf `gist:FormattedContent`) has 6 rss-namespaced properties (link, author, feedSource, isRead, isStarred, articleId) plus 3 dcterms properties via shapes (title, created, description). `rss:FeedSubscription` has 7 rss-namespaced properties (feedUrl, siteUrl, lastPolled, errorCount, lastError, etag, lastModifiedHeader) plus dcterms:title via shapes.

3. **shapes/rss-feeds.jsonld** — SHACL shapes with 7 PropertyGroups. ArticleShape has 4 groups (Basic Info, Feed, Status, Metadata) with 9 property definitions. FeedSubscriptionShape has 3 groups (Feed Info, Polling, Metadata) with 8 property definitions. Includes `sh:minCount` constraints (title required on Article, feedUrl required on FeedSubscription).

4. **views/rss-feeds.jsonld** — 2 ViewSpecs (articles table, articles card) plus 2 SavedQueries (unread articles, starred articles). Table view sorts by published date descending with columns for title, author, published, feed source, read/starred status.

## Verification

- `parse_manifest(Path('models/rss-feeds'))` — validates without errors, returns `rss-feeds v1.0.0`
- All 3 JSON-LD files parse as valid JSON with correct `@graph` entry counts (16 ontology, 9 shapes, 4 views)
- Article has 9 shape properties (≥8 required) ✓
- FeedSubscription has 8 shape properties (≥5 required) ✓
- 2 OWL classes, 2 SHACL NodeShapes, 7 PropertyGroups, 2 ViewSpecs confirmed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "from backend.app.models.manifest import parse_manifest; ..."` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import json; [json.load(open(...)) for p in ...]"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && python3 -m pytest tests/test_iri_prefix_fix.py -v` | 0 | ✅ pass (13/13) | 0.2s |
| 4 | `cd backend && python3 -m pytest tests/test_rss_feed_parser.py -v` | — | ⏳ pending (T03+) | — |
| 5 | `python3 -c "from backend.app.apps.manifest import parse_app_manifest; ..."` | — | ⏳ pending (T04+) | — |

## Diagnostics

- **Manifest validation:** `backend/.venv/bin/python3 -c "from backend.app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('models/rss-feeds')); print(m.modelId, m.version)"` → `rss-feeds 1.0.0`
- **Ontology classes:** SPARQL `SELECT ?c WHERE { ?c a owl:Class . FILTER(STRSTARTS(STR(?c), "urn:sempkm:model:rss-feeds:")) }` → returns Article and FeedSubscription
- **JSON integrity:** `python3 -c "import json; json.load(open('models/rss-feeds/ontology/rss-feeds.jsonld'))"` — any parse error means malformed JSON-LD

## Deviations

- Added a card ViewSpec (`rss:view-article-card`) and two SavedQueries (unread/starred articles) beyond the plan's minimum of one table view — these are free and useful for downstream tasks.

## Known Issues

None.

## Files Created/Modified

- `models/rss-feeds/manifest.yaml` — Model manifest with metadata, prefixes, icon definitions
- `models/rss-feeds/ontology/rss-feeds.jsonld` — OWL ontology with Article and FeedSubscription classes + 13 properties
- `models/rss-feeds/shapes/rss-feeds.jsonld` — SHACL shapes with PropertyGroups for form generation
- `models/rss-feeds/views/rss-feeds.jsonld` — ViewSpecs for articles table/card + saved queries
