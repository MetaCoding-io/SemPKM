---
estimated_steps: 6
estimated_files: 2
---

# T01: Author Zettelkasten manifest and ontology

**Slice:** S03 — Zettelkasten+ Model
**Milestone:** M011

## Description

Create the Zettelkasten model's manifest and ontology files. The manifest establishes model identity (modelId, namespace, prefixes, entrypoints, icons, entailment_defaults). The ontology defines 5 OWL classes aligned to gist hierarchy, ~25 properties (datatype + object), 3 `owl:inverseOf` pairs, 4 argumentation link properties, and 1 `owl:SymmetricProperty`.

Follow `models/crm/manifest.yaml` and `models/crm/ontology/crm.jsonld` (in the M011 worktree at `.gsd/worktrees/M011/models/crm/`) as structural templates.

## Steps

1. **Read reference files** to confirm exact structure:
   - `.gsd/worktrees/M011/models/crm/manifest.yaml` — icon format with tree/tab/graph contexts, entailment_defaults
   - `.gsd/worktrees/M011/models/crm/ontology/crm.jsonld` — OWL class/property JSON-LD patterns, @context structure, gist alignment, inverseOf declaration pattern

2. **Create `models/zettelkasten/manifest.yaml`** with:
   - `modelId: zettelkasten`, `version: "1.0.0"`, `namespace: "urn:sempkm:model:zk:"`
   - `prefixes: { zk: "urn:sempkm:model:zk:" }`
   - `entrypoints:` pointing to `ontology/zettelkasten.jsonld`, `shapes/zettelkasten.jsonld`, `views/zettelkasten.jsonld`, `seed/zettelkasten.jsonld`, `rules/zettelkasten.ttl`
   - `entailment_defaults:` — `owl_inverseOf: true`, `shacl_rules: true`, rest false
   - 5 icon entries with all 3 contexts (tree/tab/graph):
     - `zk:FleetingNote` → `zap` / `#f59e0b` (amber)
     - `zk:Source` → `book-open` / `#6366f1` (indigo)
     - `zk:LiteratureNote` → `quote` / `#8b5cf6` (violet)
     - `zk:PermanentNote` → `gem` / `#10b981` (emerald)
     - `zk:StructureNote` → `network` / `#0ea5e9` (sky blue)

3. **Validate manifest** via:
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from pathlib import Path
   from app.models.manifest import parse_manifest
   m = parse_manifest(Path('../models/zettelkasten'))
   print(f'Model: {m.model_id}, Types: {len(m.icons)}')
   "
   ```

4. **Create `models/zettelkasten/ontology/zettelkasten.jsonld`** with:
   - `@context` block with inline prefixes: `zk` (`urn:sempkm:model:zk:`), `owl`, `rdfs`, `rdf`, `xsd`, `gist` (`https://w3id.org/semanticarts/ns/ontology/gist/`), `dcterms`, `schema`, `bpkm` (`urn:sempkm:model:basic-pkm:`), `skos`
   - **No remote @context** — all prefixes inline
   - All subject IRIs use `urn:sempkm:model:zk:` namespace
   - **5 OWL Classes:**
     - `zk:FleetingNote` → `rdfs:subClassOf gist:FormattedContent`
     - `zk:Source` → `rdfs:subClassOf gist:Content`
     - `zk:LiteratureNote` → `rdfs:subClassOf gist:FormattedContent`
     - `zk:PermanentNote` → `rdfs:subClassOf gist:FormattedContent`
     - `zk:StructureNote` → `rdfs:subClassOf gist:FormattedContent`
   - **Datatype properties** (~10): `zk:body` (shared, NO rdfs:domain per D155), `zk:capturedFrom`, `zk:sourceType`, `zk:notes`, `zk:rating`, `zk:originalQuote`, `zk:pageReference`, `zk:sequenceId`, `zk:purpose`
   - Reused from other vocabs: `dcterms:title`, `dcterms:created`, `dcterms:creator`, `schema:datePublished`, `schema:url`, `bpkm:tags`
   - **Object properties with inverseOf** (3 pairs):
     - `zk:derivedFrom` (LiteratureNote→Source) ↔ `zk:hasLiteratureNote` (Source→LiteratureNote)
     - `zk:developedInto` (LiteratureNote→PermanentNote) ↔ `zk:developedFrom` (PermanentNote→LiteratureNote)
     - `zk:includes` (StructureNote→PermanentNote) ↔ `zk:includedInStructure` (PermanentNote→StructureNote)
   - **Argumentation links** (no inverses): `zk:supports`, `zk:contradicts`, `zk:followsFrom`, `zk:relatedTo` (all PermanentNote→PermanentNote)
   - **Other object properties:**
     - `zk:processedInto` (FleetingNote→LiteratureNote|PermanentNote) — one-directional, no inverse
     - `zk:relatedStructure` (StructureNote→StructureNote) → `rdf:type owl:SymmetricProperty`
   - All properties have `rdfs:label` and `rdfs:comment`

5. **Validate ontology** via rdflib parse:
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')
   print(f'Ontology: {len(g)} triples')
   assert len(g) >= 100, f'Expected 100+ triples for 5 classes + ~25 properties, got {len(g)}'
   "
   ```

6. **Check subject namespace compliance:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')
   bad = [str(s) for s in set(g.subjects()) if str(s).startswith('urn:sempkm:') and not str(s).startswith('urn:sempkm:model:zk:')]
   if bad: print(f'BAD subjects: {bad}')
   else: print('All subjects in correct namespace')
   assert not bad, f'Subject namespace violations: {bad}'
   "
   ```

## Must-Haves

- [ ] `models/zettelkasten/manifest.yaml` exists and passes `parse_manifest()` validation
- [ ] `models/zettelkasten/ontology/zettelkasten.jsonld` exists and parses with rdflib to ≥100 triples
- [ ] 5 OWL classes with correct gist alignment
- [ ] 3 owl:inverseOf pairs declared on both sides
- [ ] 4 argumentation link properties (supports/contradicts/followsFrom/relatedTo)
- [ ] `zk:relatedStructure` is `owl:SymmetricProperty`
- [ ] `zk:body` has NO `rdfs:domain` (shared across 4 types, per D155 broadening pattern)
- [ ] No remote @context in JSON-LD
- [ ] All subject IRIs use `urn:sempkm:model:zk:` namespace
- [ ] Icon entries have all 3 contexts (tree/tab/graph) with correct Lucide names
- [ ] `bpkm` prefix included in @context for `bpkm:tags` reuse

## Verification

- `parse_manifest(Path('../models/zettelkasten'))` succeeds without exception
- `Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')` returns ≥100 triples
- Subject namespace check returns no violations

## Inputs

- `.gsd/worktrees/M011/models/crm/manifest.yaml` — structural template for manifest format (icon entries, entailment_defaults)
- `.gsd/worktrees/M011/models/crm/ontology/crm.jsonld` — structural template for ontology JSON-LD (OWL class/property patterns, inverseOf, @context)
- S03 Research doc — complete type+property inventory, gist alignment targets, icon specifications

## Observability Impact

- **Manifest validation:** `parse_manifest(Path('../models/zettelkasten'))` — success returns `ManifestSchema` with `.model_id`, `.icons[]`, `.namespace`; failure raises `ValueError` with structured message indicating the specific field that failed validation.
- **Ontology triple count:** `Graph().parse(ontology_path, format='json-ld')` — `len(g)` ≥ 100 indicates complete ontology; counts below 100 suggest missing class or property definitions.
- **Subject namespace compliance:** Checking all subjects start with `urn:sempkm:model:zk:` — violations indicate a `@context` misconfiguration or typo in the JSON-LD file.
- **Failure artifacts:** Pydantic `ValidationError` on manifest parse, `json.JSONDecodeError` or rdflib parse errors on ontology parse — both produce structured error messages with field paths.

## Expected Output

- `models/zettelkasten/manifest.yaml` — Zettelkasten model manifest with 5 icon entries and entailment_defaults
- `models/zettelkasten/ontology/zettelkasten.jsonld` — OWL ontology with 5 classes, ~25 properties, 3 inverseOf pairs, 4 argumentation links, 1 symmetric property
