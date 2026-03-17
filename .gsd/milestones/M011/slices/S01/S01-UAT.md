# S01: basic-pkm v2 — Task & Milestone Types — UAT

**Milestone:** M011
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 is offline validation only — no Docker, no runtime. All files are RDF (JSON-LD, Turtle) and YAML parsed by rdflib, pyshacl, and the existing manifest/loader/validator pipeline. Docker integration testing is explicitly deferred to S05.

## Preconditions

- Python backend virtualenv activated: `source backend/.venv/bin/activate`
- Working directory: `/home/james/Code/SemPKM`
- No Docker or triplestore required

## Smoke Test

Run the full acceptance suite:
```bash
cd /home/james/Code/SemPKM && backend/.venv/bin/python -m pytest backend/tests/test_basic_pkm_v2.py -v
```
**Expected:** 10 passed, 0 failed, completes in <1s.

## Test Cases

### 1. Manifest parses as v2.0.0 with 6 icons

1. Run: `python -c "import yaml; m=yaml.safe_load(open('models/basic-pkm/manifest.yaml')); print(m['version'], len(m['icons']))"`
2. **Expected:** Output is `2.0.0 6`
3. Verify icon entries include `Task` (icon: check-square, color: #10b981) and `Milestone` (icon: flag, color: #f59e0b)

### 2. Ontology has exactly 6 OWL classes

1. Run:
   ```python
   python -c "
   from rdflib import Graph, URIRef
   g = Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld')
   classes = [str(s) for s in g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef('http://www.w3.org/2002/07/owl#Class')) if 'basic-pkm' in str(s)]
   print(sorted([c.split(':')[-1] for c in classes]))
   "
   ```
2. **Expected:** 6 classes — Concept, Milestone, Note, Person, Project, Task

### 3. Shapes has 6 NodeShapes with correct targetClass

1. Run:
   ```python
   python -c "
   from rdflib import Graph, URIRef
   SH = 'http://www.w3.org/ns/shacl#'
   g = Graph(); g.parse('models/basic-pkm/shapes/basic-pkm.jsonld', format='json-ld')
   for s in g.subjects(URIRef(SH+'targetClass'), None):
       tc = list(g.objects(s, URIRef(SH+'targetClass')))[0]
       print(str(s).split(':')[-1], '->', str(tc).split(':')[-1])
   "
   ```
2. **Expected:** 6 shapes, each mapping to their corresponding class (TaskShape→Task, MilestoneShape→Milestone, etc.)

### 4. Views has 18 ViewSpecs and 6 SavedQueries

1. Run:
   ```python
   python -c "
   from rdflib import Graph, URIRef, Namespace
   SEMPKM = Namespace('urn:sempkm:vocab:')
   g = Graph(); g.parse('models/basic-pkm/views/basic-pkm.jsonld', format='json-ld')
   vs = list(g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), SEMPKM.ViewSpec))
   sq = list(g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), SEMPKM.SavedQuery))
   print(f'{len(vs)} ViewSpecs, {len(sq)} SavedQueries')
   "
   ```
2. **Expected:** `18 ViewSpecs, 6 SavedQueries`

### 5. Seed data has Tasks and Milestones with inverse pairs

1. Run:
   ```python
   python -c "
   from rdflib import Graph, URIRef, Namespace
   BPKM = Namespace('urn:sempkm:model:basic-pkm:')
   RDF = URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
   g = Graph(); g.parse('models/basic-pkm/seed/basic-pkm.jsonld', format='json-ld')
   tasks = list(g.subjects(RDF, BPKM.Task))
   milestones = list(g.subjects(RDF, BPKM.Milestone))
   print(f'{len(tasks)} Tasks, {len(milestones)} Milestones')
   # Check inverse: project has hasProjectTasks
   proj = BPKM['seed-project-sempkm']
   has_tasks = list(g.objects(proj, BPKM.hasProjectTasks))
   print(f'Project has {len(has_tasks)} hasProjectTasks links')
   "
   ```
2. **Expected:** `4 Tasks, 2 Milestones` and `Project has 2 hasProjectTasks links` (or more)

### 6. Rules file parses as valid Turtle with 3 NodeShapes

1. Run:
   ```python
   python -c "
   from rdflib import Graph, URIRef
   g = Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle')
   shapes = list(g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef('http://www.w3.org/ns/shacl#NodeShape')))
   print(f'{len(g)} triples, {len(shapes)} NodeShapes')
   for s in shapes: print(' ', str(s).split('/')[-1])
   "
   ```
2. **Expected:** `35 triples, 3 NodeShapes` — ProjectRelatedNoteRule, TaskProjectDenormRule, OverdueTaskValidationShape

### 7. Archive passes offline validation with zero errors

1. Run:
   ```bash
   backend/.venv/bin/python -m pytest backend/tests/test_basic_pkm_v2.py::test_archive_validates_zero_errors -v
   ```
2. **Expected:** PASSED

### 8. pyshacl fires overdue-task warning on past-due seed data

1. Run:
   ```python
   python -c "
   import pyshacl
   from rdflib import Graph
   d = Graph()
   d.parse('models/basic-pkm/seed/basic-pkm.jsonld', format='json-ld')
   d.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld')
   s = Graph()
   s.parse('models/basic-pkm/shapes/basic-pkm.jsonld', format='json-ld')
   s.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle')
   c, _, t = pyshacl.validate(d, shacl_graph=s, advanced=True, allow_warnings=True)
   print('Conforms:', c)
   print(t)
   "
   ```
2. **Expected:** `Conforms: True` with exactly 1 validation result: sh:Warning on `seed-task-fix-validation` with message containing "overdue"

### 9. pyshacl does NOT fire warning for done or future tasks

1. Run:
   ```bash
   backend/.venv/bin/python -m pytest backend/tests/test_basic_pkm_v2.py::test_pyshacl_no_warning_for_done_or_future_tasks -v
   ```
2. **Expected:** PASSED — done tasks (status "done") and future-dated tasks produce zero warnings

### 10. load_archive loads all 5 graph files

1. Run:
   ```bash
   backend/.venv/bin/python -m pytest backend/tests/test_basic_pkm_v2.py::test_archive_loads_all_graphs -v
   ```
2. **Expected:** PASSED — ontology, shapes, views, seed, and rules graphs all non-empty

## Edge Cases

### Overdue task with "cancelled" status should NOT trigger warning

1. Mentally verify: the SPARQLConstraint in `rules/basic-pkm.ttl` only flags tasks with status "todo", "in-progress", or "blocked"
2. A cancelled task with a past dueDate should be excluded from the warning
3. **Expected:** The SPARQL FILTER clause does not include "cancelled" in the status VALUES list

### Empty manifest icons list

1. Verify manifest has exactly 6 icon entries (one per type)
2. **Expected:** Each icon has type_iri, icon, color, and contexts (tree, tab, graph)

### Inverse property symmetry

1. Verify in ontology that each owl:inverseOf is declared bidirectionally (A inverseOf B AND B inverseOf A)
2. Run:
   ```python
   python -c "
   from rdflib import Graph, URIRef, OWL
   g = Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld')
   inv = list(g.subject_objects(OWL.inverseOf))
   print(f'{len(inv)} inverseOf triples')
   for s, o in inv: print(f'  {str(s).split(\":\")[-1]} <-> {str(o).split(\":\")[-1]}')
   "
   ```
3. **Expected:** 8+ inverseOf triples showing bidirectional declarations for all 4 property pairs

## Failure Signals

- **Test failures** — Any of the 10 tests failing indicates a regression in the archive files
- **rdflib parse errors** — JSON-LD or Turtle syntax errors surface immediately as Python tracebacks
- **pyshacl conforms=False with allow_warnings=True** — Would indicate a SHACL constraint error (not just warning), meaning shape definitions have bugs
- **Missing classes/shapes** — OWL class count ≠ 6 or NodeShape count ≠ 6 means a type definition is missing or duplicated
- **Triple count deviations** — Significant deviation from reference counts (197/815/144/179/35) indicates unintended changes

## Requirements Proved By This UAT

- MODEL-01 (partial) — basic-pkm v2.0 archive correctness, SHACL shapes, ViewSpecs, SavedQueries, seed data, inference rules, and overdue-task SPARQLConstraint all proven via offline validation. Docker integration remains for S05.

## Not Proven By This UAT

- Docker install via refresh_artifacts — requires running stack (S05)
- SHACL form rendering in browser — requires live frontend (S05)
- ViewSpec execution in browser — requires triplestore with loaded data (S05)
- Inference materialization of inverse properties at runtime — requires inference engine (S05)
- Validation warning display in lint panel — requires validation queue + UI (S05)
- SavedQuery execution in SPARQL console — requires triplestore (S05)
- E2E Playwright tests — deferred to S05 cross-model verification

## Notes for Tester

- The overdue task seed data has dueDate `2026-03-10`. If running these tests after that date (which is now the case), the overdue rule fires correctly. If somehow run before that date, Test Case 8 would fail.
- pyshacl deprecation warnings about ConjunctiveGraph are expected and harmless (rdflib migration to Dataset in progress).
- The `allow_warnings=True` flag in pyshacl is essential — without it, sh:Warning results cause conforms=False, which would make the test logic more complex.
