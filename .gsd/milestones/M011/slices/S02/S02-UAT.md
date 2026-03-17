# S02: Personal CRM Model — UAT

**Milestone:** M011
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is a pure content slice (no platform code changes). All verification is offline — rdflib parse, pipeline validation, pyshacl advanced=True. Docker integration testing is deferred to S05.

## Preconditions

- Python venv at `backend/.venv` with rdflib, pyshacl, and app modules importable
- All 6 CRM model files exist under `models/crm/` (manifest.yaml, ontology/crm.jsonld, shapes/crm.jsonld, views/crm.jsonld, rules/crm.ttl, seed/crm.jsonld)
- No running Docker services required

## Smoke Test

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
from app.models.loader import load_archive
from app.models.validator import validate_archive
base = Path('../models/crm')
m = parse_manifest(base)
a = load_archive(base, m)
r = validate_archive(a)
print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}')
assert r.is_valid and len(r.errors) == 0
print('SMOKE TEST PASSED')
"
```

Expected: `Valid: True, Errors: 0` followed by `SMOKE TEST PASSED`

## Test Cases

### 1. All 6 files parse individually with rdflib

1. Parse each file with rdflib using its correct format (json-ld or turtle)
2. Record triple count for each file
3. **Expected:**
   - ontology/crm.jsonld: ~170 triples (json-ld)
   - shapes/crm.jsonld: ~405 triples (json-ld)
   - views/crm.jsonld: ~81 triples (json-ld)
   - seed/crm.jsonld: ~141 triples (json-ld)
   - rules/crm.ttl: ~31 triples (turtle)
   - All parse without exceptions

### 2. Manifest validates via Pydantic schema

1. Run `parse_manifest(Path('models/crm'))`
2. **Expected:** Returns ManifestSchema object with:
   - `model_id == "crm"`
   - 4 types defined (Contact, Company, Interaction, Deal)
   - Each type has icon entries with tree/tab/graph contexts
   - `entailment_defaults` includes `owl_inverseOf: true` and `shacl_rules: true`

### 3. Full pipeline validation returns zero errors

1. Run `parse_manifest()` → `load_archive()` → `validate_archive()`
2. **Expected:** `is_valid=True`, `len(errors)==0`, `len(warnings)==0`

### 4. SHACL-AF validation fires 2 Warning-level violations

1. Parse rules (turtle) + shapes (json-ld) into combined_shacl graph
2. Parse seed data and ontology
3. Run `pyshacl.validate(data, shacl_graph=combined_shacl, ont_graph=ontology, advanced=True)`
4. **Expected:**
   - `conforms == False`
   - Validation text contains "Warning"
   - StaleContactValidationShape fires on `seed-contact-marcus` (no interactions)
   - FollowUpOverdueValidationShape fires on `seed-interaction-meeting-james` (overdue follow-up)

### 5. Inference rule materializes lastContactedDate

1. Run pyshacl.validate with `inplace=True`
2. Query data graph for `(None, CRM.lastContactedDate, None)` triples
3. **Expected:**
   - 3 new triples materialized (0 existed before inference)
   - seed-contact-sarah → 2026-03-10
   - seed-contact-james → 2026-03-15
   - seed-contact-priya → 2025-11-01

### 6. Ontology has correct OWL class alignment

1. Parse ontology and query for `rdfs:subClassOf` triples
2. **Expected:**
   - Contact → gist:Person
   - Company → gist:Organization
   - Interaction → gist:Event
   - Deal → gist:Agreement

### 7. InverseOf pairs are bidirectional

1. Parse ontology and query for `owl:inverseOf` triples
2. **Expected:** 4 pairs found:
   - worksAt ↔ hasEmployee
   - withContact ↔ hasInteraction
   - dealContact ↔ hasContactDeal
   - dealCompany ↔ hasCompanyDeal

### 8. Shapes have correct targetClass declarations

1. Parse shapes and query for `sh:targetClass` triples
2. **Expected:** Exactly 4 declarations:
   - ContactShape → crm:Contact
   - CompanyShape → crm:Company
   - InteractionShape → crm:Interaction
   - DealShape → crm:Deal

### 9. Views have correct ViewSpec and SavedQuery subjects

1. Parse views and count subjects typed as `sempkm:ViewSpec` and `sempkm:SavedQuery`
2. **Expected:**
   - 10 ViewSpec subjects (Contact table/card/graph, Company table/graph, Interaction table/graph, Deal table/card, CRM Network graph)
   - 4 SavedQuery subjects (Stale Contacts, Upcoming Follow-ups, Open Deals, Network Map)

### 10. Seed data has both sides of inverseOf pre-populated

1. Parse seed data
2. Check that Contact Sarah has `worksAt` pointing to Acme
3. Check that Company Acme has `hasEmployee` pointing to Sarah
4. Check that Contact Sarah and James have mutual `knows` links
5. **Expected:** All bidirectional links present — inference adds 0 inverseOf triples for seed data

## Edge Cases

### Bad manifest path produces structured error

1. Run `parse_manifest(Path('/tmp/nonexistent-model'))`
2. **Expected:** Raises `ValueError` with message containing "manifest.yaml not found"

### Namespace compliance — no subjects outside model namespace

1. Parse ontology and enumerate all subjects starting with `urn:sempkm:`
2. Filter for subjects NOT starting with `urn:sempkm:model:crm:`
3. **Expected:** Empty list — all model-specific subjects use the `urn:sempkm:model:crm:` prefix

### Shapes use urn:sempkm: prefix, views use urn:sempkm:vocab: prefix

1. Load shapes JSON and check `@context.sempkm`
2. Load views JSON and check `@context.sempkm`
3. **Expected:** shapes = `urn:sempkm:`, views = `urn:sempkm:vocab:`

## Failure Signals

- `parse_manifest()` raises ValueError → manifest.yaml is malformed or missing required fields
- `load_archive()` raises exception → a file referenced in manifest.yaml doesn't exist or can't parse
- `validate_archive()` returns `is_valid=False` or `len(errors) > 0` → archive has structural or content errors
- `pyshacl.validate()` returns `conforms=True` → validation rules are not firing (check seed trigger data)
- Triple count significantly lower than expected (e.g., ontology < 50) → missing class/property definitions or broken @context
- `lastContactedDate` triples not materialized after inference → SPARQLRule has a SPARQL syntax error or seed data doesn't have linked interactions

## Requirements Proved By This UAT

- MODEL-02 (partial) — CRM model archive passes all offline contract verification. Forms, views, and Docker install deferred to S05.

## Not Proven By This UAT

- Docker install via model manager (S05)
- SHACL form rendering in browser (S05)
- ViewSpec rendering with actual data in browser (S05)
- Inference running in live triplestore context (S05)
- Validation warnings appearing in lint panel (S05)
- SavedQuery execution returning expected results (S05)
- Cross-model coexistence with basic-pkm, zettelkasten, research (S05)
- E2E Playwright tests (S05)

## Notes for Tester

- The stale-contact rule fires on Marcus Cole (zero interactions), not Priya Sharma (old interactions). This is correct behavior for the NOT EXISTS rule variant per D157.
- The overdue follow-up rule fires on the James Liu meeting interaction (followUpDate 2026-03-16). This date is in the past as of 2026-03-17. If testing far in the future, it will still fire correctly.
- Inference materializes `lastContactedDate` only for contacts WITH interactions (Sarah, James, Priya). Marcus has no interactions, so no date is derived for him.
- The `crm:knows` symmetric property (Sarah ↔ James) has both directions in seed data. Inference would produce 0 new triples since both are present.
