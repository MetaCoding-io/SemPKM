---
estimated_steps: 6
estimated_files: 2
---

# T01: Author CRM manifest and ontology

**Slice:** S02 — Personal CRM Model
**Milestone:** M011

## Description

Create the CRM model's manifest and ontology files. The manifest establishes model identity (modelId, namespace, prefixes, entrypoints, icons, entailment_defaults). The ontology defines 4 OWL classes aligned to gist hierarchy, ~20 properties (datatype + object), 3 `owl:inverseOf` pairs, and 1 `owl:SymmetricProperty`.

Follow `models/basic-pkm/manifest.yaml` and `models/basic-pkm/ontology/basic-pkm.jsonld` as structural templates.

## Steps

1. **Read reference files** to confirm exact structure:
   - `models/basic-pkm/manifest.yaml` — icon format with tree/tab/graph contexts, entailment_defaults
   - `models/basic-pkm/ontology/basic-pkm.jsonld` — OWL class/property JSON-LD patterns, @context structure, gist alignment

2. **Create `models/crm/manifest.yaml`** with:
   - `modelId: crm`, `version: "1.0.0"`, `namespace: "urn:sempkm:model:crm:"`
   - `prefixes: { crm: "urn:sempkm:model:crm:" }`
   - `entrypoints:` pointing to `ontology/crm.jsonld`, `shapes/crm.jsonld`, `views/crm.jsonld`, `seed/crm.jsonld`, `rules/crm.ttl`
   - `entailment_defaults:` matching basic-pkm (owl_inverseOf: true, shacl_rules: true, rest false)
   - 4 icon entries with all 3 contexts (tree/tab/graph):
     - `crm:Contact` → `user` / `#6366f1` (indigo)
     - `crm:Company` → `building-2` / `#8b5cf6` (violet)
     - `crm:Interaction` → `message-circle` / `#14b8a6` (teal)
     - `crm:Deal` → `handshake` / `#f59e0b` (amber)

3. **Validate manifest** via:
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from pathlib import Path
   from app.models.manifest import parse_manifest
   m = parse_manifest(Path('../models/crm'))
   print(f'Model: {m.model_id}, Types: {len(m.icons)}')
   "
   ```

4. **Create `models/crm/ontology/crm.jsonld`** with:
   - `@context` block with inline prefixes: `crm`, `owl`, `rdfs`, `rdf`, `xsd`, `gist`, `dcterms`, `schema`, `bpkm` (for tags reuse), `skos`
   - **No remote `@context`** — all prefixes inline
   - All subject IRIs use `urn:sempkm:model:crm:` namespace
   - **4 OWL Classes:**
     - `crm:Contact` → `rdfs:subClassOf gist:Person`
     - `crm:Company` → `rdfs:subClassOf gist:Organization`
     - `crm:Interaction` → `rdfs:subClassOf gist:Event`
     - `crm:Deal` → `rdfs:subClassOf gist:Agreement`
   - **Datatype properties** (~12): `crm:firstName`, `crm:lastName`, `crm:email`, `crm:phone`, `crm:role`, `crm:relationship`, `crm:notes`, `crm:followUpDate`, `crm:followUpDone`, `crm:industry`, `crm:website`, `crm:size`, `crm:interactionDate`, `crm:interactionType`, `crm:summary`, `crm:dealStage`, `crm:dealValue`, `crm:currency`, `crm:dealName`, `crm:lastContactedDate` (inference-only)
   - **Object properties** (~8): `crm:worksAt` (Contact→Company), `crm:hasEmployee` (Company→Contact), `crm:withContact` (Interaction→Contact), `crm:hasInteraction` (Contact→Interaction), `crm:dealContact` (Deal→Contact), `crm:hasContactDeal` (Contact→Deal), `crm:dealCompany` (Deal→Company), `crm:hasCompanyDeal` (Company→Deal), `crm:knows` (Contact→Contact, symmetric)
   - **owl:inverseOf pairs:**
     - `crm:worksAt` ↔ `crm:hasEmployee`
     - `crm:dealContact` ↔ `crm:hasContactDeal`
     - `crm:dealCompany` ↔ `crm:hasCompanyDeal`
     - `crm:withContact` ↔ `crm:hasInteraction`
   - **crm:knows** → `rdf:type owl:SymmetricProperty` (do NOT also declare owl:inverseOf)
   - All properties have `rdfs:label` and `rdfs:comment`

5. **Validate ontology** via rdflib parse:
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/crm/ontology/crm.jsonld', format='json-ld')
   print(f'Ontology: {len(g)} triples')
   assert len(g) > 50, 'Expected 50+ triples for 4 classes + ~20 properties'
   "
   ```

6. **Check subject namespace compliance:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/crm/ontology/crm.jsonld', format='json-ld')
   bad = [str(s) for s in set(g.subjects()) if str(s).startswith('urn:sempkm:') and not str(s).startswith('urn:sempkm:model:crm:')]
   if bad: print(f'BAD subjects: {bad}')
   else: print('All subjects in correct namespace')
   "
   ```

## Must-Haves

- [ ] `models/crm/manifest.yaml` exists and passes `parse_manifest()` validation
- [ ] `models/crm/ontology/crm.jsonld` exists and parses with rdflib to 50+ triples
- [ ] 4 OWL classes with correct gist alignment (Person, Organization, Event, Agreement)
- [ ] 3 owl:inverseOf pairs declared on both sides
- [ ] `crm:knows` is `owl:SymmetricProperty` (not inverseOf self)
- [ ] `crm:lastContactedDate` declared as datatype property (inference target)
- [ ] No remote @context in JSON-LD
- [ ] All subject IRIs use `urn:sempkm:model:crm:` namespace
- [ ] Icon entries have all 3 contexts (tree/tab/graph) with correct Lucide names

## Verification

- `parse_manifest(Path('../models/crm'))` succeeds without exception
- `Graph().parse('../models/crm/ontology/crm.jsonld', format='json-ld')` returns 50+ triples
- Subject namespace check returns no violations

## Inputs

- `models/basic-pkm/manifest.yaml` — structural template for manifest format
- `models/basic-pkm/ontology/basic-pkm.jsonld` — structural template for ontology JSON-LD
- S02 Research doc — complete property list, gist alignment targets, icon specifications

## Observability Impact

- **New inspection surface:** `parse_manifest(Path('../models/crm'))` — returns `ManifestSchema` on success, raises `ValueError` with structured message on failure (missing fields, namespace mismatch, invalid YAML).
- **Triple count signal:** `Graph().parse('../models/crm/ontology/crm.jsonld', format='json-ld')` — triple count >50 confirms classes+properties are properly defined. A count <50 indicates missing definitions.
- **Namespace compliance check:** Subject namespace audit reports exact IRIs that violate the `urn:sempkm:model:crm:` convention, allowing pinpoint debugging of `@context` or `@id` misconfigurations.
- **Failure visibility:** All diagnostics are CLI-inspectable — no persistent log files or state. Parse errors surface as Python exceptions with actionable messages.

## Expected Output

- `models/crm/manifest.yaml` — CRM model manifest with 4 icon entries and entailment_defaults
- `models/crm/ontology/crm.jsonld` — OWL ontology with 4 classes, ~20 properties, inverseOf pairs
