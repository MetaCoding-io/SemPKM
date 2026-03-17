# S03: Zettelkasten+ Model

**Goal:** Deliver a complete `zettelkasten` model archive (6 files under `models/zettelkasten/`) with 5 types (FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote) that passes offline validation, fires 3 SHACL-AF validation warnings (unprocessed fleeting note, orphan permanent note, unsourced permanent note), and models the full provenance chain with argumentation links.

**Demo:** Running `parse_manifest()` + `load_archive()` + `validate_archive()` on `models/zettelkasten/` returns zero errors. Running pyshacl with `advanced=True` against seed data produces 2 Warning-level violations (unprocessed, orphan) and 1 Info-level violation (unsourced).

## Must-Haves

- `models/zettelkasten/manifest.yaml` — valid ManifestSchema with 5 icon entries (tree/tab/graph contexts), `entailment_defaults` with `owl_inverseOf: true` and `shacl_rules: true`
- `models/zettelkasten/ontology/zettelkasten.jsonld` — 5 OWL classes aligned to gist, ~25 properties with 3 `owl:inverseOf` pairs, 4 argumentation link properties, 1 symmetric property (`zk:relatedStructure`)
- `models/zettelkasten/shapes/zettelkasten.jsonld` — 5 SHACL NodeShapes with PropertyGroups, `sh:in` enums using `@list`, `sempkm:editHelpText`; uses `"sempkm": "urn:sempkm:"`
- `models/zettelkasten/views/zettelkasten.jsonld` — 5 ViewSpecs + 4 SavedQueries; uses `"sempkm": "urn:sempkm:vocab:"`
- `models/zettelkasten/rules/zettelkasten.ttl` — 3 validation SPARQLConstraints on separate NodeShapes per D153 (Warning: unprocessed fleeting, orphan permanent; Info: unsourced permanent)
- `models/zettelkasten/seed/zettelkasten.jsonld` — ~12 seed objects forming a complete provenance chain (Source → LiteratureNote → PermanentNote → StructureNote), both sides of inverseOf pre-populated per D154, trigger data for all 3 validation rules
- Full pipeline `parse_manifest()` + `load_archive()` + `validate_archive()` returns zero errors
- pyshacl validate fires all 3 validation rules at correct severities

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
    ('../models/zettelkasten/ontology/zettelkasten.jsonld', 'json-ld'),
    ('../models/zettelkasten/shapes/zettelkasten.jsonld', 'json-ld'),
    ('../models/zettelkasten/views/zettelkasten.jsonld', 'json-ld'),
    ('../models/zettelkasten/seed/zettelkasten.jsonld', 'json-ld'),
    ('../models/zettelkasten/rules/zettelkasten.ttl', 'turtle'),
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

m = parse_manifest(Path('../models/zettelkasten'))
a = load_archive(Path('../models/zettelkasten'), m)
r = validate_archive(a)
print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}, Warnings: {len(r.warnings)}')
for e in r.errors: print(f'  E: {e.file}: {e.message}')
for w in r.warnings: print(f'  W: {w.file}: {w.message}')
assert r.is_valid and len(r.errors) == 0, 'Archive validation must pass with 0 errors'
"

# Step 3: SHACL-AF validation (all 3 rules fire)
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
assert not conforms, 'Expected validation violations (conforms should be False)'
assert 'Warning' in text or 'sh:Warning' in text, 'Expected Warning-level violations'
assert 'unprocessed' in text.lower() or 'fleeting' in text.lower(), 'Expected unprocessed fleeting note violation'
assert 'isolated' in text.lower() or 'orphan' in text.lower(), 'Expected orphan permanent note violation'
"

# Step 4: Diagnostic — structured error reporting
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
try:
    parse_manifest(Path('/tmp/nonexistent-model'))
    print('ERROR: should have raised')
except (ValueError, FileNotFoundError) as e:
    print(f'Structured error (expected): {type(e).__name__}: {e}')
"

# Step 5: Triple count sanity
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

## Observability / Diagnostics

- **Manifest parse errors:** `parse_manifest(Path('../models/zettelkasten'))` raises `ValueError` with structured message on failure.
- **Archive validation pipeline:** `validate_archive()` returns `ValidationResult` with `.is_valid`, `.errors[]`, `.warnings[]` — the primary diagnostic surface.
- **SHACL-AF rule firing:** `pyshacl.validate(..., advanced=True)` returns `(conforms, results_graph, text)` — text includes focus node, severity, source shape, and message per violation.
- **Triple count signals:** Ontology ≥100, Shapes ≥300, Views ≥60, Rules ≥20, Seed ≥100 — counts below these thresholds indicate missing definitions.

## Integration Closure

- Upstream surfaces consumed: CRM model files (structural template only — no runtime dependency)
- New wiring introduced in this slice: none (pure content, no platform code changes per D149)
- What remains before the milestone is truly usable end-to-end: S05 Docker install + form rendering + view rendering + E2E tests

## Tasks

- [ ] **T01: Author Zettelkasten manifest and ontology** `est:45m`
  - Why: Establishes model identity, namespace, icon manifest, and all OWL class+property definitions that shapes, views, rules, and seed depend on.
  - Files: `models/zettelkasten/manifest.yaml`, `models/zettelkasten/ontology/zettelkasten.jsonld`
  - Do: Create manifest with modelId `zettelkasten`, namespace `urn:sempkm:model:zk:`, 5 icon entries (zap/book-open/quote/gem/network) with tree/tab/graph contexts, entailment_defaults matching CRM. Create ontology with 5 OWL classes (FleetingNote→gist:FormattedContent, Source→gist:Content, LiteratureNote→gist:FormattedContent, PermanentNote→gist:FormattedContent, StructureNote→gist:FormattedContent), ~25 properties including 3 `owl:inverseOf` pairs (derivedFrom↔hasLiteratureNote, developedInto↔developedFrom, includes↔includedInStructure), 4 argumentation links (supports/contradicts/followsFrom/relatedTo), `zk:relatedStructure` as `owl:SymmetricProperty`, `zk:processedInto` (one-directional). Include `bpkm` prefix for tag reuse. Do NOT declare `rdfs:domain` on shared properties like `zk:body` (same broadening as D155).
  - Verify: `parse_manifest()` succeeds. Ontology parses to ≥100 triples. Subject namespace check clean.
  - Done when: Both files exist, parse cleanly, and manifest validates via Pydantic schema.

- [ ] **T02: Author Zettelkasten shapes and views** `est:1h`
  - Why: Shapes drive SHACL form generation with property groups, enums, and helptext. Views define 5 ViewSpecs and 4 SavedQueries for browsing Zettelkasten data.
  - Files: `models/zettelkasten/shapes/zettelkasten.jsonld`, `models/zettelkasten/views/zettelkasten.jsonld`
  - Do: Create shapes with 5 NodeShapes and PropertyGroups per type. Use `"sempkm": "urn:sempkm:"` prefix. `sh:in` enums using `{"@list": [...]}` for sourceType (8 values) and purpose (5 values). `sempkm:editHelpText` on key fields. Create views with 5 ViewSpecs (fleeting-table, source-table, litnote-card, zettelkasten-graph, structure-table) + 4 SavedQueries (Unprocessed Fleeting Notes, Isolated Permanent Notes, Contradiction Map, Provenance Chain). Use `"sempkm": "urn:sempkm:vocab:"` prefix. Full IRIs in all SPARQL queries. Provenance Chain uses CONSTRUCT query for Source→LitNote→PermanentNote path.
  - Verify: Both files parse with rdflib. Shapes has 5 `sh:targetClass` triples. Views has 5+ ViewSpec subjects plus 4 SavedQuery subjects.
  - Done when: Both files parse cleanly, shapes reference all 5 ontology classes, views cover all types.

- [ ] **T03: Author Zettelkasten rules, seed data, and run full pipeline validation** `est:1h`
  - Why: Rules define the 3 validation constraints. Seed data provides the provenance chain scenario with trigger data. Full pipeline proves the archive is correct end-to-end.
  - Files: `models/zettelkasten/rules/zettelkasten.ttl`, `models/zettelkasten/seed/zettelkasten.jsonld`
  - Do: Create rules in Turtle with 3 separate NodeShapes per D153: (1) UnprocessedFleetingValidation — `sh:severity sh:Warning`, fires when FleetingNote has no `processedInto` (NOT EXISTS, no date arithmetic per K001); (2) OrphanPermanentNoteValidation — `sh:severity sh:Warning`, fires when PermanentNote has no supports/contradicts/followsFrom/includedInStructure (use separate FILTER NOT EXISTS blocks, NOT property paths per research pitfall); (3) UnsourcedPermanentNoteValidation — `sh:severity sh:Info`, fires when PermanentNote has no `developedFrom`. Create seed data with ~12 objects: 3 Sources, 2 FleetingNotes (1 unprocessed with old dcterms:created), 3 LiteratureNotes, 3 PermanentNotes (1 orphaned, 1 unsourced), 1 StructureNote. Both sides of inverseOf pre-populated per D154. Run all 5 verification steps from the Verification section.
  - Verify: All 5 verification commands pass. `validate_archive()` returns 0 errors. pyshacl returns `conforms=False` with violations for all 3 rules at correct severities.
  - Done when: Full pipeline passes with 0 errors, pyshacl fires all 3 validation rules.

## Files Likely Touched

- `models/zettelkasten/manifest.yaml`
- `models/zettelkasten/ontology/zettelkasten.jsonld`
- `models/zettelkasten/shapes/zettelkasten.jsonld`
- `models/zettelkasten/views/zettelkasten.jsonld`
- `models/zettelkasten/rules/zettelkasten.ttl`
- `models/zettelkasten/seed/zettelkasten.jsonld`
