# S03: Zettelkasten+ Model — UAT

**Milestone:** M011
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S03 delivers a pure-content model archive (6 files, no platform code changes). All verification is offline parsing and validation. Docker integration is deferred to S05.

## Preconditions

- Python backend venv exists at `backend/.venv/`
- pyshacl, rdflib installed in venv
- Model files exist at `models/zettelkasten/` (6 files: manifest.yaml, ontology/*.jsonld, shapes/*.jsonld, views/*.jsonld, rules/*.ttl, seed/*.jsonld)

## Smoke Test

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
from app.models.loader import load_archive
from app.models.validator import validate_archive
m = parse_manifest(Path('../models/zettelkasten'))
a = load_archive(Path('../models/zettelkasten'), m)
r = validate_archive(a)
print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}')
assert r.is_valid and len(r.errors) == 0
print('SMOKE TEST PASSED')
"
```

Expected: `Valid: True, Errors: 0` followed by `SMOKE TEST PASSED`

## Test Cases

### 1. All 6 archive files parse without errors

```bash
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
```

**Expected:** All 5 files parse with triple counts: ontology ≥100, shapes ≥300, views ≥60, seed ≥100, rules ≥20.

### 2. Manifest validates with 5 types and correct icon entries

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
m = parse_manifest(Path('../models/zettelkasten'))
print(f'modelId: {m.modelId}')
print(f'namespace: {m.namespace}')
print(f'types: {len(m.icons)}')
for icon in m.icons:
    contexts = [c.context for c in icon.sizes]
    print(f'  {icon.typeLocalName}: {icon.icon} contexts={contexts}')
assert m.modelId == 'zettelkasten'
assert m.namespace == 'urn:sempkm:model:zettelkasten:'
assert len(m.icons) == 5
print('MANIFEST TEST PASSED')
"
```

**Expected:** 5 icon entries (FleetingNote/zap, Source/book-open, LiteratureNote/quote, PermanentNote/gem, StructureNote/network) each with tree/tab/graph contexts.

### 3. Full pipeline validation returns 0 errors

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
assert r.is_valid and len(r.errors) == 0
print('PIPELINE TEST PASSED')
"
```

**Expected:** Valid: True, Errors: 0

### 4. SHACL-AF validation fires all 3 rules at correct severities

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
print(text)
# Count violations by severity
warnings = text.count('sh:Warning')
infos = text.count('sh:Info')
violations = text.count('sh:Violation')
print(f'Warnings: {warnings}, Infos: {infos}, Violations: {violations}')
assert not conforms
assert warnings == 2
assert infos == 1
assert violations == 0
print('SHACL-AF RULES TEST PASSED')
"
```

**Expected:**
- conforms=False
- 2 Warning-level violations (UnprocessedFleeting + OrphanPermanent)
- 1 Info-level violation (UnsourcedPermanent)
- 0 Violation-level results
- Focus nodes: `seed-fleeting-unprocessed` (Warning), `seed-perm-confirmation-bias` (Warning + Info)

### 5. Ontology has 5 OWL classes with correct gist alignment

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from rdflib import Graph, RDF, RDFS, OWL
g = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')
classes = [str(s) for s in g.subjects(RDF.type, OWL.Class)]
print(f'OWL classes: {len(classes)}')
for c in sorted(classes): print(f'  {c}')
assert len(classes) == 5
expected = ['FleetingNote', 'Source', 'LiteratureNote', 'PermanentNote', 'StructureNote']
for name in expected:
    assert any(name in c for c in classes), f'Missing class: {name}'
print('ONTOLOGY CLASSES TEST PASSED')
"
```

**Expected:** 5 OWL classes with names matching FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote.

### 6. Shapes has 5 target classes matching ontology

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from rdflib import Graph, URIRef
SH = 'http://www.w3.org/ns/shacl#'
g = Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld')
targets = set(str(o) for s,p,o in g if str(p) == SH + 'targetClass')
print(f'Target classes: {len(targets)}')
for t in sorted(targets): print(f'  {t}')
assert len(targets) == 5
expected = ['FleetingNote', 'Source', 'LiteratureNote', 'PermanentNote', 'StructureNote']
for name in expected:
    assert any(name in t for t in targets), f'Missing target: {name}'
print('SHAPES TARGET TEST PASSED')
"
```

**Expected:** 5 target classes matching the 5 ontology classes.

### 7. Seed data has 12 objects with correct type distribution

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from rdflib import Graph, RDF
ZK = 'urn:sempkm:model:zettelkasten:'
g = Graph().parse('../models/zettelkasten/seed/zettelkasten.jsonld', format='json-ld')
types = {}
for s, p, o in g.triples((None, RDF.type, None)):
    t = str(o).replace(ZK, '')
    types[t] = types.get(t, 0) + 1
print('Seed objects by type:')
for t, c in sorted(types.items()): print(f'  {t}: {c}')
assert types.get('Source', 0) == 3
assert types.get('FleetingNote', 0) == 2
assert types.get('LiteratureNote', 0) == 3
assert types.get('PermanentNote', 0) == 3
assert types.get('StructureNote', 0) == 1
print('SEED DATA TEST PASSED')
"
```

**Expected:** Source:3, FleetingNote:2, LiteratureNote:3, PermanentNote:3, StructureNote:1 = 12 total.

### 8. InverseOf pairs are declared on both sides

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from rdflib import Graph, OWL
g = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')
pairs = [(str(s).split(':')[-1], str(o).split(':')[-1]) for s,p,o in g.triples((None, OWL.inverseOf, None))]
print(f'InverseOf declarations: {len(pairs)}')
for a, b in sorted(pairs): print(f'  {a} ↔ {b}')
assert len(pairs) == 6, f'Expected 6 (3 pairs × 2 directions), got {len(pairs)}'
print('INVERSEOF TEST PASSED')
"
```

**Expected:** 6 inverseOf declarations (3 pairs, each declared in both directions).

## Edge Cases

### Invalid model path produces structured error

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
try:
    parse_manifest(Path('/tmp/nonexistent-model'))
    print('ERROR: should have raised')
except (ValueError, FileNotFoundError) as e:
    print(f'Structured error: {type(e).__name__}: {e}')
    assert 'manifest.yaml' in str(e) or 'not found' in str(e)
    print('ERROR HANDLING TEST PASSED')
"
```

**Expected:** ValueError or FileNotFoundError with message mentioning manifest.yaml.

### Namespace compliance — no subjects outside model namespace

```bash
cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
from rdflib import Graph
g = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')
bad = [str(s) for s in set(g.subjects()) if str(s).startswith('urn:sempkm:') and not str(s).startswith('urn:sempkm:model:zettelkasten:')]
assert len(bad) == 0, f'Namespace violations: {bad}'
print('NAMESPACE COMPLIANCE TEST PASSED')
"
```

**Expected:** Zero namespace violations.

## Failure Signals

- `validate_archive()` returns errors > 0 → archive structure or reference integrity issue
- pyshacl `conforms=True` → validation rules not firing (missing trigger data or broken SPARQL)
- pyshacl shows `sh:Violation` level results → spurious SHACL datatype mismatch (likely xsd:date vs xsd:dateTime in seed data)
- Triple count below threshold → missing definitions in that file
- `parse_manifest()` raises ValueError for valid model path → manifest.yaml syntax error

## Requirements Proved By This UAT

- MODEL-03 (partial) — Zettelkasten model archive passes offline validation with 5 types, provenance chain query, argumentation links, and 3 validation rules at correct severities. Contract-level proof only.

## Not Proven By This UAT

- Docker install of zettelkasten model (S05)
- SHACL form rendering for all 5 types (S05)
- ViewSpec rendering with seed data (S05)
- SHACL-AF inference materializing inverse properties (S05)
- Provenance Chain CONSTRUCT query rendering in UI (S05)
- Cross-model coexistence with basic-pkm, CRM, and research models (S05)

## Notes for Tester

- All test commands are copy-pasteable — run from repo root or as shown with `cd` prefix
- The pyshacl test (Test Case 4) takes ~3-5 seconds due to SPARQL evaluation
- The Provenance Chain SavedQuery uses CONSTRUCT (not SELECT) — if the saved query UI only renders SELECT results, this will need frontend handling in S05
- `sh:in` enum values are plain strings — verify dropdown rendering when Docker testing in S05
