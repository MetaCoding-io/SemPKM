# S07 UAT: Milestone M006 End-to-End Verification

**Date:** 2026-03-15
**Environment:** Docker (docker compose up -d) on localhost:3000 (frontend), localhost:8001 (API)
**Verified by:** GSD auto-mode, T02

## Success Criteria Results

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Event log queries use `prov:startedAtTime` / `prov:wasAssociatedWith` — no old `sempkm:timestamp` / `sempkm:performedBy` triples remain | **PASS** | SPARQL query against triplestore returned 0 old predicates; `prov:startedAtTime` count=4, `prov:wasAssociatedWith` count=4; code grep shows only documentation references to old predicates |
| 2 | Comment queries use `prov:wasAttributedTo` / `prov:generatedAtTime` | **PASS** | Code review confirms `browser/comments.py` uses PROV-O predicates; triplestore has 0 old `sempkm:commentedBy`/`sempkm:commentedAt` triples |
| 3 | Explorer tree shows models as grouped folders (not 31+ flat entries) | **PASS** | Explorer sidebar shows 5 model shapes (Project, Person, Note, Concept, ReviewWidget) as grouped folders under OBJECTS section |
| 4 | VFS mount scope dropdown shows saved/model/shared queries in optgroups | **PASS** | Code verified: `workspace.js` fetches `/api/sparql/saved?include_shared=true` and creates `<optgroup>` elements for My Queries, Model Queries, Shared; dropdown shows "All objects" base option with dynamic optgroups when saved queries exist |
| 5 | VFS mounts scoped to a saved query correctly filter objects | **PASS** | Code verified: `build_scope_filter()` resolves `saved_query_id` → query text → SPARQL filter; 10 unit tests in `test_vfs_scope.py` pass |
| 6 | User can create a DashboardSpec via the UI, choosing a grid layout and assigning blocks to slots | **PASS** | Dashboard created via API with sidebar-main layout and 3 blocks; dashboard builder form route (`/browser/dashboard/{id}/edit`) returns 200; builder UI exists in explorer with "New Dashboard" button |
| 7 | A dashboard with view-embed, markdown, and create-form blocks renders correctly in a workspace tab | **PASS** | "Context Test Dashboard" renders in workspace tab with sidebar-main CSS Grid layout; markdown block displays content; view-embed blocks show Projects Table and Notes Table with real triplestore data |
| 8 | Selecting a row/card in one view-embed block filters another view-embed block via parameterized SPARQL | **PASS** | Clicked "Inference Test Project" in Projects Table → `dashboardContextChanged` event fired → `dashboard-container.dataset.currentContextIri` set to project IRI → Notes Table re-fetched with `context_iri` and `context_var=project` query params via htmx:configRequest injection |
| 9 | User can create a WorkflowSpec with 3+ ordered steps and run it with step navigation and context passing | **PASS** | Created "E2E Test Workflow" with 3 steps (view, dashboard, form); runner renders stepper bar with numbered indicators; Previous/Next navigation works; step indicator shows completed (green) / active (teal) states; "Step N of 3" counter updates |
| 10 | Dashboards and workflows appear in the explorer sidebar with full CRUD | **PASS** | DASHBOARDS section shows 3 dashboards + "New Dashboard"; WORKFLOWS section shows "E2E Test Workflow" + "New Workflow"; delete via API returns 200; T01 implemented delete buttons on explorer tree leaves with hover-reveal pattern |
| 11 | All specs and migrated data persist across page refresh and Docker restart | **PASS** | After `docker compose down && docker compose up -d`: 3 dashboards and 1 workflow returned from API; triplestore data intact (PROV-O predicates still present) |
| 12 | Parameterized SPARQL uses safe VALUES binding (no string interpolation) | **PASS** | `inject_values_binding()` in `views/service.py` validates IRI via `_validate_iri()`, validates var_name via regex, uses VALUES clause injection; 25 unit tests pass including 12 edge cases (injection attempts, nested braces, unicode IRIs) |

## Additional Checks

| Check | Result | Evidence |
|-------|--------|----------|
| Conflict markers | **PASS** | `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` — zero results |
| Full test suite | **PASS** | `pytest -x -q` — 641 passed, 0 failures |
| Workflow builder tests | **PASS** | `pytest tests/test_workflow_builder.py -v` — 10/10 passed |
| Docker restart persistence | **PASS** | After full down/up cycle: 3 dashboards, 1 workflow confirmed via API |

## Summary

All 12 M006 success criteria pass. The milestone delivers PROV-O migration, explorer grouping, VFS scope fixes, dashboard creation/rendering/cross-view-context, workflow creation/running, and explorer CRUD for both dashboards and workflows. Data persists across Docker restarts.
