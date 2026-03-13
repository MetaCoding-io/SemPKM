---
id: T01
parent: S01
milestone: M003
provides:
  - EXPLORER_MODES registry with by-type, hierarchy, by-tag handlers
  - GET /browser/explorer/tree endpoint with mode dispatch
  - explorer_placeholder.html template for placeholder modes
  - Backend unit tests for mode registry
  - E2E test skeleton for explorer mode switching
key_files:
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/explorer_placeholder.html
  - backend/tests/test_explorer_modes.py
  - e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts
key_decisions:
  - Placeholder handlers accept **_kwargs to absorb extra dispatch args (shapes_service, icon_svc) they don't need
  - explorer_tree endpoint passes all dependencies to every handler — handlers ignore what they don't use
patterns_established:
  - EXPLORER_MODES dict[str, Callable] as the single source of truth for mode registration
  - Handler signature: async fn(request, shapes_service, icon_svc) -> HTMLResponse
  - New modes added by inserting into EXPLORER_MODES dict; no other wiring needed
observability_surfaces:
  - DEBUG log "Explorer tree requested: mode=%s" in app.browser.workspace logger
  - HTTP 400 with {"detail": "Unknown explorer mode: {mode}"} for invalid modes
  - EXPLORER_MODES.keys() inspectable at runtime for registered modes
duration: 20m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Create test files and mode registry with by-type handler

**Added EXPLORER_MODES registry with 3 handlers, GET /browser/explorer/tree endpoint, placeholder template, unit tests, and E2E skeleton.**

## What Happened

Refactored `workspace.py` to extract the nav tree logic into `_handle_by_type()` handler and added two placeholder handlers (`_handle_hierarchy`, `_handle_by_tag`). These are registered in the `EXPLORER_MODES` dict. The existing `/browser/nav-tree` endpoint now delegates to `_handle_by_type()` — verified to produce identical HTML output.

Added `GET /browser/explorer/tree?mode={mode}` endpoint that dispatches to the registry, returning 400 for unknown modes with a structured JSON error.

Created `explorer_placeholder.html` Jinja2 template using the existing `.tree-empty` CSS class for consistent styling.

Wrote 8 backend unit tests covering registry contents, handler callability, async signatures, correct mapping, and unknown mode rejection. All pass.

Created E2E test skeleton with 5 `test.fixme` cases covering dropdown visibility, mode switching, tree restoration, and selection clearing — to be implemented in T04.

## Verification

- `cd backend && python -m pytest tests/test_explorer_modes.py -v` — **8/8 passed**
- `GET /browser/explorer/tree?mode=by-type` → 200, HTML with tree-node elements (2446 bytes)
- `GET /browser/explorer/tree?mode=hierarchy` → 200, placeholder HTML with compass icon
- `GET /browser/explorer/tree?mode=by-tag` → 200, placeholder HTML with tag icon
- `GET /browser/explorer/tree?mode=invalid` → 400, `{"detail":"Unknown explorer mode: invalid"}`
- `GET /browser/nav-tree` → 200, identical HTML to by-type mode (backwards compat confirmed)
- `/browser/nav-tree` and `/browser/explorer/tree?mode=by-type` produce byte-identical responses

### Slice-level verification status (T01 is first of 4 tasks):
- ✅ `cd backend && python -m pytest tests/test_explorer_modes.py -v` — all pass
- ⏳ `cd e2e && npx playwright test tests/19-explorer-modes/` — skeleton created, tests marked fixme (T04)
- ✅ Manual: `curl .../explorer/tree?mode=by-type` returns nav tree HTML
- ✅ Manual: `curl .../explorer/tree?mode=hierarchy` returns placeholder HTML
- ✅ Manual: `curl .../explorer/tree?mode=invalid` returns 400

## Diagnostics

- `EXPLORER_MODES.keys()` shows registered modes — inspectable via `docker compose exec api python -c "from app.browser.workspace import EXPLORER_MODES; print(list(EXPLORER_MODES.keys()))"`
- `GET /browser/explorer/tree?mode=X` directly testable for any mode
- Unknown modes return HTTP 400 with `{"detail": "Unknown explorer mode: {mode}"}`
- DEBUG-level log `"Explorer tree requested: mode=%s"` emitted on every dispatch (visible with DEBUG logging enabled)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/workspace.py` — Added EXPLORER_MODES registry, _handle_by_type, _handle_hierarchy, _handle_by_tag handlers, explorer_tree endpoint; refactored nav_tree to delegate to _handle_by_type
- `backend/app/templates/browser/explorer_placeholder.html` — New template for placeholder modes with icon and message
- `backend/tests/test_explorer_modes.py` — 8 unit tests for mode registry
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — E2E test skeleton with 5 fixme test cases
