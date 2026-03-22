# S05 Research: Task Templates & Review Workflows

**Depth:** Targeted — known patterns (WorkflowSpec stepper, ninja-keys, RDF CRUD), new service + seed data wiring.

## Summary

S05 adds two features: (1) Task Templates stored in RDF for reusable task patterns, and (2) PPV Review Workflows seeded as WorkflowSpec records. Both are built on established infrastructure — the WorkflowSpec stepper runner already supports view/dashboard/form step types, ninja-keys command palette has a proven registration pattern, and `object.create` handles RDF object creation. The main new code is a `TaskTemplateService` with RDF storage and a REST router, plus 4 seed review WorkflowSpecs.

## Recommendation

**Approach:** Two independent feature tracks that share only the command palette integration point.

**Task Templates** — new RDF-backed CRUD service storing templates in a dedicated named graph (`urn:sempkm:task-templates`). Each template is an RDF resource with a title, target type (e.g., `bpkm:Task`), default properties, and an optional subtask list. Instantiation calls `object.create` (and optionally `edge.create` for subtasks) via the existing command API. Command palette gets "Create from Template" parent entry with dynamically-populated children (same pattern as "Persona: Switch To..." and "Layout: Restore...").

**PPV Review Workflows** — 4 pre-built WorkflowSpecs (weekly, monthly, quarterly, yearly) seeded via `seed_sample_data()`. Each workflow's steps reference existing PPV review shapes and view specs. The stepper runner already handles form (create review object) and view (show filtered review table) step types — no stepper changes needed.

## Implementation Landscape

### What Exists

| Component | Location | State |
|---|---|---|
| WorkflowSpec model | `backend/app/workflow/models.py` | Complete — SQLite-backed, VALID_STEP_TYPES = {view, dashboard, form} |
| WorkflowService | `backend/app/workflow/service.py` | Complete — CRUD (create, get, list_for_user, update, delete) |
| Workflow runner (stepper) | `backend/app/workflow/router.py` + `workflow_runner.html` | Complete — stepper bar, prev/next nav, htmx step loading |
| Workflow explorer | `backend/app/templates/browser/workflow_explorer.html` | Complete — sidebar section listing user's workflows |
| Seed data function | `backend/app/dashboard/seed.py` → `seed_sample_data()` | Creates "Getting Started" dashboard + "Create & Review" workflow at first startup if user has none |
| ninja-keys palette | `frontend/static/js/workspace.js` lines 1415–1960 | Base data array with sections (Objects, Tools, Views, Layout, Persona, Navigation, Appearance). Dynamic entries via `_addTypeCreateEntries()`, `_refreshLayoutPaletteItems()`, `_refreshPersonaPaletteItems()` |
| `object.create` handler | `backend/app/commands/handlers/object_create.py` | Full IRI resolution, multi-value properties, date typing |
| `@slot:name` batch refs | `backend/app/commands/router.py` lines 141–153 | Cross-command IRI references in batch payloads — perfect for "create task + create subtask linked to it" |
| PPV review shapes | `models/ppv/shapes/ppv.jsonld` | WeeklyReviewShape (startDate, endDate, cycle, focusObjective, month link), MonthlyReviewShape (monthName, year, gratitude, learnedThisMonth, quarter link, hasWeeklyReviews), QuarterlyReviewShape (quarterName, yearLink, hasMonthlyReviews), YearlyReviewShape (yearName, quarters) |
| PPV review view specs | `models/ppv/views/ppv.jsonld` | `ppv:view-weekly-table`, `ppv:view-monthly-table`, `ppv:view-quarterly-table`, `ppv:view-yearly-table`, `ppv:view-review-graph` (Review Calendar) |
| TriplestoreClient | `backend/app/triplestore/client.py` | `query()`, `update()`, `insert_graph()`, `construct()` — all async |
| basic-pkm TaskShape | `models/basic-pkm/shapes/basic-pkm.jsonld` | Already has scheduledStart/scheduledEnd/estimatedDuration/recurrenceRule/exceptionDates (S01+S04 work), v2.2.0 |

### What Needs Building

| Component | Purpose | Complexity |
|---|---|---|
| `backend/app/task_templates/service.py` | TaskTemplate CRUD — list, get, create, update, delete against RDF4J named graph | Medium — follows TriplestoreClient pattern for SPARQL INSERT/SELECT/DELETE |
| `backend/app/task_templates/router.py` | REST API (GET/POST/PATCH/DELETE) + htmx browser routes for picker UI | Medium — follows workflow router pattern |
| `backend/app/templates/browser/template_picker.html` | htmx partial for template selection — loaded by command palette handler | Low — simple list with onclick handlers |
| Seed review workflows | 4 WorkflowSpec records in `seed_sample_data()` | Low — extend existing seed function with PPV review workflow definitions |
| Command palette entries | "Create from Template" parent + dynamic children; "Run Review" shortcuts | Low — follows _refreshLayoutPaletteItems pattern exactly |
| Unit tests | Template CRUD, workflow seed idempotency | Medium |

### Natural Task Seams

1. **Task Template Service + Router** — backend CRUD for templates (RDF storage, REST API). Independent of workflows.
2. **Seed Review Workflows** — extend `seed_sample_data()` with 4 PPV review WorkflowSpecs. Independent of templates.
3. **Command Palette + Template Picker UI** — frontend integration: ninja-keys entries, template picker partial, "Create from Template" flow. Depends on T1.
4. **Tests** — unit tests for template CRUD, seed idempotency, command palette smoke test.

### Key Design Decisions

**Template storage: RDF named graph vs SQLite**

The roadmap specifies `urn:sempkm:task-templates` RDF graph. This makes sense because templates reference RDF type IRIs, predicate IRIs, and can include subtask structures that are naturally expressed as triples. The service uses SPARQL INSERT DATA / SELECT / DELETE DATA against the named graph, with `TriplestoreClient.update()` and `query()`.

Template IRI format: `urn:sempkm:task-template:{uuid}` with properties:
- `dcterms:title` — template name (e.g., "Sprint Planning")
- `sempkm:targetClass` — RDF type IRI to create (e.g., `bpkm:Task`)
- `sempkm:defaultProperties` — JSON blob of default key/value pairs (serialized as xsd:string)
- `sempkm:subtaskDefinitions` — JSON blob of subtask patterns (serialized as xsd:string)
- `dcterms:created` / `dcterms:modified` — timestamps

Using JSON blobs for defaultProperties and subtaskDefinitions is pragmatic — deeply nested property maps are awkward to model as individual triples, and the consumer (frontend instantiation) needs the full blob anyway.

**Instantiation flow:**

1. User selects template from command palette → fetches template details
2. Frontend calls `POST /api/commands` with batch:
   - `object.create` with template defaults + `slot: "main-task"`
   - For each subtask: `object.create` + `edge.create` linking to `@slot:main-task`
3. New task tab opens for the main object (same as current create flow)

**Review workflow step definitions:**

Each PPV review workflow maps to existing step types:

*Weekly Review (4 steps):*
1. `view` — "Weekly Reviews" table (ppv:view-weekly-table) to see past weeks
2. `view` — "Action Items" table (ppv:view-action-table) to review completed work
3. `form` — create ppv:WeeklyReview with defaults (cycle="weekly", this week's dates)
4. `view` — "Review Calendar" graph (ppv:view-review-graph) to confirm

*Monthly Review (4 steps):*
1. `view` — "Monthly Reviews" table (ppv:view-monthly-table)
2. `view` — "Weekly Reviews" table filtered to current month
3. `form` — create ppv:MonthlyReview with defaults
4. `view` — "Goal Outcomes" table to track progress

*Quarterly Review (3 steps):*
1. `view` — "Quarterly Reviews" table
2. `form` — create ppv:QuarterlyReview
3. `view` — "Goals Overview" table

*Yearly Review (3 steps):*
1. `view` — "Yearly Reviews" table
2. `form` — create ppv:YearlyReview
3. `view` — "Full Hierarchy" graph (ppv:view-hierarchy-graph)

**Command palette integration:**

Add to ninja.data base array:
- `{ id: 'create-from-template', title: 'Create from Template', section: 'Objects', children: [] }` — dynamically populated like layouts/personas
- `{ id: 'run-weekly-review', title: 'Run Weekly Review', section: 'Workflows', handler: ... }` — direct workflow launcher
- `{ id: 'run-monthly-review', title: 'Run Monthly Review', section: 'Workflows', handler: ... }` — same pattern
- `{ id: 'run-quarterly-review', title: 'Run Quarterly Review', section: 'Workflows', handler: ... }`
- `{ id: 'run-yearly-review', title: 'Run Yearly Review', section: 'Workflows', handler: ... }`

The review workflow handlers fetch the workflow ID by name from `/api/workflow`, then open it in a dockview panel via the existing `openWorkflowTab()` pattern (or equivalent).

### Constraints / Gotchas

1. **Seed idempotency:** `seed_sample_data()` checks `if not existing_workflows` before seeding. But now we need to seed 4 review workflows while preserving the existing "Create & Review" workflow. The check should be by name, not by count — otherwise re-running seed after user creates their own workflow would skip seeding review workflows.

2. **PPV model must be installed:** Review workflows reference PPV type IRIs (ppv:WeeklyReview, etc.) and view spec IRIs (ppv:view-weekly-table). If PPV model isn't installed, the form step will fail (no SHACL shape to render). The workflow should gracefully handle this — either show a "PPV model required" message or skip the step. Simplest: the form step's existing error handling ("No target class configured") covers this.

3. **Template picker needs template list at command palette open time:** The `_refreshTemplatePaletteItems()` function should fetch templates from `/api/task-templates` and populate the children array. This is an async call at palette open — same pattern as persona switching, which fetches from DOM rather than API. For templates, a `fetch()` call is needed. Cache the result with a short TTL or refresh on palette open.

4. **TriplestoreClient named graph for templates:** Use `urn:sempkm:task-templates` as the named graph. INSERT DATA into this graph; SELECT with `FROM <urn:sempkm:task-templates>` clause. Delete by template IRI.

5. **No schema changes needed:** Templates don't need new SHACL shapes — they're system metadata, not user-facing RDF objects. The created tasks use existing TaskShape.

### Verification Strategy

**Unit tests:**
- Template CRUD: create template → list → get → update → delete (mock TriplestoreClient)
- Template instantiation: create from template → verify object.create command generated with correct defaults
- Seed idempotency: seed twice → only 4 review workflows exist (not 8)
- Seed with existing user workflows: user workflows preserved, review workflows added

**E2E tests:**
- Create task from template: command palette → select template → verify new task with expected properties
- Run weekly review workflow: command palette → "Run Weekly Review" → stepper appears → complete steps → verify ppv:WeeklyReview object created

**Manual verification:**
- Command palette shows "Create from Template" with template children
- Command palette shows "Run Weekly Review" etc.
- Workflow stepper navigates through review steps
- Template picker shows available templates with preview
