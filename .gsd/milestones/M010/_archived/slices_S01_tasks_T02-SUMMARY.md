---
id: T02
parent: S01
milestone: M010
provides:
  - rss-feeds Mental Model (v1.0.0) with Article and FeedSubscription OWL classes, SHACL shapes, and ViewSpec
  - Model namespace urn:sempkm:model:rss-feeds: with rss prefix
key_files:
  - models/rss-feeds/manifest.yaml
  - models/rss-feeds/ontology/rss-feeds.jsonld
  - models/rss-feeds/shapes/rss-feeds.jsonld
  - models/rss-feeds/views/rss-feeds.jsonld
key_decisions:
  - "Article subClassOf gist:FormattedContent (aligns with Note's superclass — both are rich text content); FeedSubscription has no gist superclass (no natural fit)"
  - "FeedSubscription has browserVisible: false — managed by the app, not cluttering the object browser"
  - "No seed data file — manifest.seed is null, model loader handles this gracefully"
patterns_established:
  - "RSS model uses dcterms:title/dcterms:created/dcterms:description for standard properties, rss:-prefixed properties only for domain-specific (feedSource, isRead, isStarred, articleId, feedUrl, etc.)"
  - "ViewSpec sempkm namespace uses urn:sempkm:vocab: prefix (matching basic-pkm views pattern)"
observability_surfaces:
  - "parse_manifest(Path('models/rss-feeds')) validates model structure — raises ValidationError with field-level details on failure"
  - "JSON-LD files are independently validatable: json.load() for syntax, @graph inspection for semantic content"
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Created rss-feeds Mental Model with Article and FeedSubscription types

**Standalone `rss-feeds` Mental Model (v1.0.0) defining `rss:Article` (9 properties) and `rss:FeedSubscription` (8 properties) with OWL ontology, SHACL shapes with property groups, and Articles Table ViewSpec.**

## What Happened

Created `models/rss-feeds/` following the exact patterns of `models/basic-pkm/`:

1. **manifest.yaml** — modelId `rss-feeds`, namespace `urn:sempkm:model:rss-feeds:`, prefix `rss`, two icon definitions (newspaper for Article, rss for FeedSubscription). FeedSubscription has `browserVisible: false`.

2. **ontology/rss-feeds.jsonld** — OWL ontology with 2 classes and 13 custom properties:
   - `rss:Article` (subClassOf `gist:FormattedContent`) — 6 custom properties (link, author, feedSource, isRead, isStarred, articleId) plus 3 reused dcterms properties (title, created, description) = 9 total
   - `rss:FeedSubscription` — 7 custom properties (feedUrl, siteUrl, lastPolled, errorCount, lastError, etag, lastModifiedHeader) plus dcterms:title = 8 total

3. **shapes/rss-feeds.jsonld** — SHACL shapes with 5 property groups:
   - ArticleShape: 3 groups (Basic Info, Feed, Status) with 9 properties
   - FeedSubscriptionShape: 2 groups (Feed Info, Polling) with 8 properties

4. **views/rss-feeds.jsonld** — Articles Table ViewSpec with SPARQL query selecting title, author, created, feedSource, isRead, isStarred.

## Verification

- `parse_manifest(Path('models/rss-feeds'))` — **PASS**: returns modelId `rss-feeds` v1.0.0 with 2 icons
- All 3 JSON-LD files parse as valid JSON — **PASS**
- Article has ≥8 properties (9 total: title, link, author, created, description, feedSource, isRead, isStarred, articleId) — **PASS**
- FeedSubscription has ≥5 properties (8 total: title, feedUrl, siteUrl, lastPolled, errorCount, lastError, etag, lastModifiedHeader) — **PASS**
- Both SHACL NodeShapes defined with property groups — **PASS**
- At least one ViewSpec for articles table — **PASS**

### Slice-level verification (partial — T02 is intermediate):
- `cd backend && python -m pytest tests/test_iri_prefix_fix.py -v` — **PASS** (13 tests)
- `parse_manifest(Path('models/rss-feeds'))` — **PASS**
- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — not yet (T04)
- `parse_app_manifest('apps/rss-reader/manifest.yaml')` — not yet (T03)

## Diagnostics

- Validate model: `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('../models/rss-feeds')); print(m.modelId, m.version)"`
- Inspect ontology classes: `python3 -c "import json; d=json.load(open('models/rss-feeds/ontology/rss-feeds.jsonld')); print([e['@id'] for e in d['@graph'] if e.get('@type')=='owl:Class'])"`
- Inspect shape properties: `python3 -c "import json; d=json.load(open('models/rss-feeds/shapes/rss-feeds.jsonld')); [print(e['@id'], len(e.get('sh:property',[]))) for e in d['@graph'] if e.get('@type')=='sh:NodeShape']"`

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `models/rss-feeds/manifest.yaml` — Model manifest with rss-feeds metadata, namespace, prefixes, icons
- `models/rss-feeds/ontology/rss-feeds.jsonld` — OWL ontology with Article and FeedSubscription classes, 13 custom properties
- `models/rss-feeds/shapes/rss-feeds.jsonld` — SHACL shapes for both types with 5 property groups
- `models/rss-feeds/views/rss-feeds.jsonld` — Articles Table ViewSpec with SPARQL query
- `.gsd/milestones/M010/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
