# M006: Dashboards, Workflows & Platform Alignment

**Vision:** Users compose multi-view screens and guided multi-step flows from existing primitives, while the platform aligns to PROV-O standards and the explorer/VFS become usable at scale.

## Success Criteria

- Event log queries use `prov:startedAtTime` / `prov:wasAssociatedWith` — no old `sempkm:timestamp` / `sempkm:performedBy` triples remain
- Comment queries use `prov:wasAttributedTo` / `prov:generatedAtTime`
- Explorer tree shows models as grouped folders (not 31+ flat entries)
- VFS mount scope dropdown shows saved/model/shared queries in optgroups
- VFS mounts scoped to a saved query correctly filter objects
- User can create a DashboardSpec via the UI, choosing a grid layout and assigning blocks to slots
- A dashboard with view-embed, markdown, and create-form blocks renders correctly in a workspace tab
- Selecting a row/card in one view-embed block filters another view-embed block via parameterized SPARQL
- User can create a WorkflowSpec with 3+ ordered steps and run it with step navigation and context passing
- Dashboards and workflows appear in the explorer sidebar with full CRUD
- All specs and migrated data persist across page refresh and Docker restart
- Parameterized SPARQL uses safe VALUES binding (no string interpolation)

### Known v1 Tech Debt

- **SQLite JSON storage** — DashboardSpec and WorkflowSpec stored as SQLite JSON rows, not RDF named graphs. These are model-layer concepts that should live in the triplestore (queryable, federable, consistent with MDSE architecture). Migration planned for a follow-up milestone.
- **Ephemeral workflow runs** — v1 workflow progress is in-memory only. Users want: history of completed runs, ability to resume interrupted workflows, visibility into which workflows they've done and when. Persisted run records planned for follow-up.

## Key Risks / Unknowns

- **Cross-view context passing** — The event → htmx re-fetch → parameterized SPARQL chain is untested in this codebase. If the timing or event wiring doesn't work cleanly with htmx, the interactive dashboard story breaks.
- **Parameterized SPARQL** — ViewSpec queries are currently static. Adding parameter injection requires changes to ViewSpecService. Must prove safe VALUES binding works with RDF4J.
- **PROV-O read-side migration** — EventQueryService has cursor pagination, GROUP_CONCAT, and cross-graph JOINs. Straight predicate rename should be safe but needs careful testing.

## Proof Strategy

- **Cross-view context** → retire in S05 by proving: click row in table block → custom event → second block re-fetches with filter → filtered results display
- **Parameterized SPARQL** → retire in S05 by proving: VALUES clause injection works with RDF4J for at least one view spec
- **PROV-O migration** → retire in S01 by proving: all event/comment queries return correct results after predicate rename

## Verification Classes

- Contract verification: pytest unit tests for CRUD, parameterized query building, migration scripts, scope resolution
- Integration verification: E2E browser tests for dashboard rendering, explorer tree, VFS scope filtering with real triplestore data
- Operational verification: migrated data + new specs persist across Docker restart
- UAT / human verification: dashboard and workflow creation flows feel intuitive, explorer tree is scannable

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slice deliverables are complete with passing tests
- No old `sempkm:timestamp` / `sempkm:performedBy` / `sempkm:description` triples exist in the triplestore
- Explorer tree renders grouped by model with Saved Views folder
- VFS scope dropdown populates and mount filtering works end-to-end
- A dashboard with 3+ block types renders in a workspace tab with real data
- Cross-view filtering works end-to-end (selection → re-fetch → filtered view)
- A workflow with 3+ steps runs start-to-finish with context passing
- Success criteria are re-checked against live behavior in Docker
- No conflict markers in any committed file

## Requirement Coverage

- Covers: (new DASH-*, WKFL-*, PROV-* requirements to be defined per slice)
- Leaves for later: dashboard templates in Mental Models, freeform layout, workflow scheduling, RDF storage migration, workflow run history

## Slices

- [x] **S01: PROV-O Retroactive Migration** `risk:medium` `depends:[]`
  > After this: all event graphs, comments, and query history use PROV-O predicates; write-side and read-side code updated; event log and comment UIs render correctly with new predicates; zero old `sempkm:timestamp`/`sempkm:performedBy`/`sempkm:description` triples remain
- [x] **S02: Views Rethink & VFS Scope Fixes** `risk:medium` `depends:[]`
  > After this: explorer tree groups ViewSpecs by model (~15 entries instead of 31+); duplicate routes cleaned up; VFS scope dropdown shows saved/model queries in optgroups; `build_scope_filter()` resolves `saved_query_id`; Saved Views folder merges MY VIEWS into VIEWS
- [x] **S03: DashboardSpec Model & Static Rendering** `risk:medium` `depends:[]`
  > After this: user can create a dashboard with view-embed, markdown, and create-form blocks via the API, and it renders in a workspace tab showing real data from the triplestore in a CSS Grid layout
- [x] **S04: Dashboard Builder UI & Explorer Integration** `risk:low` `depends:[S02, S03]`
  > After this: user can create and edit dashboards through a form-based UI in the workspace — picking layouts, adding blocks, configuring each block; dashboards appear in the consolidated explorer sidebar
- [x] **S05: Interactive Dashboards — Cross-View Context** `risk:high` `depends:[S03]`
  > After this: selecting a row in one view-embed block filters another view-embed block in the same dashboard via parameterized SPARQL with VALUES binding; dashboard context variables flow via custom events and htmx re-fetch
- [x] **S06: WorkflowSpec Model & Runner** `risk:medium` `depends:[S03]`
  > After this: user can create a workflow with ordered steps (view, dashboard, or form) via the API, and run it with a step indicator bar, prev/next navigation, and context flowing between steps
- [ ] **S07: Workflow Builder UI & Final Integration** `risk:low` `depends:[S04, S05, S06]`
  > After this: user can create/edit workflows through a form-based UI; workflows appear in explorer; full CRUD for both dashboards and workflows; all success criteria verified end-to-end

## Boundary Map

### S01 (PROV-O) — independent

Produces:
- Migrated triplestore data: all event/comment/query-history triples use PROV-O predicates
- Updated write-side code: `events/models.py`, `browser/comments.py`, `sparql/query_service.py` emit PROV-O predicates
- Updated read-side code: `events/query.py`, `federation/router.py`, templates use PROV-O predicates
- `sempkm:Event rdfs:subClassOf prov:Activity` declaration in vocabulary graph
- Idempotent migration script (Alembic or standalone)

Consumes:
- nothing (independent workstream)

### S02 (Views/VFS) — independent

Produces:
- Consolidated `views_explorer.html` template (grouped by model, Saved Views folder)
- Clean `views/router.py` (duplicate routes removed)
- Fixed VFS scope dropdown (correct fetch URL, optgroups for model/shared/user queries)
- Wired `build_scope_filter()` resolving `saved_query_id` → query text → SPARQL filter
- `sempkm:scopeQuery` support in ViewSpecService

Consumes:
- nothing (independent workstream)

### S03 → S04, S05, S06

Produces:
- `DashboardSpec` SQLAlchemy model with JSON `blocks` and `layout` fields
- `DashboardService` with CRUD methods (create, get, list, update, delete)
- `GET /browser/dashboard/{id}` route rendering a CSS Grid with htmx-loaded blocks
- `dashboard_page.html` template with named grid slots
- Block rendering endpoints for `view-embed`, `markdown`, `object-embed`, `create-form`, `divider`
- Dashboard tab type registered in workspace-layout.js
- Command handlers: `dashboard.create`, `dashboard.patch`, `dashboard.delete`

Consumes:
- nothing (first dashboard slice)

### S02 + S03 → S04

Produces:
- Dashboard builder form template and route (`GET /browser/dashboard/{id}/edit`)
- Layout picker component
- Block configuration form components
- Dashboard section in consolidated explorer sidebar

Consumes:
- S02: consolidated explorer template (adds dashboard folder to it)
- S03: DashboardService, block rendering infrastructure

### S03 → S05

Produces:
- `sempkm:dashboard-context-changed` custom event system
- Parameterized SPARQL support in ViewSpecService (`inject_values_binding()`)
- Block selection event wiring (table row click → context variable → re-fetch)

Consumes:
- S03: DashboardSpec model, block rendering, dashboard page template

### S03 → S06

Produces:
- `WorkflowSpec` SQLAlchemy model with JSON `steps` field
- `WorkflowService` with CRUD methods
- `GET /browser/workflow/{id}/run` route with stepper UI
- Workflow runner JS module (step navigation, context state machine)
- Command handlers: `workflow.create`, `workflow.patch`, `workflow.delete`

Consumes:
- S03: Dashboard rendering infrastructure (workflows can embed dashboards as step types)

### S04 + S05 + S06 → S07

Produces:
- Workflow builder form template and route
- Workflow section in explorer sidebar
- End-to-end verification of all success criteria

Consumes:
- S04: Dashboard builder UI, explorer integration patterns
- S05: Cross-view context system (workflows use same parameterized SPARQL)
- S06: WorkflowService, workflow runner infrastructure
