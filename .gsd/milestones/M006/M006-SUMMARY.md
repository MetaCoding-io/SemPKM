---
id: M006
provides:
  - DashboardSpec model with SQLite JSON storage, CRUD API, CSS Grid rendering, and cross-view context filtering
  - WorkflowSpec model with SQLite JSON storage, CRUD API, stepper runner UI, and step navigation
  - Dashboard builder UI with layout picker, dynamic block configuration, and explorer section
  - Workflow builder UI with step type config and explorer section
  - Parameterized SPARQL via VALUES clause injection (inject_values_binding)
  - PROV-O predicate migration (6 predicates renamed, vocabulary declaration added)
  - Explorer tree consolidated to model-grouped folders
  - VFS scope dropdown fixed (correct fetch URL, optgroup rendering, saved query resolution)
  - Delete UI for both dashboards and workflows
key_decisions:
  - "D103: Dashboard builder uses fetch() with JSON body — htmx form encoding doesn't map to nested JSON"
  - "D104: Explorer refresh via JS-dispatched htmx trigger — JSON API responses aren't htmx-processed"
  - "D105: Single implicit IRI context variable per dashboard, not Retool-style named variables"
  - "D106: htmx:configRequest for context_iri URL injection, not hx-vals"
  - "D107: Context emission limited to table renderer for v1"
  - "D108: dashboard_mode query parameter for conditional row behavior"
  - "D109: dashboardContextChanged uses camelCase — htmx parses colons as modifiers"
  - "D110: Context params forwarded server-side in render_block, not purely client-side"
patterns_established:
  - inject_values_binding(query, var_name, iri) for parameterized SPARQL — reusable across views, dashboards, workflows
  - dashboardContextChanged event with {iri, dashboardId} detail for cross-view communication
  - htmx:configRequest on dashboard containers for context param injection
  - dashboard_mode=1 query param for template-level behavior switching
  - fetch()-based builder forms with JSON API + htmx.trigger() refresh pattern
  - Tree-leaf delete buttons with hover-reveal opacity
  - Explorer sections with hx-trigger="load, {event} from:body" auto-refresh pattern
observability_surfaces:
  - GET /browser/dashboard/explorer — current dashboard list HTML
  - GET /browser/workflow/explorer — current workflow list HTML
  - GET /api/dashboard — JSON list of user dashboards
  - GET /api/workflow — JSON list of user workflows
  - dashboardsRefreshed / workflowsRefreshed events on document.body
  - #builder-error element in builder templates shows save errors
  - logger.debug("inject_values_binding: var=%s iri=%s") on successful injection
  - S07-UAT.md — persistent verification record for all 12 success criteria
requirement_outcomes:
  - id: PROV-01
    from_status: active
    to_status: validated
    proof: "All event/comment/query triples use PROV-O predicates; zero old sempkm:timestamp/performedBy/description triples; 13 migration tests pass"
  - id: PROV-02
    from_status: active
    to_status: validated
    proof: "Comment queries use prov:wasAttributedTo/prov:generatedAtTime; triplestore has 0 old comment predicates"
  - id: EXP-06
    from_status: active
    to_status: validated
    proof: "Explorer tree groups ViewSpecs by model with ~5 entries instead of 31+; views_explorer.html rewritten for nested structure"
  - id: VFS-06
    from_status: active
    to_status: validated
    proof: "VFS scope dropdown fetches /api/sparql/saved, renders optgroups, build_scope_filter resolves saved_query_id; 10 unit tests"
  - id: DASH-01
    from_status: active
    to_status: validated
    proof: "Dashboard builder UI creates/edits dashboards with layout picker and block config; dashboards render in workspace tabs with CSS Grid; explorer section with CRUD"
  - id: DASH-02
    from_status: active
    to_status: validated
    proof: "Dashboard with view-embed, markdown, and create-form blocks renders correctly; cross-view context filtering works via parameterized SPARQL VALUES injection"
  - id: WKFL-01
    from_status: active
    to_status: validated
    proof: "Workflow builder UI creates/edits workflows with step config; 3-step workflow runs with stepper navigation and context passing; explorer section with CRUD"
duration: ~5h across 7 slices
verification_result: passed
completed_at: 2026-03-15
---

# M006: Dashboards, Workflows & Platform Alignment

**Users compose multi-view dashboard screens and guided multi-step workflows from existing primitives, while the platform aligns to PROV-O standards and the explorer/VFS become usable at scale.**

## What Happened

M006 delivered three converging workstreams across 7 slices:

**Platform alignment (S01–S02)** addressed two independent debts. S01 migrated all custom `sempkm:` provenance predicates to PROV-O equivalents — 6 predicates renamed across 13 files (write-side, read-side, tests), an idempotent migration script for existing triplestore data, and `sempkm:Event rdfs:subClassOf prov:Activity` vocabulary declaration. S02 fixed three explorer/VFS problems: rewrote the explorer tree to group ViewSpecs by model (~5 entries instead of 31+ flat), removed 3 duplicate route definitions from views/router.py, and fixed VFS scope filtering end-to-end (corrected the fetch URL, added optgroup rendering, and wired `build_scope_filter()` to resolve saved queries).

**Dashboard subsystem (S03–S05)** built composable multi-view screens from scratch. S03 established the data layer (`DashboardSpec` SQLAlchemy model, `DashboardService` with async CRUD, Alembic migration), rendering pipeline (CSS Grid layouts, htmx-loaded blocks for 6 block types), and workspace tab integration. S04 added the builder UI (form-based layout picker, dynamic block configuration, fetch()-based JSON save) and explorer integration (DASHBOARDS sidebar section with auto-refresh). S05 delivered the crown jewel — cross-view context filtering via parameterized SPARQL. `inject_values_binding()` safely prepends `VALUES ?{var} { <iri> }` to SPARQL WHERE clauses with full IRI and variable name validation. The event chain — table row click → `dashboardContextChanged` custom event → htmx:configRequest context injection → server-side render_block forwarding → filtered re-fetch — was the highest-risk deliverable in the milestone and works cleanly.

**Workflow subsystem (S06–S07)** built guided multi-step experiences. S06 created the `WorkflowSpec` model, service, runner UI (stepper bar with numbered indicators, prev/next navigation, htmx step loading), and API endpoints. S07 added the builder form (step type config for view/dashboard/form steps), explorer section, delete UI for both dashboards and workflows, and verified all 12 success criteria end-to-end against live Docker.

The slices connected cleanly: S03 provided the foundation consumed by S04 (builder patterns), S05 (context system), and S06 (dashboard step type in workflows). S04's explorer pattern was reused by S07 for workflows. S05's parameterized SPARQL is reusable by any future VALUES-based filtering.

## Cross-Slice Verification

Each success criterion from the roadmap was verified in T02 of S07 against live Docker, documented in S07-UAT.md:

1. **Event log queries use PROV-O predicates** — PASS. SPARQL query returned 0 old `sempkm:timestamp`/`sempkm:performedBy` triples. `prov:startedAtTime` and `prov:wasAssociatedWith` confirmed present.
2. **Comment queries use PROV-O predicates** — PASS. Code review confirms `browser/comments.py` uses `prov:wasAttributedTo`/`prov:generatedAtTime`. Triplestore has 0 old comment predicates.
3. **Explorer tree shows grouped folders** — PASS. 5 model shapes as grouped folders under OBJECTS section.
4. **VFS scope dropdown shows optgroups** — PASS. `workspace.js` fetches `/api/sparql/saved?include_shared=true`, creates optgroup elements.
5. **VFS mounts scoped to saved query filter correctly** — PASS. `build_scope_filter()` resolves saved_query_id → query text → SPARQL filter. 10 unit tests pass.
6. **User can create DashboardSpec via UI** — PASS. Builder form creates dashboards with layout picker and block config. Explorer shows with "New Dashboard" action.
7. **Dashboard with 3+ block types renders** — PASS. sidebar-main layout with view-embed (×2) + markdown block renders in workspace tab with real triplestore data.
8. **Cross-view context filtering works** — PASS. Row click in Projects Table → `dashboardContextChanged` event → Notes Table re-fetched with `context_iri`/`context_var` params → filtered results displayed.
9. **Workflow with 3+ steps runs** — PASS. 3-step workflow (view, dashboard, form) runs with stepper bar, prev/next navigation, step state indicators.
10. **Dashboards and workflows in explorer with CRUD** — PASS. DASHBOARDS section (3 items + New), WORKFLOWS section (1 item + New), delete returns 200.
11. **Persistence across Docker restart** — PASS. After `docker compose down/up`: 3 dashboards and 1 workflow confirmed via API.
12. **Parameterized SPARQL uses safe VALUES binding** — PASS. `inject_values_binding()` validates IRI and var_name. 25 unit tests including 12 edge cases (injection attempts, nested braces, unicode IRIs).

**Additional verification:**
- 641 pytest tests pass (93 new across 7 test files), 0 failures
- Zero conflict markers across all source files
- Zero regressions in existing functionality

## Requirement Changes

- PROV-01: active → validated — All event/comment/query triples use PROV-O predicates; migration script + 13 tests
- PROV-02: active → validated — Comment queries use prov:wasAttributedTo/generatedAtTime; 0 old predicates
- EXP-06: active → validated — Explorer groups ViewSpecs by model; rewritten template
- VFS-06: active → validated — VFS scope dropdown fixed with optgroups and saved query resolution; 10 tests
- DASH-01: active → validated — Full dashboard CRUD through builder UI + explorer; CSS Grid rendering
- DASH-02: active → validated — Cross-view context filtering via parameterized SPARQL VALUES injection
- WKFL-01: active → validated — Full workflow CRUD through builder UI + explorer; stepper runner

## Forward Intelligence

### What the next milestone should know
- `inject_values_binding()` is reusable for any VALUES-based SPARQL filtering — workflows, VFS scoping, or any future parameterized query need
- The fetch()-based builder pattern (JSON API + htmx.trigger() refresh) is now proven for two subsystems and should be the default for any new builder UI
- Explorer sections with `hx-trigger="load, {event} from:body"` auto-refresh is a stable, reusable pattern (now used by FAVORITES, DASHBOARDS, WORKFLOWS)
- DashboardSpec and WorkflowSpec are in SQLite JSON — migration to RDF named graphs is planned tech debt
- Workflow runs are ephemeral (in-memory JS) — run history persistence is planned tech debt

### What's fragile
- htmx:configRequest listener targets `.dashboard-slot` elements — if dashboard HTML structure changes, context injection silently breaks
- `_extract_where_body()` uses brace-counting for WHERE clause detection — deeply nested SPARQL with unmatched braces in string literals could break it
- Explorer route order in dashboard/workflow routers — string-path routes (`/explorer`, `/new`) must be registered before `/{id}` to avoid FastAPI path capture
- View-embed spec dropdown fetches from `/browser/views/available` — if that endpoint changes, both builder dropdowns silently break

### Authoritative diagnostics
- `S07-UAT.md` is the persistent verification record for all 12 success criteria
- `GET /browser/dashboard/explorer` and `GET /browser/workflow/explorer` return current list HTML
- `GET /api/dashboard` and `GET /api/workflow` return JSON for programmatic inspection
- Browser devtools: `dashboardContextChanged` event on body, `dashboardsRefreshed`/`workflowsRefreshed` events
- Network tab: `context_iri=` params on render-block requests confirm cross-view chain

### What assumptions changed
- Plan assumed `sempkm:dashboard-context-changed` event name would work with htmx — colons are reserved in hx-trigger syntax (D109)
- Plan assumed client-side htmx:configRequest alone could handle context injection — nested elements cause double-injection, required server-side forwarding (D110)
- Plan assumed HX-Trigger header on JSON API responses would work — htmx only processes headers from htmx-initiated requests, required JS dispatch (D104)

## Files Created/Modified

### New Modules
- `backend/app/dashboard/` — `__init__.py`, `models.py`, `service.py`, `router.py` (dashboard subsystem)
- `backend/app/workflow/` — `__init__.py`, `models.py`, `service.py`, `router.py` (workflow subsystem)

### Templates
- `backend/app/templates/browser/dashboard_page.html` — CSS Grid layout with htmx-loaded blocks
- `backend/app/templates/browser/dashboard_builder.html` — builder form with layout picker and block config
- `backend/app/templates/browser/dashboard_explorer.html` — explorer partial with delete buttons
- `backend/app/templates/browser/workflow_runner.html` — stepper UI with prev/next navigation
- `backend/app/templates/browser/workflow_builder.html` — builder form with step type config
- `backend/app/templates/browser/workflow_explorer.html` — explorer partial with delete buttons
- `backend/app/templates/browser/workspace.html` — added DASHBOARDS and WORKFLOWS sections
- `backend/app/templates/browser/views_explorer.html` — rewritten for model-grouped structure
- `backend/app/templates/browser/table_view.html` — conditional dashboard_mode row click

### Migrations
- `backend/migrations/versions/011_dashboard_specs.py` — DashboardSpec table
- `backend/migrations/versions/012_workflow_specs.py` — WorkflowSpec table

### Backend (modified)
- `backend/app/events/models.py` — PROV-O predicate constants
- `backend/app/events/query.py` — PROV-O read-side queries
- `backend/app/browser/comments.py` — PROV-O comment predicates
- `backend/app/sparql/query_service.py` — PROV-O query history predicates
- `backend/app/views/service.py` — `inject_values_binding()` for parameterized SPARQL
- `backend/app/views/router.py` — context params, duplicate routes removed, explorer rewritten
- `backend/app/vfs/strategies.py` — `build_scope_filter()` with saved query resolution
- `backend/app/browser/workspace.py` — `_resolve_saved_query_text()` helper
- `backend/scripts/migrate_provo.py` — idempotent PROV-O migration script

### Frontend
- `frontend/static/js/workspace.js` — `openDashboardTab()`, `openDashboardBuilderTab()`, `openWorkflowBuilderTab()`, VFS scope fix
- `frontend/static/js/workspace-layout.js` — dashboard, dashboard-builder, workflow-builder specialTypes
- `frontend/static/css/workspace.css` — dashboard/workflow builder CSS, context-selected highlight, tree-leaf delete

### Tests (7 new files, 93 new tests)
- `backend/tests/test_provo_migration.py` — 13 tests
- `backend/tests/test_vfs_scope.py` — 10 tests
- `backend/tests/test_dashboard.py` — 27 tests
- `backend/tests/test_dashboard_builder.py` — 9 tests
- `backend/tests/test_values_injection.py` — 25 tests
- `backend/tests/test_workflow.py` — 13 tests (S06 — existed before but new in M006)
- `backend/tests/test_workflow_builder.py` — 10 tests
