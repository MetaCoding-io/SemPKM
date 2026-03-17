# M011: Mental Models Expansion — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

M011 is a **pure content milestone** — no platform code changes, no new Python modules, no schema migrations, no frontend JS. The deliverable is 4 model archives (`models/{id}/` directories), each containing 6 files: `manifest.yaml`, `ontology/{id}.jsonld`, `shapes/{id}.jsonld`, `views/{id}.jsonld`, `rules/{id}.ttl`, and `seed/{id}.jsonld`. These files must pass the existing `ManifestSchema` validation, `load_archive()` parsing, and `validate_archive()` namespace/reference checks. Once on disk, `refresh_artifacts` (for basic-pkm upgrade) or `install` (for new models) loads them through the existing pipeline with zero platform changes.

The design document (`.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md`, 1107 lines) is comprehensive and nearly implementation-ready — type definitions, property tables, SHACL shape group structures, view SPARQL queries, rule logic, seed data, and icon manifests are all specified. The primary research question was whether the existing platform machinery (manifest validation, archive loader, SHACL-AF rules, pyshacl validation, inference pipeline) can support the new patterns without platform changes. **The answer is yes**, with minor constraints noted below.

The risk profile is low: each model is independent, the archive format is well-exercised by basic-pkm and ppv (2100+ lines of proven JSON-LD/Turtle), and offline validation (rdflib + pyshacl) can catch errors before Docker deployment. The highest-risk items are the SPARQL-based validation rules (date arithmetic for overdue tasks, 90-day stale contacts) which require `sh:sparql` SPARQLConstraint — confirmed working in pyshacl 0.31.0 with `advanced=True`.

## Recommendation

**Approach:** Build models one at a time, in design doc order (basic-pkm v2 → CRM → Zettelkasten+ → Research Workflow), with offline validation gates between each. Follow the PPV model (2111 lines, 11 types) as the structural reference — it exercises every pattern the new models need.

**Why this order:**
1. **basic-pkm v2** is an upgrade to an existing installed model. It must be tested with `refresh_artifacts` (not fresh install). It's also the simplest addition (2 new types on an existing 4-type model) and exercises the upgrade path.
2. **Personal CRM** introduces a new model with 4 types and cross-model relationships (`crm:Contact` → `bpkm:Person`). Tests the co-installation story.
3. **Zettelkasten+** has the most complex relationship graph (5 types, argumentation links) and the most validation rules.
4. **Research Workflow** has the most complex evidence/claim patterns and builds on patterns proved by earlier models.

**Slice count:** 6 slices recommended — one per model, one for cross-model verification + dashboards documentation, one for E2E tests + user guide docs.

## Implementation Landscape

### Key Files

**Existing references (read-only, follow these patterns):**
- `models/basic-pkm/manifest.yaml` — Reference manifest structure with icons (tree/tab/graph contexts)
- `models/basic-pkm/ontology/basic-pkm.jsonld` — OWL classes + properties with gist alignment
- `models/basic-pkm/shapes/basic-pkm.jsonld` — SHACL shapes with PropertyGroups, `sh:in`, `sempkm:editHelpText`
- `models/basic-pkm/views/basic-pkm.jsonld` — ViewSpec + SavedQuery definitions with full SPARQL
- `models/basic-pkm/rules/basic-pkm.ttl` — SHACL-AF SPARQLRule in Turtle format
- `models/basic-pkm/seed/basic-pkm.jsonld` — JSON-LD seed objects with typed references
- `models/ppv/` — More complex reference (11 types, 7 inverseOf pairs, denorm rules)

**Platform code that processes models (no changes needed):**
- `backend/app/models/manifest.py` — `ManifestSchema` Pydantic validation, `parse_manifest()`
- `backend/app/models/loader.py` — `load_archive()`, `load_rdf_file()`, remote @context check
- `backend/app/models/validator.py` — IRI namespace check (subjects only), cross-file reference integrity
- `backend/app/services/models.py` — `install()`, `refresh_artifacts()`, `remove()` pipeline
- `backend/app/inference/service.py` — `run_inference()` with `advanced=True` for SHACL-AF
- `backend/app/services/validation.py` — `pyshacl.validate()` for lint panel

**Files to create (4 models × 6 files each = 24 new files + basic-pkm updates):**
- `models/crm/` — New directory (6 files)
- `models/zettelkasten/` — New directory (6 files)
- `models/research/` — New directory (6 files)
- `models/basic-pkm/*` — Updated files (version bump, new types/shapes/views/rules/seed)

### Structural Patterns to Follow

**Manifest (YAML):**
```yaml
modelId: crm                          # lowercase alphanumeric + hyphens
version: "1.0.0"                      # semver
namespace: "urn:sempkm:model:crm:"    # must match urn:sempkm:model:{modelId}:
prefixes:
  crm: "urn:sempkm:model:crm:"
entrypoints:                          # default paths with {modelId} placeholder
  ontology: "ontology/crm.jsonld"
  shapes: "shapes/crm.jsonld"
  views: "views/crm.jsonld"
  seed: "seed/crm.jsonld"
  rules: "rules/crm.ttl"
entailment_defaults:
  owl_inverseOf: true
  shacl_rules: true                   # Enable SPARQLRule execution
icons:                                # Each icon needs tree/tab/graph contexts
  - type: "crm:Contact"
    icon: "user"
    color: "#6366f1"
    tree: { icon: "user", color: "#6366f1", size: 16 }
    tab: { icon: "user", color: "#6366f1", size: 14 }
    graph: { icon: "user", color: "#6366f1" }
```

**Ontology (JSON-LD):**
- `@context` must include all needed prefixes (model namespace, gist, dcterms, schema, foaf, etc.)
- All subject IRIs must use model namespace (e.g., `crm:Contact`, `crm:worksAt`)
- Classes use `rdfs:subClassOf` pointing to gist classes (as objects — passes validator)
- `owl:inverseOf` declarations for bidirectional navigation
- No remote `@context` URLs (Docker isolation constraint)

**Shapes (JSON-LD):**
- PropertyGroups for form section organization (`sh:order` for display order)
- Property shapes with `sh:path`, `sh:name`, `sh:datatype`/`sh:class`, `sh:order`, `sh:group`
- `sh:in` with `@list` for enum constraints
- `sh:minCount`/`sh:maxCount` for cardinality
- `sempkm:editHelpText` on NodeShape (type-level) and on PropertyShape (field-level)
- Object properties use `sh:class` for range, `sh:nodeKind { "@id": "sh:IRI" }`

**Views (JSON-LD):**
- `sempkm:ViewSpec` with `sempkm:targetClass`, `sempkm:rendererType`, `sempkm:sparqlQuery`
- Table views need `sempkm:columns` and `sempkm:sortDefault`
- Card views need `sempkm:cardTitle` and `sempkm:cardSubtitle`
- Graph views use CONSTRUCT queries
- `sempkm:SavedQuery` entries with `sempkm:queryText` and `sempkm:source`
- Full IRIs in SPARQL (no prefixed names inside query strings)

**Rules (Turtle):**
- `sh:SPARQLRule` for inference (CONSTRUCT produces new triples)
- `sh:sparql` `sh:SPARQLConstraint` for validation warnings (SELECT finds violations)
- Both need `sh:prefixes` declaration block
- Prefix declarations use `sh:declare` with `sh:prefix` + `sh:namespace`
- Inference rules: `sh:targetClass` + `sh:rule [ a sh:SPARQLRule ]`
- Validation rules: separate NodeShape with `sh:severity sh:Warning` + `sh:sparql [ a sh:SPARQLConstraint ]`

**Seed (JSON-LD):**
- Objects with `@id` using model namespace (e.g., `crm:seed-contact-sarah`)
- `@type` using model class IRI
- Cross-references via `{ "@id": "crm:seed-company-acme" }`
- Dates as typed literals: `{ "@value": "2026-03-10", "@type": "xsd:date" }`
- Tags as arrays: `"bpkm:tags": ["tag1", "tag2"]`

### Build Order

1. **basic-pkm v2.0** — Prove the upgrade path works. Add Task and Milestone types to existing model. Test with `refresh_artifacts`. Validates that new types appear in forms, views, and explorer without breaking existing Project/Person/Note/Concept data.

2. **Personal CRM** — First new standalone model. 4 types, moderate relationship complexity. Validates fresh install pipeline. Test cross-model reference (Contact → basic-pkm Person) when both models are installed.

3. **Zettelkasten+** — 5 types, rich argumentation links. The provenance chain (Source → LiteratureNote → PermanentNote) exercises deep relationship traversal. SPARQL-based validation rules (unprocessed fleeting notes) test the SPARQLConstraint path.

4. **Research Workflow** — 5 types, most complex validation rules (unsupported claims, contested claims). Evidence map graph view is the most complex CONSTRUCT query.

5. **Cross-model verification** — Test all 4 models installed simultaneously. Verify cross-model edges, lint panel warnings, dashboard documentation.

6. **E2E tests + User guide docs** — Playwright tests for install + object creation + form rendering + view rendering per model. User guide pages for each model.

### Verification Approach

**Offline validation (per model, no Docker needed):**
```bash
cd backend
.venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
from app.models.loader import load_archive
from app.models.validator import validate_archive

m = parse_manifest(Path('../models/{model_id}'))
a = load_archive(Path('../models/{model_id}'), m)
r = validate_archive(a)
print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}, Warnings: {len(r.warnings)}')
for e in r.errors: print(f'  E: {e.file}: {e.message}')
"
```

**SHACL-AF rule validation (per model, no Docker):**
```bash
.venv/bin/python3 -c "
from rdflib import Graph
import pyshacl
rules = Graph().parse('../models/{model_id}/rules/{model_id}.ttl', format='turtle')
# Create minimal test data graph with one object of each type
data = Graph().parse('../models/{model_id}/seed/{model_id}.jsonld', format='json-ld')
ontology = Graph().parse('../models/{model_id}/ontology/{model_id}.jsonld', format='json-ld')
conforms, results_graph, text = pyshacl.validate(
    data, shacl_graph=rules, ont_graph=ontology, advanced=True
)
print(text[:500])
"
```

**Docker verification (after offline passes):**
1. `docker compose up -d` with models on disk
2. Admin > Mental Models > Install (for new models) or Refresh (for basic-pkm)
3. Create one object of each type — verify SHACL form renders with correct groups, fields, enums, helptext
4. Open each ViewSpec — verify table/card/graph views load with seed data
5. Run inference — verify inverse properties materialize
6. Run validation — verify lint warnings appear (overdue tasks, stale contacts, etc.)

## Constraints

- **No remote @context in JSON-LD** — rdflib attempts HTTP fetches during parsing, which fails in Docker. All contexts must be inline. This is enforced by `_check_no_remote_context()` in loader.py.
- **Subject IRIs must use model namespace** — The validator checks all subject IRIs start with `urn:sempkm:model:{modelId}:` or allowed external namespaces (w3.org, purl.org/dc, schema.org, xmlns.com/foaf). Objects/ranges (like gist: classes) are not checked.
- **Full IRIs in SPARQL queries** — ViewSpec SPARQL queries must use full IRIs, not prefixed names (the query strings are passed directly to RDF4J, not through a prefix resolver).
- **Icon definitions need all 3 contexts** — Manifest icon entries need `tree`, `tab`, and `graph` sub-objects with icon/color/size. Missing contexts cause fallback behavior that may not render correctly.
- **`entailment_defaults.shacl_rules: true`** — Required in manifest for SPARQLRule execution during inference. Both basic-pkm and ppv already have this enabled.
- **SHACL validation (shapes) vs. SHACL-AF inference (rules) are separate files** — Shapes go in `shapes/*.jsonld` (PropertyGroups, constraints, form generation). SHACL-AF rules go in `rules/*.ttl` (SPARQLRule for inference, SPARQLConstraint for validation warnings). The inference pipeline processes rules; the validation service processes shapes. However, SPARQL-based validation constraints (`sh:sparql` blocks) can go in *either* location — they work in shapes (processed by pyshacl.validate) or in rules (if processed with `advanced=True`). Recommendation: put validation-only rules (warnings) in the rules file alongside inference rules, for organization clarity.
- **Dashboards cannot be bundled in model archives** — DashboardSpec is SQLite JSON (D105). Models can't declare dashboards in archives. The design doc recommends documenting dashboard configurations in model README/user guide, not shipping them as archive files. This is an open question noted in the context.

## Common Pitfalls

- **`sh:in` must use `@list` in JSON-LD** — `"sh:in": { "@list": ["a", "b", "c"] }` not `"sh:in": ["a", "b", "c"]`. The latter creates multiple `sh:in` triples instead of an RDF list. PPV shapes demonstrate the correct pattern.

- **`owl:inverseOf` both-side pre-population in seed data** — Current seed data has both forward and inverse sides pre-populated (e.g., Project → hasParticipant → Person AND Person → participatesIn → Project). This makes `owl:inverseOf` inference produce 0 new triples but ensures data appears correctly even without inference. Follow the same pattern in new seed data.

- **SPARQL date arithmetic for validation rules** — Rules like "overdue task" (`dueDate < today`) need hardcoded date comparison or `NOW()`. pyshacl executes SPARQL locally against an in-memory rdflib graph, so `NOW()` works. However, the date comparison must use proper typed literals: `FILTER(?dueDate < xsd:date(NOW()))` or `FILTER(?dueDate < "2026-03-17"^^xsd:date)`. The `NOW()` approach is correct for live validation.

- **Cross-model type references** — CRM Contact `rdfs:subClassOf gist:Person`, not `rdfs:subClassOf bpkm:Person`. Cross-model edges (CRM Contact → basic-pkm Project) work through shared gist hierarchy, not direct cross-model type references. Models must work standalone.

- **basic-pkm v2 upgrade is additive-only** — No changes to existing type IRIs, property IRIs, or shape structures. New types (Task, Milestone, Event) added alongside existing ones. `refresh_artifacts` clears and rewrites ontology/shapes/views/rules graphs but does NOT touch the seed graph. This means new seed data (tasks, milestones, events) won't appear automatically — users must create objects manually or a separate seed update must be triggered.

- **`sh:severity sh:Warning` goes on the NodeShape, not the SPARQLConstraint** — Tested with pyshacl 0.31.0: severity on the constraint node is ignored; it must be on the parent NodeShape. The constraint violation text then reports the correct Warning severity.

- **Validation rules need separate NodeShapes from inference rules** — An inference SPARQLRule uses `sh:rule` and generates triples. A validation SPARQLConstraint uses `sh:sparql` and produces violations. They can share `sh:targetClass` but must be on different NodeShape instances (mixing them on one shape causes unpredictable behavior with pyshacl).

## Open Risks

- **SPARQL-based validation rules with date comparison may not fire as expected** — pyshacl validates against an in-memory rdflib copy of the data graph. If `NOW()` returns UTC and seed data uses local dates, comparisons may produce unexpected results. Mitigate by using UTC dates consistently in seed data and testing validation offline.

- **Large seed data volume** — 4 models × ~10-20 seed objects each = ~60-80 objects. Each seed object goes through `EventStore.commit()` individually during install, which creates a named graph event per object. 80 events is well within normal operating range (Ideaverse import creates 895), but install time may be noticeable (~5-10 seconds per model).

- **basic-pkm v2 seed data gap** — `refresh_artifacts` only updates ontology/shapes/views/rules graphs. New seed objects (Tasks, Milestones, Events) won't be created. Users upgrading from v1.3 will see the new types in forms but have no example data. This is acceptable for a version upgrade but should be documented.

- **No automated cross-model edge testing** — Cross-model relationships (CRM Contact → basic-pkm Project) depend on both models being installed. Offline validation can't test this. Docker-based integration verification is needed.

- **Icon name validation** — Lucide icon names in manifests (e.g., `check-square`, `flag`, `calendar`) are not validated at install time. A typo renders as an empty box. Verify icon names against Lucide's icon set.

## Candidate Requirements

The following should be created as requirements during roadmap planning:

- **MODEL-01**: basic-pkm v2.0 — Task, Milestone, Event types with shapes, views, rules, seed, icons
- **MODEL-02**: Personal CRM — Contact, Company, Interaction, Deal types with pipeline views and SHACL-AF rules
- **MODEL-03**: Zettelkasten+ — FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote with argumentation links and provenance chain queries
- **MODEL-04**: Research Workflow — Paper, Claim, Evidence, ResearchQuestion, Argument with evidence map and confidence-based validation rules

Additional observations:
- **Dashboard bundling is out of scope** — DashboardSpec is SQLite JSON (D105). Pre-built dashboards described in the design doc cannot be shipped in model archives. Document recommended dashboard configurations in user guide instead.
- **Browser extension integration is out of scope** — References in the design doc are forward-looking (M014/M015). Ignore for M011.
- **Calendar provider sync apps are out of scope** — The Task/Event "integration hub" fields (`externalProvider`, `externalId`, `lastSyncedAt`, `syncDirection`) should still be included in the schema (future-proofing for M016-M024) but won't be exercised in M011.

## Structural Size Estimates

Based on PPV (11 types, 2111 lines total) as the reference:

| Model | Types | Estimated Lines | Complexity |
|-------|-------|----------------|------------|
| basic-pkm v2 (upgrade) | 7 (was 4) | ~2200 (was 1296) | Medium — adds to existing files |
| Personal CRM | 4 | ~1500 | Medium — moderate relationships |
| Zettelkasten+ | 5 | ~1800 | High — argumentation links, provenance chain |
| Research Workflow | 5 | ~1800 | High — complex evidence map, multiple validation rules |
| **Total new content** | | **~6000 lines** | |

## Sources

- Design doc: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` (1107 lines, comprehensive)
- Integration mapping: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` (validates Task/Event schema)
- PPV model reference: `models/ppv/` (2111 lines, 11 types — structural pattern for complex models)
- basic-pkm model reference: `models/basic-pkm/` (1296 lines, 4 types — upgrade target)
- pyshacl version: 0.31.0 (SPARQLConstraint with `sh:severity sh:Warning` confirmed working)
- ManifestSchema: `backend/app/models/manifest.py` (supports `browserVisible`, `entailment_defaults`, nested icon contexts)
- Archive validator: `backend/app/models/validator.py` (subject-only IRI check, ALLOWED_EXTERNAL_NAMESPACES)
