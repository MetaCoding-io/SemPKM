# S02: Personal CRM Model

**Goal:** Deliver a complete `crm` model archive (6 files under `models/crm/`) with 4 types (Contact, Company, Interaction, Deal) that passes offline validation, fires SHACL-AF validation warnings for stale contacts and overdue follow-ups, and materializes `crm:lastContactedDate` via inference.

**Demo:** Running `parse_manifest()` + `load_archive()` + `validate_archive()` on `models/crm/` returns zero errors. Running pyshacl with `advanced=True` against seed data produces Warning-level violations for the stale contact and overdue follow-up, and the inference rule derives `crm:lastContactedDate`.

## Must-Haves

- `models/crm/manifest.yaml` — valid ManifestSchema with 4 icon entries (tree/tab/graph contexts), `entailment_defaults` with `owl_inverseOf: true` and `shacl_rules: true`
- `models/crm/ontology/crm.jsonld` — 4 OWL classes aligned to gist, ~20 properties with `owl:inverseOf` pairs, `crm:knows` as `owl:SymmetricProperty`
- `models/crm/shapes/crm.jsonld` — 4 SHACL NodeShapes with PropertyGroups, `sh:in` enums using `@list`, `sempkm:editHelpText`
- `models/crm/views/crm.jsonld` — ~10 ViewSpecs (table/card/graph per type) + 4 SavedQueries, using `sempkm:vocab:` namespace (not `urn:sempkm:`)
- `models/crm/rules/crm.ttl` — 1 inference SPARQLRule (LastContactedDeriveRule) + 2 validation SPARQLConstraints (StaleContact, FollowUpOverdue) on separate NodeShapes per D153
- `models/crm/seed/crm.jsonld` — ~12 seed objects with both sides of inverseOf pre-populated per D154, including trigger data for validation warnings
- All files parse with rdflib without errors
- Full pipeline `parse_manifest()` + `load_archive()` + `validate_archive()` returns zero errors
- pyshacl validate fires Warning-level violations for stale contact and overdue follow-up

## Proof Level

- This slice proves: contract
- Real runtime required: no (offline validation only; Docker integration in S05)
- Human/UAT required: no

## Verification

```bash
# Step 1: Individual file parse
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
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

# Step 2: Full pipeline validation
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
assert r.is_valid and len(r.errors) == 0, 'Archive validation must pass with 0 errors'
"

# Step 3: SHACL-AF validation (rules fire correctly)
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
assert 'Warning' in text or 'sh:Warning' in text, 'Expected Warning-level violations'
"

# Step 4: Diagnostic — verify structured error reporting on intentionally bad input
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
try:
    parse_manifest(Path('/tmp/nonexistent-model'))
    print('ERROR: should have raised ValueError')
except ValueError as e:
    print(f'Structured error (expected): {e}')
"
```

## Observability / Diagnostics

- **Manifest parse errors:** `parse_manifest(Path('../models/crm'))` raises `ValueError` with structured message (missing field, namespace mismatch, bad YAML) — agents can re-run to inspect.
- **Ontology triple count:** `Graph().parse(..., format='json-ld')` returns triple count; <50 triples signals missing class/property definitions.
- **Subject namespace violations:** The namespace compliance check (`urn:sempkm:model:crm:`) reports exact bad subject IRIs, pinpointing misconfigured `@context` or `@id` values.
- **Archive validation pipeline:** `validate_archive()` returns a `ValidationResult` with `.is_valid`, `.errors[]` (file + message), and `.warnings[]` — the primary diagnostic surface for all 6 files.
- **SHACL-AF rule firing:** `pyshacl.validate(..., advanced=True)` returns `(conforms, results_graph, text)` — `text` includes human-readable violation details with focus node, path, and severity. If rules don't fire, check that seed data contains trigger conditions (stale contact >90 days, overdue follow-up).
- **Failure artifact:** No persistent failure artifacts; all diagnostics are CLI-inspectable via the verification commands. Errors surface as Python exceptions or validation result objects.

## Integration Closure

- Upstream surfaces consumed: basic-pkm v2 files (structural template only — no runtime dependency)
- New wiring introduced in this slice: none (pure content, no platform code changes)
- What remains before the milestone is truly usable end-to-end: S05 Docker install + form rendering + view rendering + E2E tests

## Tasks

- [x] **T01: Author CRM manifest and ontology** `est:45m`
  - Why: Establishes the model identity, namespace, icon manifest, and OWL class+property definitions that all other files depend on.
  - Files: `models/crm/manifest.yaml`, `models/crm/ontology/crm.jsonld`
  - Do: Create manifest with modelId `crm`, namespace `urn:sempkm:model:crm:`, 4 icon entries with tree/tab/graph contexts, entailment_defaults matching basic-pkm. Create ontology with 4 OWL classes (Contact→gist:Person, Company→gist:Organization, Interaction→gist:Event, Deal→gist:Agreement), ~20 datatype+object properties, 3 `owl:inverseOf` pairs (worksAt↔hasEmployee, dealContact↔hasContactDeal, dealCompany↔hasCompanyDeal), `crm:knows` as `owl:SymmetricProperty`. Include `bpkm` prefix in @context for `bpkm:tags` reuse. Declare `crm:lastContactedDate` as datatype property (inference-only, no shape).
  - Verify: `parse_manifest(Path('../models/crm'))` succeeds. `Graph().parse('../models/crm/ontology/crm.jsonld', format='json-ld')` succeeds with >50 triples.
  - Done when: Both files exist, parse cleanly, and manifest validates via Pydantic schema.

- [x] **T02: Author CRM shapes and views** `est:1h`
  - Why: Shapes drive SHACL form generation (property groups, enums, helptext). Views define table/card/graph ViewSpecs and SavedQueries for browsing CRM data.
  - Files: `models/crm/shapes/crm.jsonld`, `models/crm/views/crm.jsonld`
  - Do: Create shapes with 4 NodeShapes (ContactShape, CompanyShape, InteractionShape, DealShape), PropertyGroups for logical field grouping, `sh:in` enums using `{"@list": [...]}` for relationship/interactionType/dealStage/size/currency, `sempkm:editHelpText` on shapes. Use `"sempkm": "urn:sempkm:"` prefix in shapes. Create views with ~10 ViewSpecs (Contact table/card/graph, Company table/graph, Interaction table/graph, Deal table/card, CRM Network graph) + 4 SavedQueries (Stale Contacts, Upcoming Follow-ups, Open Deals, Network Map). Use `"sempkm": "urn:sempkm:vocab:"` prefix in views. Use full IRIs in SPARQL queries (e.g. `<urn:sempkm:model:crm:Contact>`).
  - Verify: Both files parse with rdflib. Shapes file has 4 `sh:targetClass` triples. Views file has 10+ ViewSpec subjects.
  - Done when: Both files parse cleanly, shapes reference all 4 ontology classes, views cover all types.

- [ ] **T03: Author CRM rules, seed data, and run full pipeline validation** `est:1h`
  - Why: Rules define the inference and validation logic. Seed data provides a realistic CRM scenario with trigger data for validation warnings. Full pipeline validation proves the archive is correct end-to-end.
  - Files: `models/crm/rules/crm.ttl`, `models/crm/seed/crm.jsonld`
  - Do: Create rules in Turtle with 3 separate NodeShapes per D153: (1) LastContactedDeriveRule — SPARQLRule targeting Contact, CONSTRUCT `crm:lastContactedDate` from `MAX(crm:interactionDate)` of linked Interactions; (2) StaleContactValidationShape — SPARQLConstraint with `sh:severity sh:Warning`, fires when Contact has no Interaction in last 90 days using `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` pattern; (3) FollowUpOverdueValidationShape — SPARQLConstraint with `sh:severity sh:Warning`, fires when `crm:followUpDate < today` and `crm:followUpDone` is not true. Create seed data with 3 companies, 4 contacts, 3 interactions, 2 deals — both sides of inverseOf pre-populated per D154. Include 1 contact with old interactions only (>90 days ago) to trigger stale-contact warning, and 1 interaction with past followUpDate and no followUpDone to trigger follow-up warning. Run all 3 verification steps: individual rdflib parse, full pipeline validation (0 errors), pyshacl validate with advanced=True (expect Warning violations). If 90-day duration arithmetic fails in rdflib, fall back to simpler NOT EXISTS pattern.
  - Verify: All 3 verification commands from the Verification section pass.
  - Done when: `validate_archive()` returns 0 errors, pyshacl returns conforms=False with Warning-level violations for stale contact and overdue follow-up.

## Files Likely Touched

- `models/crm/manifest.yaml`
- `models/crm/ontology/crm.jsonld`
- `models/crm/shapes/crm.jsonld`
- `models/crm/views/crm.jsonld`
- `models/crm/rules/crm.ttl`
- `models/crm/seed/crm.jsonld`
