---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T01: Create media-scheduler Mental Model

**Slice:** S01 — Mental Model + Podcast Sources
**Milestone:** M038

## Description

Create the `media-scheduler` Mental Model with three core types (MediaSource, MediaItem, MediaCategory), OWL ontology, SHACL shapes for form generation, ViewSpecs for table/card browsing, and a model manifest. This follows the exact pattern established by `models/rss-feeds/` — JSON-LD ontology, JSON-LD shapes, JSON-LD views, YAML manifest.

The key design decisions for the ontology:
- **MediaSource** — represents a content source (podcast feed, YouTube channel, Spotify playlist). Has `sourceType` property with `sh:in` enum constraint (podcast, youtube, spotify). Has `feedUrl` for podcast/YouTube, plus conditional GET state fields (etag, lastModifiedHeader, lastPolled, errorCount, lastError) following the rss-feeds FeedSubscription pattern.
- **MediaItem** — an individual episode/video/track discovered from a source. Has `status` with `sh:in` enum (queued, playing, completed, skipped, saved). Has `enclosureUrl` (audio/video URL), `duration` (xsd:integer seconds), `thumbnailUrl`, `externalId` (episode GUID from feed). Linked to its MediaSource via `ms:mediaSource` object property.
- **MediaCategory** — user-defined grouping (news, podcasts, music, learning). Simple type with title and color.

Namespace: `urn:sempkm:model:media-scheduler:` with prefix `ms`.

## Steps

1. Create `models/media-scheduler/manifest.yaml` following the `models/rss-feeds/manifest.yaml` pattern. Set modelId to `media-scheduler`, version `1.0.0`, namespace `urn:sempkm:model:media-scheduler:`, prefix `ms`. Declare entrypoints for ontology, shapes, and views (no seed data, no rules). Add icon entries for all 3 types: MediaSource (radio, blue), MediaItem (play-circle, green), MediaCategory (folder-music, amber). Set `browserVisible: false` on MediaCategory (it's a configuration type, not browsed directly).

2. Create `models/media-scheduler/ontology/media-scheduler.jsonld` with `@context` declaring standard prefixes (owl, rdf, rdfs, xsd, schema, dcterms, gist) plus `ms` prefix. Define 3 `owl:Class` nodes (MediaSource, MediaItem, MediaCategory). Define datatype properties: `ms:sourceType` (xsd:string, domain MediaSource), `ms:feedUrl` (xsd:anyURI, domain MediaSource), `ms:enclosureUrl` (xsd:anyURI, domain MediaItem), `ms:duration` (xsd:integer, domain MediaItem), `ms:thumbnailUrl` (xsd:anyURI, domain MediaItem), `ms:externalId` (xsd:string, domain MediaItem), `ms:status` (xsd:string, domain MediaItem), `ms:lastPolled` (xsd:dateTime), `ms:errorCount` (xsd:integer), `ms:lastError` (xsd:string), `ms:etag` (xsd:string), `ms:lastModifiedHeader` (xsd:string), `ms:color` (xsd:string, domain MediaCategory). Define object property: `ms:mediaSource` (domain MediaItem, range MediaSource), `ms:category` (domain MediaSource, range MediaCategory).

3. Create `models/media-scheduler/shapes/media-scheduler.jsonld` with SHACL NodeShapes for all 3 types. Each shape has PropertyGroups for logical form sections. MediaSourceShape: "Source Info" group (title, sourceType with sh:in, feedUrl), "Polling" group (lastPolled, errorCount, lastError), "Metadata" group (etag, lastModifiedHeader). MediaItemShape: "Basic Info" group (title, enclosureUrl, externalId, duration, thumbnailUrl, published date), "Source" group (mediaSource ref), "Status" group (status with sh:in). MediaCategoryShape: "Basic Info" group (title, description, color). Use `sh:in` for sourceType values: `["podcast", "youtube", "spotify"]`. Use `sh:in` for status values: `["queued", "playing", "completed", "skipped", "saved"]`.

4. Create `models/media-scheduler/views/media-scheduler.jsonld` with ViewSpecs. At minimum: a table view for MediaItem (columns: title, status, duration, published, source name) and a table view for MediaSource (columns: title, sourceType, feedUrl, lastPolled, errorCount). Follow the `rss-feeds/views/rss-feeds.jsonld` pattern.

## Must-Haves

- [ ] `manifest.yaml` parseable by `yaml.safe_load()` with modelId `media-scheduler`
- [ ] Ontology JSON-LD defines 3 owl:Class nodes and all properties listed above
- [ ] SHACL shapes define NodeShapes for all 3 types with `sh:in` constraints on sourceType and status
- [ ] ViewSpecs define at least one table view per browseable type
- [ ] Icons declared for all 3 types in manifest

## Verification

- `python -c "import yaml; m=yaml.safe_load(open('models/media-scheduler/manifest.yaml')); assert m['modelId']=='media-scheduler' and m['version']=='1.0.0'"` passes
- `python -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); types=[n['@id'] for n in d['@graph'] if n.get('@type')=='owl:Class']; assert 'ms:MediaSource' in types and 'ms:MediaItem' in types and 'ms:MediaCategory' in types"` passes
- `python -c "import json; d=json.load(open('models/media-scheduler/shapes/media-scheduler.jsonld')); shapes=[n['@id'] for n in d['@graph'] if n.get('@type')=='sh:NodeShape']; assert 'ms:MediaSourceShape' in shapes and 'ms:MediaItemShape' in shapes"` passes

## Observability Impact

- **Model manifest validation:** `parse_app_manifest` or `yaml.safe_load` on `manifest.yaml` emits clear parse errors if YAML is malformed or required fields missing
- **Ontology inspection:** `@graph` array in the JSON-LD is queryable for class/property counts; SPARQL `SELECT ?c WHERE { ?c a owl:Class }` returns the 3 types after install
- **Shape inspection:** SHACL shapes with `sh:in` constraints are inspectable via `SELECT ?shape WHERE { ?shape a sh:NodeShape }` and drive form generation — broken shapes produce visible form rendering failures
- **Failure visibility:** JSON parse errors on any `.jsonld` file surface immediately at model install time; missing `sh:targetClass` prevents form/view rendering for that type

## Inputs

- `models/rss-feeds/manifest.yaml` — reference pattern for model manifest structure
- `models/rss-feeds/ontology/rss-feeds.jsonld` — reference pattern for JSON-LD ontology
- `models/rss-feeds/shapes/rss-feeds.jsonld` — reference pattern for SHACL shapes with PropertyGroups
- `models/rss-feeds/views/rss-feeds.jsonld` — reference pattern for ViewSpecs

## Expected Output

- `models/media-scheduler/manifest.yaml` — model manifest with 3 type icons
- `models/media-scheduler/ontology/media-scheduler.jsonld` — OWL ontology with 3 classes and ~15 properties
- `models/media-scheduler/shapes/media-scheduler.jsonld` — SHACL shapes with sh:in constraints
- `models/media-scheduler/views/media-scheduler.jsonld` — ViewSpecs for table views
