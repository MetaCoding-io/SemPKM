---
estimated_steps: 8
estimated_files: 2
---

# T03: Author CRM rules, seed data, and run full pipeline validation

**Slice:** S02 — Personal CRM Model
**Milestone:** M011

## Description

Create the SHACL-AF rules file (1 inference rule + 2 validation rules) and seed data (~12 objects with realistic CRM scenario). Then run the complete validation pipeline: individual rdflib parse → `parse_manifest()` + `load_archive()` + `validate_archive()` → pyshacl `advanced=True`. The seed data must trigger validation warnings for stale contact and overdue follow-up.

Follow `models/basic-pkm/rules/basic-pkm.ttl` for rules structure and `models/basic-pkm/seed/basic-pkm.jsonld` for seed data structure.

## Steps

1. **Read reference files** for exact structural patterns:
   - `models/basic-pkm/rules/basic-pkm.ttl` — Turtle format, sh:SPARQLRule for inference, sh:SPARQLConstraint for validation, separate NodeShapes per D153, PrefixDeclarations pattern, `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` date arithmetic
   - `models/basic-pkm/seed/basic-pkm.jsonld` — JSON-LD seed objects with typed dates (`{"@value": "...", "@type": "xsd:date"}`), cross-references, both-side inverse population per D154

2. **Create `models/crm/rules/crm.ttl`** in Turtle format with:
   - `@prefix` declarations for `sh:`, `crm:`, `rdf:`, `rdfs:`, `xsd:`, `owl:`
   - **crm:PrefixDeclarations** — shared prefix declarations node (same pattern as bpkm:PrefixDeclarations)
   
   **Rule 1: LastContactedDeriveRule** (inference, separate NodeShape):
   ```
   crm:LastContactedDeriveShape
       a sh:NodeShape ;
       sh:targetClass crm:Contact ;
       sh:rule [
           a sh:SPARQLRule ;
           sh:order 0 ;
           rdfs:label "Derive lastContactedDate from most recent interaction" ;
           sh:prefixes crm:PrefixDeclarations ;
           sh:construct """
               CONSTRUCT { $this crm:lastContactedDate ?maxDate . }
               WHERE {
                   SELECT $this (MAX(?iDate) AS ?maxDate)
                   WHERE {
                       ?interaction crm:withContact $this .
                       ?interaction crm:interactionDate ?iDate .
                   }
                   GROUP BY $this
               }
           """ ;
       ] .
   ```
   
   **Rule 2: StaleContactValidation** (validation, separate NodeShape with `sh:severity sh:Warning`):
   ```
   crm:StaleContactValidationShape
       a sh:NodeShape ;
       sh:targetClass crm:Contact ;
       sh:severity sh:Warning ;
       sh:sparql [
           a sh:SPARQLConstraint ;
           sh:message "Contact has had no interaction in the last 90 days." ;
           sh:prefixes crm:PrefixDeclarations ;
           sh:select """
               SELECT $this
               WHERE {
                   FILTER NOT EXISTS {
                       ?interaction crm:withContact $this .
                       ?interaction crm:interactionDate ?iDate .
                       BIND(STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date) AS ?today)
                       FILTER(?iDate > ?today - "P90D"^^xsd:dayTimeDuration)
                   }
               }
           """ ;
       ] .
   ```
   **Risk mitigation:** If `?today - "P90D"^^xsd:dayTimeDuration` doesn't work in rdflib, simplify to:
   ```sparql
   SELECT $this WHERE {
       FILTER NOT EXISTS {
           ?interaction crm:withContact $this .
           ?interaction crm:interactionDate ?iDate .
       }
   }
   ```
   This catches contacts with zero interactions (still useful). Refine in S05.
   
   Alternatively, try the string-comparison approach that S01 proved works:
   ```sparql
   BIND(STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date) AS ?today)
   ```
   and just compare `?iDate` directly — contacts with ALL interactions older than 90 days. Test which pattern rdflib accepts.
   
   **Rule 3: FollowUpOverdueValidation** (validation, separate NodeShape with `sh:severity sh:Warning`):
   Same `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` pattern as S01's overdue task rule. Fires when `crm:followUpDate < ?today` and `crm:followUpDone` is not true.

3. **Validate rules parse:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/crm/rules/crm.ttl', format='turtle')
   print(f'Rules: {len(g)} triples')
   "
   ```

4. **Create `models/crm/seed/crm.jsonld`** with:
   - `@context` matching ontology prefixes (crm, bpkm, dcterms, schema, xsd, gist, rdfs, rdf)
   - `@graph` array with ~12 objects:
   
   **3 Companies:**
   - Acme Corp (technology, large) — has employees Sarah, James
   - Bright Ideas Studio (design, small) — has employee Priya
   - DataFlow Inc (data analytics, medium) — has employee Marcus
   
   **4 Contacts:**
   - Sarah Park — works at Acme, role: "VP of Engineering", relationship: "client", knows James. Has recent interaction.
   - James Liu — works at Acme, role: "CTO", relationship: "colleague". Has recent interaction.
   - Priya Sharma — works at Bright Ideas, relationship: "prospect". Has **only old interactions** (>90 days ago) → triggers stale-contact warning.
   - Marcus Cole — works at DataFlow, relationship: "mentor". Has recent interaction.
   
   **3 Interactions:**
   - Coffee with Sarah (2026-03-10) — recent, no follow-up issues
   - Meeting with James (2026-03-15) — recent, with **past followUpDate (2026-03-16) and followUpDone: false** → triggers follow-up-overdue warning
   - Email with Priya (2025-11-01) — old interaction (>90 days ago), stale contact trigger
   
   **2 Deals:**
   - "Enterprise Platform License" — Acme Corp, Sarah Park contact, stage: "proposal", value: 150000
   - "Design System Audit" — Bright Ideas, Priya Sharma contact, stage: "lead", value: 25000
   
   **Both sides of inverseOf pre-populated per D154:**
   - Contact.worksAt AND Company.hasEmployee
   - Interaction.withContact AND Contact.hasInteraction
   - Deal.dealContact AND Contact.hasContactDeal
   - Deal.dealCompany AND Company.hasCompanyDeal
   - Contact.knows both directions (Sarah knows James, James knows Sarah)
   
   **Typed dates:** Use `{"@value": "2026-03-10", "@type": "xsd:date"}` format
   **Tags:** Use `bpkm:tags` array format

5. **Validate seed parse:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/crm/seed/crm.jsonld', format='json-ld')
   print(f'Seed: {len(g)} triples')
   assert len(g) > 80, 'Expected 80+ triples for ~12 seed objects'
   "
   ```

6. **Run full pipeline validation:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from pathlib import Path
   from app.models.manifest import parse_manifest
   from app.models.loader import load_archive
   from app.models.validator import validate_archive
   
   m = parse_manifest(Path('../models/crm'))
   a = load_archive(Path('../models/crm'), m)
   r = validate_archive(a)
   print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}, Warnings: {len(r.warnings)}')
   for e in r.errors: print(f'  E: {e.file}: {e.message}')
   for w in r.warnings: print(f'  W: {w.file}: {w.message}')
   assert r.is_valid and len(r.errors) == 0, f'Archive validation failed: {[e.message for e in r.errors]}'
   "
   ```

7. **Run pyshacl validation with advanced=True:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   import pyshacl
   rules = Graph().parse('../models/crm/rules/crm.ttl', format='turtle')
   shapes = Graph().parse('../models/crm/shapes/crm.jsonld', format='json-ld')
   data = Graph().parse('../models/crm/seed/crm.jsonld', format='json-ld')
   ontology = Graph().parse('../models/crm/ontology/crm.jsonld', format='json-ld')
   combined_shacl = shapes + rules
   conforms, results_graph, text = pyshacl.validate(
       data, shacl_graph=combined_shacl, ont_graph=ontology, advanced=True
   )
   print('Conforms:', conforms)
   print(text[:2000])
   assert not conforms, 'Expected validation warnings (conforms should be False)'
   print()
   print('=== PASS: pyshacl validation fires warnings as expected ===')
   "
   ```
   Expected: `conforms: False` with Warning-level violations for stale contact (Priya) and overdue follow-up.

8. **If 90-day duration arithmetic fails:** Adjust the StaleContactValidation SPARQL to a simpler pattern that rdflib supports. Options:
   - Remove duration subtraction, use direct date comparison with a hardcoded past date in the seed
   - Use `NOT EXISTS` without date arithmetic (catches contacts with zero interactions)
   - Re-run pyshacl validation to confirm the fallback works
   
   Document whichever pattern works in a comment in the rules file.

## Must-Haves

- [ ] `models/crm/rules/crm.ttl` has 3 separate NodeShapes: 1 inference + 2 validation per D153
- [ ] Validation shapes have `sh:severity sh:Warning` on the NodeShape (not on the constraint)
- [ ] `models/crm/seed/crm.jsonld` has ~12 objects covering all 4 types
- [ ] Seed data pre-populates both sides of owl:inverseOf pairs per D154
- [ ] Seed includes trigger data: 1 stale contact (old interactions only) + 1 overdue follow-up
- [ ] Individual rdflib parse succeeds for all 5 archive files (ontology, shapes, views, seed, rules)
- [ ] `parse_manifest()` + `load_archive()` + `validate_archive()` returns 0 errors
- [ ] pyshacl validate with `advanced=True` fires Warning-level violations

## Verification

- All 5 model files parse with rdflib without errors
- `validate_archive()` returns `is_valid=True` with 0 errors
- pyshacl returns `conforms=False` with Warning-level violations for stale contact and/or overdue follow-up
- Inference rule constructs `crm:lastContactedDate` (visible in pyshacl output or separate inference test)

## Inputs

- `models/crm/manifest.yaml` — model identity (from T01)
- `models/crm/ontology/crm.jsonld` — OWL classes and properties (from T01)
- `models/crm/shapes/crm.jsonld` — SHACL shapes (from T02)
- `models/crm/views/crm.jsonld` — ViewSpecs and SavedQueries (from T02)
- `models/basic-pkm/rules/basic-pkm.ttl` — structural template for rules (especially OverdueTaskValidationShape and PrefixDeclarations)
- `models/basic-pkm/seed/basic-pkm.jsonld` — structural template for seed data (typed dates, cross-refs, both-side inverse)

## Expected Output

- `models/crm/rules/crm.ttl` — SHACL-AF rules with 1 inference rule + 2 validation rules
- `models/crm/seed/crm.jsonld` — ~12 seed objects with trigger data for validation warnings
- All 3 verification steps pass (rdflib parse, pipeline validation, pyshacl validation)
