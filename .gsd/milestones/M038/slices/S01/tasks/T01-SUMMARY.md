---
id: T01
parent: S01
milestone: M038
provides:
  - media-scheduler Mental Model with 3 OWL classes, 15 properties, SHACL shapes, and ViewSpecs
key_files:
  - models/media-scheduler/manifest.yaml
  - models/media-scheduler/ontology/media-scheduler.jsonld
  - models/media-scheduler/shapes/media-scheduler.jsonld
  - models/media-scheduler/views/media-scheduler.jsonld
key_decisions:
  - Used gist:FormattedContent as superclass for MediaItem (matches rss-feeds Article pattern)
  - Added dcterms:description to MediaItemShape for episode summaries (not in original plan but needed for card view)
patterns_established:
  - Media scheduler namespace urn:sempkm:model:media-scheduler: with ms prefix
  - Polling state fields (etag, lastModifiedHeader, lastPolled, errorCount, lastError) follow rss-feeds FeedSubscription pattern exactly
observability_surfaces:
  - JSON-LD files parseable with json.load() for programmatic inspection
  - SHACL shapes with sh:in constraints drive form enum dropdowns for sourceType and status
  - ViewSpec SPARQL queries inspectable for correct property IRIs
duration: 8m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Create media-scheduler Mental Model

**Created media-scheduler Mental Model with MediaSource, MediaItem, and MediaCategory types — OWL ontology (3 classes, 15 properties), SHACL shapes with sh:in enum constraints, and 3 ViewSpecs for table/card browsing.**

## What Happened

Built the complete media-scheduler Mental Model following the rss-feeds reference pattern. The ontology defines MediaSource (podcast/youtube/spotify content sources with polling state), MediaItem (episodes/videos/tracks with consumption status), and MediaCategory (user-defined groupings). SHACL shapes include PropertyGroups for logical form sections and sh:in constraints for sourceType (podcast/youtube/spotify) and status (queued/playing/completed/skipped/saved). ViewSpecs provide two table views (MediaItem and MediaSource) plus a card view for MediaItem. All files use JSON-LD format consistent with the rss-feeds model.

## Verification

All task-level and applicable slice-level checks pass:
- Manifest YAML loads with correct modelId and version
- Ontology contains all 3 owl:Class nodes and 15 properties (13 datatype + 2 object)
- Shapes contain all 3 NodeShapes with sh:in constraints on sourceType and status
- ViewSpecs define 2 table views + 1 card view
- Icons declared for all 3 types in manifest

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import yaml; m=yaml.safe_load(open('models/media-scheduler/manifest.yaml')); assert m['modelId']=='media-scheduler' and m['version']=='1.0.0'"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); types=[n['@id'] for n in d['@graph'] if n.get('@type')=='owl:Class']; assert 'ms:MediaSource' in types and 'ms:MediaItem' in types and 'ms:MediaCategory' in types"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import json; d=json.load(open('models/media-scheduler/shapes/media-scheduler.jsonld')); shapes=[n['@id'] for n in d['@graph'] if n.get('@type')=='sh:NodeShape']; assert 'ms:MediaSourceShape' in shapes and 'ms:MediaItemShape' in shapes"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); assert any(n.get('@id','').endswith('MediaSource') for n in d['@graph'])"` | 0 | ✅ pass | <1s |
| 5 | ViewSpecs count check (2 table + 1 card) | 0 | ✅ pass | <1s |
| 6 | Icons declared for all 3 types | 0 | ✅ pass | <1s |

## Diagnostics

- Inspect model structure: `python3 -c "import json; print(json.dumps(json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')), indent=2))"`
- List classes: `python3 -c "import json; d=json.load(open('models/media-scheduler/ontology/media-scheduler.jsonld')); print([n['@id'] for n in d['@graph'] if n.get('@type')=='owl:Class'])"`
- List shapes: `python3 -c "import json; d=json.load(open('models/media-scheduler/shapes/media-scheduler.jsonld')); print([n['@id'] for n in d['@graph'] if n.get('@type')=='sh:NodeShape'])"`

## Deviations

- Added `dcterms:description` property to MediaItemShape (not explicitly in the plan's property list) — needed for card view subtitle and episode summaries, matches the rss-feeds Article pattern.
- Used `folder` icon for MediaCategory instead of `folder-music` — Lucide icon set doesn't include `folder-music`, `folder` is the closest standard icon.

## Known Issues

None.

## Files Created/Modified

- `models/media-scheduler/manifest.yaml` — Model manifest with 3 type icons, namespace, and entrypoints
- `models/media-scheduler/ontology/media-scheduler.jsonld` — OWL ontology with 3 classes and 15 properties
- `models/media-scheduler/shapes/media-scheduler.jsonld` — SHACL shapes with PropertyGroups and sh:in constraints
- `models/media-scheduler/views/media-scheduler.jsonld` — 3 ViewSpecs (2 table + 1 card)
- `.gsd/milestones/M038/slices/S01/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
