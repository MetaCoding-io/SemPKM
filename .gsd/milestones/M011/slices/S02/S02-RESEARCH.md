# S02: Personal CRM Model — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

S02 is a straightforward content-authoring slice — create 6 files under `models/crm/` following the exact patterns proven by basic-pkm v2 (S01) and PPV. The design doc (§2 Personal CRM, lines ~315–510 of `MENTAL-MODELS-EXPANSION-DESIGN.md`) specifies 4 types (Contact, Company, Interaction, Deal), their properties, relationships, SHACL shapes, views, SHACL-AF rules, seed data, and icon manifest in full detail. The gist alignment targets (`gist:Person`, `gist:Organization`, `gist:Event`, `gist:Agreement`) all exist in gistCore14.0.0 — confirmed in the bundled Turtle file.

The only technical novelty beyond what S01 proved is the **stale-contact validation rule** — a `sh:sparql` `sh:SPARQLConstraint` that checks whether a Contact has any Interaction with `interactionDate` within the last 90 days. This requires the same `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` date arithmetic pattern already proven in S01's overdue-task rule (see KNOWLEDGE.md pattern #1), plus a `NOT EXISTS` subquery joining across two types (`crm:Contact` → `crm:Interaction`). The follow-up-overdue rule uses the same date pattern on a single type. A third rule (`LastContactedDeriveRule`) is an inference `sh:SPARQLRule` that derives `crm:lastContactedDate` on each Contact from their most recent Interaction — this uses `MAX()` aggregate which is standard SPARQL and works in rdflib.

No platform code changes are needed. No new libraries. No new patterns to discover.

## Recommendation

**Approach:** Author all 6 files in order (manifest → ontology → shapes → views → rules → seed), validate offline after each file via rdflib parse, then run the full `parse_manifest()` + `load_archive()` + `validate_archive()` pipeline. Follow the basic-pkm v2 files as the direct structural template, with PPV as reference for complex models.

**Build order within the slice:**

1. **manifest.yaml** — Establishes modelId, namespace, prefixes, entrypoints, icons. Fastest to write, validates immediately via `parse_manifest()`.
2. **ontology/crm.jsonld** — OWL classes (4 types) + properties (datatype + object) + `owl:inverseOf` declarations. Validate by parsing with rdflib.
3. **shapes/crm.jsonld** — SHACL NodeShapes with PropertyGroups, `sh:in` for enums, `sempkm:editHelpText`. Validate by parsing + checking `sh:targetClass` references resolve to ontology classes.
4. **views/crm.jsonld** — ViewSpecs (table/card/graph per type) + SavedQueries. Note: `sempkm` prefix in views is `urn:sempkm:vocab:` (not `urn:sempkm:` as in shapes).
5. **rules/crm.ttl** — Turtle file with inference rules (LastContactedDeriveRule) and validation rules (StaleContactValidation, FollowUpOverdueValidation) on separate NodeShapes per D153. Date arithmetic uses `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` pattern.
6. **seed/crm.jsonld** — Seed objects with both forward and inverse sides pre-populated per D154. Include one stale contact (interaction >90 days ago) and one overdue follow-up to trigger validation warnings.

## Implementation Landscape

### Key Files

**Reference files (read, follow patterns):**
- `models/basic-pkm/manifest.yaml` — Reference manifest with icon contexts (tree/tab/graph), `entailment_defaults`, `shacl_rules: true`
- `models/basic-pkm/ontology/basic-pkm.jsonld` — OWL classes + properties with gist alignment, `owl:inverseOf` both-side declarations
- `models/basic-pkm/shapes/basic-pkm.jsonld` — SHACL shapes with PropertyGroups, `sh:in` with `@list`, `sempkm:editHelpText` on NodeShape and PropertyShape. Note: `"sempkm": "urn:sempkm:"` in `@context`
- `models/basic-pkm/views/basic-pkm.jsonld` — ViewSpec + SavedQuery definitions. Note: `"sempkm": "urn:sempkm:vocab:"` in `@context` (different prefix namespace)
- `models/basic-pkm/rules/basic-pkm.ttl` — SHACL-AF rules with `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` date arithmetic, separate NodeShapes for inference vs validation per D153
- `models/basic-pkm/seed/basic-pkm.jsonld` — Seed objects with typed dates (`@value`/`@type`), cross-references, both-side inverse population per D154

**Files to create (6 new files):**
- `models/crm/manifest.yaml` — Model manifest
- `models/crm/ontology/crm.jsonld` — OWL ontology (4 classes, ~20 properties)
- `models/crm/shapes/crm.jsonld` — SHACL shapes (4 NodeShapes, ~16 PropertyGroups)
- `models/crm/views/crm.jsonld` — ViewSpecs (~10 views) + SavedQueries (~4 queries)
- `models/crm/rules/crm.ttl` — 1 inference rule + 2 validation rules
- `models/crm/seed/crm.jsonld` — ~12 seed objects (3 companies + 4 contacts + 3 interactions + 2 deals)

**Platform code (no changes, reference only):**
- `backend/app/models/manifest.py` — `ManifestSchema` Pydantic validation, `parse_manifest()`
- `backend/app/models/loader.py` — `load_archive()`, `load_rdf_file()`
- `backend/app/models/validator.py` — `validate_archive()` with IRI namespace check (subjects only, `ALLOWED_EXTERNAL_NAMESPACES` includes `schema.org`, `foaf`, `purl.org/dc`, `w3.org`)

### CRM-Specific Design Details

**Types and gist alignment:**
- `crm:Contact` → `rdfs:subClassOf gist:Person` (NOT `bpkm:Person` — cross-model refs use gist hierarchy)
- `crm:Company` → `rdfs:subClassOf gist:Organization`
- `crm:Interaction` → `rdfs:subClassOf gist:Event`
- `crm:Deal` → `rdfs:subClassOf gist:Agreement`

**owl:inverseOf pairs (3 declared, 1 symmetric):**
- `crm:worksAt` ↔ `crm:hasEmployee` (Contact → Company)
- `crm:dealContact` ↔ `crm:hasDeal` on Contact
- `crm:dealCompany` ↔ `crm:hasDeal` on Company
- `crm:knows` — symmetric (`owl:inverseOf` self, or just `rdf:type owl:SymmetricProperty`)

**Key `sh:in` enums:**
- `crm:relationship`: `["friend", "colleague", "client", "prospect", "mentor", "mentee", "other"]`
- `crm:interactionType`: `["call", "email", "meeting", "coffee", "lunch", "conference", "message", "other"]`
- `crm:dealStage`: `["lead", "qualified", "proposal", "negotiation", "won", "lost"]`
- `crm:size`: `["solo", "small", "medium", "large", "enterprise"]`
- `crm:currency`: `["USD", "EUR", "GBP"]`

**SHACL-AF Rules (3 rules, 3 separate NodeShapes):**

1. **LastContactedDeriveRule** (inference SPARQLRule) — Derives `crm:lastContactedDate` on Contact from `MAX(?date)` of linked Interactions' `crm:interactionDate`. Target: `crm:Contact`.

2. **StaleContactValidation** (validation SPARQLConstraint, `sh:severity sh:Warning`) — Fires when a Contact has no Interaction with `crm:interactionDate` in the last 90 days. Uses:
   ```sparql
   BIND(STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date) AS ?today)
   FILTER NOT EXISTS {
       ?interaction crm:withContact $this ;
                    crm:interactionDate ?iDate .
       FILTER(?iDate > (?today - "P90D"^^xsd:dayTimeDuration))
   }
   ```
   **Risk:** The `?today - "P90D"^^xsd:dayTimeDuration` arithmetic may not work in rdflib's SPARQL engine. Alternative: compute 90-day-ago date as string math or use a simpler `FILTER(?iDate > "2025-12-17"^^xsd:date)` for seed testing, then use the `NOW()` approach for live. Need to test this pattern.

   **Safer approach:** Since S01 proved `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` works for date comparison, use the same approach but compare against a hardcoded threshold or use string arithmetic: `SUBSTR(STR(NOW() - "P90D"^^xsd:dayTimeDuration), 1, 10)`. If rdflib doesn't support duration subtraction, fall back to checking `NOT EXISTS { ... crm:interactionDate ?iDate }` (any interaction) which is simpler but less precise. The design doc says "90 days" but the validation will still be useful even if it just checks "no interactions at all" — refine in S05 integration testing.

3. **FollowUpOverdueValidation** (validation SPARQLConstraint, `sh:severity sh:Warning`) — Fires when `crm:followUpDate < today` and `crm:followUpDone` is not true. Same date pattern as overdue-task from S01.

**Seed data strategy (per D154 — both sides pre-populated):**
- 3 Companies (Acme Corp, Bright Ideas Studio, DataFlow Inc)
- 4 Contacts (Sarah Park, James Liu, Priya Sharma, Marcus Cole) with `crm:worksAt` AND companies with `crm:hasEmployee`
- 3 Interactions with `crm:withContact` AND contacts with `crm:hasInteraction`
- 2 Deals with `crm:dealContact`/`crm:dealCompany` AND contacts/companies with `crm:hasDeal`
- 1 contact with old interactions only (>90 days ago) to trigger stale-contact warning
- 1 interaction with past `followUpDate` and no `followUpDone` to trigger follow-up warning

**ViewSpecs (10 views):**
- Contact: table, card, graph (3)
- Company: table (1)
- Interaction: table/timeline (1)
- Deal: table, card (2 — card grouped by dealStage = pipeline view)
- CRM Network: graph (1) — full contact + company graph
- Per-type graph views for Company and Interaction (2)

**SavedQueries (4):**
- "Stale Contacts" — no interaction in 90 days
- "Upcoming Follow-ups" — followUpDate in next 7 days, not done
- "Open Deals" — dealStage not in (won, lost)
- "Network Map" — full contact graph

**Icon manifest (4 icons with tree/tab/graph contexts):**
- `crm:Contact` → `user` / `#6366f1` (indigo)
- `crm:Company` → `building-2` / `#8b5cf6` (violet)
- `crm:Interaction` → `message-circle` / `#14b8a6` (teal)
- `crm:Deal` → `handshake` / `#f59e0b` (amber)

### Build Order

1. **manifest.yaml** — validate with `parse_manifest()`. Unblocks all other files.
2. **ontology/crm.jsonld** — validate rdflib parse. Unblocks shapes + views + seed (reference integrity).
3. **shapes/crm.jsonld** — validate rdflib parse. Independent of views/rules/seed.
4. **views/crm.jsonld** — validate rdflib parse. Depends on ontology classes for `sempkm:targetClass`.
5. **rules/crm.ttl** — validate rdflib parse (Turtle format). Test validation rules against seed data with pyshacl.
6. **seed/crm.jsonld** — validate rdflib parse. Depends on ontology classes for `@type` references.
7. **Full pipeline validation** — `parse_manifest()` + `load_archive()` + `validate_archive()` = 0 errors.
8. **pyshacl validation test** — Run shapes + rules against seed data to confirm stale-contact and follow-up warnings fire.

### Verification Approach

**Step 1: Offline archive validation (no Docker):**
```bash
cd backend
.venv/bin/python3 -c "
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
"
```

**Step 2: SHACL-AF validation (rules fire correctly):**
```bash
cd backend
.venv/bin/python3 -c "
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
print(text[:1500])
"
```
Expected: `conforms: False` with Warning-level violations for stale contact and overdue follow-up.

**Step 3: Individual file rdflib parse (catch JSON-LD syntax errors early):**
```bash
cd backend
.venv/bin/python3 -c "
from rdflib import Graph
for f, fmt in [
    ('../models/crm/ontology/crm.jsonld', 'json-ld'),
    ('../models/crm/shapes/crm.jsonld', 'json-ld'),
    ('../models/crm/views/crm.jsonld', 'json-ld'),
    ('../models/crm/seed/crm.jsonld', 'json-ld'),
    ('../models/crm/rules/crm.ttl', 'turtle'),
]:
    g = Graph().parse(f, format=fmt)
    print(f'{f}: {len(g)} triples - OK')
"
```

## Constraints

- **No remote `@context` in JSON-LD** — All prefixes inline in `@context` block. Enforced by loader.py `_check_no_remote_context()`.
- **Subject IRIs must use `urn:sempkm:model:crm:` namespace** — Validator checks subjects. Objects/ranges (gist classes, schema.org predicates) are not checked.
- **Full IRIs in SPARQL query strings** — ViewSpec SPARQL uses `<urn:sempkm:model:crm:Contact>`, not `crm:Contact`. Queries are passed raw to RDF4J.
- **`sempkm` namespace differs between shapes and views** — Shapes: `"sempkm": "urn:sempkm:"`. Views: `"sempkm": "urn:sempkm:vocab:"`. Must match existing pattern exactly.
- **`sh:in` must use `@list`** — `"sh:in": { "@list": ["a", "b"] }` not `"sh:in": ["a", "b"]`. The latter creates multiple triples instead of an RDF list.
- **Icon definitions need all 3 contexts** — `tree`, `tab`, `graph` sub-objects with `icon`/`color`/`size`.
- **Validation rules on separate NodeShapes from inference rules** — Per D153, `sh:severity sh:Warning` goes on the parent NodeShape, not on the `sh:SPARQLConstraint`.
- **Seed data pre-populates both sides of inverseOf pairs** — Per D154, forward and inverse sides both present in seed JSON-LD.
- **`bpkm:tags` reuse** — CRM types use `bpkm:tags` (from basic-pkm namespace) for tags. This is a cross-model property reference. The validator only checks *subjects*, not *predicates/objects*, so using `bpkm:tags` as a predicate on a `crm:Contact` subject is allowed. However, to be clean, define `crm:tags` or just use a local property. Check design doc — it says `bpkm:tags` which means the CRM ontology @context needs the `bpkm` prefix too.

## Common Pitfalls

- **`bpkm:tags` in CRM seed data** — The design doc uses `bpkm:tags` on CRM types. The ontology `@context` must include `"bpkm": "urn:sempkm:model:basic-pkm:"` for this to resolve. Since `bpkm:tags` is used as a *predicate* (not subject), it passes the validator's IRI namespace check. But if basic-pkm isn't installed, the SHACL form won't know about the tag field. Safer to define a local `crm:tags` property OR just keep `bpkm:tags` and accept the cross-model dependency (both models will typically be installed).

- **`crm:knows` symmetric modeling** — The design doc says `crm:knows` is symmetric. In OWL, this is `rdf:type owl:SymmetricProperty`. Do NOT also declare `owl:inverseOf` for a symmetric property — it's redundant and may confuse reasoners. Just declare `owl:SymmetricProperty` and the inference engine will materialize the inverse automatically.

- **`crm:hasDeal` ambiguity** — The design doc uses `crm:hasDeal` on both Contact and Company as inverse of `crm:dealContact` and `crm:dealCompany` respectively. This is problematic — one property can't be inverse of two different properties. Solution: use `crm:hasContactDeal` (inverse of `crm:dealContact`) and `crm:hasCompanyDeal` (inverse of `crm:dealCompany`), or just define one `crm:hasDeal` inverse of `crm:dealContact` and handle Company→Deal via a separate property.

- **90-day stale contact date arithmetic** — rdflib may not support `xsd:dayTimeDuration` subtraction from dates. Test the `NOW() - "P90D"^^xsd:dayTimeDuration` pattern. If it fails, use a simpler NOT EXISTS check or hardcode a test threshold in seed data.

- **`crm:lastContactedDate` derived property** — This is a new datatype property that only exists via inference (not in forms). It should be declared in the ontology but NOT in the shapes (no form field for a derived value). It needs to appear in ViewSpec SPARQL queries though.

## Open Risks

- **90-day duration arithmetic in rdflib SPARQL** — The `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date) - "P90D"^^xsd:dayTimeDuration` pattern is unproven. If it fails, the stale-contact rule will need a simpler fallback (e.g., `NOT EXISTS { ?i crm:withContact $this }` which catches contacts with zero interactions, or a string-comparison hack). This can be refined during S05 integration testing.

- **`crm:hasDeal` inverse ambiguity** — Design doc assigns `crm:hasDeal` as inverse for both `crm:dealContact` and `crm:dealCompany`. Need to disambiguate during implementation. Minor naming decision.

## Sources

- Design doc §2 Personal CRM: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` lines ~315-510
- KNOWLEDGE.md Pattern #1: `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` for date comparison in rdflib
- D153: Validation rules use separate NodeShapes from inference rules
- D154: Seed data pre-populates both sides of owl:inverseOf pairs
- basic-pkm v2 (S01 output): Complete structural reference for all 6 file types
