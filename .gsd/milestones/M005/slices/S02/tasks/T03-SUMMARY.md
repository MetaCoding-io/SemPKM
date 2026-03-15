---
id: T03
parent: S02
milestone: M005
provides:
  - Admin UI page at /admin/ops-log showing PROV-O activities with filter and pagination
  - Operations Log card on admin index page
  - Operations Log sidebar nav link with activity icon
key_files:
  - backend/app/admin/router.py
  - backend/app/templates/admin/ops_log.html
  - backend/app/templates/admin/index.html
  - backend/app/templates/components/_sidebar.html
key_decisions:
  - Used HX-Target header to distinguish sidebar nav (returns content block) from filter/pagination (returns table_rows block) — avoids content duplication on htmx partial swap
  - Duration and relative time computed server-side in router helpers (_compute_duration, _relative_time) rather than client-side JS — simpler, no JS dependency
  - Actor IRI shortened to display format (user:id or system) in router before template rendering
patterns_established:
  - htmx target-aware block rendering — check HX-Target header value to decide which Jinja2 block to return for the same route
observability_surfaces:
  - /admin/ops-log page renders prov:Activity instances from urn:sempkm:ops-log graph
  - Failed activities show error details in expandable <details> element
  - Activity type filter enables narrowing to specific operation categories
duration: 25min
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T03: Admin UI — ops log page, route, and sidebar link

**Added /admin/ops-log page with filterable, paginated activity table, admin index card, and sidebar nav link**

## What Happened

Implemented all four steps from the task plan:

1. **Route** — Added `GET /admin/ops-log` to `backend/app/admin/router.py` with `require_role("owner")`, `activity_type` and `cursor` query params, and htmx-aware block rendering. Uses HX-Target header to distinguish sidebar navigation (returns `content` block for `#app-content`) from filter/pagination (returns `table_rows` block for `#ops-log-table`). Includes helper functions `_compute_duration()` and `_relative_time()` for server-side formatting.

2. **Template** — Created `backend/app/templates/admin/ops_log.html` extending `base.html`. Contains filter dropdown with htmx `hx-get`, table with 6 columns (Time, Activity, Type, Actor, Status, Duration), expandable error details via `<details>`, and cursor-based "Load more" pagination. Inline CSS for status badges and error styling using CSS custom properties.

3. **Admin index card** — Added "Operations Log" card as third item in `dashboard-cards` grid with htmx navigation link.

4. **Sidebar link** — Added "Operations Log" nav link in Admin group after Webhooks using `activity` Lucide icon with same htmx pattern.

## Verification

- **Page render**: Navigated to `/admin/ops-log` — renders with heading, lead text, filter dropdown, and table headers ✓
- **Owner role**: Non-owner user gets "Access Denied" page; owner user sees full page ✓
- **Data display**: Seeded 3 test activities (model.install success, inference.run failed, validation.run success) — all appear with correct columns ✓
- **Filter**: Selected "Inference Run" from dropdown — only 1 matching entry shown, no content duplication ✓
- **Error expansion**: Clicked expandable summary on failed activity — error message "Connection to triplestore timed out" displayed in red monospace ✓
- **Sidebar link**: "Operations Log" visible with activity icon in Admin group, htmx navigation works ✓
- **Admin index card**: Third card "Operations Log" with "View Operations Log" button visible ✓
- **Unit tests**: All 35 existing ops_log tests pass ✓
- **Python syntax**: `ast.parse()` passes on router.py ✓
- **No conflict markers**: `grep -rn "^<<<<<<< "` returns zero results ✓

### Slice-level verification status (T03 is final task):
- ✅ `backend/tests/test_ops_log.py` — 35/35 unit tests pass
- ✅ Docker browser verification — /admin/ops-log renders with correct layout
- ✅ Activity entries appear in log table (seeded via OperationsLogService)
- ✅ Filter by activity type narrows the list
- ✅ `grep -rn "ops_log"` confirms instrumentation wired in router.py, inference/router.py, validation/queue.py

## Diagnostics

- Navigate to `/admin/ops-log` to see all logged operations
- Use filter dropdown to narrow by type (model.install, model.remove, inference.run, validation.run)
- Click expandable ▸ on failed activities to see error message
- Data source is PROV-O activities in `urn:sempkm:ops-log` named graph
- Direct SPARQL query: `SELECT * WHERE { GRAPH <urn:sempkm:ops-log> { ?s ?p ?o } }` via SPARQL console

## Deviations

- Added HX-Target header check for block selection instead of using separate endpoints — the plan didn't specify htmx targeting strategy, and initial implementation with `block_name="content"` for filter htmx caused content duplication. Fixed by inspecting HX-Target to return appropriate block.

## Known Issues

None

## Files Created/Modified

- `backend/app/admin/router.py` — Added `admin_ops_log()` route, `_compute_duration()`, `_relative_time()` helpers, and `OPS_LOG_ACTIVITY_TYPES` constant
- `backend/app/templates/admin/ops_log.html` — New ops log page template with table, filter, pagination, and inline CSS
- `backend/app/templates/admin/index.html` — Added Operations Log card to dashboard grid
- `backend/app/templates/components/_sidebar.html` — Added Operations Log nav link in Admin group
- `.gsd/milestones/M005/slices/S02/tasks/T03-PLAN.md` — Added Observability Impact section
