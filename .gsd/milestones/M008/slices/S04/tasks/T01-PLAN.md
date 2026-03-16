---
estimated_steps: 8
estimated_files: 2
---

# T01: E2E Playwright Tests for Property Flip and Embeds

**Slice:** S04 — E2E Tests & User Guide
**Milestone:** M008

## Description

Create two Playwright E2E spec files that exercise the property flip (S02) and live embed (S03) features against the real running system. Resize already has full E2E coverage (`canvas-resize.spec.ts`). Follow the established combined-test-per-file pattern to respect magic-link rate limits (5/minute).

## Steps

1. Create `e2e/tests/17-spatial-canvas/canvas-property-flip.spec.ts`:
   - Import from `../../fixtures/auth` (`test`, `expect`, `BASE_URL`), `../../fixtures/seed-data` (`SEED`), `../../helpers/wait-for` (`waitForWorkspace`)
   - Copy the `openCanvas()` helper pattern from `canvas-resize.spec.ts` (goto → waitForWorkspace → openCanvasTab → waitForSelector → waitForFunction)
   - Write `test.describe('Spatial Canvas: Property Flip', () => { ... })` with two combined tests:
   - **API test** (`ownerRequest`): `GET /api/canvas/properties?iri=${SEED.notes.architecture.iri}` — verify 200, response has `properties` array (length > 0) and `type_label` string. Also verify `?iri=invalid` returns 400.
   - **UI test** (`ownerPage`): Open canvas, import a node with `SEED.notes.architecture.iri`, verify flip button exists (`.spatial-node-flip`), click it, verify property table appears (`.spatial-node-property-table`), verify `exportState()` node has `showProperties: true`. Click flip again, verify markdown body returns, `showProperties` goes false/absent. Then test persistence: import a node with `showProperties: true` via `importState()`, verify property table fetches and renders. Test backward compat: import a node without `showProperties`, verify no error and markdown body shown.

2. Create `e2e/tests/17-spatial-canvas/canvas-embeds.spec.ts`:
   - Same imports and `openCanvas()` helper
   - Write `test.describe('Spatial Canvas: Embeds', () => { ... })` with two combined tests:
   - **API test** (`ownerRequest`):
     - Create a session with an embed node (nodeType: 'embed', embedConfig: {type: 'view', id: 'table', url: '/browser/views/generic/table?embed=1', label: 'Table View'}). Load it back, verify nodeType and embedConfig preserved.
     - Create a session without nodeType fields — load back, verify no errors and nodeType is undefined (backward compat).
     - `GET /browser/views/generic/table?embed=1` — verify response includes `X-Embed-Mode: 1` header.
   - **UI test** (`ownerPage`): Open canvas, verify Embed toolbar button exists, click it to open picker, verify picker tabs appear (Views/Dashboards/Queries). Place a view embed: click the Views tab, wait for rows to load, click first row — verify `exportState()` has a node with `nodeType: 'embed'`. Test max-8: use `SemPKMCanvas.addEmbed()` to add 8 embeds, try 9th, verify rejection (exportState still has 8 embed nodes or toast appeared). Test mixed save/load: import a document with 2 regular nodes + 1 embed node via `importState()`, verify `exportState()` returns all 3 with correct types.

3. Run the full spatial canvas E2E suite to verify all 5 specs pass together:
   ```bash
   cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list
   ```

4. Run existing backend unit tests to verify no regressions:
   ```bash
   cd backend && .venv/bin/pytest tests/test_canvas_properties.py tests/test_canvas_embeds.py tests/test_canvas_resize.py -v
   ```

## Must-Haves

- [ ] `canvas-property-flip.spec.ts` has API test for `/api/canvas/properties` endpoint (200 with valid IRI, 400 with invalid)
- [ ] `canvas-property-flip.spec.ts` has UI test for flip button toggle, property table rendering, showProperties persistence, backward compat
- [ ] `canvas-embeds.spec.ts` has API test for embed node serialization round-trip, backward compat, X-Embed-Mode header
- [ ] `canvas-embeds.spec.ts` has UI test for toolbar picker, embed placement, max-8 enforcement, mixed save/load
- [ ] All existing canvas E2E specs still pass (no regressions)
- [ ] Combined-test-per-file pattern (rate-limit friendly)
- [ ] Uses `SEED.notes.architecture.iri` and `SEED.concepts.eventSourcing.iri` as test objects

## Verification

- `cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list` — all 5 spec files pass
- `cd backend && .venv/bin/pytest tests/test_canvas_properties.py tests/test_canvas_embeds.py tests/test_canvas_resize.py -v` — all pass

## Inputs

- `e2e/tests/17-spatial-canvas/canvas-resize.spec.ts` — reference for `openCanvas()` helper, combined-test pattern, `SemPKMCanvas.exportState()/importState()` usage
- `e2e/tests/17-spatial-canvas/canvas-api.spec.ts` — reference for API-only tests with `ownerRequest`
- `e2e/tests/17-spatial-canvas/canvas-ui.spec.ts` — reference for complex UI interaction tests
- `e2e/fixtures/auth.ts` — `ownerRequest`, `ownerPage`, `BASE_URL`
- `e2e/fixtures/seed-data.ts` — `SEED` constants with known object IRIs
- S02 summary: `GET /api/canvas/properties?iri=<IRI>` returns `{properties: [...], type_label}`. Flip button class: `.spatial-node-flip`. Property table class: `.spatial-node-property-table`. State field: `node.showProperties`.
- S03 summary: Embed nodes have `nodeType: 'embed'` and `embedConfig: {type, id, url, label}`. Toolbar "Embed" button opens picker with 3 tabs. `SemPKMCanvas.addEmbed(embedConfig, x, y)` exposed on window. Max 8 enforced. `X-Embed-Mode: 1` response header on all embed endpoints.

## Expected Output

- `e2e/tests/17-spatial-canvas/canvas-property-flip.spec.ts` — new file, ~150-200 lines, 2 tests (API + UI)
- `e2e/tests/17-spatial-canvas/canvas-embeds.spec.ts` — new file, ~200-250 lines, 2 tests (API + UI)

## Observability Impact

- **New signals**: Two Playwright spec files add persistent automated regression coverage for property flip and embed features. Test pass/fail status is the primary signal.
- **Inspection method**: A future agent can run `cd e2e && npx playwright test tests/17-spatial-canvas/ --reporter=list` to check all 5 canvas specs. Individual specs can be run in isolation with `--grep` or by filename.
- **Failure state**: Failed Playwright tests produce trace files in `e2e/test-results/` with screenshots, DOM snapshots, and network logs. The `--reporter=list` output shows which specific assertion failed with line numbers.
- **No runtime changes**: This task adds only test files — no changes to production code, no new logs or endpoints.
