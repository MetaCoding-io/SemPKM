# S04: Kanban Renderer — Summary

**Status:** Complete  
**Tasks:** 2/2 done (T01: backend, T02: frontend)  
**Duration:** ~40 minutes total  
**Blocker discovered:** No

## What This Slice Delivered

A fully wired kanban view renderer — backend endpoint, SHACL-driven status field detection, SPARQL grouping query, Jinja2 template, CSS board layout, and HTML5 drag-drop with dockview isolation. Users can click "Kanban View" in the explorer sidebar, select a type via filter pills, and see objects grouped into status columns. Dragging a card between columns fires an `object.patch` command to update the object's status in the triplestore.

## Key Artifacts

| File | Role |
|------|------|
| `backend/app/views/service.py` | `_detect_status_field()`, `_build_kanban_select()`, `execute_kanban_query()` |
| `backend/app/views/router.py` | Kanban branch in `generic_view()`, `"kanban"` in `_VALID_RENDERERS` |
| `backend/app/views/registry.py` | `"kanban"` entry in `RENDERER_REGISTRY` |
| `backend/app/templates/browser/kanban_view.html` | Template with type pills, toolbar, status columns, draggable cards |
| `frontend/static/js/kanban.js` | HTML5 drag-drop IIFE with `stopPropagation()` dockview isolation |
| `frontend/static/css/views.css` | Kanban board/column/card styles (~90 lines appended) |
| `backend/app/templates/browser/views_explorer.html` | "Kanban View" explorer sidebar entry |
| `frontend/static/js/workspace.js` | `kanban: 'Kanban View'` in `openGenericViewTab()` labels |
| `backend/app/templates/base.html` | `kanban.js` script tag |
| `backend/tests/test_kanban.py` | 18 unit tests across 3 test classes |

## Architecture Decisions

- **SHACL-based status field detection** (evolved beyond D286): Instead of hardcoding to `bpkm:taskStatus`, `_detect_status_field()` scans all SHACL PropertyShapes for the type and finds the first with non-empty `sh:in` values, preferring properties with "status" in the path (case-insensitive). This makes the kanban work for any Mental Model type that has enum-constrained properties.
- **Unset column sentinel**: Objects with unrecognized or missing status values go into an "Unset" column using `__unset__` sentinel. Appended at the end of ordered columns.
- **Column labels**: Derived from status values via title-casing with dash/underscore-to-space conversion (e.g., `in-progress` → `In Progress`).
- **Drag-drop dockview isolation**: All drag handlers call `e.stopPropagation()` to prevent dockview from intercepting kanban card drags (same pattern as canvas resize handles, D127).
- **Optimistic DOM move**: Card is moved in the DOM immediately on drop; if the `object.patch` POST fails, the card is reverted back and an error toast is shown.
- **`dragLeave` flicker prevention**: Uses `e.currentTarget.contains(e.relatedTarget)` check to avoid premature removal of the drag-over CSS class when cursor moves between child elements within a column.

## Patterns Established

1. **Kanban scope filter**: Uses the same `scope_filter` sub-select pattern as table/card/graph views, injected by `_build_kanban_select()`.
2. **`initKanban()` at template bottom**: Called inline with `typeof` guard for load-order safety — same pattern as other view initializers.
3. **`/api/commands` POST for drag-drop**: Uses the same command API pattern as `app.js` for `object.patch`, dispatching `sempkm:command-executed` on success.

## Observability

- `logger.info("generic_view: renderer=kanban ...")` on every kanban request with type and scope_query
- `logger.warning(...)` when status field detection fails for a type
- `console.error('kanban: failed to patch status for', iri, err)` on client-side PATCH failure
- `sempkm:command-executed` custom event after successful status update
- Three graceful error states: no type selected, type has no status property, empty results

## Verification Results

All 7 slice-level checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `pytest tests/test_kanban.py -v` — 18 unit tests | ✅ 18/18 pass |
| 2 | `kanban` in `registry.py` | ✅ |
| 3 | `kanban` branch in `router.py` | ✅ |
| 4 | `kanban_view.html` exists | ✅ |
| 5 | `kanban.js` exists | ✅ |
| 6 | `Kanban View` in explorer | ✅ |
| 7 | `kanban` label in `workspace.js` | ✅ |

## What the Next Slice Should Know

- **S05** (SPARQL/Ontology/Full-Height): The kanban view needs full-height CSS propagation (VIEW-13) — it currently relies on the container hierarchy passing height through, which S05 addresses globally for all views.
- **S07** (E2E Tests): Kanban drag-drop E2E tests need a type with `sh:in` status values in the test data. The basic-pkm Task type has `bpkm:taskStatus` with `sh:in` values — use that. The drag-drop isolation (stopPropagation) should be specifically tested to prove dockview doesn't intercept.
- **Scope query support** is wired through `execute_kanban_query(scope_filter=...)` but requires saved queries to exist in the triplestore — covered by S01/S03 upstream.

## Requirement Satisfied

- **VIEW-12** (Kanban renderer with status-based columns and drag-drop): All acceptance criteria met. Backend detects status fields from SHACL, groups objects into columns, template renders board layout, drag-drop updates status via command API. Explorer entry provides access.
