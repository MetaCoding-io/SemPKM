---
estimated_steps: 8
estimated_files: 2
---

# T03: Author Zettelkasten rules, seed data, and run full pipeline validation

**Slice:** S03 — Zettelkasten+ Model
**Milestone:** M011

## Description

Create the Zettelkasten model's SHACL-AF validation rules (Turtle) and seed data (JSON-LD), then run the full validation pipeline to prove the archive is correct. The rules define 3 validation-only SPARQLConstraints on separate NodeShapes (per D153). The seed data provides ~12 objects forming a complete provenance chain (Source → LiteratureNote → PermanentNote → StructureNote) with trigger data for all 3 validation rules.

No inference rules are needed — all relationships are user-created. The `owl:inverseOf` entailment handles inverse property materialization automatically.

## Steps

1. **Read reference files** to confirm exact rule and seed patterns:
   - `.gsd/worktrees/M011/models/crm/rules/crm.ttl` — SHACL-AF Turtle pattern with SPARQLConstraint, PrefixDeclarations, separate NodeShapes per D153
   - `.gsd/worktrees/M011/models/crm/seed/crm.jsonld` — Seed JSON-LD pattern with typed dates, both-side inverseOf, @context structure

2. **Create `models/zettelkasten/rules/zettelkasten.ttl`** with:
   - Prefix declarations: `@prefix zk:`, `@prefix sh:`, `@prefix xsd:`, `@prefix rdfs:`, `@prefix rdf:`, `@prefix dcterms:`
   - `zk:PrefixDeclarations` — `sh:declare` entries for `zk` and `xsd` prefixes (needed for SPARQL prefix expansion in pyshacl)
   - **Rule 1 — UnprocessedFleetingValidationShape:**
     - `sh:targetClass zk:FleetingNote`
     - `sh:severity sh:Warning` (on the NodeShape, NOT on the constraint per D153)
     - `sh:sparql` → SPARQLConstraint with `sh:prefixes zk:PrefixDeclarations`
     - SPARQL: `SELECT $this WHERE { $this a <urn:sempkm:model:zk:FleetingNote> . FILTER NOT EXISTS { $this <urn:sempkm:model:zk:processedInto> ?x } }`
     - `sh:message "This fleeting note hasn't been processed. Develop it into a literature or permanent note, or delete it."`
     - Note: No date arithmetic per K001. Simple NOT EXISTS for the SHACL rule. The SavedQuery handles age-based filtering.
   - **Rule 2 — OrphanPermanentNoteValidationShape:**
     - `sh:targetClass zk:PermanentNote`
     - `sh:severity sh:Warning`
     - `sh:sparql` → SPARQLConstraint
     - SPARQL: Use **separate** `FILTER NOT EXISTS` blocks for each predicate (do NOT use property paths `|` in NOT EXISTS — rdflib is inconsistent per research pitfalls):
       ```sparql
       SELECT $this WHERE {
         $this a <urn:sempkm:model:zk:PermanentNote> .
         FILTER NOT EXISTS { $this <urn:sempkm:model:zk:supports> ?a }
         FILTER NOT EXISTS { $this <urn:sempkm:model:zk:contradicts> ?b }
         FILTER NOT EXISTS { $this <urn:sempkm:model:zk:followsFrom> ?c }
         FILTER NOT EXISTS { $this <urn:sempkm:model:zk:includedInStructure> ?d }
       }
       ```
     - `sh:message "This permanent note is isolated. Connect it to other ideas or include it in a structure note."`
   - **Rule 3 — UnsourcedPermanentNoteValidationShape:**
     - `sh:targetClass zk:PermanentNote`
     - `sh:severity sh:Info` (Info, not Warning — less urgent)
     - `sh:sparql` → SPARQLConstraint
     - SPARQL: `SELECT $this WHERE { $this a <urn:sempkm:model:zk:PermanentNote> . FILTER NOT EXISTS { $this <urn:sempkm:model:zk:developedFrom> ?x } }`
     - `sh:message "This idea has no literature source. Consider linking it to supporting evidence."`

3. **Validate rules parse:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/zettelkasten/rules/zettelkasten.ttl', format='turtle')
   print(f'Rules: {len(g)} triples')
   assert len(g) >= 20, f'Expected 20+ triples for 3 validation shapes, got {len(g)}'
   "
   ```

4. **Create `models/zettelkasten/seed/zettelkasten.jsonld`** with:
   - `@context` with all needed prefixes: `zk`, `dcterms`, `schema`, `bpkm`, `xsd`, `rdf`, `rdfs`, `gist`
   - All subject IRIs use `urn:sempkm:model:zk:` namespace (e.g., `zk:seed-source-ahrens`)
   - **3 Sources:**
     - `seed-source-ahrens` — "How to Take Smart Notes" (Ahrens, book, 2017)
     - `seed-source-dobelli` — "The Art of Thinking Clearly" (Dobelli, book, 2013)
     - `seed-source-networked` — "Networked Thought" (article, 2024)
   - **2 FleetingNotes:**
     - `seed-fleeting-unprocessed` — Old unprocessed note, `dcterms:created` set to `2026-03-12T09:00:00Z` (5+ days ago), NO `zk:processedInto` → **triggers UnprocessedFleetingValidation**
     - `seed-fleeting-recent` — Recently captured note, has `zk:processedInto` linking to a LiteratureNote
   - **3 LiteratureNotes:**
     - `seed-litnote-ahrens-slip` — From Ahrens, about slip-box method
     - `seed-litnote-ahrens-writing` — From Ahrens, about writing as thinking
     - `seed-litnote-dobelli-bias` — From Dobelli, about confirmation bias
     - Each has `zk:derivedFrom` → Source AND Source has `zk:hasLiteratureNote` → LiteratureNote (both sides per D154)
   - **3 PermanentNotes:**
     - `seed-perm-cognitive-load` — "Externalized thinking reduces cognitive load" — has `zk:supports` → next note, `zk:developedFrom` → lit note, `zk:includedInStructure` → structure note ✓ (not orphan, not unsourced)
     - `seed-perm-emergent-structure` — "Structure emerges from connections, not planning" — has `zk:developedFrom` → lit note, `zk:includedInStructure` → structure note, has NO `zk:supports|contradicts|followsFrom` but HAS `zk:includedInStructure` ✓ (not orphan because included in structure)
     - `seed-perm-confirmation-bias` — "Confirmation bias threatens knowledge systems" — has NO `zk:supports`, NO `zk:contradicts`, NO `zk:followsFrom`, NO `zk:includedInStructure`, and NO `zk:developedFrom` → **triggers both OrphanPermanentNote (Warning) AND UnsourcedPermanentNote (Info)**
     - Also have `zk:developedInto`/`zk:developedFrom` both sides pre-populated per D154
   - **1 StructureNote:**
     - `seed-structure-case` — "The Case for Structured Note-Taking" — purpose: "argument", `zk:includes` → all 3 permanent notes (except confirmation-bias to keep it orphaned), `zk:includedInStructure` reverse on the included PermanentNotes per D154
   - **Typed dates:** Use `{"@value": "2017-01-01", "@type": "xsd:date"}` format for datePublished
   - **Tags:** Use `bpkm:tags` with string arrays

5. **Validate seed parse:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/zettelkasten/seed/zettelkasten.jsonld', format='json-ld')
   print(f'Seed: {len(g)} triples')
   assert len(g) >= 100, f'Expected 100+ triples for ~12 objects, got {len(g)}'
   "
   ```

6. **Run full pipeline validation (Step 2 from slice verification):**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from pathlib import Path
   from app.models.manifest import parse_manifest
   from app.models.loader import load_archive
   from app.models.validator import validate_archive
   m = parse_manifest(Path('../models/zettelkasten'))
   a = load_archive(Path('../models/zettelkasten'), m)
   r = validate_archive(a)
   print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}, Warnings: {len(r.warnings)}')
   for e in r.errors: print(f'  E: {e.file}: {e.message}')
   for w in r.warnings: print(f'  W: {w.file}: {w.message}')
   assert r.is_valid and len(r.errors) == 0, f'Expected 0 errors, got {len(r.errors)}'
   "
   ```

7. **Run SHACL-AF validation (Step 3 from slice verification):**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   import pyshacl
   rules = Graph().parse('../models/zettelkasten/rules/zettelkasten.ttl', format='turtle')
   shapes = Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld')
   data = Graph().parse('../models/zettelkasten/seed/zettelkasten.jsonld', format='json-ld')
   ontology = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')
   combined_shacl = shapes + rules
   conforms, results_graph, text = pyshacl.validate(
       data, shacl_graph=combined_shacl, ont_graph=ontology, advanced=True
   )
   print('Conforms:', conforms)
   print(text[:3000])
   assert not conforms, 'Expected validation violations (conforms=False)'
   # Check for the 3 expected violations
   assert 'fleeting' in text.lower() or 'unprocessed' in text.lower(), 'Missing unprocessed fleeting note violation'
   assert 'isolated' in text.lower() or 'orphan' in text.lower() or 'permanent note is isolated' in text.lower(), 'Missing orphan permanent note violation'
   print('All expected validation rules fired')
   "
   ```

8. **Run triple count sanity (Step 5 from slice verification):**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   onto = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')
   shapes = Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld')
   views = Graph().parse('../models/zettelkasten/views/zettelkasten.jsonld', format='json-ld')
   rules = Graph().parse('../models/zettelkasten/rules/zettelkasten.ttl', format='turtle')
   seed = Graph().parse('../models/zettelkasten/seed/zettelkasten.jsonld', format='json-ld')
   print(f'Ontology: {len(onto)} (expect 100+)')
   print(f'Shapes: {len(shapes)} (expect 300+)')
   print(f'Views: {len(views)} (expect 60+)')
   print(f'Rules: {len(rules)} (expect 20+)')
   print(f'Seed: {len(seed)} (expect 100+)')
   assert len(onto) >= 100 and len(shapes) >= 300 and len(views) >= 60 and len(rules) >= 20 and len(seed) >= 100
   print('All triple counts in expected range')
   "
   ```

## Must-Haves

- [ ] `models/zettelkasten/rules/zettelkasten.ttl` parses to ≥20 triples with 3 NodeShapes
- [ ] 3 validation rules on separate NodeShapes (per D153): UnprocessedFleeting (Warning), OrphanPermanent (Warning), UnsourcedPermanent (Info)
- [ ] OrphanPermanentNote rule uses separate FILTER NOT EXISTS blocks (NOT property paths)
- [ ] `sh:severity` on NodeShape, not on SPARQLConstraint
- [ ] `models/zettelkasten/seed/zettelkasten.jsonld` parses to ≥100 triples
- [ ] Seed data contains complete provenance chain: Source → LiteratureNote → PermanentNote → StructureNote
- [ ] Both sides of all 3 inverseOf pairs pre-populated in seed data (per D154)
- [ ] Trigger data present: 1 FleetingNote without processedInto, 1 PermanentNote without argumentation links, 1 PermanentNote without developedFrom
- [ ] Full pipeline `validate_archive()` returns 0 errors
- [ ] pyshacl fires all 3 validation rules at correct severity levels

## Verification

- Rules file parses with rdflib to ≥20 triples
- Seed file parses with rdflib to ≥100 triples
- `validate_archive()` returns `is_valid=True` with 0 errors
- `pyshacl.validate(..., advanced=True)` returns `conforms=False` with violations for unprocessed fleeting note and orphan permanent note
- All triple counts in expected ranges (Ontology ≥100, Shapes ≥300, Views ≥60, Rules ≥20, Seed ≥100)

## Inputs

- `models/zettelkasten/manifest.yaml` — model identity (from T01)
- `models/zettelkasten/ontology/zettelkasten.jsonld` — class + property IRIs (from T01)
- `models/zettelkasten/shapes/zettelkasten.jsonld` — SHACL shapes for combined validation (from T02)
- `models/zettelkasten/views/zettelkasten.jsonld` — views (from T02, needed for complete archive)
- `.gsd/worktrees/M011/models/crm/rules/crm.ttl` — structural template for rules Turtle
- `.gsd/worktrees/M011/models/crm/seed/crm.jsonld` — structural template for seed JSON-LD

## Observability Impact

- **SHACL-AF rule firing:** `pyshacl.validate(data, shacl_graph=combined_shacl, ont_graph=ontology, advanced=True)` returns `(conforms, results_graph, text)` — text includes focus node, severity, source shape, and message per violation. The 3 rules produce: 2 Warning (unprocessed fleeting, orphan permanent) + 1 Info (unsourced permanent).
- **Seed data diagnostic surface:** Seed objects are designed to trigger known violations — agents can verify rule correctness by checking that `conforms=False` and the violation text matches expected messages.
- **Triple count signals:** Rules ≥20, Seed ≥100. Counts below these thresholds after edits indicate missing definitions or parse failures.
- **Pipeline error surface:** `validate_archive()` returns `ValidationResult` with `.is_valid`, `.errors[]`, `.warnings[]` — inspectable by agents. Zero errors expected for a valid archive.

## Expected Output

- `models/zettelkasten/rules/zettelkasten.ttl` — 3 validation rules in Turtle (≥20 triples)
- `models/zettelkasten/seed/zettelkasten.jsonld` — ~12 seed objects with provenance chain and trigger data (≥100 triples)
- Full pipeline passes with 0 errors and 3 SHACL-AF violations at correct severities
