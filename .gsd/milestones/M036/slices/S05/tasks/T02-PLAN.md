---
estimated_steps: 5
estimated_files: 3
skills_used:
  - test
---

# T02: E2E Playwright tests for business-planning model install and custom renderers

**Slice:** S05 — Cross-Model Integration, E2E Tests & Documentation
**Milestone:** M036

## Description

Write an E2E Playwright test spec that exercises the full vertical: install the business-planning model via Admin UI, create objects via the Command API, open all 4 custom view renderers (quadrant, bmc, okr, decision-matrix), verify their board containers render, run a cross-model SPARQL query, and clean up. Also update the E2E helper files to include the new renderer types in TypeScript unions and add view selectors.

Follows the established `mental-model-expansion.spec.ts` pattern: single consolidated `test()` block to stay within the 5/minute magic-link rate limit.

## Steps

1. **Update `e2e/helpers/dockview.ts`:**
   - Extend the `renderer` parameter type union in `openGenericViewTab()` from `'table' | 'card' | 'graph' | 'kanban' | 'calendar' | 'map' | 'timeline'` to also include `'quadrant' | 'bmc' | 'okr' | 'decision-matrix'`.

2. **Update `e2e/helpers/selectors.ts`:**
   - Add to `SEL.views`:
     ```typescript
     quadrantBoard: '.quadrant-board',
     quadrantCell: '.quadrant-cell',
     bmcBoard: '.bmc-board',
     bmcSection: '.bmc-section',
     okrBoard: '.okr-board',
     okrObjectiveCard: '.okr-objective-card',
     dmBoard: '.dm-board',
     dmRow: '.dm-row',
     ```

3. **Create `e2e/tests/36-business-planning/business-planning.spec.ts`:**
   - Import: `test`, `expect`, `BASE_URL` from `../../fixtures/auth`; `SEL` from `../../helpers/selectors`; `openGenericViewTab` from `../../helpers/dockview`; `waitForWorkspace`, `waitForIdle` from `../../helpers/wait-for`.
   - Set test timeout to 180_000 (3 min — model install + 4 view opens + SPARQL).
   - Use `ownerPage.on('dialog', d => d.accept())` for hx-confirm dialogs.
   - **Model install:** Navigate to `${BASE_URL}/admin/models`, fill `#model-path` with `/app/models/business-planning`, click Install, wait 5s + idle. Reload and verify "Business Planning" appears in model list.
   - **Create test objects via Command API (POST to `/api/commands`):**
     - 1 EisenhowerMatrix + 2 EisenhowerItems (high/high and low/low urgency/importance)
     - 1 BusinessModelCanvas + 1 BMCSection (sectionType: "value-propositions")
     - 1 Objective + 1 KeyResult (currentValue: 60, targetValue: 100)
     - 1 DecisionMatrix + 1 Criterion (weight: 5) + 1 Alternative + 1 Score (value: 4)
   - **Navigate to workspace and pre-set localStorage type selections:**
     ```javascript
     localStorage.setItem('sempkm_generic_type_quadrant', 'urn:sempkm:model:business-planning:EisenhowerItem');
     localStorage.setItem('sempkm_generic_type_bmc', 'urn:sempkm:model:business-planning:BMCSection');
     localStorage.setItem('sempkm_generic_type_okr', 'urn:sempkm:model:business-planning:KeyResult');
     localStorage.setItem('sempkm_generic_type_decision-matrix', 'urn:sempkm:model:business-planning:Alternative');
     ```
   - **Open and verify each custom renderer tab (with 20s timeouts):**
     - `openGenericViewTab(ownerPage, 'quadrant', '.quadrant-board', '', '', 20000)` then assert `.quadrant-board` visible
     - `openGenericViewTab(ownerPage, 'bmc', '.bmc-board', '', '', 20000)` then assert `.bmc-board` visible
     - `openGenericViewTab(ownerPage, 'okr', '.okr-board', '', '', 20000)` then assert `.okr-board` visible
     - `openGenericViewTab(ownerPage, 'decision-matrix', '.dm-board', '', '', 20000)` then assert `.dm-board` visible
   - **SPARQL cross-model query:** POST to `/api/sparql` with `SELECT ?item WHERE { ?item a <urn:sempkm:model:business-planning:EisenhowerItem> }`, verify response has ≥ 2 results.
   - **Best-effort cleanup:** Try to delete created objects (optional, may fail). Try to uninstall model (optional, may fail with seed data).

4. **Ensure the directory `e2e/tests/36-business-planning/` exists** (create it if needed).

5. **Type-check the E2E project:**
   - `cd e2e && npx tsc --noEmit` — must complete without errors.

## Must-Haves

- [ ] `openGenericViewTab` renderer union includes 'quadrant', 'bmc', 'okr', 'decision-matrix'
- [ ] `SEL.views` has quadrantBoard, bmcBoard, okrBoard, dmBoard selectors
- [ ] E2E spec covers model install via Admin UI
- [ ] E2E spec creates objects for all 4 custom renderer types via Command API
- [ ] E2E spec opens and verifies all 4 custom renderer tabs
- [ ] E2E spec runs a SPARQL query and verifies structured results
- [ ] E2E project type-checks cleanly

## Verification

- `cd e2e && npx tsc --noEmit` — zero errors
- `test -f e2e/tests/36-business-planning/business-planning.spec.ts` — spec file exists
- `rg "quadrant.*bmc.*okr.*decision-matrix" e2e/helpers/dockview.ts` — all 4 types in union (may need looser grep)
- `rg "quadrantBoard|bmcBoard|okrBoard|dmBoard" e2e/helpers/selectors.ts` — all 4 selectors present

## Inputs

- `e2e/helpers/dockview.ts` — existing helper with `openGenericViewTab` function
- `e2e/helpers/selectors.ts` — existing selector constants
- `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` — pattern reference for model install E2E tests
- `models/business-planning/ontology/business-planning.jsonld` — for type IRIs used in object creation

## Expected Output

- `e2e/tests/36-business-planning/business-planning.spec.ts` — new E2E spec file
- `e2e/helpers/dockview.ts` — updated renderer type union
- `e2e/helpers/selectors.ts` — updated with new view selectors

## Observability Impact

- **E2E test runtime:** `npx playwright test tests/36-business-planning/` exercises model install, 4 view renderers, and SPARQL query — failures identify the exact step and selector that broke
- **TypeScript compile:** `cd e2e && npx tsc --noEmit 2>&1 | grep 36-business-planning` confirms new spec has no type errors; grep for `helpers/dockview` and `helpers/selectors` verifies helper changes are clean
- **Selector constants:** `rg "quadrantBoard|bmcBoard|okrBoard|dmBoard" e2e/helpers/selectors.ts` confirms all 4 view selectors exist
- **Renderer union:** `rg "quadrant.*bmc.*okr.*decision-matrix" e2e/helpers/dockview.ts` confirms the type union includes all business-planning renderers
- **Failure state visibility:** Playwright reports include step name, selector, timeout, and screenshot on failure — no custom instrumentation needed beyond the assertions in the spec
