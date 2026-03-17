---
estimated_steps: 8
estimated_files: 1
---

# T02: Write E2E Playwright test for mental model expansion

**Slice:** S05 — Cross-Model Verification, E2E Tests & User Guide
**Milestone:** M011

## Description

Write a comprehensive E2E Playwright test that exercises the full Docker lifecycle for all 4 M011 models: install models, create objects via API, verify SHACL forms render in the UI, run inference, check validation via lint API, and clean up. This is the integration proof that retires MODEL-01 through MODEL-04.

The test follows established patterns from:
- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — model install/uninstall via UI and API
- `e2e/tests/09-inference/inference.spec.ts` — inference run via API
- `e2e/tests/04-validation/lint-panel.spec.ts` — lint API endpoint

All tests share a single `ownerPage`/`ownerRequest` fixture to stay within the 5/minute magic-link rate limit.

**Relevant skill:** Load the `test` skill for E2E test generation patterns.

## Steps

1. **Create directory and test file:** `e2e/tests/26-mental-models/mental-model-expansion.spec.ts`

2. **Write imports and constants:**
   ```typescript
   import { test, expect, BASE_URL } from '../../fixtures/auth';
   import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
   ```
   
   Define model IDs and type IRIs as constants:
   ```typescript
   const MODELS_TO_INSTALL = ['crm', 'zettelkasten', 'research'];
   
   const NEW_TYPES = {
     'crm:Contact': 'urn:sempkm:model:crm:Contact',
     'crm:Company': 'urn:sempkm:model:crm:Company',
     'zk:FleetingNote': 'urn:sempkm:model:zettelkasten:FleetingNote',
     'zk:PermanentNote': 'urn:sempkm:model:zettelkasten:PermanentNote',
     'research:Paper': 'urn:sempkm:model:research:Paper',
     'research:Claim': 'urn:sempkm:model:research:Claim',
     'bpkm:Task': 'urn:sempkm:model:basic-pkm:Task',
     'bpkm:Milestone': 'urn:sempkm:model:basic-pkm:Milestone',
   };
   ```

3. **Write cleanup helper function** (following `cleanupPpvInstances` pattern):
   ```typescript
   async function cleanupModelInstances(ownerRequest: any, modelId: string): Promise<void> {
     const typeQuery = `
       SELECT DISTINCT ?type WHERE {
         GRAPH <urn:sempkm:model:${modelId}:ontology> {
           ?type a <http://www.w3.org/2002/07/owl#Class> .
         }
       }
     `;
     // ... delete instances of each type from urn:sempkm:user graph
   }
   ```

4. **Write `test.describe('Mental Model Expansion', () => { ... })` with ordered sequential tests:**

   **Test 1: Install CRM, zettelkasten, and research models**
   - Navigate to `${BASE_URL}/admin/models`
   - For each model in `MODELS_TO_INSTALL`:
     - Fill `#model-path` with `/app/models/${modelId}`
     - Click Install button
     - `waitForTimeout(5000)` + `waitForIdle(ownerPage)` (model install involves triplestore writes that take 3-10 seconds)
   - Reload admin models page
   - Verify all 3 new models appear in model table (use `toContainText` with model names)
   - Also verify basic-pkm is already listed (it's pre-installed by setup)

   **Test 2: Refresh basic-pkm to v2.0 via API**
   - `POST ${BASE_URL}/admin/models/basic-pkm/refresh-artifacts`
   - Verify response is 200
   - This tests the upgrade path for basic-pkm from v1.x to v2.0

   **Test 3: Create one object per new type via Command API**
   - For each type in `NEW_TYPES`, send `POST ${BASE_URL}/api/commands` with `object.create`:
     ```typescript
     {
       command: 'object.create',
       params: {
         type: typeIri,
         properties: { 'http://purl.org/dc/terms/title': `Test ${typeName}` },
       },
     }
     ```
   - Store returned IRIs for later cleanup
   - Verify each creation returns status 200 and has an `iri` in the response

   **Test 4: Verify SHACL forms render for created objects**
   - Navigate to workspace: `${BASE_URL}/browser/`
   - `waitForWorkspace(ownerPage)`
   - For a subset of created objects (e.g., Task, Contact, FleetingNote, Paper — one per model):
     - Open object in workspace via `openTab()` evaluate pattern (same as lint-panel.spec.ts):
       ```typescript
       await ownerPage.evaluate((iri) => {
         if (typeof (window as any).openTab === 'function') {
           (window as any).openTab(iri, 'Test Object');
         }
       }, objectIri);
       ```
     - Wait for form to load: `waitForIdle(ownerPage)` + `waitForTimeout(2000)`
     - Verify the object form area has content (object loaded, not error)
     - Check the editor area contains some form content (not blank):
       ```typescript
       const editorArea = ownerPage.locator('[data-testid="editor-area"]');
       await expect(editorArea).not.toBeEmpty();
       ```

   **Test 5: Run inference via API and verify completion**
   - `POST ${BASE_URL}/api/inference/run`
   - Verify response 200 with `total_inferred` >= 0 and `run_timestamp` present
   - Pattern from `inference.spec.ts`

   **Test 6: Check lint API returns results**
   - For one seed object from each model that should trigger warnings:
     - basic-pkm: `urn:sempkm:model:basic-pkm:seed-task-fix-validation` (overdue task)
     - CRM: `urn:sempkm:model:crm:seed-contact-marcus` (stale contact)
     - zettelkasten: `urn:sempkm:model:zettelkasten:seed-fleeting-unprocessed` (unprocessed fleeting)
     - research: `urn:sempkm:model:research:seed-claim-kg-reduce-silos` (unsupported claim)
   - Call `GET ${BASE_URL}/browser/lint/${encodeURIComponent(iri)}` with HX-Request header
   - Verify response is 200 (lint endpoint works for these objects)
   - Note: Validation may or may not have fired yet for seed objects — the key assertion is the endpoint works and returns HTML content

   **Test 7: Cleanup — delete created objects and uninstall models**
   - Delete all test-created objects via SPARQL DELETE
   - For each model in `MODELS_TO_INSTALL` (reverse order), call `cleanupModelInstances()` then `DELETE ${BASE_URL}/admin/models/${modelId}`
   - Verify admin models page no longer shows CRM/zettelkasten/research (basic-pkm stays)

5. **Use `test.describe.configure({ mode: 'serial' })` or a single test() if Playwright serial mode isn't available** — the tests MUST run in order since they share Docker state. If serial mode isn't supported, consolidate into a single large test with labeled sections (following the `admin-model-lifecycle.spec.ts` pattern of one large test).

6. **Handle dialog events:** Add `ownerPage.on('dialog', (dialog) => dialog.accept())` early in the test — model install may trigger confirm dialogs.

7. **Set generous timeouts:** Model install involves triplestore writes + seed data loading that takes 3-10s per model. Use `test.setTimeout(120000)` for the entire describe block.

8. **Check for TypeScript compilation:** `cd e2e && npx tsc --noEmit tests/26-mental-models/mental-model-expansion.spec.ts` (or just verify no red squiggles). Note: The E2E project may not have strict tsconfig — check `e2e/tsconfig.json` if TS issues arise.

## Must-Haves

- [ ] Test installs CRM, zettelkasten, and research models in Docker
- [ ] Test refreshes basic-pkm to v2.0 via refresh-artifacts endpoint
- [ ] Test creates at least one object per new type (Task, Milestone, Contact, Company, FleetingNote, PermanentNote, Paper, Claim)
- [ ] Test verifies SHACL form content loads for at least one object per model
- [ ] Test runs inference via API and checks response
- [ ] Test calls lint API endpoint for seed objects with trigger data
- [ ] Test cleans up: deletes created objects, uninstalls 3 models (leaves basic-pkm)
- [ ] All tests pass when run against Docker test stack on port 3901

## Verification

- `cd e2e && npx playwright test tests/26-mental-models/ --project=chromium` — all tests pass
- File exists: `e2e/tests/26-mental-models/mental-model-expansion.spec.ts`
- No TypeScript errors in the file

## Inputs

- `e2e/fixtures/auth.ts` — provides `test`, `expect`, `BASE_URL`, `ownerPage`, `ownerRequest`, `ownerSessionToken` fixtures. Key: `BASE_URL` defaults to `http://localhost:3901`. `ownerPage` is an authenticated Playwright Page. `ownerRequest` is an authenticated APIRequestContext.
- `e2e/helpers/wait-for.ts` — provides `waitForWorkspace(page)`, `waitForIdle(page)`, `waitForElement(page, selector)`
- `e2e/helpers/selectors.ts` — `SEL.admin.modelList` = `'[data-testid="model-list"]'`, `SEL.editor.form` = `'[data-testid="object-form"]'`, `SEL.workspace.editorArea` = `'[data-testid="editor-area"]'`
- `e2e/tests/05-admin/admin-model-lifecycle.spec.ts` — reference for install pattern: fill `#model-path`, click Install button, `waitForTimeout(3000)` + `waitForIdle()`, reload page, assert model in table. Also reference for `cleanupPpvInstances()` cleanup pattern.
- `e2e/tests/09-inference/inference.spec.ts` — reference for `POST /api/inference/run` and response assertions (`total_inferred`, `run_timestamp`, `by_entailment_type`)
- `e2e/tests/04-validation/lint-panel.spec.ts` — reference for `GET /browser/lint/${encodeURIComponent(iri)}` with `HX-Request: true` header
- Model manifests: basic-pkm (modelId: `basic-pkm`), CRM (modelId: `crm`), zettelkasten (modelId: `zettelkasten`), research (modelId: `research`). Docker paths: `/app/models/{modelId}`.
- Type IRIs follow pattern `urn:sempkm:model:{modelId}:{TypeName}` e.g. `urn:sempkm:model:crm:Contact`
- Seed object IRIs with trigger data:
  - basic-pkm: `urn:sempkm:model:basic-pkm:seed-task-fix-validation` (overdue task warning)
  - CRM: `urn:sempkm:model:crm:seed-contact-marcus` (stale contact warning)
  - zettelkasten: `urn:sempkm:model:zettelkasten:seed-fleeting-unprocessed` (unprocessed note warning)
  - research: `urn:sempkm:model:research:seed-claim-kg-reduce-silos` (unsupported claim warning)
- Install API: `POST /admin/models/install` with form field `model_path=/app/models/{id}` (or fill `#model-path` input and click Install button)
- Refresh API: `POST /admin/models/{id}/refresh-artifacts`
- Remove API: `DELETE /admin/models/{id}`
- Create object API: `POST /api/commands` with `{ command: 'object.create', params: { type: IRI, properties: { 'http://purl.org/dc/terms/title': 'name' } } }`

## Expected Output

- `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` — E2E test spec covering full model lifecycle for all 4 M011 models (~200-300 lines)
