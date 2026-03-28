/**
 * Business Planning Model E2E Tests
 *
 * Exercises the full vertical for the business-planning model:
 *   install model → create objects for all 4 custom renderers →
 *   open quadrant/bmc/okr/decision-matrix views → SPARQL query → cleanup
 *
 * Consolidated into a single test() to stay within the 5/minute
 * magic-link rate limit (one ownerPage/ownerRequest session).
 *
 * Follows patterns from mental-model-expansion.spec.ts.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { openGenericViewTab } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

// ---- Constants ----

const BP = 'urn:sempkm:model:business-planning:';
const DCTERMS = 'http://purl.org/dc/terms/';

// ---- Helpers ----

/**
 * Best-effort pre-clean: attempt to remove the model via the admin API.
 * May fail if seed data or user instances exist — that's expected.
 */
async function tryRemoveModel(ownerRequest: any): Promise<void> {
  try {
    await ownerRequest.delete(`${BASE_URL}/admin/models/business-planning`);
  } catch {
    // Silently ignore — best-effort cleanup
  }
}

// ---- Test Suite ----

test.describe('Business Planning Model', () => {
  // Model install + 4 view opens + SPARQL + cleanup
  test.setTimeout(180_000);

  test('install, create objects, verify 4 custom renderers, SPARQL query, and clean up', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Accept any confirm dialogs (hx-confirm on model actions)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Track created object IRIs for cleanup
    const createdIris: string[] = [];

    // ================================================================
    // STEP 1: Install business-planning model via Admin UI
    // ================================================================
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15_000 });

    // Pre-clean: if model is already installed from a prior run, try removal
    const existingRow = ownerPage
      .locator(`${SEL.admin.modelList} tbody tr`)
      .filter({ hasText: /Business Planning/i });
    if ((await existingRow.count()) > 0) {
      await tryRemoveModel(ownerRequest);
      await ownerPage.waitForTimeout(1000);
      await ownerPage.goto(`${BASE_URL}/admin/models`);
      await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15_000 });
    }

    // Install model via UI form
    const pathInput = ownerPage.locator('#model-path');
    await pathInput.fill('/app/models/business-planning');
    await ownerPage.locator('button', { hasText: 'Install' }).click();

    // Model install involves triplestore writes + seed loading: 5-15s
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Reload and verify model appears in the list
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15_000 });
    await waitForIdle(ownerPage);

    const modelTable = ownerPage.locator(SEL.admin.modelList);
    await expect(modelTable).toContainText('Business Planning', { timeout: 10_000 });

    // ================================================================
    // STEP 2: Create test objects via Command API (batch)
    // ================================================================

    // --- Eisenhower Matrix + 2 Items ---
    const eisenhowerResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: [
        {
          command: 'object.create',
          params: {
            type: `${BP}EisenhowerMatrix`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Test Matrix',
            },
          },
          slot: 'matrix',
        },
        {
          command: 'object.create',
          params: {
            type: `${BP}EisenhowerItem`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Urgent Important Item',
              [`${BP}urgency`]: 'high',
              [`${BP}importance`]: 'high',
              [`${BP}belongsToMatrix`]: '@slot:matrix',
            },
          },
          slot: 'item1',
        },
        {
          command: 'object.create',
          params: {
            type: `${BP}EisenhowerItem`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Not Urgent Not Important Item',
              [`${BP}urgency`]: 'low',
              [`${BP}importance`]: 'low',
              [`${BP}belongsToMatrix`]: '@slot:matrix',
            },
          },
          slot: 'item2',
        },
      ],
    });
    expect(eisenhowerResp.status()).toBe(200);
    const eisenhowerData = await eisenhowerResp.json();
    for (const r of eisenhowerData.results) {
      createdIris.push(r.iri);
    }

    // --- Business Model Canvas + 1 BMCSection ---
    const bmcResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: [
        {
          command: 'object.create',
          params: {
            type: `${BP}BusinessModelCanvas`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Test Canvas',
            },
          },
          slot: 'canvas',
        },
        {
          command: 'object.create',
          params: {
            type: `${BP}BMCSection`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Value Propositions',
              [`${BP}sectionType`]: 'value-propositions',
              [`${BP}sectionContent`]: 'Semantic knowledge management for everyone',
              [`${BP}belongsToCanvas`]: '@slot:canvas',
            },
          },
          slot: 'section',
        },
      ],
    });
    expect(bmcResp.status()).toBe(200);
    const bmcData = await bmcResp.json();
    for (const r of bmcData.results) {
      createdIris.push(r.iri);
    }

    // --- Objective + 1 KeyResult ---
    const okrResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: [
        {
          command: 'object.create',
          params: {
            type: `${BP}Objective`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Test Objective',
              [`${DCTERMS}description`]: 'Improve test coverage for business planning',
            },
          },
          slot: 'objective',
        },
        {
          command: 'object.create',
          params: {
            type: `${BP}KeyResult`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Test Key Result',
              [`${BP}currentValue`]: '60',
              [`${BP}targetValue`]: '100',
              [`${BP}unit`]: 'percent',
              [`${BP}belongsToObjective`]: '@slot:objective',
            },
          },
          slot: 'kr',
        },
      ],
    });
    expect(okrResp.status()).toBe(200);
    const okrData = await okrResp.json();
    for (const r of okrData.results) {
      createdIris.push(r.iri);
    }

    // --- DecisionMatrix + 1 Criterion + 1 Alternative + 1 Score ---
    const dmResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: [
        {
          command: 'object.create',
          params: {
            type: `${BP}DecisionMatrix`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Test Decision Matrix',
            },
          },
          slot: 'dm',
        },
        {
          command: 'object.create',
          params: {
            type: `${BP}Criterion`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Cost Criterion',
              [`${BP}weight`]: '5',
              [`${BP}belongsToDecisionMatrix`]: '@slot:dm',
            },
          },
          slot: 'criterion',
        },
        {
          command: 'object.create',
          params: {
            type: `${BP}Alternative`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Option A',
              [`${BP}belongsToDecisionMatrix`]: '@slot:dm',
            },
          },
          slot: 'alt',
        },
        {
          command: 'object.create',
          params: {
            type: `${BP}Score`,
            properties: {
              [`${DCTERMS}title`]: 'E2E Score for Option A',
              [`${BP}value`]: '4',
              [`${BP}scoreAlternative`]: '@slot:alt',
              [`${BP}scoreCriterion`]: '@slot:criterion',
            },
          },
          slot: 'score',
        },
      ],
    });
    expect(dmResp.status()).toBe(200);
    const dmData = await dmResp.json();
    for (const r of dmData.results) {
      createdIris.push(r.iri);
    }

    // Verify all 11 objects created (3 + 2 + 2 + 4)
    expect(createdIris).toHaveLength(11);

    // ================================================================
    // STEP 3: Navigate to workspace and set localStorage type selections
    // ================================================================
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set the localStorage keys so each generic view tab knows which type to load
    await ownerPage.evaluate(() => {
      localStorage.setItem('sempkm_generic_type_quadrant', 'urn:sempkm:model:business-planning:EisenhowerItem');
      localStorage.setItem('sempkm_generic_type_bmc', 'urn:sempkm:model:business-planning:BMCSection');
      localStorage.setItem('sempkm_generic_type_okr', 'urn:sempkm:model:business-planning:KeyResult');
      localStorage.setItem('sempkm_generic_type_decision-matrix', 'urn:sempkm:model:business-planning:Alternative');
    });

    // ================================================================
    // STEP 4: Open and verify each custom renderer tab
    // ================================================================

    // Quadrant view (Eisenhower Matrix)
    await openGenericViewTab(ownerPage, 'quadrant', SEL.views.quadrantBoard, '', '', 20000);
    await expect(ownerPage.locator(SEL.views.quadrantBoard)).toBeVisible({ timeout: 10_000 });

    // BMC view (Business Model Canvas)
    await openGenericViewTab(ownerPage, 'bmc', SEL.views.bmcBoard, '', '', 20000);
    await expect(ownerPage.locator(SEL.views.bmcBoard)).toBeVisible({ timeout: 10_000 });

    // OKR view (Objectives & Key Results)
    await openGenericViewTab(ownerPage, 'okr', SEL.views.okrBoard, '', '', 20000);
    await expect(ownerPage.locator(SEL.views.okrBoard)).toBeVisible({ timeout: 10_000 });

    // Decision Matrix view
    await openGenericViewTab(ownerPage, 'decision-matrix', SEL.views.dmBoard, '', '', 30000);
    await expect(ownerPage.locator(SEL.views.dmBoard)).toBeVisible({ timeout: 15_000 });

    // ================================================================
    // STEP 5: SPARQL cross-model query
    // ================================================================
    const sparqlResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `SELECT ?item WHERE { ?item a <${BP}EisenhowerItem> }`,
      },
    });
    expect(sparqlResp.status()).toBe(200);

    const sparqlData = await sparqlResp.json();
    // We created 2 EisenhowerItems, but seed data may also include some
    expect(sparqlData.results.bindings.length).toBeGreaterThanOrEqual(2);

    // ================================================================
    // STEP 6: Best-effort cleanup
    // ================================================================

    // Try to delete created objects (optional — may fail)
    for (const iri of createdIris.reverse()) {
      try {
        await ownerRequest.post(`${BASE_URL}/api/commands`, {
          data: {
            command: 'object.patch',
            params: {
              iri,
              properties: { '__delete': 'true' },
            },
          },
        });
      } catch {
        // Best-effort — don't fail the test on cleanup errors
      }
    }

    // Try to uninstall model (optional — may fail with seed data)
    try {
      await tryRemoveModel(ownerRequest);
    } catch {
      // Best-effort
    }
  });
});
