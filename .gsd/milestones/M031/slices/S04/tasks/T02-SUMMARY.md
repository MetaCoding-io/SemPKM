---
id: T02
parent: S04
milestone: M031
provides:
  - kanban_view.html template with type filter pills, view toolbar, status columns, and draggable cards
  - kanban.js drag-drop module with dockview isolation (stopPropagation), optimistic DOM moves, and object.patch POST
  - Kanban CSS in views.css with flex column layout, horizontal scroll, drag states
  - "Kanban View" explorer sidebar entry and workspace.js label registration
key_files:
  - backend/app/templates/browser/kanban_view.html
  - frontend/static/js/kanban.js
  - frontend/static/css/views.css
  - backend/app/templates/browser/views_explorer.html
  - backend/app/templates/base.html
  - frontend/static/js/workspace.js
key_decisions:
  - Template uses error_message context variable (set by router) rather than empty_message, matching the actual router branch output from T01
  - dragLeave handler checks e.currentTarget.contains(e.relatedTarget) to avoid premature removal of drag-over state when moving between child elements
patterns_established:
  - Kanban JS uses same /api/commands POST pattern as app.js for object.patch with sempkm:command-executed dispatch
  - initKanban() called inline at template bottom, guarded by typeof check for load-order safety
observability_surfaces:
  - console.error('kanban: failed to patch status for', iri, err) on PATCH failure
  - sempkm:command-executed custom event after successful status update
  - User-facing toast on patch failure (via showToast if available)
  - Empty state messages rendered when no type selected or no status property detected
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Kanban template, CSS, drag-drop JS, and view wiring

**Add kanban frontend with Jinja2 template, CSS board layout, HTML5 drag-drop JS module with dockview isolation, and explorer/workspace wiring.**

## What Happened

Created the complete frontend for the kanban view across six files:

1. **kanban_view.html** — Jinja2 template following the same opening pattern as cards_view.html (type filter pills + view toolbar includes). Renders three states: error_message (no type or no status property), kanban board with columns/cards (normal), and fallback empty state. Each card is draggable with `data-iri` attribute; the board element carries `data-status-predicate` for the JS module. The init script at the bottom calls `initKanban()` with a typeof guard.

2. **views.css** — Appended kanban CSS block with flex column layout, horizontal overflow scroll, drag/hover states, and column count badges. Uses existing theme custom properties (`--color-surface-raised`, `--color-border`, `--color-primary`, etc.).

3. **kanban.js** — Self-contained IIFE module (~130 lines) implementing HTML5 drag-drop. Key features: `stopPropagation()` on dragstart/dragover/drop to prevent dockview from intercepting; optimistic DOM card move on drop with column count updates; `POST /api/commands` with `object.patch` payload; `sempkm:command-executed` dispatch on success; revert + console.error + toast on failure. `dragLeave` handler uses `contains(relatedTarget)` check to avoid flickering.

4. **base.html** — Added `kanban.js` script tag after `graph.js`.

5. **views_explorer.html** — Added "Kanban View" leaf after Graph View, with the same draggable/ondragstart/onclick pattern for canvas drag-drop and tab opening.

6. **workspace.js** — Added `kanban: 'Kanban View'` to the labels object in `openGenericViewTab()`.

## Verification

All 8 task-level checks pass. All 7 slice-level verification checks pass (including 18/18 unit tests from T01). This is the final task of S04 — all slice verification checks are green.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f backend/app/templates/browser/kanban_view.html` | 0 | ✅ pass | <1s |
| 2 | `test -f frontend/static/js/kanban.js` | 0 | ✅ pass | <1s |
| 3 | `grep -q 'Kanban View' backend/app/templates/browser/views_explorer.html` | 0 | ✅ pass | <1s |
| 4 | `grep -q 'kanban' frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 5 | `grep -q 'kanban.js' backend/app/templates/base.html` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'kanban-board' frontend/static/css/views.css` | 0 | ✅ pass | <1s |
| 7 | `grep -q 'initKanban' frontend/static/js/kanban.js` | 0 | ✅ pass | <1s |
| 8 | `grep -q 'stopPropagation' frontend/static/js/kanban.js` | 0 | ✅ pass | <1s |

### Slice-level verification (all pass — final task)

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v` | 0 | ✅ pass | 0.45s |
| 2 | `grep -q '"kanban"' backend/app/views/registry.py` | 0 | ✅ pass | <1s |
| 3 | `grep -q 'kanban' backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 4 | `test -f backend/app/templates/browser/kanban_view.html` | 0 | ✅ pass | <1s |
| 5 | `test -f frontend/static/js/kanban.js` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'Kanban View' backend/app/templates/browser/views_explorer.html` | 0 | ✅ pass | <1s |
| 7 | `grep -q 'kanban' frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |

## Diagnostics

- **Client-side errors:** `console.error('kanban: failed to patch status for', iri, err)` in browser DevTools console on failed PATCH requests.
- **Network inspection:** Drag-drop triggers `POST /api/commands` with `{"command": "object.patch", "params": {"iri": "...", "properties": {"<predicate>": "<status>"}}}` — visible in DevTools Network tab.
- **Custom event:** `sempkm:command-executed` dispatched after successful status update — other UI components (explorer, etc.) react automatically.
- **Empty states:** When no type selected → "Select a type to use Kanban View"; when type has no status property → "This type has no status-like properties for Kanban grouping"; when no columns/no data → "Select a type with status values to use Kanban View."

## Deviations

- Template uses `error_message` variable (set by router in T01) instead of `empty_message` as originally specified in the plan. The router always passes `error_message` for the no-type and no-status cases, so the template was adapted to match actual context.
- Added `contains(relatedTarget)` check in `onDragLeave` handler — not in the plan but prevents drag-over class flickering when cursor moves between child elements within the column body.

## Known Issues

- None. All planned functionality implemented and verified.

## Files Created/Modified

- `backend/app/templates/browser/kanban_view.html` — New kanban view template with type pills, toolbar, status columns, draggable cards, and empty states
- `frontend/static/js/kanban.js` — New drag-drop module with dockview isolation, optimistic moves, object.patch POST, and error handling
- `frontend/static/css/views.css` — Added kanban board/column/card CSS styles (~90 lines)
- `backend/app/templates/base.html` — Added kanban.js script tag after graph.js
- `backend/app/templates/browser/views_explorer.html` — Added "Kanban View" explorer sidebar leaf entry
- `frontend/static/js/workspace.js` — Added `kanban: 'Kanban View'` label to openGenericViewTab()
- `.gsd/milestones/M031/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
