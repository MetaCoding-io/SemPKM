# S01: Explorer Mode Infrastructure

**Goal:** Explorer pane has a working mode dropdown that switches between "By Type" (default, current behavior preserved) and placeholder modes — the tree re-renders via htmx on mode change.
**Demo:** User opens workspace, sees "By Type" in the OBJECTS dropdown, types and objects load as before. Switching to "By Hierarchy" or "By Tag" renders placeholder content. Switching back to "By Type" restores the real tree. Multi-select, drag-drop, bulk delete, and `refreshNavTree()` all continue working.

## Must-Haves

- Mode dropdown in OBJECTS section header with "By Type", "By Hierarchy", "By Tag" options
- `GET /browser/explorer/tree?mode={mode}` endpoint dispatches to mode registry
- By-type handler reuses existing `nav_tree` logic (types + lazy children expansion)
- Placeholder handlers for `hierarchy` and `by-tag` return styled empty-state HTML
- `refreshNavTree()` reads current dropdown value and hits mode-aware endpoint
- Multi-select (`selectedIris`) cleared on mode switch — no stale selection state
- `_addTypeCreateEntries(ninja)` still populates command palette on any mode change
- Lucide icons re-initialized after htmx swaps
- `#section-objects` DOM ID, `data-testid="nav-section"`, `data-testid="nav-item"` preserved
- tree-leaf/tree-node CSS classes emitted consistently across all modes
- Initial page load server-renders by-type tree (no flash of empty content)
- Mode persisted in localStorage, restored on workspace init
- EXP-01: dropdown switches between modes with htmx re-render
- EXP-02: by-type mode is the default, identical to current behavior

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (Docker Compose stack for E2E)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_explorer_modes.py -v` — unit tests for mode registry, mode dispatch, handler returns
- `cd e2e && npx playwright test tests/19-explorer-modes/explorer-mode-switching.spec.ts` — E2E: dropdown visible, mode switch re-renders tree, by-type shows real types, placeholder modes show empty-state, multi-select clears on switch, refreshNavTree respects mode
- Manual: `curl http://localhost:8001/browser/explorer/tree?mode=by-type` returns nav tree HTML
- Manual: `curl http://localhost:8001/browser/explorer/tree?mode=hierarchy` returns placeholder HTML
- Manual: `curl http://localhost:8001/browser/explorer/tree?mode=invalid` returns 400

## Observability / Diagnostics

- Runtime signals: Logger `app.browser.workspace` logs mode dispatch at DEBUG level (`"Explorer tree requested: mode=%s"`)
- Inspection surfaces: `GET /browser/explorer/tree?mode=by-type` directly testable; dropdown value readable via JS `document.getElementById('explorer-mode-select').value`
- Failure visibility: Unknown mode returns HTTP 400 with JSON `{"detail": "Unknown explorer mode: {mode}"}`. Handler exceptions logged with traceback at ERROR level.
- Redaction constraints: none (no secrets in explorer)

## Integration Closure

- Upstream surfaces consumed: `ShapesService.get_types()`, `IconService.get_icon_map()`, `LabelService.resolve_batch()` — all existing, no changes
- New wiring introduced in this slice:
  - `explorer_modes` registry dict in `workspace.py` mapping mode IDs to async handler functions
  - `GET /browser/explorer/tree` endpoint dispatching to registry
  - `<select id="explorer-mode-select">` in workspace.html OBJECTS header with `hx-get` + `hx-include`
  - `refreshNavTree()` updated to read dropdown value
  - localStorage persistence of `sempkm_explorer_mode`
- What remains before the milestone is truly usable end-to-end:
  - S02 registers `hierarchy` handler (real content replaces placeholder)
  - S03 registers VFS mount handlers and injects dynamic dropdown entries
  - S04 registers `by-tag` handler
  - S05 adds FAVORITES section (separate from mode system)

## Tasks

- [x] **T01: Create test files and mode registry with by-type handler** `est:1h`
  - Why: Establishes the mode registry pattern, refactors existing nav-tree logic into the by-type handler, and creates test files that define the acceptance criteria (initially failing for the full feature, passing for the registry unit)
  - Files: `backend/app/browser/workspace.py`, `backend/tests/test_explorer_modes.py`, `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts`
  - Do: (1) Add `EXPLORER_MODES` dict in workspace.py mapping mode IDs to async handler functions. (2) Create `_handle_by_type` handler extracting logic from `nav_tree()`. (3) Add placeholder handlers `_handle_hierarchy` and `_handle_by_tag` returning styled HTML. (4) Add `GET /browser/explorer/tree` endpoint with `mode` query param dispatching to registry, returning 400 for unknown modes. (5) Keep existing `/browser/nav-tree` endpoint for backwards compat (delegates to by-type handler). (6) Write `test_explorer_modes.py` with unit tests for registry lookup, unknown mode 400, handler signatures. (7) Write E2E test file skeleton with test cases (will fail until UI wired in T02).
  - Verify: `cd backend && python -m pytest tests/test_explorer_modes.py -v` passes; `curl localhost:8001/browser/explorer/tree?mode=by-type` returns nav tree HTML
  - Done when: Mode registry exists, by-type handler returns same HTML as `/browser/nav-tree`, placeholder handlers return styled content, unknown modes return 400, backend unit tests pass

- [x] **T02: Add mode dropdown to workspace UI and wire htmx swap** `est:45m`
  - Why: Delivers the user-facing dropdown, htmx wiring for mode switching, and connects the UI to the backend endpoint from T01
  - Files: `backend/app/templates/browser/workspace.html`, `frontend/static/css/workspace.css`, `backend/app/templates/browser/explorer_placeholder.html`
  - Do: (1) Add `<select id="explorer-mode-select" name="mode">` to OBJECTS section header with options for "By Type", "By Hierarchy", "By Tag". (2) Add `hx-get="/browser/explorer/tree"` with `hx-include="this"` and `hx-target="#explorer-tree-body"` and `hx-trigger="change"`. (3) Add `id="explorer-tree-body"` to the existing `.explorer-section-body` div inside `#section-objects`. (4) Create `explorer_placeholder.html` template for placeholder modes with icon and message. (5) Add CSS for the mode dropdown (`.explorer-mode-select`) — compact, fits in header next to action buttons. (6) Ensure `hx-on::after-swap="if(typeof lucide!=='undefined')lucide.createIcons()"` on the select for Lucide re-init after swap.
  - Verify: Docker stack up, navigate to workspace — dropdown visible in OBJECTS header, switching modes swaps tree content, by-type shows real types, placeholder modes show styled message
  - Done when: Dropdown renders in OBJECTS header, mode switching triggers htmx swap, by-type renders identical to current behavior, placeholders render with icon and message

- [x] **T03: Update refreshNavTree, clear selection on mode switch, persist mode** `est:45m`
  - Why: Ensures backwards compatibility (refreshNavTree, command palette), proper state management (selection cleared on mode switch), and UX polish (mode persisted across reloads)
  - Files: `frontend/static/js/workspace.js`, `backend/app/templates/browser/workspace.html`
  - Do: (1) Update `refreshNavTree()` to read `#explorer-mode-select` value and hit `/browser/explorer/tree?mode={value}` instead of `/browser/nav-tree`. Fall back to `/browser/nav-tree` if dropdown doesn't exist. (2) Add `change` event listener on `#explorer-mode-select` that calls `clearSelection()` before the htmx swap fires. (3) Save mode to `localStorage.setItem('sempkm_explorer_mode', value)` on change. (4) On workspace init, read `localStorage.getItem('sempkm_explorer_mode')` and set dropdown value + trigger initial load if not default. (5) Ensure `_addTypeCreateEntries(ninja)` is called after every mode swap (not just by-type) so command palette always has type-create entries. (6) Add `hx-on::after-swap` or post-swap handler to call `lucide.createIcons()` and re-apply selection UI after tree swap.
  - Verify: After switching to placeholder mode and back to by-type, objects load correctly. After selecting objects and switching mode, selection badge disappears. After setting mode to "By Tag" and reloading page, dropdown shows "By Tag". `refreshNavTree()` from console respects current mode. Command palette "Create new..." entries available in all modes.
  - Done when: refreshNavTree mode-aware, selection clears on switch, mode persists in localStorage, command palette entries always available, Lucide icons render after every swap

- [x] **T04: E2E tests and final verification** `est:45m`
  - Why: Proves EXP-01 and EXP-02 requirements are met via automated tests against running Docker stack
  - Files: `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: (1) Add explorer mode selectors to `selectors.ts`: `modeSelect`, `explorerTreeBody`. (2) Complete E2E test with cases: dropdown visible with 3 options, by-type mode shows nav sections, switching to hierarchy shows placeholder, switching to by-tag shows placeholder, switching back to by-type restores tree, multi-select + mode switch clears selection, refreshNavTree after mode switch loads correct mode. (3) Run full test suite to verify no regressions in existing nav tree tests. (4) Verify the initial server-render path (fresh page load shows by-type tree without extra htmx fetch).
  - Verify: `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list` all pass; existing `01-objects` and `03-navigation` test suites still pass
  - Done when: All E2E tests pass, no regressions in existing tests, EXP-01 and EXP-02 verified

## Files Likely Touched

- `backend/app/browser/workspace.py` — mode registry, explorer tree endpoint, by-type handler
- `backend/tests/test_explorer_modes.py` — unit tests for mode registry and dispatch
- `backend/app/templates/browser/workspace.html` — dropdown in OBJECTS header, `#explorer-tree-body` ID
- `backend/app/templates/browser/explorer_placeholder.html` — placeholder mode template
- `frontend/static/js/workspace.js` — refreshNavTree mode-awareness, selection clear, localStorage persistence
- `frontend/static/css/workspace.css` — dropdown styling
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — E2E tests
- `e2e/helpers/selectors.ts` — new explorer mode selectors
