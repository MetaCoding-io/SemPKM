---
id: T03
parent: S01
milestone: M011
provides:
  - 18 ViewSpecs (6 types × 3 renderers) for browsing all basic-pkm types
  - 6 SavedQueries (3 existing + 3 new task-focused queries)
  - 6 seed objects (4 Tasks + 2 Milestones) with inverse properties pre-populated
  - Manifest v2.0.0 with 6 icon entries and rules entrypoint
key_files:
  - models/basic-pkm/views/basic-pkm.jsonld
  - models/basic-pkm/seed/basic-pkm.jsonld
  - models/basic-pkm/manifest.yaml
key_decisions:
  - Used STRDT(SUBSTR(STR(NOW()),1,10),xsd:date) in the Overdue Tasks SavedQuery to match T02's rdflib-compatible date comparison pattern
  - seed-task-fix-validation has dueDate 2026-03-10 (past) with taskStatus "todo" — the critical overdue trigger for T04 pyshacl tests
patterns_established:
  - ViewSpec naming: view-{type}-{renderer} (e.g. view-task-table, view-milestone-graph)
  - SavedQuery IRI pattern: urn:sempkm:model:basic-pkm:query:{slug}
  - Seed object inverse pre-population (D154): both sides of owl:inverseOf pairs explicitly set on seed objects
observability_surfaces:
  - "Views triple count: python -c \"from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/views/basic-pkm.jsonld', format='json-ld'); print(len(g))\" → 144"
  - "Seed triple count: python -c \"from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/seed/basic-pkm.jsonld', format='json-ld'); print(len(g))\" → 179"
  - "Manifest version: python -c \"import yaml; m=yaml.safe_load(open('models/basic-pkm/manifest.yaml')); print(m['version'], len(m['icons']), 'icons')\" → 2.0.0 6 icons"
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Add views, seed data, and update manifest to v2.0.0

**Added 6 Task/Milestone ViewSpecs, 3 task-focused SavedQueries, 6 seed objects with D154 inverse pre-population, and bumped manifest to v2.0.0 with icons.**

## What Happened

Added 6 new ViewSpecs (Task table/card/graph + Milestone table/card/graph) to the views file, following exact existing JSON-LD pattern with full IRI URIs in SPARQL queries. Added 3 SavedQueries: "My Open Tasks" (filters out done/cancelled), "Overdue Tasks" (past dueDate + still open, using rdflib-compatible STRDT date comparison), and "Blocked Tasks" (status=blocked OR depends on incomplete task via UNION).

Created seed data: 2 Milestones (v1.0 Launch=active, Documentation Complete=planned) and 4 Tasks (write-guide=in-progress, fix-validation=todo with past dueDate 2026-03-10, review-pr=todo with external GitHub link, design-onboarding=blocked with dependsOn). Updated existing seed-project-sempkm with hasProjectTasks and hasMilestones, and all three Person objects with hasAssignedTask — fulfilling D154 inverse pre-population requirement.

Bumped manifest from v1.3.0 → v2.0.0, added Task (check-square/#10b981) and Milestone (flag/#f59e0b) icon entries with tree/tab/graph contexts. Rules entrypoint was already present from T02.

## Verification

- Views: 144 triples (up from 91) — 18 ViewSpecs + 6 SavedQueries confirmed
- Seed: 179 triples (up from 111) — 4 Tasks, 2 Milestones, all inverse properties verified
- Manifest: v2.0.0, 6 icons, 5 entrypoints including rules — all assertions pass
- Overdue task dueDate confirmed: `Literal('2026-03-10', datatype=xsd:date)` on seed-task-fix-validation
- D154 inverse checks: project has 2 hasProjectTasks + 2 hasMilestones; Alice has 2, Bob has 1, Carol has 1 hasAssignedTask
- Slice-level checks: 6 OWL classes, 6 NodeShapes, 35 rules triples — all passing
- T04 test file not yet created (next task)

## Diagnostics

```bash
# Views triple count and ViewSpec inventory
python -c "from rdflib import Graph, URIRef, Namespace; SEMPKM=Namespace('urn:sempkm:vocab:'); g=Graph(); g.parse('models/basic-pkm/views/basic-pkm.jsonld', format='json-ld'); print(len(list(g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), SEMPKM.ViewSpec))), 'ViewSpecs'); print(len(list(g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), SEMPKM.SavedQuery))), 'SavedQueries')"

# Seed overdue task check
python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/seed/basic-pkm.jsonld', format='json-ld'); print(list(g.objects(URIRef('urn:sempkm:model:basic-pkm:seed-task-fix-validation'), URIRef('urn:sempkm:model:basic-pkm:dueDate'))))"

# Manifest check
python -c "import yaml; m=yaml.safe_load(open('models/basic-pkm/manifest.yaml')); print(m['version'], len(m['icons']), 'icons')"
```

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `models/basic-pkm/views/basic-pkm.jsonld` — Added 6 ViewSpecs (Task/Milestone × table/card/graph) and 3 SavedQueries (open-tasks, overdue-tasks, blocked-tasks); 91→144 triples
- `models/basic-pkm/seed/basic-pkm.jsonld` — Added 2 Milestones + 4 Tasks as seed data; updated 4 existing objects with inverse properties (D154); 111→179 triples
- `models/basic-pkm/manifest.yaml` — Bumped version 1.3.0→2.0.0; added Task and Milestone icon entries (6 total)
- `.gsd/milestones/M011/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
