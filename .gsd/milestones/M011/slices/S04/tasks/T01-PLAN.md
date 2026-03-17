---
estimated_steps: 5
estimated_files: 2
---

# T01: Create manifest and OWL ontology for Research model

**Slice:** S04 — Research Workflow Model
**Milestone:** M011

## Description

Create the Research model's manifest.yaml and OWL ontology. The manifest establishes model identity, namespace, icon entries, and entailment defaults. The ontology defines 5 OWL classes aligned to gist hierarchy, ~40 properties (datatype + object), 6 owl:inverseOf pairs, and 5 one-directional object properties. Use the CRM model (`models/crm/`) as the structural template — it's the closest match (rich relationships, multiple types).

## Steps

1. **Read the CRM manifest for structural reference:** `models/crm/manifest.yaml` — copy structure, adapt for research model. Key differences: modelId `research`, 5 icon entries (not 4), namespace `urn:sempkm:model:research:`.

2. **Create `models/research/manifest.yaml`:**
   - `modelId: research`
   - `version: "1.0.0"`
   - `name: "Research Workflow"`
   - `description:` academic research tracking with Paper, Claim, Evidence, ResearchQuestion, Argument types
   - `namespace: "urn:sempkm:model:research:"`
   - `prefixes: { res: "urn:sempkm:model:research:" }`
   - `entrypoints:` ontology/research.jsonld, shapes/research.jsonld, views/research.jsonld, seed/research.jsonld, rules/research.ttl
   - `entailment_defaults:` owl_inverseOf: true, shacl_rules: true, all others false
   - 5 `icons` entries with tree/tab/graph contexts:
     - `res:Paper` → file-text, #6366f1 (indigo)
     - `res:Claim` → message-square-quote, #f59e0b (amber)
     - `res:Evidence` → flask-conical, #10b981 (emerald)
     - `res:ResearchQuestion` → help-circle, #ef4444 (red)
     - `res:Argument` → scale, #8b5cf6 (violet)

3. **Read the CRM ontology for structural reference:** `models/crm/ontology/crm.jsonld` — copy JSON-LD structure, @context pattern, class definition pattern, property definition pattern, inverseOf pattern.

4. **Create `models/research/ontology/research.jsonld`:**
   - **@context:** inline only (no remote URLs). Include res, owl, rdfs, rdf, xsd, dcterms, gist, bpkm prefixes.
   - **5 OWL classes** (all `owl:Class` with `rdfs:subClassOf` gist alignment):
     - `res:Paper` → `gist:Content` (label: "Paper")
     - `res:Claim` → `gist:FormattedContent` (label: "Claim")
     - `res:Evidence` → `gist:FormattedContent` (label: "Evidence")
     - `res:ResearchQuestion` → `gist:Intention` (label: "Research Question")
     - `res:Argument` → `gist:FormattedContent` (label: "Argument")
   - **Datatype properties** (~20, all `owl:DatatypeProperty`):
     - Paper: title (xsd:string), abstract (xsd:string), doi (xsd:anyURI), year (xsd:gYear), venue (xsd:string), authors (xsd:string), paperType (xsd:string)
     - Claim: statement (xsd:string), confidence (xsd:string), rationale (xsd:string)
     - Evidence: description (xsd:string), evidenceType (xsd:string), source (xsd:string), methodology (xsd:string), strength (xsd:string)
     - ResearchQuestion: question (xsd:string), status (xsd:string), context (xsd:string), significance (xsd:string)
     - Argument: thesis (xsd:string), argumentType (xsd:string), summary (xsd:string)
     - Shared: dcterms:created (xsd:date) — no new property needed, use dcterms directly in shapes
   - **Object properties with inverseOf** (6 pairs, each direction as separate `owl:ObjectProperty`):
     1. `res:extractedFrom` (Claim→Paper) ↔ `res:hasClaim` (Paper→Claim)
     2. `res:supports` (Evidence→Claim) ↔ `res:supportedBy` (Claim→Evidence)
     3. `res:refutes` (Evidence→Claim) ↔ `res:refutedBy` (Claim→Evidence)
     4. `res:cites` (Paper→Paper) ↔ `res:citedBy` (Paper→Paper)
     5. `res:addresses` (Argument→ResearchQuestion) ↔ `res:hasArgument` (ResearchQuestion→Argument)
     6. `res:usesClaim` (Argument→Claim) ↔ `res:addressedBy` (Claim→Argument)
   - **One-directional object properties** (no inverse):
     - `res:fromPaper` (Evidence→Paper)
     - `res:corroborates` (Claim→Claim)
     - `res:contradicts` (Claim→Claim)
     - `res:dependsOn` (Claim→Claim)
     - `res:usesEvidence` (Argument→Evidence)
   - All subject IRIs use full `urn:sempkm:model:research:` namespace
   - gist classes appear ONLY as objects in rdfs:subClassOf (never as subjects)

5. **Verify both files:**
   ```bash
   cd backend && .venv/bin/python3 -c "
   from pathlib import Path
   from app.models.manifest import parse_manifest
   m = parse_manifest(Path('../models/research'))
   print(f'Manifest OK: {m.model_id}, {m.version}, {len(m.icons)} icons')
   "
   ```
   ```bash
   cd backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/research/ontology/research.jsonld', format='json-ld')
   print(f'Ontology triples: {len(g)}')
   assert len(g) >= 150, f'Expected ≥150 triples, got {len(g)}'
   "
   ```

## Must-Haves

- [ ] `manifest.yaml` parses via `parse_manifest()` without errors
- [ ] Ontology has 5 OWL classes aligned to gist
- [ ] Ontology has 6 owl:inverseOf pairs correctly declared
- [ ] All subject IRIs use `urn:sempkm:model:research:` namespace
- [ ] No remote @context URLs — all inline
- [ ] Ontology parses with ≥150 triples

## Verification

- `parse_manifest(Path('../models/research'))` succeeds and returns manifest with modelId="research", 5 icons
- `rdflib.Graph().parse()` on ontology succeeds with ≥150 triples
- No Python exceptions during parsing

## Inputs

- `models/crm/manifest.yaml` — structural template for manifest format (5 icon entries with tree/tab/graph)
- `models/crm/ontology/crm.jsonld` — structural template for JSON-LD ontology (class/property/inverseOf patterns)

## Expected Output

- `models/research/manifest.yaml` — complete manifest with 5 icon entries, entailment_defaults, all entrypoints
- `models/research/ontology/research.jsonld` — OWL ontology with 5 classes, ~40 properties, 6 inverseOf pairs, ≥150 triples

## Observability Impact

- **New signals:** `parse_manifest(Path('../models/research'))` becomes a valid call — returns `ManifestModel` with `model_id="research"`, 5 icons. `rdflib.Graph().parse()` on `ontology/research.jsonld` produces ≥150 triples.
- **Inspection surface:** Triple count is the primary health metric for the ontology. Class count (5), inverseOf pair count (6), and property count (~40) can be verified via SPARQL queries on the parsed graph.
- **Failure visibility:** If manifest is malformed, `parse_manifest()` raises `ValidationError` with field-level detail. If ontology has invalid JSON-LD, `rdflib` raises `json.JSONDecodeError` with line info. If @context is wrong, triples parse but with unexpected IRIs — triple count drops below threshold.
