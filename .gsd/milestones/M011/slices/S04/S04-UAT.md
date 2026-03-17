# S04: Research Workflow Model — UAT

**Milestone:** M011
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S04 is pure content (6-file .sempkm-model archive) with no platform code changes (D149). All verification is offline parsing + validation. Docker integration testing is deferred to S05.

## Preconditions

- Python 3.14+ with backend venv available at `backend/.venv/`
- `rdflib`, `pyshacl` installed in the venv
- `models/research/` directory contains all 6 files: manifest.yaml, ontology/research.jsonld, shapes/research.jsonld, views/research.jsonld, rules/research.ttl, seed/research.jsonld
- Backend app modules importable (`app.models.manifest`, `app.models.loader`, `app.models.validator`)

## Smoke Test

Run the full pipeline validation:
```bash
cd backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
from app.models.loader import load_archive
from app.models.validator import validate_archive
m = parse_manifest(Path('../models/research'))
a = load_archive(Path('../models/research'), m)
r = validate_archive(a)
print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}, Warnings: {len(r.warnings)}')
assert r.is_valid and len(r.errors) == 0
"
```
**Expected:** `Valid: True, Errors: 0, Warnings: 0`

## Test Cases

### 1. Manifest Parsing

1. Run: `cd backend && .venv/bin/python3 -c "from pathlib import Path; from app.models.manifest import parse_manifest; m = parse_manifest(Path('../models/research')); print(f'{m.modelId} v{m.version}: {len(m.icons)} icons, ns={m.namespace}')"`
2. **Expected:** `research v1.0.0: 5 icons, ns=urn:sempkm:model:research:`

### 2. Ontology Triple Count and Classes

1. Run:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph, OWL
   g = Graph().parse('../models/research/ontology/research.jsonld', format='json-ld')
   classes = set(s for s, p, o in g.triples((None, None, OWL.Class)) if 'research' in str(s))
   print(f'Ontology: {len(g)} triples, {len(classes)} classes')
   for c in sorted(classes): print(f'  {c}')
   "
   ```
2. **Expected:** 230 triples, 5 classes: Paper, Claim, Evidence, ResearchQuestion, Argument (all with `urn:sempkm:model:research:` prefix)

### 3. Shapes Triple Count and NodeShapes

1. Run:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph, SH
   SH = __import__('rdflib').Namespace('http://www.w3.org/ns/shacl#')
   g = Graph().parse('../models/research/shapes/research.jsonld', format='json-ld')
   shapes = set(s for s, p, o in g.triples((None, SH.targetClass, None)))
   print(f'Shapes: {len(g)} triples, {len(shapes)} NodeShapes')
   "
   ```
2. **Expected:** 535 triples, 5 NodeShapes

### 4. Views Triple Count

1. Run: `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g = Graph().parse('../models/research/views/research.jsonld', format='json-ld'); print(f'Views: {len(g)} triples')"`
2. **Expected:** 81 triples (≥80)

### 5. Rules Parse and Triple Count

1. Run: `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g = Graph().parse('../models/research/rules/research.ttl', format='turtle'); print(f'Rules: {len(g)} triples')"`
2. **Expected:** 39 triples

### 6. Seed Data Parse and Object Count

1. Run:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph, RDF
   g = Graph().parse('../models/research/seed/research.jsonld', format='json-ld')
   types = {}
   for s, p, o in g.triples((None, RDF.type, None)):
       t = str(o).split(':')[-1] if ':' in str(o) else str(o)
       types[t] = types.get(t, 0) + 1
   print(f'Seed: {len(g)} triples, {sum(types.values())} typed objects')
   for t, c in sorted(types.items()): print(f'  {t}: {c}')
   "
   ```
2. **Expected:** 175 triples, 16 typed objects (3 Paper, 5 Claim, 5 Evidence, 2 ResearchQuestion, 1 Argument)

### 7. Full Pipeline Validation (parse_manifest + load_archive + validate_archive)

1. Run:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from pathlib import Path
   from app.models.manifest import parse_manifest
   from app.models.loader import load_archive
   from app.models.validator import validate_archive
   m = parse_manifest(Path('../models/research'))
   a = load_archive(Path('../models/research'), m)
   r = validate_archive(a)
   print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}, Warnings: {len(r.warnings)}')
   for e in r.errors: print(f'  E: {e.file}: {e.message}')
   for w in r.warnings: print(f'  W: {w.file}: {w.message}')
   assert r.is_valid and len(r.errors) == 0, 'Pipeline validation failed'
   print('PASS')
   "
   ```
2. **Expected:** `Valid: True, Errors: 0, Warnings: 0` then `PASS`

### 8. SHACL-AF Validation Fires All 4 Rules

1. Run:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph
   import pyshacl
   data = Graph().parse('../models/research/seed/research.jsonld', format='json-ld')
   shapes = Graph().parse('../models/research/shapes/research.jsonld', format='json-ld')
   rules = Graph().parse('../models/research/rules/research.ttl', format='turtle')
   ontology = Graph().parse('../models/research/ontology/research.jsonld', format='json-ld')
   combined = shapes + rules
   conforms, rg, text = pyshacl.validate(data, shacl_graph=combined, ont_graph=ontology, advanced=True)
   print(f'Conforms: {conforms}')
   print(text[:3000])
   assert not conforms, 'Expected conforms=False'
   # Count severities
   warnings = text.count('sh:Warning')
   infos = text.count('sh:Info')
   print(f'Warnings: {warnings}, Infos: {infos}')
   assert warnings == 2 and infos == 2, f'Expected 2W+2I, got {warnings}W+{infos}I'
   print('PASS')
   "
   ```
2. **Expected:** `Conforms: False` with exactly 4 violations:
   - Warning: UnsupportedClaimValidationShape → `seed-claim-kg-reduce-silos`
   - Info: ContestedClaimValidationShape → `seed-claim-pkm-failure`
   - Warning: OrphanEvidenceValidationShape → `seed-evidence-orphan`
   - Info: UnansweredQuestionValidationShape → `seed-rq-scaling-limits`

### 9. InverseOf Pairs in Ontology

1. Run:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph, OWL
   g = Graph().parse('../models/research/ontology/research.jsonld', format='json-ld')
   pairs = list(g.triples((None, OWL.inverseOf, None)))
   print(f'inverseOf declarations: {len(pairs)} (expect 12 for 6 bidirectional pairs)')
   for s, p, o in sorted(pairs, key=lambda x: str(x[0])):
       print(f'  {str(s).split(\":\")[-1]} ↔ {str(o).split(\":\")[-1]}')
   assert len(pairs) == 12, f'Expected 12 inverseOf declarations, got {len(pairs)}'
   print('PASS')
   "
   ```
2. **Expected:** 12 inverseOf declarations (6 pairs × 2 directions)

## Edge Cases

### Confidence Enum Values in Seed Data

1. Verify all `confidence` values in seed data match the shapes enum:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph, URIRef
   g = Graph().parse('../models/research/seed/research.jsonld', format='json-ld')
   conf_pred = URIRef('urn:sempkm:model:research:confidence')
   vals = sorted(set(str(o) for s, p, o in g.triples((None, conf_pred, None))))
   print(f'Confidence values in seed: {vals}')
   valid = {'established', 'supported', 'contested', 'speculative', 'refuted'}
   assert all(v in valid for v in vals), f'Invalid confidence values: {set(vals) - valid}'
   print('PASS')
   "
   ```
2. **Expected:** All values are in {established, supported, contested, speculative, refuted}

### All Subjects Use Research Namespace

1. Verify no subjects from other model namespaces:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/research/seed/research.jsonld', format='json-ld')
   ns = 'urn:sempkm:model:research:'
   foreign = [str(s) for s in set(g.subjects()) if str(s).startswith('urn:sempkm:model:') and not str(s).startswith(ns)]
   print(f'Foreign subjects: {len(foreign)}')
   if foreign: print(foreign[:5])
   assert len(foreign) == 0, 'Found subjects from other model namespaces'
   print('PASS')
   "
   ```
2. **Expected:** 0 foreign subjects — all use `urn:sempkm:model:research:` namespace

### Namespace Split Verification

1. Verify shapes and views use correct sempkm namespace:
   ```bash
   cd backend && .venv/bin/python3 -c "
   import json
   with open('../models/research/shapes/research.jsonld') as f:
       shapes_ctx = json.load(f)['@context']
   with open('../models/research/views/research.jsonld') as f:
       views_ctx = json.load(f)['@context']
   shapes_ns = shapes_ctx.get('sempkm', 'MISSING')
   views_ns = views_ctx.get('sempkm', 'MISSING')
   print(f'Shapes sempkm: {shapes_ns}')
   print(f'Views sempkm: {views_ns}')
   assert shapes_ns == 'urn:sempkm:', f'Shapes should use urn:sempkm:, got {shapes_ns}'
   assert views_ns == 'urn:sempkm:vocab:', f'Views should use urn:sempkm:vocab:, got {views_ns}'
   print('PASS')
   "
   ```
2. **Expected:** Shapes uses `urn:sempkm:`, Views uses `urn:sempkm:vocab:`

## Failure Signals

- `parse_manifest()` raises ValidationError → manifest.yaml has wrong structure or missing fields
- `rdflib.Graph().parse()` raises JSON-LD or Turtle parse error → syntax error in model files
- `validate_archive()` returns `is_valid=False` with errors → structural issues in the archive (missing files, broken references)
- `pyshacl.validate()` returns `conforms=True` → validation rules not firing (check rule SPARQL, seed trigger data)
- Wrong violation count → a rule fires on unintended seed objects, or a trigger object doesn't match the rule pattern
- Triple counts below threshold → missing properties, classes, or shapes in the model files

## Requirements Proved By This UAT

- MODEL-04 (partial) — Research Workflow model archive passes offline validation with all 5 types, 4 validation rules, 6 ViewSpecs, 7 SavedQueries, and 16 seed objects. Confidence levels and evidence tracking modeled. Unsupported-claims and contested-claims SPARQLConstraints fire correctly.

## Not Proven By This UAT

- Docker installation and runtime behavior (S05)
- SHACL form rendering for all 5 types (S05)
- ViewSpec rendering — table views and Evidence Map graph view (S05)
- Inference materializing inverse properties at runtime (S05)
- SavedQuery execution against live triplestore (S05)
- Cross-model coexistence with basic-pkm, CRM, Zettelkasten (S05)
- E2E Playwright tests (S05)
- User guide documentation (S05)

## Notes for Tester

- The ManifestSchema attribute is `modelId` (camelCase), not `model_id` — use `m.modelId` in any verification scripts.
- The CRM model directory exists but has empty subdirectories — this is expected (CRM archive files live elsewhere or haven't been copied to this worktree).
- pyshacl validation with `advanced=True` is required — without it, SPARQLConstraints won't fire.
- Seed data intentionally contains 4 "bad" objects designed to trigger validation rules. This is by design, not a bug.
