# M006/S07 — Research

**Date:** 2026-03-15

## Summary

S07 is a low-risk integration slice. All heavy infrastructure exists: WorkflowService CRUD (S06), workflow runner with stepper UI (S06), dashboard builder form pattern (S04), explorer section pattern (S04), cross-view context system (S05), and workspace tab routing (S06). The remaining work is: (1) a workflow builder form template mirroring the dashboard builder, (2) a WORKFLOWS explorer section mirroring the DASHBOARDS section, (3) delete UI for both dashboards and workflows, and (4) end-to-end milestone verification.

The builder needs to handle 3 step types (`view`, `dashboard`, `form`), each with type-specific config. This mirrors exactly what the dashboard builder does with 6 block types — the pattern is proven and can be reused almost structurally. The primary integration risk is route ordering in `workflow/router.py` (string path `/explorer` and `/new` must register before `/{workflow_id}`), which is a known issue already solved in `dashboard/router.py`.

## Recommendation

Mirror the dashboard builder pattern exactly. Use `fetch()` with JSON body (D103), `htmx.trigger()` for explorer refresh (D104), and the same `specialType` routing in `workspace-layout.js`. The workflow builder is structurally simpler than the dashboard builder — no layout picker, no slot assignment, just ordered steps with type-specific config. Add delete buttons (with `window.confirm()`) to both dashboard and workflow explorer sections. For the milestone-level end-to-end verification, check all 12 success criteria from the roadmap against live Docker behavior.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Builder form with JSON save | `dashboard_builder.html` fetch() pattern (D103) | Proven; avoids htmx form-encoding vs nested JSON mismatch |
| Explorer section with auto-refresh | DASHBOARDS section in `workspace.html` (D104) | `hx-trigger="load, workflowsRefreshed from:body"` pattern |
| Tab routing for special panels | `workspace-layout.js` specialType routing | Already handles `dashboard`, `dashboard-builder`, `workflow` |
| Step type config fields | Dashboard builder `getTypeConfigHTML()` | Same switch-on-type pattern, different types |
| View spec dropdown | Dashboard builder `populateViewSelect()` from `/browser/views/available` | Reuse same fetch + populate pattern for view steps |
| Dashboard list dropdown | Workflow builder needs `GET /api/dashboard` | Existing endpoint, same pattern as view dropdown |

## Existing Code and Patterns

- `backend/app/templates/browser/dashboard_builder.html` — **Primary template to mirror.** fetch()-based save, dynamic block rows with type-specific config switching via `onchange`, layout picker (skip for workflows — no layout concept). Key functions: `_builderSave()`, `_builderAddBlock()`, `_builderTypeChanged()`, `getTypeConfigHTML()`. 
- `backend/app/templates/browser/dashboard_explorer.html` — **Explorer partial to mirror.** Lists items as `.tree-leaf` with click handlers, includes "+ New" action leaf. Copy structure, change to `openWorkflowTab()` / `openWorkflowBuilderTab()`.
- `backend/app/dashboard/router.py` — **Route pattern to mirror.** `/explorer` before `/{id}` to avoid path capture. Builder routes: `/new` (create), `/{id}/edit` (edit). Same pattern needed for workflow router.
- `frontend/static/js/workspace.js` — `openDashboardBuilderTab()` — **Function to mirror** for `openWorkflowBuilderTab()`. Same `special-panel` + `specialType: 'workflow-builder'` pattern.
- `frontend/static/js/workspace-layout.js` — Already routes `workflow` specialType to `/browser/workflow/{id}/run`. Needs `workflow-builder` specialType added.
- `backend/app/workflow/router.py` — **Existing runner + API routes.** Builder and explorer routes get added here. Route ordering: `/explorer` and `/new` must come before `/{workflow_id}/run` and `/{workflow_id}/step/{step_index}`.
- `backend/app/workflow/models.py` — `VALID_STEP_TYPES = {"view", "dashboard", "form"}`. Builder must present these as options.
- `backend/app/templates/browser/workspace.html` — DASHBOARDS section at line 87. WORKFLOWS section goes after DASHBOARDS (before SHARED). Same `hx-trigger` pattern.

## Constraints

- **Route ordering in workflow/router.py** — `/explorer` and `/new` must be registered before `/{workflow_id}/run`, otherwise FastAPI treats "explorer" and "new" as workflow IDs. Same constraint as dashboard router (S04 forward intelligence).
- **JSON API endpoints already exist** — POST/PATCH/DELETE at `/api/workflow`. Builder must POST/PATCH these, not create new endpoints.
- **fetch() required for save** (D103) — htmx form encoding doesn't map to nested JSON `{name, steps: [{type, label, config}]}`.
- **Step types are fixed** — `view`, `dashboard`, `form`. Each needs type-specific config fields (spec_iri + renderer for view, dashboard_id for dashboard, target_class for form).
- **No workflow-builder specialType exists** — Must add to `workspace-layout.js`.
- **No `openWorkflowBuilderTab()` exists** — Must add to `workspace.js`.

## Common Pitfalls

- **Route ordering** — If `/{workflow_id}` routes are registered before `/explorer` or `/new`, those strings get captured as workflow IDs, returning 400 (invalid UUID) or 404. Register string-path routes first. S04 already solved this for dashboards.
- **htmx:configRequest double-injection** (D110) — If workflow builder ever embeds dashboard context events, the nested htmx element issue returns. Not likely for v1 builder but worth noting.
- **Explorer refresh event naming** — Use `workflowsRefreshed` (camelCase-ish, no colons). Follows `dashboardsRefreshed` and `favoritesRefreshed` naming convention.
- **Lucide icon re-render timing** — After dynamically adding step rows, call `lucide.createIcons({ nodes: [newRow] })` scoped to the new DOM node. Dashboard builder does this correctly — follow the pattern.
- **Delete-then-refresh race** — After `DELETE /api/workflow/{id}` via fetch(), dispatch `workflowsRefreshed` in the `.then()` handler. Don't dispatch on failure.
- **Dashboard dropdown population** — Workflow steps of type `dashboard` need a dropdown of available dashboards. Fetch from `GET /api/dashboard` (returns JSON array with id/name). Cache like the view spec dropdown does.

## Open Risks

- **No real risk.** All infrastructure exists. This is assembly work. The only surprise would be if route ordering causes issues during testing, but the pattern is well-established.
- **Milestone verification scope** — S07 must verify ALL 12 success criteria from the roadmap. Some criteria (PROV-O, explorer grouping, VFS scope) were completed in S01/S02 and may have regressed. Docker restart test + full E2E verification is the safety net.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | N/A | Standard patterns, no special skill needed |
| htmx | N/A | Established patterns in codebase |
| Jinja2 | N/A | Template mirroring, no special skill needed |

No external technology skills are needed for this slice — it's pure pattern replication from S04/S06.

## Sources

- Dashboard builder implementation: `backend/app/templates/browser/dashboard_builder.html`, `backend/app/dashboard/router.py`
- Dashboard explorer implementation: `backend/app/templates/browser/dashboard_explorer.html`, `backend/app/templates/browser/workspace.html`
- Workflow runner implementation: `backend/app/workflow/router.py`, `backend/app/templates/browser/workflow_runner.html`
- S04 summary forward intelligence: route ordering, htmx.trigger() dispatch pattern
- S05 summary forward intelligence: dashboardContextChanged event contract
- S06 summary: WorkflowSpec model, WorkflowService, runner UI, openWorkflowTab()
- Decisions register: D103 (fetch not htmx), D104 (JS-dispatched htmx trigger), D109 (camelCase events)
