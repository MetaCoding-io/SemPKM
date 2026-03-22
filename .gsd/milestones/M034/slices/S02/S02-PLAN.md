# S02: Timeline / Gantt View

**Goal:** Add "timeline" as the 7th generic view renderer, using Frappe Gantt to render task bars with dependency arrows, drag-to-reschedule, zoom levels, and saved-query scoping.
**Demo:** Open Timeline view from explorer sidebar. Tasks appear as horizontal bars with `bpkm:dependsOn` arrows. Drag a bar to reschedule — dates persist. Switch zoom from Week to Month. Select a saved-query scope — tasks filter down.

## Must-Haves

- Timeline renders tasks as horizontal bars with correct start/end positioning
- Dependency arrows show between tasks linked via `bpkm:dependsOn`
- Drag-to-reschedule persists via existing calendar PATCH endpoint
- Zoom levels (Day/Week/Month/Year) work via Frappe Gantt view_mode_select
- Saved-query scope filtering works via the standard scope dropdown
- Dark mode CSS overrides render correctly
- Empty state shown when no tasks have date fields
- Timeline entry appears in the views explorer sidebar
- `openGenericViewTab('timeline')` works from workspace.js

## Proof Level

- This slice proves: contract, integration
- Real runtime required: yes (for E2E)
- Human/UAT required: no (visual polish is nice-to-have, functional correctness is testable)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` — unit tests for SPARQL construction, dependency grouping, date fallback, empty results
- `cd e2e && npx playwright test specs/timeline.spec.ts` — E2E test: open timeline, verify task bars rendered, verify dependency arrows, zoom change
- `curl -s http://localhost:3901/browser/views/generic/timeline/data | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'tasks' in d; print('timeline data endpoint OK')"` — verifies JSON error shape when no type provided (empty tasks array)

## Observability / Diagnostics

- Runtime signals: `logger.info("generic_view: renderer=timeline ...")` and `logger.info("execute_timeline_query: type=%s tasks=%d deps=%d")` structured logs following calendar pattern
- Inspection surfaces: `/browser/views/generic/timeline/data?type=<iri>` JSON endpoint returns raw task+dependency data
- Failure visibility: Error message rendered in template when type has no date fields; JSON endpoint returns `{"tasks": []}` for empty results
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `_detect_date_fields()` from `service.py`, `calendar/patch` endpoint from `router.py`, `extract_scope_where_body()` from `service.py`, `openGenericViewTab()` from `workspace.js`, `views_explorer.html` sidebar template
- New wiring introduced: `"timeline"` added to `_VALID_RENDERERS`, new `elif renderer == "timeline":` blocks in `generic_view()` and `generic_view_data()`, new `_build_timeline_select()` and `execute_timeline_query()` in service, new template `timeline_view.html`
- What remains before milestone is truly usable end-to-end: S03 (cross-view drag), S04 (recurring tasks), S05 (templates & review workflows)

## Tasks

- [x] **T01: Backend timeline data layer — service methods, router endpoints, unit tests** `est:2h`
  - Why: The SPARQL query and JSON data contract are the foundation. Frontend can't render without correct data. The dependency-edge grouping logic is the riskiest piece — unit tests prove it before any frontend work.
  - Files: `backend/app/views/service.py`, `backend/app/views/router.py`, `backend/tests/test_timeline.py`
  - Do: Add `_build_timeline_select()` that fetches task IRI, label, start/end dates (reuse `_detect_date_fields()` for start/end paths), and `bpkm:dependsOn` edges. Add `execute_timeline_query()` that groups multi-row SPARQL results by task IRI, collecting dependency arrays. Add `"timeline"` to `_VALID_RENDERERS`. Add `elif renderer == "timeline":` in both `generic_view()` (renders template with context) and `generic_view_data()` (returns JSON). Reuse the calendar PATCH endpoint for drag-to-reschedule — no new PATCH route needed. Write comprehensive unit tests covering: SPARQL construction with/without scope filter, multi-row dependency grouping, dueDate fallback when no scheduledStart, tasks without dates excluded, empty results.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` passes all tests
  - Done when: Unit tests pass for SPARQL build, dependency grouping, date fallback, and empty results; router accepts `renderer=timeline` in both `generic_view` and `generic_view_data`

- [ ] **T02: Frontend timeline template, CSS, explorer wiring** `est:1.5h`
  - Why: The template renders Frappe Gantt in the dockview panel. The explorer entry and workspace.js label make it discoverable. CSS ensures dark mode compatibility.
  - Files: `backend/app/templates/browser/timeline_view.html`, `frontend/static/css/views.css`, `backend/app/templates/browser/views_explorer.html`, `frontend/static/js/workspace.js`
  - Do: Create `timeline_view.html` following the calendar_view.html IIFE+CDN pattern — lazy-load Frappe Gantt from `cdn.jsdelivr.net/npm/frappe-gantt@1.2.2/dist/frappe-gantt.umd.js` + CSS. Fetch JSON from the `timeline_data_url` context var. Transform JSON tasks into Frappe Gantt format (slice datetime to YYYY-MM-DD). Init with `view_mode_select: true`, `on_date_change` calling calendar PATCH, `on_click` calling `openTab()`. Handle empty state. Add `.view-flex-column` wrapper. Add dark mode CSS overrides in `views.css`. Add Timeline entry in `views_explorer.html` (same pattern as Calendar/Map entries). Add `timeline: 'Timeline View'` to the labels map in `openGenericViewTab()` in workspace.js.
  - Verify: Docker stack renders the timeline view when navigated to `/browser/views/generic/timeline?type=urn:sempkm:model:basic-pkm:Task`; dark mode toggle doesn't break rendering
  - Done when: Timeline view loads from explorer sidebar, shows Frappe Gantt chart with task bars, dependency arrows visible, zoom selector works, drag fires PATCH request

- [ ] **T03: E2E test proving timeline renders with bars and dependencies** `est:1h`
  - Why: Proves the full pipeline end-to-end — SPARQL → JSON → Frappe Gantt rendering. Without this, visual regressions are invisible.
  - Files: `e2e/specs/timeline.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Add `timeline` selector to `SEL.views` in selectors.ts. Write Playwright spec: open timeline via `openGenericViewTab('timeline')`, wait for `.gantt-container` or `[data-testid="timeline-view"]`, assert `.bar-wrapper` elements exist (task bars rendered), assert `.arrow` elements exist (dependency arrows). Test zoom level change via Frappe Gantt's view mode selector. Verify empty state when no tasks have dates (use a type with no date fields).
  - Verify: `cd e2e && npx playwright test specs/timeline.spec.ts` passes
  - Done when: E2E test passes confirming task bars, dependency arrows, and zoom functionality

## Files Likely Touched

- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/tests/test_timeline.py`
- `backend/app/templates/browser/timeline_view.html`
- `frontend/static/css/views.css`
- `backend/app/templates/browser/views_explorer.html`
- `frontend/static/js/workspace.js`
- `e2e/specs/timeline.spec.ts`
- `e2e/helpers/selectors.ts`
