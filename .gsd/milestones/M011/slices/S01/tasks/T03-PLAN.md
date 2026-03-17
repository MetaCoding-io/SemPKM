---
estimated_steps: 8
estimated_files: 3
---

# T03: Add views, seed data, and update manifest to v2.0.0

**Slice:** S01 — basic-pkm v2 — Task & Milestone Types
**Milestone:** M011

## Description

Complete the model archive by adding ViewSpecs and SavedQueries for the new types, creating seed data that demonstrates Task/Milestone usage (including an overdue task for validation testing), and bumping the manifest to v2.0.0 with icon entries. This task makes the model fully browsable and installable.

Per D154: seed data must pre-populate both sides of owl:inverseOf pairs so objects display correctly even without inference.
Per D152: no Event type in v2.0 — only Task and Milestone.

## Steps

1. **Edit `models/basic-pkm/views/basic-pkm.jsonld`** — Add to existing `@graph` array:

   **Task ViewSpecs (3):**
   - `bpkm:view-task-table` — Task Table View: SELECT query returning title, taskStatus, priority, dueDate, assignedTo (name), taskProject (title), milestone (title). Columns: title,taskStatus,priority,dueDate,assignedTo,taskProject. Sort: dueDate ascending.
   - `bpkm:view-task-card` — Task Card View: SELECT query returning title, taskStatus, priority, dueDate, description. cardTitle: dcterms:title, cardSubtitle: bpkm:taskStatus.
   - `bpkm:view-task-graph` — Task Graph View: CONSTRUCT query showing Tasks with dependsOn edges, assignedTo→Person edges, taskProject→Project edges. Include labels for all connected nodes.

   **Milestone ViewSpecs (3):**
   - `bpkm:view-milestone-table` — Milestone Table View: SELECT query returning title, milestoneStatus, targetDate, milestoneProject (title). Columns: title,milestoneStatus,targetDate,milestoneProject. Sort: targetDate ascending.
   - `bpkm:view-milestone-card` — Milestone Card View: SELECT returning title, milestoneStatus, targetDate, description. cardTitle: dcterms:title, cardSubtitle: bpkm:milestoneStatus.
   - `bpkm:view-milestone-graph` — Milestone Graph View: CONSTRUCT showing Milestones with hasTasks edges and milestoneProject→Project edges.

   **SavedQueries (3):**
   - `bpkm:query:open-tasks` — "My Open Tasks": SELECT tasks where taskStatus NOT IN ("done", "cancelled"), ORDER BY dueDate.
   - `bpkm:query:overdue-tasks` — "Overdue Tasks": SELECT tasks where dueDate < NOW() AND taskStatus NOT IN ("done", "cancelled").
   - `bpkm:query:blocked-tasks` — "Blocked Tasks": SELECT tasks where taskStatus = "blocked" OR has dependsOn pointing to an undone task.

   Follow the exact JSON-LD pattern used by existing ViewSpecs and SavedQueries in the file. Use full IRI URIs in SPARQL (no prefixes within query strings, matching existing pattern). All SavedQuery IRIs must use the `urn:sempkm:model:basic-pkm:query:` prefix.

2. **Edit `models/basic-pkm/seed/basic-pkm.jsonld`** — Add to existing `@graph` array:

   **Milestones (2):**
   - `bpkm:seed-milestone-launch` — "v1.0 Launch": milestoneStatus "active", targetDate "2026-04-15", milestoneProject → seed-project-sempkm, hasTasks → [seed-task-fix-validation, seed-task-review-pr]
   - `bpkm:seed-milestone-docs` — "Documentation Complete": milestoneStatus "planned", targetDate "2026-04-01", milestoneProject → seed-project-sempkm, hasTasks → [seed-task-write-guide, seed-task-design-onboarding]

   **Tasks (4):**
   - `bpkm:seed-task-write-guide` — "Write user guide for graph view": taskStatus "in-progress", priority "high", dueDate "2026-03-25" (future), assignedTo → seed-person-alice, milestone → seed-milestone-docs, relatedNote → seed-note-architecture, tags ["documentation", "guide"]. Set bpkm:body with brief markdown notes.
   - `bpkm:seed-task-fix-validation` — "Fix validation edge case": taskStatus "todo", priority "medium", dueDate "2026-03-10" (PAST — this triggers overdue validation), assignedTo → seed-person-bob, milestone → seed-milestone-launch, taskProject → seed-project-sempkm. **Critical: this task MUST have a past dueDate to trigger the overdue-task SPARQLConstraint in T04 tests.**
   - `bpkm:seed-task-review-pr` — "Review PR #42": taskStatus "todo", priority "low", externalProvider "github", externalId "#42", externalUrl "https://github.com/example/sempkm/pull/42", assignedTo → seed-person-carol, taskProject → seed-project-sempkm
   - `bpkm:seed-task-design-onboarding` — "Design onboarding flow": taskStatus "blocked", priority "high", dependsOn → seed-task-write-guide, assignedTo → seed-person-alice, milestone → seed-milestone-docs

   **Update existing objects for inverse pre-population (D154):**
   - `bpkm:seed-project-sempkm` — add `bpkm:hasProjectTasks` → [seed-task-fix-validation, seed-task-review-pr], add `bpkm:hasMilestones` → [seed-milestone-launch, seed-milestone-docs]
   - `bpkm:seed-person-alice` — add `bpkm:hasAssignedTask` → [seed-task-write-guide, seed-task-design-onboarding]
   - `bpkm:seed-person-bob` — add `bpkm:hasAssignedTask` → [seed-task-fix-validation]
   - `bpkm:seed-person-carol` — add `bpkm:hasAssignedTask` → [seed-task-review-pr]

3. **Edit `models/basic-pkm/manifest.yaml`** — Update:
   - `version: "2.0.0"` (was "1.3.0")
   - Add `rules: "rules/basic-pkm.ttl"` to entrypoints (may already be there — verify)
   - Add icon entries for Task and Milestone with tree/tab/graph contexts:
     ```yaml
     - type: "bpkm:Task"
       icon: "check-square"
       color: "#10b981"
       tree:
         icon: "check-square"
         color: "#10b981"
         size: 16
       tab:
         icon: "check-square"
         color: "#10b981"
         size: 14
       graph:
         icon: "check-square"
         color: "#10b981"
     - type: "bpkm:Milestone"
       icon: "flag"
       color: "#f59e0b"
       tree:
         icon: "flag"
         color: "#f59e0b"
         size: 16
       tab:
         icon: "flag"
         color: "#f59e0b"
         size: 14
       graph:
         icon: "flag"
         color: "#f59e0b"
     ```

4. **Verify** all files parse:
   ```bash
   cd /home/james/Code/SemPKM
   python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/views/basic-pkm.jsonld', format='json-ld'); print(f'Views: {len(g)} triples')"
   python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/seed/basic-pkm.jsonld', format='json-ld'); print(f'Seed: {len(g)} triples')"
   python -c "import yaml; m=yaml.safe_load(open('models/basic-pkm/manifest.yaml')); assert m['version']=='2.0.0'; assert len(m['icons'])==6; print('Manifest OK')"
   ```

## Must-Haves

- [ ] 6 new ViewSpecs (3 Task + 3 Milestone) following existing JSON-LD pattern
- [ ] 3 new SavedQueries (open tasks, overdue tasks, blocked tasks) with model:basic-pkm source
- [ ] 4 seed tasks including one with past dueDate + status "todo" (triggers overdue validation)
- [ ] 2 seed milestones linked to existing project and tasks
- [ ] Existing seed objects updated with inverse relationship properties (D154)
- [ ] Manifest version bumped to "2.0.0"
- [ ] 2 new icon entries (Task + Milestone) with tree/tab/graph contexts
- [ ] All files parse without error via rdflib / yaml

## Verification

- Views rdflib parse succeeds with more triples than before
- Seed rdflib parse succeeds with more triples than before
- `python -c "import yaml; m=yaml.safe_load(open('models/basic-pkm/manifest.yaml')); assert m['version']=='2.0.0'; print(len(m['icons']), 'icons')"` prints "6 icons"
- Seed data contains a task with past dueDate: `python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/seed/basic-pkm.jsonld', format='json-ld'); overdue=list(g.objects(URIRef('urn:sempkm:model:basic-pkm:seed-task-fix-validation'), URIRef('urn:sempkm:model:basic-pkm:dueDate'))); print(f'dueDate: {overdue}'); assert len(overdue)==1"`

## Observability Impact

- **Views triple count** increases from ~91 to ~200+ (6 new ViewSpecs + 3 new SavedQueries add ~100+ triples). Diagnostic: `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/views/basic-pkm.jsonld', format='json-ld'); print(len(g))"`
- **Seed triple count** increases from ~111 to ~170+ (4 tasks, 2 milestones, inverse properties on existing objects). Diagnostic: `python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/seed/basic-pkm.jsonld', format='json-ld'); print(len(g))"`
- **Manifest version** bumps from 1.3.0 → 2.0.0. Diagnostic: `python -c "import yaml; m=yaml.safe_load(open('models/basic-pkm/manifest.yaml')); print(m['version'], len(m['icons']), 'icons')"`
- **Overdue seed task** visible via: `python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/seed/basic-pkm.jsonld', format='json-ld'); print(list(g.objects(URIRef('urn:sempkm:model:basic-pkm:seed-task-fix-validation'), URIRef('urn:sempkm:model:basic-pkm:dueDate'))))"`
- **Failure visibility:** rdflib parse errors surface immediately as Python tracebacks. YAML syntax errors caught by yaml.safe_load(). Invalid JSON-LD context references produce rdflib warnings.

## Inputs

- `models/basic-pkm/views/basic-pkm.jsonld` — existing v1.3 views with 12 ViewSpecs + 3 SavedQueries
- `models/basic-pkm/seed/basic-pkm.jsonld` — existing v1.3 seed with Project, Person, Note, Concept instances
- `models/basic-pkm/manifest.yaml` — existing v1.3 manifest with 4 icon entries
- T01 output: ontology/shapes have Task and Milestone classes with all property IRIs
- T02 output: rules file has inference and validation rules

## Expected Output

- `models/basic-pkm/views/basic-pkm.jsonld` — expanded with 18 ViewSpecs + 6 SavedQueries
- `models/basic-pkm/seed/basic-pkm.jsonld` — expanded with Task and Milestone seed instances, existing objects updated with inverse properties
- `models/basic-pkm/manifest.yaml` — version 2.0.0, 6 icon entries, entrypoints including rules
