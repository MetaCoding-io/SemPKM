# S10: E2E Test Coverage Gaps

**Goal:** Achieve comprehensive e2e test coverage for all shipped SemPKM features. Every backend route and user-visible UI feature should have at least one Playwright e2e test.
**Demo:** Running `npx playwright test --project=chromium` exercises all feature areas — object/edge deletion, edge.patch, event undo, spatial canvas, bottom-panel SPARQL, admin model lifecycle, rate limiting, LLM config, federation UI, SPARQL advanced features, pagination, tooltips, edge provenance, markdown rendering, health check, column preferences, sidebar panel reorder, and graph node interaction all have green tests.

## Must-Haves

- All 27 `test.skip()` stubs in `17-spatial-canvas/` replaced with real implementations
- Object deletion (single + bulk) tested via API and UI
- Edge deletion tested via API
- `edge.patch` command tested via API
- Event undo (compensating events) tested via API
- Spatial canvas session save/load and subgraph loading tested
- Bottom-panel SPARQL workspace panel tested (distinct from admin console)
- Admin model install/uninstall lifecycle tested end-to-end
- Auth rate limiting (429 response) tested
- LLM config save/test endpoints tested
- Federation UI partials (inbox, collab panel, shared graph management) tested
- SPARQL advanced features (saved queries, server-side history) tested
- Table view pagination tested
- Object tooltip endpoint tested
- Edge provenance endpoint tested
- Markdown rendering fidelity tested (headers, bold, code, XSS sanitization)
- Health check endpoint tested
- Column visibility preferences persistence tested
- Sidebar panel drag-drop reorder persistence tested
- Graph view node click → open object tested
- Admin model detail page and ontology diagram tested
- Admin webhook deletion tested
- Event log detail expansion tested
- VFS MountSpec management tested
- User guide docs navigation tested
- Debug pages access control tested
- Auth invite flow (owner invites user) tested

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (Docker test stack)
- Human/UAT required: no

## Verification

- `cd e2e && npx playwright test --project=chromium` — all new tests pass
- `rg "test\.skip\(" e2e/tests/ -c -g '*.ts' | awk -F: '{sum+=$2} END{print sum}'` — returns 0 (no remaining stubs)
- Every backend router module (`find backend/app -name 'router.py'`) has at least one corresponding e2e test exercising its routes

## Observability / Diagnostics

- Runtime signals: Playwright test runner output with pass/fail per test
- Inspection surfaces: `npx playwright show-report` for HTML test report
- Failure visibility: Playwright traces + screenshots on failure (already configured)
- Redaction constraints: none (test code only)

## Integration Closure

- Upstream surfaces consumed: all existing backend routers, existing auth fixtures, seed data
- New wiring introduced in this slice: none (test-only, no production code changes)
- What remains before the milestone is truly usable end-to-end: nothing for this slice

## Tasks

- [x] **T01: Object & edge deletion tests** `est:1h`
  - Why: Object deletion (single + bulk via `POST /browser/objects/delete`) and edge deletion (`POST /browser/edge/delete`) are core CRUD operations with zero e2e coverage. `edge.patch` command handler also has zero coverage.
  - Files: `e2e/tests/01-objects/delete-object.spec.ts`, `e2e/tests/01-objects/delete-edge.spec.ts`, `e2e/tests/01-objects/edge-patch.spec.ts`
  - Do: Create test that creates an object via API, deletes it via `POST /browser/objects/delete`, verifies it's gone from nav tree. Create bulk delete test (create 3 objects, select all, delete, verify). Create edge deletion test (create edge, delete it, verify relations panel empty). Create `edge.patch` test (create edge, patch its predicate, verify change persists). Use existing auth fixtures.
  - Verify: `npx playwright test tests/01-objects/delete-object.spec.ts tests/01-objects/delete-edge.spec.ts tests/01-objects/edge-patch.spec.ts`
  - Done when: All 4 test files pass — single delete, bulk delete, edge delete, and edge.patch confirmed working

- [x] **T02: Event undo & event log detail tests** `est:45m`
  - Why: Event undo (`POST /browser/events/{event_iri}/undo`) creates compensating events but has zero coverage. Event log detail expansion (`GET /browser/events/{event_iri}/detail`) is also untested.
  - Files: `e2e/tests/06-settings/event-undo.spec.ts`
  - Do: Create an object via API, capture the event IRI. Open event log bottom panel, verify the event row appears. Click event row to expand detail view, verify diff content loads. Call undo endpoint for the event, verify the object is removed/reverted. Verify undo event appears in log.
  - Verify: `npx playwright test tests/06-settings/event-undo.spec.ts`
  - Done when: Event detail expansion and undo round-trip verified end-to-end

- [x] **T03: Spatial canvas tests — implement all 27 stubs** `est:2h`
  - Why: All 27 tests in `17-spatial-canvas/` are `test.skip()` stubs with zero implementation. Canvas is a shipped v2.6 feature.
  - Files: `e2e/tests/17-spatial-canvas/snap-to-grid.spec.ts`, `e2e/tests/17-spatial-canvas/edge-labels.spec.ts`, `e2e/tests/17-spatial-canvas/keyboard-nav.spec.ts`, `e2e/tests/17-spatial-canvas/bulk-drop.spec.ts`, `e2e/tests/17-spatial-canvas/wiki-link-edges.spec.ts`, `e2e/tests/17-spatial-canvas/canvas-sessions.spec.ts`
  - Do: Replace all `test.skip()` stubs with real implementations. Add a new `canvas-sessions.spec.ts` for session save/load (`POST /api/canvas/sessions`, `GET /api/canvas/{id}`) and subgraph loading (`GET /api/canvas/subgraph`). For snap-to-grid: navigate to canvas, add node via API, verify position is grid-aligned. For edge-labels: create edge between objects, verify label text uses predicate label. For keyboard-nav: add nodes, test arrow keys, Tab cycling, Escape, Delete. For bulk-drop: test multi-select from nav tree. For wiki-link-edges: create objects with wiki-links in body, verify dashed edge rendering.
  - Verify: `npx playwright test tests/17-spatial-canvas/`
  - Done when: All 27 stubs replaced with real tests + canvas session tests added, `rg "test\.skip\(" e2e/tests/17-spatial-canvas/ -c` returns 0

- [x] **T04: Bottom-panel SPARQL & SPARQL advanced features tests** `est:1h`
  - Why: The SPARQL workspace bottom panel (distinct from admin console at `/admin/sparql`) is untested. v2.6 SPARQL advanced features (saved queries, server-side history, shared queries, promoted queries as named views, ontology-aware autocomplete, IRI pill links) have zero coverage.
  - Files: `e2e/tests/05-admin/sparql-workspace.spec.ts`, `e2e/tests/05-admin/sparql-advanced.spec.ts`
  - Do: Test workspace bottom panel: open via `panel-tab[data-panel="sparql"]`, verify Yasgui initializes, execute a query, verify results. Test saved queries: save a query, verify it appears in list, load it, verify content. Test server-side history: execute queries, verify history endpoint returns them. Test IRI pill rendering: execute a query returning IRIs, verify pills render with labels.
  - Verify: `npx playwright test tests/05-admin/sparql-workspace.spec.ts tests/05-admin/sparql-advanced.spec.ts`
  - Done when: Bottom-panel SPARQL, saved queries, history, and IRI pills all verified

- [x] **T05: Admin model lifecycle & admin detail pages tests** `est:1h`
  - Why: Admin model install/uninstall is a core admin workflow but only the form's existence is verified — no actual install/remove operation is tested. Model detail page (`/admin/models/{model_id}`), ontology diagram, and webhook deletion are also untested.
  - Files: `e2e/tests/05-admin/admin-model-lifecycle.spec.ts`, `e2e/tests/05-admin/admin-model-detail.spec.ts`
  - Do: Test model detail page: navigate to `/admin/models/basic-pkm`, verify page loads with model info, stats, type list. Test ontology diagram: navigate to `/admin/models/basic-pkm/ontology-diagram`, verify SVG or diagram renders. Test model install: use the PPV model path to install, verify it appears in model list. Test model uninstall: remove the just-installed model, verify it disappears. Test webhook delete: create a webhook, delete it, verify it's gone from list.
  - Verify: `npx playwright test tests/05-admin/admin-model-lifecycle.spec.ts tests/05-admin/admin-model-detail.spec.ts`
  - Done when: Full model install → detail → uninstall cycle verified; webhook CRUD complete; ontology diagram renders

- [x] **T06: Auth rate limiting & invite flow tests** `est:45m`
  - Why: Rate limiting via slowapi (M002 SEC-01) has zero e2e verification. The owner invite flow (`POST /api/auth/invite`) is only tested as a permission denial for members, never as a successful owner operation.
  - Files: `e2e/tests/00-setup/rate-limiting.spec.ts`, `e2e/tests/07-multi-user/invite-flow.spec.ts`
  - Do: Rate limiting: send magic-link requests in rapid succession (>5 per minute), verify 429 response. Invite flow: owner invites a new email via API, verify invite response, verify invited user can log in with the invite token, verify they get member role.
  - Verify: `npx playwright test tests/00-setup/rate-limiting.spec.ts tests/07-multi-user/invite-flow.spec.ts`
  - Done when: 429 rate limit verified; full invite → accept → login cycle verified

- [x] **T07: LLM config, tooltip, edge provenance, health check tests** `est:1h`
  - Why: LLM config routes (`PUT /browser/llm/config`, `POST /browser/llm/test`), object tooltip (`GET /browser/tooltip/{iri}`), edge provenance (`GET /browser/edge-provenance`), and health check (`GET /api/health`) all have zero coverage.
  - Files: `e2e/tests/06-settings/llm-config.spec.ts`, `e2e/tests/01-objects/tooltip-and-provenance.spec.ts`, `e2e/tests/00-setup/health-check.spec.ts`
  - Do: LLM config: open settings, navigate to LLM category (if exists), verify config form renders, test save endpoint returns success (without real API key — verify form submission mechanics). Tooltip: create an object, fetch tooltip endpoint, verify HTML response includes object label and type. Edge provenance: create an edge, query provenance endpoint with source+target+predicate params, verify provenance data returned. Health check: GET `/api/health`, verify JSON structure with status, services, version.
  - Verify: `npx playwright test tests/06-settings/llm-config.spec.ts tests/01-objects/tooltip-and-provenance.spec.ts tests/00-setup/health-check.spec.ts`
  - Done when: All 4 endpoint categories verified with correct response shapes

- [x] **T08: Federation UI, VFS MountSpec, debug pages tests** `est:1h`
  - Why: Federation UI partials (inbox, collab panel, contact list), VFS MountSpec management, and debug page access control have zero coverage.
  - Files: `e2e/tests/18-federation/federation-ui.spec.ts`, `e2e/tests/13-v24-coverage/vfs-mountspec.spec.ts`, `e2e/tests/05-admin/debug-pages.spec.ts`
  - Do: Federation UI: verify inbox partial loads (`GET /api/federation/inbox-partial`), collab partial loads (`GET /api/federation/collab-partial`), shared graph list returns valid JSON, contact list endpoint works. VFS MountSpec: verify mount management UI elements exist in VFS settings, test creating a mount spec (if UI exists), verify it appears in list. Debug pages: verify `/debug/sparql` returns 200 for owner, 403 for member; verify `/debug/events` returns 200 for owner, 403 for member.
  - Verify: `npx playwright test tests/18-federation/federation-ui.spec.ts tests/13-v24-coverage/vfs-mountspec.spec.ts tests/05-admin/debug-pages.spec.ts`
  - Done when: Federation UI partials, VFS mount management, and debug access control all verified

- [x] **T09: Table pagination, graph node click, view filtering tests** `est:45m`
  - Why: Table view pagination, graph view node click → open object, and view-level filtering are untested interaction paths.
  - Files: `e2e/tests/02-views/table-pagination.spec.ts`, `e2e/tests/02-views/graph-interaction.spec.ts`
  - Do: Table pagination: create enough objects (>10) to trigger pagination, verify pagination controls appear, click next page, verify new rows load, verify page indicator updates. Graph node click: load a graph view, verify nodes render in Cytoscape, click a node, verify object tab opens. View filtering: if views have search/filter inputs, verify typing filters visible results.
  - Verify: `npx playwright test tests/02-views/table-pagination.spec.ts tests/02-views/graph-interaction.spec.ts`
  - Done when: Pagination navigation, graph node click-through, and view filtering all verified

- [x] **T10: Markdown rendering, column prefs, sidebar reorder, docs navigation tests** `est:1h`
  - Why: Markdown rendering fidelity (including XSS sanitization via DOMPurify), table column visibility persistence, sidebar panel drag-drop reorder, and user guide docs page navigation all have zero coverage.
  - Files: `e2e/tests/01-objects/markdown-rendering.spec.ts`, `e2e/tests/02-views/column-preferences.spec.ts`, `e2e/tests/03-navigation/sidebar-panel-reorder.spec.ts`, `e2e/tests/06-settings/docs-navigation.spec.ts`
  - Do: Markdown: create object with markdown body (headers, bold, links, code blocks, `<script>` tag), open in read mode, verify rendered HTML has correct elements, verify `<script>` tag is sanitized. Column prefs: open table view, toggle a column off, verify it disappears, reload page, verify preference persists via localStorage. Sidebar reorder: drag a panel to a new position, verify DOM order changed, reload, verify position persisted. Docs navigation: open docs tab, click through guide pages, verify content loads for each page.
  - Verify: `npx playwright test tests/01-objects/markdown-rendering.spec.ts tests/02-views/column-preferences.spec.ts tests/03-navigation/sidebar-panel-reorder.spec.ts tests/06-settings/docs-navigation.spec.ts`
  - Done when: Markdown renders correctly with XSS blocked, column prefs persist, panel positions persist, guide pages navigate correctly

- [x] **T11: Lint API, validation endpoints, monitoring config, icons, my-views tests** `est:45m`
  - Why: Several API endpoints have zero direct e2e coverage: lint results/status/diff/stream APIs (`/api/lint/*`), validation latest/by-event (`/api/validation/*`), monitoring config (`/api/monitoring/config`), icons (`/browser/icons`), and my-views (`/browser/my-views`).
  - Files: `e2e/tests/04-validation/lint-api.spec.ts`, `e2e/tests/04-validation/validation-api.spec.ts`, `e2e/tests/06-settings/misc-endpoints.spec.ts`
  - Do: Lint API: GET `/api/lint/results`, verify paginated response shape; GET `/api/lint/status`, verify status response; GET `/api/lint/diff`, verify diff response. Validation: GET `/api/validation/latest`, verify latest validation result shape. Monitoring: GET `/api/monitoring/config`, verify PostHog config response (may be empty/disabled). Icons: GET `/browser/icons`, verify JSON response with icon mappings. My-views: GET `/browser/my-views`, verify HTML fragment with view links.
  - Verify: `npx playwright test tests/04-validation/lint-api.spec.ts tests/04-validation/validation-api.spec.ts tests/06-settings/misc-endpoints.spec.ts`
  - Done when: All remaining API endpoints have response shape verification

- [x] **T12: Final coverage audit & zero-skip verification** `est:30m`
  - Why: Verify the entire gap list is closed — no `test.skip()` stubs remain, every backend router has at least one e2e test, and the full suite passes.
  - Files: (no new files — audit only)
  - Do: Run `rg "test\.skip\(" e2e/tests/ -c -g '*.ts'` and verify it returns 0. Run `find backend/app -name 'router.py' | sort` and cross-reference each module against `find e2e/tests -name '*.spec.ts' | sort` to confirm coverage. Run the full test suite. Fix any flakes or failures. Update the CODEBASE.md E2E tests table to reflect the new test count and directory structure.
  - Verify: `cd e2e && npx playwright test --project=chromium` — full green suite
  - Done when: Zero `test.skip()` stubs, every router module has e2e coverage, full suite passes, CODEBASE.md updated

## Files Likely Touched

- `e2e/tests/01-objects/delete-object.spec.ts` (new)
- `e2e/tests/01-objects/delete-edge.spec.ts` (new)
- `e2e/tests/01-objects/edge-patch.spec.ts` (new)
- `e2e/tests/01-objects/tooltip-and-provenance.spec.ts` (new)
- `e2e/tests/01-objects/markdown-rendering.spec.ts` (new)
- `e2e/tests/00-setup/health-check.spec.ts` (new)
- `e2e/tests/00-setup/rate-limiting.spec.ts` (new)
- `e2e/tests/02-views/table-pagination.spec.ts` (new)
- `e2e/tests/02-views/graph-interaction.spec.ts` (new)
- `e2e/tests/02-views/column-preferences.spec.ts` (new)
- `e2e/tests/03-navigation/sidebar-panel-reorder.spec.ts` (new)
- `e2e/tests/04-validation/lint-api.spec.ts` (new)
- `e2e/tests/04-validation/validation-api.spec.ts` (new)
- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` (new)
- `e2e/tests/05-admin/admin-model-detail.spec.ts` (new)
- `e2e/tests/05-admin/sparql-workspace.spec.ts` (new)
- `e2e/tests/05-admin/sparql-advanced.spec.ts` (new)
- `e2e/tests/05-admin/debug-pages.spec.ts` (new)
- `e2e/tests/06-settings/event-undo.spec.ts` (new)
- `e2e/tests/06-settings/llm-config.spec.ts` (new)
- `e2e/tests/06-settings/docs-navigation.spec.ts` (new)
- `e2e/tests/06-settings/misc-endpoints.spec.ts` (new)
- `e2e/tests/07-multi-user/invite-flow.spec.ts` (new)
- `e2e/tests/13-v24-coverage/vfs-mountspec.spec.ts` (new)
- `e2e/tests/17-spatial-canvas/snap-to-grid.spec.ts` (rewrite)
- `e2e/tests/17-spatial-canvas/edge-labels.spec.ts` (rewrite)
- `e2e/tests/17-spatial-canvas/keyboard-nav.spec.ts` (rewrite)
- `e2e/tests/17-spatial-canvas/bulk-drop.spec.ts` (rewrite)
- `e2e/tests/17-spatial-canvas/wiki-link-edges.spec.ts` (rewrite)
- `e2e/tests/17-spatial-canvas/canvas-sessions.spec.ts` (new)
- `e2e/tests/18-federation/federation-ui.spec.ts` (new)
- `CODEBASE.md` (update E2E tests table)
