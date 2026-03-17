# S01: basic-pkm v2 — Task & Milestone Types

**Goal:** Upgrade basic-pkm from v1.3.0 to v2.0.0 by adding Task and Milestone types with full SHACL shapes, views, inference rules, validation rules, and seed data — all passing offline validation.
**Demo:** `pytest backend/tests/test_basic_pkm_v2.py` passes — proving parse_manifest + load_archive + validate_archive return zero errors, pyshacl fires overdue-task warning on seed data, and all 6 types (Project, Person, Note, Concept, Task, Milestone) have OWL classes, SHACL shapes, and ViewSpecs.

## Must-Haves

- Task class with taskStatus/priority/dueDate/effort enums and relationships to Person, Project, Milestone, Note, Concept
- Milestone class with milestoneStatus enum and relationships to Project and Tasks
- owl:inverseOf declarations for taskProject↔hasTasks, milestone↔hasTasks, milestoneProject↔hasMilestones, assignedTo↔hasAssignedTask
- SHACL shapes with PropertyGroups, editHelpText, and enum constraints for both types
- Inference rule: TaskProjectDenormRule (derive taskProject from milestone's project)
- Validation rule: OverdueTask SPARQLConstraint on separate NodeShape with sh:severity sh:Warning (D153)
- Table, Card, and Graph ViewSpecs for Task and Milestone
- Saved queries: "My Open Tasks", "Overdue Tasks", "Blocked Tasks"
- Seed data with example tasks and milestones, pre-populating both sides of inverseOf pairs (D154)
- Manifest bumped to v2.0.0 with Lucide icon entries for Task (check-square, emerald) and Milestone (flag, amber)
- All offline validation passes: parse_manifest + load_archive + validate_archive = zero errors
- pyshacl validates overdue-task SPARQLConstraint fires sh:Warning against seed data with past due dates

## Proof Level

- This slice proves: contract (offline validation of archive correctness + pyshacl rule firing)
- Real runtime required: no (offline rdflib + pyshacl only — Docker integration deferred to S05)
- Human/UAT required: no

## Verification

- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_basic_pkm_v2.py -v` — all tests pass
- Tests cover:
  - `parse_manifest()` succeeds on updated manifest.yaml (v2.0.0)
  - `load_archive()` loads all 6 files without errors
  - `validate_archive()` returns zero errors
  - Ontology has 6 OWL classes (Project, Person, Note, Concept, Task, Milestone)
  - Shapes has 6 NodeShapes with correct targetClass references
  - Views has ViewSpecs for all 6 types (18 total: 6 types × 3 renderers)
  - Seed data has Task and Milestone instances with correct types
  - Seed data has both sides of inverseOf pairs (e.g., Task.taskProject and Project.hasTasks)
  - pyshacl validates with advanced=True, fires sh:Warning for overdue task in seed data
  - pyshacl does NOT fire warning for tasks that are done or have future due dates
  - Rules file parses as valid Turtle with inference + validation rules

## Integration Closure

- Upstream surfaces consumed: existing `models/basic-pkm/` v1.3.0 files (all 6 replaced in-place), `backend/app/models/{manifest,loader,validator}.py` (called by tests, not modified)
- New wiring introduced in this slice: none — pure content, no platform code changes (D149)
- What remains before the milestone is truly usable end-to-end: S05 Docker integration tests + E2E Playwright tests

## Tasks

- [x] **T01: Add Task and Milestone classes to ontology and SHACL shapes** `est:1h`
  - Why: Defines the two new types with full OWL class hierarchy, datatype/object properties, owl:inverseOf declarations, and SHACL shapes with PropertyGroups, enums, and editHelpText. This is the schema foundation everything else depends on.
  - Files: `models/basic-pkm/ontology/basic-pkm.jsonld`, `models/basic-pkm/shapes/basic-pkm.jsonld`
  - Do: Add bpkm:Task (extends gist:Task) and bpkm:Milestone (extends gist:Event) classes with all properties from design doc §1. Add owl:inverseOf pairs. Add TaskShape (4 groups: Basic Info, Dates, Relationships, Metadata) and MilestoneShape (3 groups: Basic Info, Dates, Relationships) with enums, editHelpText, and sh:order. Update ProjectShape to include hasTasks and hasMilestones properties in Relationships group.
  - Verify: `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld'); print(f'{len(g)} triples')"` succeeds. Same for shapes.
  - Done when: ontology has 6 OWL classes, shapes has 6 NodeShapes, all owl:inverseOf pairs declared, rdflib parses both files without error.

- [x] **T02: Add inference and validation rules for Tasks** `est:45m`
  - Why: Implements TaskProjectDenormRule (SPARQL inference) and OverdueTaskValidation (SPARQL constraint). The overdue-task rule is the highest-risk item in this slice — it requires sh:sparql SPARQLConstraint with date arithmetic and correct sh:severity placement (D153).
  - Files: `models/basic-pkm/rules/basic-pkm.ttl`
  - Do: Add TaskProjectDenormRule (derive bpkm:taskProject from milestone's project chain, same pattern as PPV's ProjectPillarDenormRule). Add OverdueTaskValidation as a SEPARATE NodeShape (D153) with sh:targetClass bpkm:Task, sh:severity sh:Warning, and sh:sparql constraint using `xsd:date` comparison with `BIND(NOW() AS ?now)` and `FILTER(?dueDate < ?now)` for tasks where status is "todo" or "in-progress". Add owl:inverseOf inference rules for taskProject↔hasTasks and milestoneProject↔hasMilestones.
  - Verify: `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(f'{len(g)} triples')"` succeeds.
  - Done when: rules file parses as valid Turtle, contains inference rule for task project denorm, contains validation shape with sh:sparql + sh:severity sh:Warning for overdue tasks, separate from inference shapes.

- [x] **T03: Add views, seed data, and update manifest to v2.0.0** `est:1h`
  - Why: Completes the archive with ViewSpecs for browsing Tasks/Milestones, seed data demonstrating the types (including an overdue task for validation testing), and manifest version bump with icon entries.
  - Files: `models/basic-pkm/views/basic-pkm.jsonld`, `models/basic-pkm/seed/basic-pkm.jsonld`, `models/basic-pkm/manifest.yaml`
  - Do: Add 6 ViewSpecs (Task table/card/graph, Milestone table/card/graph) following existing pattern. Add 3 SavedQueries ("My Open Tasks", "Overdue Tasks", "Blocked Tasks"). Add seed tasks and milestones per design doc §1 with both sides of inverseOf pre-populated (D154). Include one task with dueDate in the past and status "todo" (triggers overdue validation). Bump manifest version to "2.0.0", add Task and Milestone icon entries with tree/tab/graph contexts, add entailment_defaults.
  - Verify: `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/views/basic-pkm.jsonld', format='json-ld'); print(f'{len(g)} triples')"` succeeds. `python -c "import yaml; m=yaml.safe_load(open('models/basic-pkm/manifest.yaml')); assert m['version']=='2.0.0'; print('OK')"`.
  - Done when: Views has 18 ViewSpecs + 3 SavedQueries, seed has Task and Milestone instances with inverse pairs, manifest is v2.0.0 with 6 icon entries.

- [x] **T04: Write offline validation test proving archive correctness and overdue-task rule** `est:45m`
  - Why: This is the slice's acceptance test — proving the archive passes parse_manifest + load_archive + validate_archive with zero errors, and that the overdue-task SPARQLConstraint fires sh:Warning via pyshacl. Retires the three key risks from the roadmap.
  - Files: `backend/tests/test_basic_pkm_v2.py`
  - Do: Write pytest test file using the existing `parse_manifest`, `load_archive`, `validate_archive` functions from `backend/app/models/`. Test manifest parsing (version 2.0.0, 6 icons). Test archive loading (all graphs non-empty). Test validation (zero errors). Count OWL classes in ontology (expect 6). Count NodeShapes in shapes (expect 6+). Count ViewSpecs in views (expect 18). Count SavedQueries (expect 6: 3 existing + 3 new). Test seed data has Task and Milestone instances. Test pyshacl validation: load data graph from seed, shapes graph from shapes + rules, run pyshacl.validate(advanced=True), assert conforms=False (because of warnings), parse results graph for sh:Warning about overdue task. Test that done tasks and future-dated tasks do NOT trigger warning.
  - Verify: `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_basic_pkm_v2.py -v`
  - Done when: All tests pass, pyshacl fires overdue warning on past-due seed task, archive has zero validation errors.

## Observability / Diagnostics

- **Ontology triple count:** `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld'); print(len(g))"` — expect >60 triples after T01
- **Shapes triple count:** `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/shapes/basic-pkm.jsonld', format='json-ld'); print(len(g))"` — expect >250 triples after T01
- **OWL class count:** `python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld'); print(len([s for s in g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef('http://www.w3.org/2002/07/owl#Class')) if 'basic-pkm' in str(s)]))"` — expect 6
- **NodeShape count:** `python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/shapes/basic-pkm.jsonld', format='json-ld'); print(len(list(g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef('http://www.w3.org/ns/shacl#NodeShape')))))"` — expect 6
- **Archive validation:** `python -m pytest backend/tests/test_basic_pkm_v2.py -v` — all tests pass (after T04)
- **Failure visibility:** rdflib parse errors surface immediately via Python tracebacks; pyshacl validation results include full violation reports with source shapes and focus nodes
- **No secrets/redaction needed:** all files are schema definitions (JSON-LD, Turtle), no runtime credentials

## Files Likely Touched

- `models/basic-pkm/manifest.yaml`
- `models/basic-pkm/ontology/basic-pkm.jsonld`
- `models/basic-pkm/shapes/basic-pkm.jsonld`
- `models/basic-pkm/views/basic-pkm.jsonld`
- `models/basic-pkm/seed/basic-pkm.jsonld`
- `models/basic-pkm/rules/basic-pkm.ttl`
- `backend/tests/test_basic_pkm_v2.py`
