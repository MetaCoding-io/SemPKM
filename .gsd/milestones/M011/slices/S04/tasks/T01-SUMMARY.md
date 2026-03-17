---
id: T01
parent: S04
milestone: M011
provides:
  - models/research/manifest.yaml — model identity, namespace, 5 icon entries, entailment defaults
  - models/research/ontology/research.jsonld — OWL ontology with 5 classes, 22 datatype properties, 17 object properties, 6 inverseOf pairs
key_files:
  - models/research/manifest.yaml
  - models/research/ontology/research.jsonld
key_decisions:
  - Used Zettelkasten model as structural template (CRM model dir exists but has no manifest/ontology files yet)
  - No rdfs:domain omissions — all datatype properties have explicit domains (consistent with Zettelkasten pattern)
patterns_established:
  - Research ontology follows same JSON-LD @context pattern as Zettelkasten/PPV — inline only, no remote URLs
  - inverseOf declared bidirectionally on both properties in each pair (12 declarations for 6 pairs)
observability_surfaces:
  - parse_manifest(Path('../models/research')) → ManifestSchema with modelId="research", 5 icons
  - rdflib.Graph().parse() on ontology → 230 triples (≥150 threshold)
  - SPARQL on parsed graph to count classes (5), inverseOf pairs (6), object properties (17), datatype properties (22)
duration: 6m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Create manifest and OWL ontology for Research model

**Created manifest.yaml with 5 icon entries and research.jsonld ontology with 230 triples (5 classes, 22 datatype properties, 17 object properties, 6 inverseOf pairs)**

## What Happened

Created the Research model's identity and OWL foundation:

1. Read Zettelkasten manifest/ontology as structural templates (CRM dir had no manifest or ontology files)
2. Created `manifest.yaml` with modelId `research`, namespace `urn:sempkm:model:research:`, 5 icon entries (Paper/Claim/Evidence/ResearchQuestion/Argument), entailment_defaults with owl_inverseOf + shacl_rules enabled
3. Created `ontology/research.jsonld` with inline-only @context, 5 OWL classes aligned to gist (Paper→Content, Claim/Evidence/Argument→FormattedContent, ResearchQuestion→Intention), 22 datatype properties, 12 object properties in 6 inverseOf pairs, and 5 one-directional object properties
4. Added observability sections to S04-PLAN.md and T01-PLAN.md per pre-flight requirements

## Verification

- `parse_manifest(Path('../models/research'))` → ManifestSchema OK: modelId=research, version=1.0.0, 5 icons ✓
- `rdflib.Graph().parse()` → 230 triples (≥150 threshold) ✓
- 5 OWL classes confirmed: res:Paper, res:Claim, res:Evidence, res:ResearchQuestion, res:Argument ✓
- 12 owl:inverseOf declarations (6 bidirectional pairs) ✓
- 17 object properties, 22 datatype properties ✓
- All 45 subjects use `urn:sempkm:model:research:` namespace ✓
- No remote @context URLs — all inline ✓
- Slice verification check 1: Ontology: 230 (≥150) ✓
- Remaining slice checks (shapes, views, pipeline, SHACL) expected to fail until T02/T03

## Diagnostics

- `cd backend && .venv/bin/python3 -c "from pathlib import Path; from app.models.manifest import parse_manifest; m = parse_manifest(Path('../models/research')); print(f'{m.modelId} v{m.version}: {len(m.icons)} icons')"` — verify manifest
- `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g = Graph().parse('../models/research/ontology/research.jsonld', format='json-ld'); print(f'Ontology: {len(g)} triples')"` — verify ontology triple count
- Note: ManifestSchema uses `modelId` (camelCase), not `model_id` — the task plan's verification snippet had the wrong attribute name

## Deviations

- Used Zettelkasten model as structural template instead of CRM — the CRM directory had empty subdirectories (rules/, seed/, shapes/, views/) but no manifest.yaml or ontology files. Zettelkasten has the same structure needed: 5 types, inverseOf pairs, inline @context.
- ManifestSchema attribute is `modelId` not `model_id` — adjusted verification command accordingly.

## Known Issues

None.

## Files Created/Modified

- `models/research/manifest.yaml` — model manifest with 5 icon entries, research namespace, entailment defaults
- `models/research/ontology/research.jsonld` — OWL ontology with 230 triples: 5 classes, 22 datatype props, 17 object props, 6 inverseOf pairs, 5 one-directional props
- `.gsd/milestones/M011/slices/S04/S04-PLAN.md` — added Observability / Diagnostics section
- `.gsd/milestones/M011/slices/S04/tasks/T01-PLAN.md` — added Observability Impact section
