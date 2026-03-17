---
estimated_steps: 7
estimated_files: 2
---

# T03: Create validation rules, seed data, and run full pipeline validation

**Slice:** S04 — Research Workflow Model
**Milestone:** M011

## Description

Create 4 SHACL-AF SPARQLConstraint validation rules and 16 seed objects with trigger data designed to fire all 4 rules. Then run the full offline validation pipeline (parse_manifest + load_archive + validate_archive) and pyshacl validation to prove the complete archive is correct. This is the final task — it proves the slice goal.

## Steps

1. **Read the CRM rules for structural reference:** `models/crm/rules/crm.ttl` — copy Turtle structure, SPARQLConstraint pattern, separate-NodeShape pattern (D153), sh:severity on parent NodeShape.

2. **Create `models/research/rules/research.ttl`:**
   - Use Turtle format (not JSON-LD) — consistent with S01/S02/S03 rules files
   - Declare prefixes: sh, xsd, res (`<urn:sempkm:model:research:>`), rdf, rdfs
   - **4 validation rules on separate NodeShapes** (per D153 — severity on parent, not constraint):

   **(a) UnsupportedClaimValidationShape** — `sh:severity sh:Warning`, `sh:targetClass res:Claim`
   - SPARQLConstraint checks: claim has confidence "established" or "supported" BUT no evidence supports it
   - SPARQL: `SELECT $this ?confidence WHERE { $this <urn:sempkm:model:research:confidence> ?confidence . FILTER(?confidence IN ("established", "supported")) . FILTER NOT EXISTS { ?e <urn:sempkm:model:research:supports> $this } }`
   - Message: `"Claim marked as {?confidence} but has no supporting evidence."`

   **(b) ContestedClaimValidationShape** — `sh:severity sh:Info`, `sh:targetClass res:Claim`
   - SPARQLConstraint checks: claim has BOTH supporting AND refuting evidence (EXISTS, not NOT EXISTS)
   - SPARQL: `SELECT $this WHERE { FILTER EXISTS { ?e1 <urn:sempkm:model:research:supports> $this } . FILTER EXISTS { ?e2 <urn:sempkm:model:research:refutes> $this } }`
   - Message: `"This claim has conflicting evidence — review the argument."`

   **(c) OrphanEvidenceValidationShape** — `sh:severity sh:Warning`, `sh:targetClass res:Evidence`
   - SPARQLConstraint checks: evidence links to no claim at all (neither supports nor refutes)
   - SPARQL: `SELECT $this WHERE { FILTER NOT EXISTS { $this <urn:sempkm:model:research:supports> ?x } . FILTER NOT EXISTS { $this <urn:sempkm:model:research:refutes> ?y } }`
   - Message: `"This evidence isn't linked to any claim."`

   **(d) UnansweredQuestionValidationShape** — `sh:severity sh:Info`, `sh:targetClass res:ResearchQuestion`
   - SPARQLConstraint checks: question status is "open" AND no argument addresses it
   - SPARQL: `SELECT $this WHERE { $this <urn:sempkm:model:research:status> "open" . FILTER NOT EXISTS { ?arg <urn:sempkm:model:research:addresses> $this } }`
   - Message: `"This research question has no arguments yet."`

3. **Read the CRM seed data for structural reference:** `models/crm/seed/crm.jsonld` — copy JSON-LD @graph pattern, typed literal patterns (xsd:date, xsd:gYear, xsd:anyURI), inverseOf both-sides pattern (D154).

4. **Create `models/research/seed/research.jsonld`:**
   - **@context:** inline with res, dcterms, xsd, rdfs, rdf, owl prefixes
   - **16 seed objects in @graph array:**

   **3 Papers:**
   - `res:seed-paper-kg-survey` — "Knowledge Graphs: A Survey" (2021, journal-article, doi)
   - `res:seed-paper-pkm-tools` — "Personal Knowledge Management Tools" (2023, conference-paper)
   - `res:seed-paper-rdf-scaling` — "RDF at Scale: Challenges and Solutions" (2022, preprint)

   **5 Claims:**
   - `res:seed-claim-kg-reduce-silos` — "Knowledge graphs reduce information silos" (confidence: "supported", extractedFrom: paper-kg-survey). **This is the trigger for UnsupportedClaim** — confidence is "supported" but NO evidence supports it in seed data.
   - `res:seed-claim-pkm-adoption` — "PKM tool adoption follows power-law distribution" (confidence: "established", extractedFrom: paper-pkm-tools). Has supporting evidence → no trigger.
   - `res:seed-claim-pkm-failure` — "Most PKM systems are abandoned within 6 months" (confidence: "contested", extractedFrom: paper-pkm-tools). **Trigger for ContestedClaim** — has both supporting (seed-evidence-survey) AND refuting (seed-evidence-longitudinal) evidence.
   - `res:seed-claim-rdf-scales` — "RDF scales better than property graphs for enterprise use" (confidence: "speculative", extractedFrom: paper-rdf-scaling). No trigger (speculative is not in established/supported).
   - `res:seed-claim-sem-interop` — "Semantic standards improve data interoperability" (confidence: "established", extractedFrom: paper-kg-survey). Has supporting evidence → no trigger.

   **5 Evidence:**
   - `res:seed-evidence-enterprise` — empirical-data, supports seed-claim-pkm-adoption, fromPaper: paper-pkm-tools
   - `res:seed-evidence-interop-study` — statistical-finding, supports seed-claim-sem-interop, fromPaper: paper-kg-survey
   - `res:seed-evidence-survey` — case-study, supports seed-claim-pkm-failure, fromPaper: paper-pkm-tools
   - `res:seed-evidence-longitudinal` — empirical-data, refutes seed-claim-pkm-failure, fromPaper: paper-pkm-tools
   - `res:seed-evidence-orphan` — observation, NOT linked to any claim. **Trigger for OrphanEvidence.**

   **2 Research Questions:**
   - `res:seed-rq-pkm-effectiveness` — "How effective are PKM tools for long-term knowledge retention?" (status: "open"). Has argument-1 addressing it → no trigger.
   - `res:seed-rq-scaling-limits` — "What are the practical scaling limits of RDF stores?" (status: "open"). **Trigger for UnansweredQuestion** — no arguments address it.

   **1 Argument:**
   - `res:seed-argument-1` — "Literature review of PKM effectiveness" (argumentType: "literature-review"), addresses seed-rq-pkm-effectiveness, usesClaim: seed-claim-pkm-adoption, usesEvidence: seed-evidence-enterprise

   **Both sides of inverseOf pre-populated** per D154:
   - extractedFrom/hasClaim: claims link to papers AND papers link back to claims
   - supports/supportedBy: evidence links to claims AND claims link back to evidence
   - refutes/refutedBy: evidence links to claims AND claims link back to evidence
   - addresses/hasArgument: argument links to question AND question links back to argument
   - usesClaim/addressedBy: argument links to claim AND claim links back to argument
   - cites/citedBy: paper-pkm-tools cites paper-kg-survey AND paper-kg-survey citedBy paper-pkm-tools

   **Typed literals per K002:**
   - `dcterms:created` → `{"@value": "2026-03-17", "@type": "xsd:date"}`
   - `res:year` → `{"@value": "2021", "@type": "xsd:gYear"}`
   - `res:doi` → `{"@value": "https://doi.org/10.1234/example", "@type": "xsd:anyURI"}`

5. **Verify rules parse:**
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/research/rules/research.ttl', format='turtle')
   print(f'Rules triples: {len(g)}')
   assert len(g) >= 30, f'Expected ≥30, got {len(g)}'
   "
   ```

6. **Run full pipeline validation:**
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
   assert r.is_valid and len(r.errors) == 0, f'Pipeline validation failed with {len(r.errors)} errors'
   "
   ```

7. **Run pyshacl validation:**
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
   assert not conforms, 'Expected conforms=False (4 validation rules should fire)'
   # Count violations by severity
   from rdflib.namespace import Namespace
   SH = Namespace('http://www.w3.org/ns/shacl#')
   warnings = list(rg.triples((None, SH.resultSeverity, SH.Warning)))
   infos = list(rg.triples((None, SH.resultSeverity, SH.Info)))
   print(f'Warnings: {len(warnings)}, Infos: {len(infos)}')
   assert len(warnings) == 2, f'Expected 2 warnings, got {len(warnings)}'
   assert len(infos) == 2, f'Expected 2 infos, got {len(infos)}'
   "
   ```
   Expected violations:
   - Warning: UnsupportedClaimValidationShape on seed-claim-kg-reduce-silos
   - Info: ContestedClaimValidationShape on seed-claim-pkm-failure
   - Warning: OrphanEvidenceValidationShape on seed-evidence-orphan
   - Info: UnansweredQuestionValidationShape on seed-rq-scaling-limits

## Must-Haves

- [ ] 4 validation rules on separate NodeShapes per D153
- [ ] sh:severity on parent NodeShape (Warning for unsupported/orphan, Info for contested/unanswered)
- [ ] UnsupportedClaim rule checks confidence filter (established/supported) before NOT EXISTS
- [ ] ContestedClaim rule uses EXISTS (not NOT EXISTS) for both supporting and refuting
- [ ] Seed data has 16 objects with 4 dedicated trigger objects
- [ ] Both sides of all 6 inverseOf pairs pre-populated in seed per D154
- [ ] Typed literals match SHACL shape datatypes (xsd:date, xsd:gYear, xsd:anyURI) per K002
- [ ] `validate_archive()` returns 0 errors
- [ ] `pyshacl.validate()` returns conforms=False with exactly 2 Warning + 2 Info violations

## Verification

- Rules parse with ≥30 triples, seed parses with ≥120 triples
- `parse_manifest()` + `load_archive()` + `validate_archive()` → is_valid=True, 0 errors
- `pyshacl.validate(advanced=True)` → conforms=False with 2 Warning + 2 Info
- Each violation fires on the correct focus node (the trigger objects)

## Inputs

- `models/research/manifest.yaml` — from T01
- `models/research/ontology/research.jsonld` — from T01 (class/property IRIs)
- `models/research/shapes/research.jsonld` — from T02 (NodeShape targetClass, property constraints)
- `models/research/views/research.jsonld` — from T02
- `models/crm/rules/crm.ttl` — structural template for SPARQLConstraint rules
- `models/crm/seed/crm.jsonld` — structural template for seed data patterns
- `backend/app/models/manifest.py`, `loader.py`, `validator.py` — validation pipeline (read-only)

## Expected Output

- `models/research/rules/research.ttl` — 4 SPARQLConstraint rules on separate NodeShapes, ≥30 triples
- `models/research/seed/research.jsonld` — 16 seed objects with trigger data, ≥120 triples
- All slice verification commands pass (0 pipeline errors, 4 pyshacl violations at correct severities)
