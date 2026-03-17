---
estimated_steps: 8
estimated_files: 2
---

# T01: Add Task and Milestone classes to ontology and SHACL shapes

**Slice:** S01 — basic-pkm v2 — Task & Milestone Types
**Milestone:** M011

## Description

Define the two new types (Task and Milestone) in the basic-pkm ontology and SHACL shapes. This is the schema foundation that T02 (rules), T03 (views/seed), and T04 (tests) all depend on. The ontology defines OWL classes, datatype properties, object properties, and owl:inverseOf declarations. The shapes define SHACL NodeShapes with PropertyGroups, enum constraints, editHelpText, and field ordering.

Per D149: this is pure content work — no platform code changes. Per D152: only Task and Milestone (no Event type in v2.0).

## Steps

1. **Edit `models/basic-pkm/ontology/basic-pkm.jsonld`** — Add to the existing `@graph` array:
   - `bpkm:Task` class (`rdfs:subClassOf gist:Task`) with label "Task" and comment
   - `bpkm:Milestone` class (`rdfs:subClassOf gist:Event`) with label "Milestone" and comment
   - Datatype properties for Task: `bpkm:taskStatus`, `bpkm:dueDate`, `bpkm:completedDate`, `bpkm:effort`, `bpkm:externalId`, `bpkm:externalUrl`, `bpkm:externalProvider`, `bpkm:lastSyncedAt`, `bpkm:syncDirection`
   - Datatype properties for Milestone: `bpkm:milestoneStatus`, `bpkm:targetDate` (reuse `bpkm:completedDate`)
   - Object properties for Task: `bpkm:assignedTo` (→Person), `bpkm:taskProject` (→Project), `bpkm:milestone` (→Milestone), `bpkm:dependsOn` (→Task), `bpkm:relatedNote` (→Note), `bpkm:relatedConcept` (→Concept)
   - Object properties for Milestone: `bpkm:milestoneProject` (→Project), `bpkm:hasTasks` (→Task, inverse of `bpkm:milestone`)
   - Object properties on Project: `bpkm:hasProjectTasks` (→Task, inverse of `bpkm:taskProject`), `bpkm:hasMilestones` (→Milestone, inverse of `bpkm:milestoneProject`)
   - Object property on Person: `bpkm:hasAssignedTask` (→Task, inverse of `bpkm:assignedTo`)
   - owl:inverseOf declarations: `bpkm:taskProject` ↔ `bpkm:hasProjectTasks`, `bpkm:milestone` ↔ `bpkm:hasTasks`, `bpkm:milestoneProject` ↔ `bpkm:hasMilestones`, `bpkm:assignedTo` ↔ `bpkm:hasAssignedTask`
   - Note: Keep `bpkm:priority` domain broad (remove the Project-only domain or leave it unscoped) since both Project and Task use it. Keep `bpkm:body` domain broad too since Task also has a body field.

2. **Edit `models/basic-pkm/shapes/basic-pkm.jsonld`** — Add to the existing `@graph` array:
   - **TaskShape** PropertyGroups: `bpkm:TaskBasicInfoGroup` (order 1), `bpkm:TaskDatesGroup` (order 2), `bpkm:TaskRelationshipsGroup` (order 3), `bpkm:TaskMetadataGroup` (order 4)
   - **TaskShape** NodeShape targeting `bpkm:Task` with properties:
     - Basic Info: title (required), description, taskStatus (sh:in [todo, in-progress, done, blocked, cancelled], default "todo"), priority (sh:in [low, medium, high, critical], default "medium"), effort (sh:in [trivial, small, medium, large, epic])
     - Dates: dueDate (xsd:date), completedDate (xsd:date)
     - Relationships: assignedTo (Person), taskProject (Project), milestone (Milestone), dependsOn (Task, multi-value), relatedNote (Note, multi-value), relatedConcept (Concept, multi-value)
     - Metadata: tags, body (markdown), externalProvider, externalId, externalUrl, lastSyncedAt, created, modified
   - **MilestoneShape** PropertyGroups: `bpkm:MilestoneBasicInfoGroup` (order 1), `bpkm:MilestoneDatesGroup` (order 2), `bpkm:MilestoneRelationshipsGroup` (order 3), `bpkm:MilestoneMetadataGroup` (order 4)
   - **MilestoneShape** NodeShape targeting `bpkm:Milestone` with properties:
     - Basic Info: title (required), description, milestoneStatus (sh:in [planned, active, completed, cancelled], default "planned")
     - Dates: targetDate (xsd:date), completedDate (xsd:date)
     - Relationships: milestoneProject (Project), hasTasks (Task, multi-value — display-only via inverse)
     - Metadata: tags, created, modified
   - **Update ProjectShape**: add `bpkm:hasProjectTasks` (Tasks, class bpkm:Task, multi-value) and `bpkm:hasMilestones` (Milestones, class bpkm:Milestone, multi-value) in ProjectRelationshipsGroup
   - All fields must have editHelpText with guidance text per design doc §1
   - All sh:order values must be sequential within each group

3. **Verify**: Run rdflib parse on both files:
   ```bash
   cd /home/james/Code/SemPKM
   python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld'); print(f'Ontology: {len(g)} triples')"
   python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/shapes/basic-pkm.jsonld', format='json-ld'); print(f'Shapes: {len(g)} triples')"
   ```

## Must-Haves

- [ ] bpkm:Task class extends gist:Task with rdfs:label "Task"
- [ ] bpkm:Milestone class extends gist:Event with rdfs:label "Milestone"
- [ ] All datatype and object properties from design doc §1 declared with rdfs:label, rdfs:domain, rdfs:range
- [ ] owl:inverseOf pairs: taskProject↔hasProjectTasks, milestone↔hasTasks, milestoneProject↔hasMilestones, assignedTo↔hasAssignedTask
- [ ] TaskShape with 4 PropertyGroups, enum constraints (taskStatus, priority, effort), and editHelpText on all fields
- [ ] MilestoneShape with 4 PropertyGroups, enum constraint (milestoneStatus), and editHelpText
- [ ] ProjectShape updated with hasProjectTasks and hasMilestones in Relationships group
- [ ] Both files parse without error via rdflib

## Verification

- `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld'); print(f'{len(g)} triples')"` succeeds with >60 triples (was ~40)
- `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/shapes/basic-pkm.jsonld', format='json-ld'); print(f'{len(g)} triples')"` succeeds with >250 triples (was ~180)
- `python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld'); OWL_CLASS=URIRef('http://www.w3.org/2002/07/owl#Class'); classes=[str(s) for s in g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), OWL_CLASS) if 'basic-pkm' in str(s)]; print(f'Classes: {len(classes)}'); assert len(classes)==6, classes"` — confirms 6 classes

## Observability Impact

- **What changes:** Ontology gains 2 new OWL classes and ~15 new properties; shapes gain 2 new NodeShapes and 8 PropertyGroups. Triple counts increase significantly.
- **Inspection surface:** Use rdflib triple count commands (see Verification section) to confirm schema expansion. `OWL_CLASS` count should be exactly 6 after this task.
- **Failure visibility:** JSON-LD parse errors surface as rdflib exceptions with line/character context. Missing `@id` references or malformed `@list` arrays produce specific JSON-LD expansion errors.
- **No runtime signals:** This is pure schema content — no logs, endpoints, or processes affected.

## Inputs

- `models/basic-pkm/ontology/basic-pkm.jsonld` — existing v1.3 ontology with 4 classes (Project, Person, Note, Concept)
- `models/basic-pkm/shapes/basic-pkm.jsonld` — existing v1.3 shapes with 4 NodeShapes
- Design doc: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` §1 — complete property tables and shape group definitions (already summarized in task steps above)

## Expected Output

- `models/basic-pkm/ontology/basic-pkm.jsonld` — expanded with 6 OWL classes, ~15 new properties, 4 owl:inverseOf pairs
- `models/basic-pkm/shapes/basic-pkm.jsonld` — expanded with 6 NodeShapes (4 existing + 2 new), updated ProjectShape, all with PropertyGroups and editHelpText
