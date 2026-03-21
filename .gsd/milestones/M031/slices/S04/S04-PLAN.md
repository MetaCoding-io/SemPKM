# S04: Kanban Renderer

**Goal:** Users can open a Kanban view that groups objects by a status-like property into draggable columns, with drag-drop to change status.
**Demo:** User clicks "Kanban View" in the explorer sidebar, selects a type (e.g., Task) via type filter pills, sees columns for each status value (todo, in-progress, done, etc.), drags a card from one column to another, and the object's status updates in the triplestore.

## Must-Haves

- `kanban` renderer registered in `_VALID_RENDERERS`, `RENDERER_REGISTRY`, and `generic_view()` endpoint
- Status field auto-detection from SHACL `sh:in` property values via ShapesService
- Server-side grouping of objects by status value into column data structures
- Kanban template with type filter pills, view toolbar, and draggable cards in status columns
- HTML5 drag-drop with `stopPropagation()` to isolate from dockview panel drag system
- `object.patch` command dispatched on drop to update status, with `sempkm:command-executed` event
- "Kanban View" entry in explorer sidebar
- Graceful fallback when no type selected or type has no `sh:in` status property
- Scope query support (same `scope_filter` pattern as table/card/graph)

## Proof Level

- This slice proves: integration (backend endpoint → SPARQL → template → JS drag-drop → command API)
- Real runtime required: yes (needs triplestore + SHACL shapes for status detection)
- Human/UAT required: yes (visual drag-drop behavior, column layout)

## Verification

- `python -m pytest backend/tests/test_kanban.py -v` — unit tests for `_detect_status_field()`, `execute_kanban_query()`, and `_build_kanban_select()` pass
- `grep -q '"kanban"' backend/app/views/registry.py` — kanban registered in renderer registry
- `grep -q 'kanban' backend/app/views/router.py` — kanban branch exists in router
- `test -f backend/app/templates/browser/kanban_view.html` — template exists
- `test -f frontend/static/js/kanban.js` — drag-drop JS exists
- `grep -q 'Kanban View' backend/app/templates/browser/views_explorer.html` — explorer entry exists
- `grep -q 'kanban' frontend/static/js/workspace.js` — label registered in openGenericViewTab

## Observability / Diagnostics

- Runtime signals: `logger.info("generic_view: renderer=kanban type=%s scope_query=%s")` on every kanban request; `logger.warning(...)` when status field detection fails
- Inspection surfaces: `/browser/views/generic/kanban?type=<iri>` renders kanban HTML; browser DevTools network tab shows `object.patch` command POSTs on drag-drop
- Failure visibility: kanban shows user-facing message when type has no status property; console.error on failed patch requests

## Integration Closure

- Upstream surfaces consumed: `build_dynamic_query()` scope_filter pattern from S01, `ShapesService.get_form_for_type()` for status detection, `object.patch` command handler, `view_toolbar.html` and `type_filter_pills.html` includes
- New wiring introduced in this slice: kanban endpoint in router.py, kanban.js in base.html, explorer leaf in views_explorer.html
- What remains before the milestone is truly usable end-to-end: E2E Playwright tests (S07), full-height CSS (S05)

## Tasks

- [x] **T01: Backend kanban endpoint, status detection, and unit tests** `est:40m`
  - Why: The kanban view needs a backend endpoint that detects the status field for a type via SHACL `sh:in`, executes a grouping query, and returns structured column data. Unit tests verify the logic in isolation.
  - Files: `backend/app/views/router.py`, `backend/app/views/service.py`, `backend/app/views/registry.py`, `backend/tests/test_kanban.py`
  - Do: Add `_detect_status_field()` to ViewSpecService (finds first PropertyShape with non-empty `in_values`, preferring "status" in the path). Add `_build_kanban_select()` and `execute_kanban_query()` for SPARQL query + server-side grouping. Add `"kanban"` to `_VALID_RENDERERS` and kanban branch in `generic_view()`. Register in `RENDERER_REGISTRY`. Write pytest unit tests.
  - Verify: `python -m pytest backend/tests/test_kanban.py -v` — all tests pass; `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` — no syntax errors
  - Done when: kanban endpoint exists, status detection works on types with `sh:in` properties, query groups objects by status, tests pass

- [x] **T02: Kanban template, CSS, drag-drop JS, and view wiring** `est:45m`
  - Why: The backend endpoint from T01 needs a template to render, CSS for the kanban board layout, JS for drag-drop with dockview isolation, and wiring so users can access the view from the explorer sidebar.
  - Files: `backend/app/templates/browser/kanban_view.html`, `frontend/static/css/views.css`, `frontend/static/js/kanban.js`, `backend/app/templates/base.html`, `backend/app/templates/browser/views_explorer.html`, `frontend/static/js/workspace.js`
  - Do: Create `kanban_view.html` (type pills + toolbar + kanban board). Add kanban CSS (flex columns, overflow-x, drag states). Create `kanban.js` (initKanban, HTML5 drag handlers with stopPropagation, patchStatus via /api/commands, optimistic DOM move, sempkm:command-executed dispatch). Add script tag in base.html. Add "Kanban View" explorer leaf. Add `kanban` label in openGenericViewTab().
  - Verify: `test -f backend/app/templates/browser/kanban_view.html && test -f frontend/static/js/kanban.js` — files exist; `grep -q 'Kanban View' backend/app/templates/browser/views_explorer.html` — explorer entry present; `grep -q 'kanban' frontend/static/js/workspace.js` — label registered
  - Done when: kanban view renders from explorer click, columns display with cards, drag-drop between columns fires object.patch command

## Files Likely Touched

- `backend/app/views/router.py`
- `backend/app/views/service.py`
- `backend/app/views/registry.py`
- `backend/app/templates/browser/kanban_view.html` (new)
- `backend/app/templates/browser/views_explorer.html`
- `frontend/static/css/views.css`
- `frontend/static/js/kanban.js` (new)
- `frontend/static/js/workspace.js`
- `backend/app/templates/base.html`
- `backend/tests/test_kanban.py` (new)
