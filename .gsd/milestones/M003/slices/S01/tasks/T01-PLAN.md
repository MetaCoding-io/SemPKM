---
estimated_steps: 5
estimated_files: 4
---

# T01: Create test files and mode registry with by-type handler

**Slice:** S01 — Explorer Mode Infrastructure
**Milestone:** M003

## Description

Establish the `EXPLORER_MODES` registry pattern in `workspace.py`, refactor the existing `nav_tree()` logic into a `_handle_by_type` handler function, add placeholder handlers for `hierarchy` and `by-tag`, and create the `GET /browser/explorer/tree?mode={mode}` endpoint. Also create test files (backend unit + E2E skeleton) that define the acceptance criteria for the full slice.

The existing `/browser/nav-tree` endpoint remains for backwards compatibility — it delegates to the by-type handler internally. This ensures `refreshNavTree()` continues to work before T03 updates it.

## Steps

1. **Add mode registry and handlers to `workspace.py`:**
   - Define `EXPLORER_MODES: dict[str, Callable]` mapping `"by-type"` → `_handle_by_type`, `"hierarchy"` → `_handle_hierarchy`, `"by-tag"` → `_handle_by_tag`
   - Extract `_handle_by_type(request, shapes_service, icon_svc)` from the existing `nav_tree()` body — queries `get_types()`, gets `icon_map`, renders `nav_tree.html`
   - `_handle_hierarchy(request)` returns an HTML string: styled placeholder with compass icon and "Hierarchy mode — coming soon" text
   - `_handle_by_tag(request)` returns an HTML string: styled placeholder with tag icon and "Tag mode — coming soon" text
   - Update `nav_tree()` to call `_handle_by_type()` internally (no duplicate logic)

2. **Add `GET /browser/explorer/tree` endpoint:**
   - `explorer_tree(request, mode: str = "by-type", ...)` with `Depends` for shapes_service, icon_svc
   - Look up handler in `EXPLORER_MODES`; if not found, raise `HTTPException(400, detail=f"Unknown explorer mode: {mode}")`
   - Call handler and return its response
   - Log mode dispatch at DEBUG level

3. **Create `explorer_placeholder.html` template:**
   - Simple Jinja2 template accepting `mode_label` and `icon_name` context vars
   - Renders a `.tree-empty` div with an icon and message: "Switch to By Type to browse objects, or install models."
   - Uses same CSS classes as existing `.tree-empty` for consistency

4. **Write `backend/tests/test_explorer_modes.py`:**
   - Test that `EXPLORER_MODES` contains exactly `{"by-type", "hierarchy", "by-tag"}`
   - Test that all handlers are callable (async functions)
   - Test registry lookup returns correct handler for each mode
   - Test that unknown mode key is not in registry (validates the 400 path logic at unit level)
   - Note: full HTTP-level tests require running server — covered by E2E in T04

5. **Create E2E test skeleton `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts`:**
   - Import auth fixtures and selectors
   - Define test.describe block with placeholder test cases (marked `test.skip` or `test.fixme`):
     - "dropdown visible with three mode options"
     - "by-type mode shows nav sections"
     - "switching to hierarchy shows placeholder"
     - "switching back to by-type restores tree"
     - "multi-select clears on mode switch"
   - These tests will be implemented in T04 after the UI is wired

## Must-Haves

- [ ] `EXPLORER_MODES` dict exists in `workspace.py` with 3 entries
- [ ] `_handle_by_type` produces identical HTML to current `nav_tree()` endpoint
- [ ] `/browser/explorer/tree?mode=by-type` returns 200 with nav tree HTML
- [ ] `/browser/explorer/tree?mode=hierarchy` returns 200 with placeholder HTML
- [ ] `/browser/explorer/tree?mode=invalid` returns 400
- [ ] `/browser/nav-tree` still works (backwards compat)
- [ ] Backend unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_explorer_modes.py -v` — all tests pass
- `curl -s http://localhost:8001/browser/explorer/tree?mode=by-type` — returns HTML with `tree-node` elements (when models installed)
- `curl -s http://localhost:8001/browser/explorer/tree?mode=hierarchy` — returns placeholder HTML
- `curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/browser/explorer/tree?mode=invalid` — returns 400

## Observability Impact

- Signals added/changed: DEBUG log `"Explorer tree requested: mode=%s"` in `workspace` logger
- How a future agent inspects this: `EXPLORER_MODES.keys()` shows registered modes; `/browser/explorer/tree?mode=X` directly testable
- Failure state exposed: HTTP 400 with `{"detail": "Unknown explorer mode: {mode}"}` for invalid modes; ERROR log with traceback for handler exceptions

## Inputs

- `backend/app/browser/workspace.py` — existing `nav_tree()` endpoint to refactor
- `backend/app/templates/browser/nav_tree.html` — template used by by-type handler
- `e2e/fixtures/auth.ts` — auth fixture pattern for E2E test skeleton
- `e2e/helpers/selectors.ts` — existing selector pattern

## Expected Output

- `backend/app/browser/workspace.py` — mode registry, handlers, and `/browser/explorer/tree` endpoint added
- `backend/app/templates/browser/explorer_placeholder.html` — placeholder template created
- `backend/tests/test_explorer_modes.py` — unit tests passing
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — test skeleton created (tests skipped)
