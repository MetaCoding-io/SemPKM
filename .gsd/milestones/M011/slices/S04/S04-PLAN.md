# S04: Research Workflow Model

**Goal:** Deliver a complete `.sempkm-model` archive at `models/research/` with 5 types (Paper, Claim, Evidence, ResearchQuestion, Argument), 6 inverseOf pairs, 4 SHACL-AF validation rules, 5 ViewSpecs, 5 SavedQueries, and 16 seed objects — all passing offline validation.
**Demo:** Run `parse_manifest()` + `load_archive()` + `validate_archive()` → 0 errors. Run pyshacl validation → conforms=False with exactly 4 violations at correct severities (2 Warning + 2 Info).

## Must-Haves

- 6-file archive: manifest.yaml, ontology/research.jsonld, shapes/research.jsonld, views/research.jsonld, rules/research.ttl, seed/research.jsonld
- 5 OWL classes aligned to gist hierarchy (Paper→Content, Claim/Evidence/Argument→FormattedContent, ResearchQuestion→Intention)
- ~40 properties across 5 types with 6 owl:inverseOf pairs and 5 one-directional properties
- 5 sh:in enums (paperType, confidence, evidenceType, status, argumentType)
- 5 ViewSpecs (table views per type + Evidence Map graph) and 5 SavedQueries
- 4 validation SPARQLConstraints on separate NodeShapes (UnsupportedClaim Warning, ContestedClaim Info, OrphanEvidence Warning, UnansweredQuestion Info)
- 16 seed objects with trigger data for all 4 validation rules
- Full pipeline: parse_manifest + load_archive + validate_archive → 0 errors
- pyshacl.validate → conforms=False with 2 Warning + 2 Info violations

## Proof Level

- This slice proves: contract
- Real runtime required: no (offline validation only — Docker integration in S05)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/ontology/research.jsonld', format='json-ld'); print(f'Ontology: {len(g)}')"` → ≥150 triples
- `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/shapes/research.jsonld', format='json-ld'); print(f'Shapes: {len(g)}')"` → ≥350 triples
- `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph().parse('../models/research/views/research.jsonld', format='json-ld'); print(f'Views: {len(g)}')"` → ≥80 triples
- Full pipeline validation:
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
  assert r.is_valid and len(r.errors) == 0, 'Pipeline validation failed'
  "
  ```
- SHACL-AF validation:
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
  print(text[:2000])
  assert not conforms, 'Expected conforms=False (4 violations should fire)'
  "
  ```
  Expected: conforms=False with 4 violations — UnsupportedClaim (Warning), ContestedClaim (Info), OrphanEvidence (Warning), UnansweredQuestion (Info)

## Integration Closure

- Upstream surfaces consumed: none (independent slice per D151)
- New wiring introduced: none (pure content — no platform code changes per D149)
- What remains: S05 integrates all 4 models in Docker with E2E tests and user guide

## Tasks

- [x] **T01: Create manifest and OWL ontology for Research model** `est:15m`
  - Why: Establishes model identity (manifest.yaml) and the OWL class/property foundation that shapes, views, rules, and seed all reference
  - Files: `models/research/manifest.yaml`, `models/research/ontology/research.jsonld`
  - Do: Create manifest with modelId `research`, namespace `urn:sempkm:model:research:`, 5 icon entries (file-text/message-square-quote/flask-conical/help-circle/scale), entailment_defaults with owl_inverseOf and shacl_rules enabled. Create ontology with 5 OWL classes (gist-aligned), ~40 properties (20 datatype + 20 object), 6 owl:inverseOf pairs, 5 one-directional object properties. Use CRM ontology as structural template. All subject IRIs must use `urn:sempkm:model:research:` namespace.
  - Verify: `rdflib.Graph().parse()` succeeds on ontology with ≥150 triples. `parse_manifest()` succeeds without error.
  - Done when: Both files parse cleanly and manifest validates via Pydantic schema

- [x] **T02: Create SHACL shapes and ViewSpec/SavedQuery definitions** `est:20m`
  - Why: Shapes drive form rendering (property groups, enums, helptext) and views provide table/card/graph display — required for both offline validation and Docker integration in S05
  - Files: `models/research/shapes/research.jsonld`, `models/research/views/research.jsonld`
  - Do: Create shapes with 5 NodeShapes, ~20 PropertyGroups, 5 sh:in enums (paperType 7 values, confidence 5 values, evidenceType 7 values, status 4 values, argumentType 5 values), sempkm:editHelpText on key fields. Create views with 5 ViewSpecs (Paper table, Claim table, Evidence table, ResearchQuestion table, Evidence Map graph with CONSTRUCT query) and 5 SavedQueries (Unsupported Claims, Contested Claims, Research Gaps, Orphan Evidence, All Papers). Shapes @context uses `"sempkm": "urn:sempkm:"`, views @context uses `"sempkm": "urn:sempkm:vocab:"` (critical namespace split). All SPARQL queries use full IRIs.
  - Verify: Shapes parse with ≥350 triples, views parse with ≥80 triples via rdflib
  - Done when: Both files parse cleanly with triple counts in expected ranges

- [ ] **T03: Create validation rules, seed data, and run full pipeline validation** `est:25m`
  - Why: Validation rules are the core differentiator of this model (unsupported claims, contested claims detection). Seed data must trigger all 4 rules. Full pipeline validation proves the archive is correct end-to-end.
  - Files: `models/research/rules/research.ttl`, `models/research/seed/research.jsonld`
  - Do: Create 4 SPARQLConstraint rules on separate NodeShapes per D153: (1) UnsupportedClaimValidationShape — Warning, fires when confidence is "established"/"supported" but no evidence supports the claim; (2) ContestedClaimValidationShape — Info, fires when claim has both supporting AND refuting evidence; (3) OrphanEvidenceValidationShape — Warning, fires when evidence links to no claim; (4) UnansweredQuestionValidationShape — Info, fires when status is "open" with no arguments. Create seed data with 16 objects: 3 papers, 5 claims (including 1 "supported" with no evidence for trigger), 5 evidence (including 1 orphan), 2 research questions (1 with no arguments for trigger), 1 argument. Both sides of all 6 inverseOf pairs pre-populated per D154. Run full pipeline validation and pyshacl validation.
  - Verify: `validate_archive()` → 0 errors. `pyshacl.validate()` → conforms=False with 4 violations (2 Warning + 2 Info)
  - Done when: All slice-level verification commands pass

## Observability / Diagnostics

- **Manifest parsing:** `cd backend && .venv/bin/python3 -c "from pathlib import Path; from app.models.manifest import parse_manifest; m = parse_manifest(Path('../models/research')); print(f'{m.model_id} v{m.version}: {len(m.icons)} icons')"` — validates model identity, icon count, namespace
- **Ontology triple count:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g = Graph().parse('../models/research/ontology/research.jsonld', format='json-ld'); print(f'Ontology: {len(g)} triples')"` — ≥150 triples confirms class/property/inverseOf coverage
- **Full pipeline:** `validate_archive()` returns structured `ValidationResult` with `.is_valid`, `.errors[]`, `.warnings[]` — any failure produces actionable file+message diagnostics
- **SHACL rule firing:** `pyshacl.validate()` text report lists each violation with source shape IRI, focus node, severity — confirms rule triggers fire correctly
- **Failure shapes:** Parse errors surface as Python exceptions with line/column info. Validation errors include file path and descriptive message. SHACL violations include focus node IRI and constraint IRI.
- **No secrets or PII** in any model files — all content is ontology definitions and synthetic seed data

## Files Likely Touched

- `models/research/manifest.yaml`
- `models/research/ontology/research.jsonld`
- `models/research/shapes/research.jsonld`
- `models/research/views/research.jsonld`
- `models/research/rules/research.ttl`
- `models/research/seed/research.jsonld`
