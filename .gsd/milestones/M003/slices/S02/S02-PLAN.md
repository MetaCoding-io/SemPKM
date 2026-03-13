# S02: Hierarchy Explorer Mode

**Goal:** Replace the hierarchy mode placeholder with a working `dcterms:isPartOf`-based tree in the explorer — root objects (no parent) at top level, lazy-expanding children at arbitrary depth.
**Demo:** User switches to "By Hierarchy" mode in explorer dropdown and sees objects nested by parent/child relationships. Expanding a parent node lazy-loads its children. Objects without `dcterms:isPartOf` appear as roots. Empty state shows a descriptive message.

## Must-Haves

- `_handle_hierarchy` returns real SPARQL-driven tree of root objects (those with no `dcterms:isPartOf` parent)
- `GET /browser/explorer/children?parent={iri}` endpoint returns direct children of a given parent, with labels and per-type icons
- Hierarchy nodes are expandable `.tree-node` elements with `hx-trigger="click once"` for lazy child loading
- Hierarchy leaf click opens object tab via `handleTreeLeafClick()`
- All nodes show per-type icons (not a single icon for all hierarchy nodes)
- Empty hierarchy shows descriptive message: "No hierarchy relationships found"
- Backend unit tests cover root query, children query, handler dispatch, and children endpoint validation
- E2E tests verify hierarchy mode shows real content or appropriate empty state

## Proof Level

- This slice proves: contract + integration (SPARQL queries against real triplestore, htmx rendering verified in browser)
- Real runtime required: yes (Docker Compose stack with RDF4J for SPARQL)
- Human/UAT required: no (automated tests cover all acceptance criteria)

## Verification

- `cd backend && python -m pytest tests/test_explorer_modes.py tests/test_hierarchy_explorer.py -v` — all pass
- `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — all pass (updated hierarchy test expects real content or empty state, not placeholder)
- Manual: `GET /browser/explorer/tree?mode=hierarchy` returns tree HTML (root objects or empty state message)
- Manual: `GET /browser/explorer/children?parent={iri}` returns children HTML or empty state
- Manual: hierarchy node click in browser expands to show children, leaf click opens object tab

## Observability / Diagnostics

- Runtime signals: DEBUG log `"Hierarchy roots query returned %d objects"` and `"Hierarchy children query for %s returned %d objects"` in `app.browser.workspace` logger
- Inspection surfaces: `GET /browser/explorer/tree?mode=hierarchy` directly testable; `GET /browser/explorer/children?parent={iri}` directly testable; SPARQL queries logged at DEBUG level
- Failure visibility: HTTP 400 with structured JSON for invalid parent IRI; HTTP 400 for unknown mode (existing); SPARQL errors logged with `exc_info=True`
- Redaction constraints: none (no secrets in hierarchy queries)

## Integration Closure

- Upstream surfaces consumed: `EXPLORER_MODES` registry (S01), `#explorer-tree-body` swap target (S01), `.tree-node`/`.tree-leaf`/`.tree-children` CSS classes (existing), `LabelService.resolve_batch()`, `IconService.get_type_icon()`, `_validate_iri()` from `_helpers.py`, `handleTreeLeafClick()` from `workspace.js`
- New wiring introduced in this slice: `_handle_hierarchy` handler replaces placeholder with real SPARQL-driven implementation; new `/browser/explorer/children` endpoint for lazy child expansion; `hierarchy_tree.html` and `hierarchy_children.html` templates
- What remains before the milestone is truly usable end-to-end: S03 (VFS modes), S04 (tag mode), S05 (favorites), S06 (comments), S07 (ontology viewer), S08 (class creation), S09 (admin stats). Users also need a way to set `dcterms:isPartOf` on objects (outside this slice's scope — requires object edit form support for object properties).

## Tasks

- [x] **T01: SPARQL queries, hierarchy handler, and children endpoint** `est:45m`
  - Why: Core backend — replaces the hierarchy placeholder handler with real SPARQL queries for root objects and adds the lazy children endpoint. This is the foundational work that makes hierarchy mode functional.
  - Files: `backend/app/browser/workspace.py`, `backend/app/templates/browser/hierarchy_tree.html`, `backend/app/templates/browser/hierarchy_children.html`
  - Do: Write two SPARQL queries (roots: objects with no `dcterms:isPartOf`; children: objects where `dcterms:isPartOf` = parent IRI). Replace `_handle_hierarchy` with real handler that queries roots, resolves labels/icons, renders `hierarchy_tree.html`. Add `GET /browser/explorer/children?parent={iri}` endpoint that queries children, resolves labels/icons, renders `hierarchy_children.html`. Both templates reuse `.tree-node`/`.tree-leaf`/`.tree-children` CSS classes. Hierarchy nodes use `hx-get="/browser/explorer/children?parent={iri}"` with `hx-trigger="click once"`. Each node's leaf label has `onclick="handleTreeLeafClick(...)"`. Nodes query `rdf:type` alongside the object IRI to resolve per-type icons. All SPARQL scoped to `GRAPH <urn:sempkm:current>`. Empty state shows descriptive message.
  - Verify: `GET /browser/explorer/tree?mode=hierarchy` returns HTML (empty state message or tree nodes); `GET /browser/explorer/children?parent={valid_iri}` returns HTML; `GET /browser/explorer/children?parent=invalid` returns 400
  - Done when: hierarchy handler returns real SPARQL-driven content, children endpoint responds correctly, templates render with correct CSS classes and htmx attributes

- [x] **T02: Backend unit tests for hierarchy SPARQL and endpoint validation** `est:30m`
  - Why: Verifies the SPARQL queries, handler dispatch, and children endpoint input validation without requiring a running triplestore. Catches regressions in query structure and handler wiring.
  - Files: `backend/tests/test_hierarchy_explorer.py`, `backend/tests/test_explorer_modes.py`
  - Do: Create `test_hierarchy_explorer.py` with tests: (1) root objects SPARQL uses FILTER NOT EXISTS for `dcterms:isPartOf`, (2) children SPARQL filters by parent IRI, (3) both queries scope to `GRAPH <urn:sempkm:current>`, (4) `_handle_hierarchy` is async and callable, (5) children endpoint rejects invalid IRI with 400, (6) empty results produce empty-state HTML. Update `test_explorer_modes.py` if the handler signature changed (e.g. now accepts `label_service`). Test SPARQL query structure by inspecting the query strings or by mocking the triplestore client.
  - Verify: `cd backend && python -m pytest tests/test_hierarchy_explorer.py tests/test_explorer_modes.py -v` — all pass
  - Done when: All hierarchy-specific unit tests pass; existing explorer mode tests still pass

- [x] **T03: E2E tests and final integration verification** `est:30m`
  - Why: Proves the hierarchy mode works end-to-end in a real browser with the full stack running. Updates the existing E2E test that expected placeholder content to verify real hierarchy behavior.
  - Files: `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts`
  - Do: Update the "switching to hierarchy shows placeholder" test to verify real hierarchy mode behavior: (1) switch to hierarchy mode, (2) verify either tree nodes or descriptive empty-state message appears (not placeholder), (3) verify no `[data-testid="explorer-placeholder"]` is shown. Keep within 5-test limit. Test the empty state message content ("No hierarchy relationships found" or similar). If test data with `dcterms:isPartOf` can be created via existing API, test lazy expansion of a hierarchy node.
  - Verify: `cd e2e && npx playwright test tests/19-explorer-modes/ --reporter=list --project=chromium` — all 5 pass; `cd backend && python -m pytest tests/test_explorer_modes.py tests/test_hierarchy_explorer.py -v` — all pass
  - Done when: All E2E tests pass with updated hierarchy assertions; all backend tests pass; hierarchy mode shows real content or meaningful empty state in the browser

## Files Likely Touched

- `backend/app/browser/workspace.py` — replace `_handle_hierarchy` placeholder, add children endpoint
- `backend/app/templates/browser/hierarchy_tree.html` — new template for root hierarchy nodes
- `backend/app/templates/browser/hierarchy_children.html` — new template for lazy-loaded child nodes
- `backend/tests/test_hierarchy_explorer.py` — new test file for hierarchy-specific tests
- `backend/tests/test_explorer_modes.py` — update if handler signature changed
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — update hierarchy test from placeholder to real behavior
