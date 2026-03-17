---
id: T01
parent: S01
milestone: M011
provides:
  - OWL classes for Task and Milestone in basic-pkm ontology
  - SHACL NodeShapes with PropertyGroups, enums, and editHelpText for Task and Milestone
  - Updated ProjectShape and PersonShape with inverse relationship properties
  - owl:inverseOf declarations for 4 property pairs
key_files:
  - models/basic-pkm/ontology/basic-pkm.jsonld
  - models/basic-pkm/shapes/basic-pkm.jsonld
key_decisions:
  - Removed rdfs:domain from bpkm:priority and bpkm:body to allow reuse across Project and Task (was Project-only and Note-only)
  - completedDate left domain-free since both Task and Milestone use it
  - PersonShape updated with hasAssignedTask in Relationships group for inverse visibility
patterns_established:
  - Inverse property pairs declared symmetrically on both sides (owl:inverseOf on both properties)
  - PropertyGroup naming convention: {Type}{GroupName}Group (e.g. TaskBasicInfoGroup)
  - sh:order is sequential within each shape (not within each group) for consistent field ordering
observability_surfaces:
  - rdflib triple count on ontology (197 triples, was ~40)
  - rdflib triple count on shapes (815 triples, was ~180)
  - OWL class count check: expect exactly 6
  - NodeShape count check: expect exactly 6
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Add Task and Milestone classes to ontology and SHACL shapes

**Defined Task and Milestone OWL classes, 15+ properties with inverse pairs, and full SHACL shapes with 4 PropertyGroups each, enum constraints, and editHelpText on all fields.**

## What Happened

Added two new OWL classes to the basic-pkm ontology:
- `bpkm:Task` (extends `gist:Task`) — the atomic unit of work with 9 datatype properties (taskStatus, dueDate, completedDate, effort, externalId, externalUrl, externalProvider, lastSyncedAt, syncDirection) and 6 object properties (assignedTo, taskProject, milestone, dependsOn, relatedNote, relatedConcept)
- `bpkm:Milestone` (extends `gist:Event`) — a task grouping with 2 datatype properties (milestoneStatus, targetDate, reusing completedDate) and 2 object properties (milestoneProject, hasTasks)

Declared 4 owl:inverseOf pairs: taskProject↔hasProjectTasks, milestone↔hasTasks, milestoneProject↔hasMilestones, assignedTo↔hasAssignedTask. Added inverse-side properties to Project (hasProjectTasks, hasMilestones) and Person (hasAssignedTask).

Broadened `bpkm:priority` (removed Project-only domain) and `bpkm:body` (removed Note-only domain) so both can be reused on Task without domain conflicts.

Built SHACL shapes:
- **TaskShape** — 21 properties across 4 groups (Basic Info, Dates, Relationships, Metadata). Enums on taskStatus (5 values), priority (4 values), effort (5 values), externalProvider (7 values). All fields have editHelpText.
- **MilestoneShape** — 10 properties across 4 groups (Basic Info, Dates, Relationships, Metadata). Enum on milestoneStatus (4 values). All fields have editHelpText.
- **ProjectShape** — updated with hasProjectTasks and hasMilestones in Relationships group
- **PersonShape** — updated with hasAssignedTask in Relationships group

## Verification

- `rdflib parse ontology` → 197 triples ✓ (>60 required)
- `rdflib parse shapes` → 815 triples ✓ (>250 required)
- OWL class count = 6 ✓ (Project, Person, Note, Concept, Task, Milestone)
- NodeShape count = 6 ✓ (one per class)
- PropertyGroup count = 22 ✓ (4 existing types × varying groups + Task 4 + Milestone 4)
- owl:inverseOf pairs = 4 bidirectional pairs (9 triples) ✓
- Slice-level verification: test file `backend/tests/test_basic_pkm_v2.py` not yet created (T04)

## Diagnostics

Inspect schema state with:
```bash
backend/.venv/bin/python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/ontology/basic-pkm.jsonld', format='json-ld'); print(len(g))"
# → 197

backend/.venv/bin/python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/shapes/basic-pkm.jsonld', format='json-ld'); print(len(g))"
# → 815
```

## Deviations

- Plan said MilestoneShape has "3 groups" but task steps said 4. Used 4 groups (Basic Info, Dates, Relationships, Metadata) matching the full spec in the task steps and design doc.
- Added `hasAssignedTask` to PersonShape (not explicitly in plan but required for inverse pair visibility and consistency with ProjectShape updates).
- sh:order is sequential within each shape (1-21 for TaskShape) rather than restarting within each group — matching the existing pattern in ProjectShape/PersonShape.

## Known Issues

None.

## Files Created/Modified

- `models/basic-pkm/ontology/basic-pkm.jsonld` — Added Task and Milestone classes, 15+ properties, 4 inverse pairs, broadened priority/body domains
- `models/basic-pkm/shapes/basic-pkm.jsonld` — Added TaskShape (21 props, 4 groups), MilestoneShape (10 props, 4 groups), updated ProjectShape (+2 props) and PersonShape (+1 prop)
