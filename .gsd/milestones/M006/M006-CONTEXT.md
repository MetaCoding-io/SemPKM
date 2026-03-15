# M006: Dashboards, Workflows & Platform Alignment

**Gathered:** 2026-03-15
**Status:** Ready for planning

## Project Description

Three workstreams converge in this milestone:

1. **Custom Dashboards & Guided Workflows** — Two new composable model types (DashboardSpec, WorkflowSpec) that let users build multi-view screens and guided multi-step experiences. The composition and sequencing layer above individual views and forms.

2. **PROV-O Alignment** — Retroactive SPARQL UPDATE migration of event graphs, comments, and query history to PROV-O predicates, followed by write-side and read-side code updates. Eliminates all custom provenance predicates that have standard equivalents.

3. **Views Rethink & VFS v2 Fixes** — Explorer tree consolidation (31+ entries → grouped folders), query-scoped views via `sempkm:scopeQuery`, VFS scope dropdown bug fix (wrong fetch URL + dead `build_scope_filter()`), duplicate route cleanup.

## Why This Milestone

**Dashboards/Workflows:** SemPKM has strong primitives — ViewSpecs, SHACL forms, SPARQL queries — but no way to compose them. A user who wants "untagged notes next to active projects next to a quick-add form" cannot build that screen. Recurring review patterns require manual navigation through 4-5 separate views with no state continuity.

**PROV-O:** The EventStore uses 7 custom `sempkm:` predicates where PROV-O equivalents exist. The ops log already uses PROV-O correctly — events and comments should align. Single user with test data makes retroactive migration cheap (D103).

**Views/VFS:** The explorer tree is unusable at scale (31+ entries from 2 models). The VFS scope dropdown is broken (404 fetch + dead backend wiring). Both have accepted designs ready to implement.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Create a dashboard that arranges multiple views, objects, forms, and markdown in a grid layout
- Open dashboards as tabs in the workspace
- Define and run a guided workflow with ordered steps and context passing between steps
- See a clean explorer tree grouped by model (not 31+ flat entries)
- Scope VFS mounts to saved queries (dropdown actually works)
- Query events and comments using standard PROV-O predicates (`prov:startedAtTime`, `prov:wasAssociatedWith`)
- Browse and manage dashboards and workflows from the explorer sidebar

### Entry point / environment

- Entry point: Browser workspace at `http://localhost:3000/workspace`
- Environment: Docker dev (docker-compose)
- Live dependencies involved: RDF4J triplestore, SQLite (dashboard/workflow storage)

## Completion Class

- Contract complete means: unit tests for dashboard/workflow CRUD, rendering, context passing; PROV-O migration verified by SPARQL queries; VFS scope resolution tested
- Integration complete means: dashboards render real ViewSpec data from triplestore; PROV-O predicates used end-to-end; VFS mounts filter by saved query
- Operational complete means: all specs and migrated data persist across Docker restart

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A dashboard with 3+ blocks (view-embed, markdown, create-form) renders correctly in a workspace tab with real triplestore data
- A workflow with 3+ steps runs start-to-finish with context flowing between steps
- Event log queries use `prov:startedAtTime` / `prov:wasAssociatedWith` and return correct results (no mixed-era data)
- Explorer tree shows models as grouped folders, not 31+ flat entries
- VFS mount scope dropdown shows saved queries and mount correctly filters to query results
- Dashboards and workflows appear in the explorer and support full CRUD

## Risks and Unknowns

- **Cross-view context passing** — The event → htmx re-fetch → parameterized SPARQL chain is untested. Medium risk.
- **SPARQL parameterization security** — Must use VALUES clause binding, not string interpolation. Low risk — RDF4J supports this.
- **PROV-O migration scope** — 3 event predicates + 2 comment predicates + 1 query history predicate across all named graphs. Low risk for single-user data volume, but must verify cursor pagination and GROUP_CONCAT queries still work after predicate rename.
- **Storage format** — SQLite JSON for v1 dashboards/workflows. **Tech debt:** these are model-layer concepts that belong in RDF (consistent with MDSE architecture). Migration to RDF named graphs planned for follow-up.
- **Workflow state persistence** — v1 runs are ephemeral. Users want: history of completed runs, resume interrupted workflows, track frequency. Planned for follow-up.
- **views/router.py duplicate routes** — 3 pairs of duplicate definitions (lines 68/468, 92/507, 49/565). Must clean up before adding endpoints.

## Existing Codebase / Prior Art

- `backend/app/views/service.py` — ViewSpecService; DashboardService follows same pattern
- `backend/app/views/router.py` — View rendering routes; has 3 duplicate route pairs to clean up
- `backend/app/sparql/models.py` — `PromotedQueryView` is proto-dashboard block
- `backend/app/events/models.py` — Event predicate constants (migration targets)
- `backend/app/events/query.py` — EventQueryService SPARQL queries (read-side migration)
- `backend/app/events/store.py` — EventStore write path (write-side migration)
- `backend/app/browser/comments.py` — Comment predicates (migration targets)
- `backend/app/services/ops_log.py` — Already PROV-O aligned (reference implementation)
- `backend/app/vfs/strategies.py` — `build_scope_filter()` ignores `saved_query_id` (bug)
- `frontend/static/js/workspace.js` — Tab system; scope dropdown fetches wrong URL (bug)
- `docs/research/dashboard-builder-and-workflows.md` — Comprehensive research doc

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Design Documents

- `.gsd/design/PROV-O-ALIGNMENT.md` — Predicate audit, migration plan, SPARQL UPDATE scripts (312 lines)
- `.gsd/design/VFS-V2-DESIGN.md` — Saved query scoping, frontend/backend bug fixes, dropdown optgroups (515 lines)
- `.gsd/design/VIEWS-RETHINK.md` — Explorer consolidation, query-scoped views, duplicate route cleanup (288 lines)

## Relevant Requirements

- No existing dashboard/workflow requirements — this milestone establishes new capability
- Existing: views/VFS functionality tested via E2E specs (M005)

## Scope

### In Scope

**Dashboards & Workflows:**
- DashboardSpec model (SQLite JSON storage, CRUD API, command handlers)
- Dashboard renderer (CSS Grid layouts, htmx block loading)
- Dashboard builder UI (form-based, not drag-and-drop)
- Block types: view-embed, markdown, object-embed, create-form, sparql-result, divider
- Cross-view context variables with htmx re-fetch
- Parameterized SPARQL in ViewSpec queries (safe VALUES binding)
- WorkflowSpec model (SQLite JSON storage, CRUD API)
- Workflow runner UI (stepper bar, step navigation, context sidebar)
- Workflow builder UI (form-based step definition)
- Explorer integration (dashboard/workflow sections in sidebar)

**PROV-O Alignment:**
- Retroactive SPARQL UPDATE migration (events, comments, query history)
- Write-side predicate swap (events/models.py, comments.py, query_service.py)
- Read-side predicate swap (events/query.py, federation/router.py, templates)
- `sempkm:Event rdfs:subClassOf prov:Activity` declaration

**Views & VFS:**
- Explorer tree consolidation (group by model, one entry per type)
- Duplicate route cleanup in views/router.py
- VFS scope dropdown bug fix (wrong fetch URL → `/api/sparql/saved`)
- `build_scope_filter()` wired to resolve `saved_query_id`
- Model/shared query optgroups in scope dropdown
- `sempkm:scopeQuery` support in ViewSpecService
- Saved Views folder (merge MY VIEWS into VIEWS)

### Out of Scope / Non-Goals (v1)

- Freeform drag-and-drop layout
- Dashboard scheduling / recurring workflows
- Mobile-responsive layouts
- Chart/metrics block integration (Chart.js)
- Dashboard-as-homepage
- Mental Model bundled dashboard/workflow templates
- VFS composable strategy chains (items 5-6 from VFS v2 design)
- VFS write support

### Planned Tech Debt (v1 → v2)

- **RDF storage migration** — v1 stores DashboardSpec and WorkflowSpec as SQLite JSON. These are model-layer concepts that belong in RDF named graphs (consistent with MDSE architecture, queryable, federable). Migrate to RDF in a follow-up milestone.
- **Workflow run history** — v1 workflow runs are ephemeral (in-memory/sessionStorage, lost on page close). Users want to: see completed past runs, resume interrupted workflows, track frequency of recurring workflows. Persist run records (start time, completion status, step reached, context snapshot) in a follow-up.

## Technical Constraints

- Must use htmx partial rendering — no client-side JS framework
- Dashboard/workflow specs stored in SQLite (not RDF) for v1 — simpler CRUD
- SPARQL parameterization must use VALUES clause binding, not string interpolation
- Grid layouts use CSS Grid with predefined named templates
- Blocks load via htmx `hx-get` with lazy loading
- Must work with existing dockview tab system
- PROV-O migration must be idempotent (safe to re-run)

## Integration Points

- **ViewSpecService** — Dashboard view-embed blocks call existing view rendering endpoints; scopeQuery support added
- **ShapesService** — Dashboard create-form blocks use existing SHACL form generation
- **EventStore / EventQueryService** — Predicate migration (write + read sides)
- **VFS MountService / strategies.py** — Scope filter resolution wired to saved queries
- **Tab system** — Dashboards and workflows register as new tab types
- **Explorer** — Consolidated view tree + dashboard/workflow sections
- **Command system** — CRUD operations through existing dispatcher

## Open Questions

- **Layout template set** — Which predefined layouts to ship? Candidates: single, sidebar-main, grid-2x2, grid-3, top-bottom
- **Context variable naming** — Implicit (always exports selected IRI) or explicit (block config names the variable)?
- **PROV-O migration ordering** — Run migration before or after write-side code update? Before is safer (migration script uses old predicates).
