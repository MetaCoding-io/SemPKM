/**
 * Mental Model Expansion E2E Tests
 *
 * Exercises the full Docker lifecycle for all 4 M011 models:
 *   basic-pkm v2.0, CRM, Zettelkasten+, Research Workflow
 *
 * Tests: install models → refresh basic-pkm → create objects → verify
 * SHACL forms → run inference → lint API → cleanup.
 *
 * Consolidated into a single test() to stay within the 5/minute
 * magic-link rate limit (one ownerPage/ownerRequest session).
 *
 * Follows patterns from:
 *   - admin-model-lifecycle.spec.ts (install/uninstall)
 *   - inference.spec.ts (inference API)
 *   - lint-panel.spec.ts (lint endpoint)
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

// ---- Constants ----

const MODELS_TO_INSTALL = ['crm', 'zettelkasten', 'research'] as const;

const MODEL_DISPLAY_NAMES: Record<string, string> = {
  crm: 'Personal CRM',
  zettelkasten: 'Zettelkasten+',
  research: 'Research Workflow',
  'basic-pkm': 'Basic PKM',
};

/** Types to create — one per model, covering all 4 M011 models. */
const NEW_TYPES: Record<string, string> = {
  'bpkm:Task': 'urn:sempkm:model:basic-pkm:Task',
  'bpkm:Milestone': 'urn:sempkm:model:basic-pkm:Milestone',
  'crm:Contact': 'urn:sempkm:model:crm:Contact',
  'crm:Company': 'urn:sempkm:model:crm:Company',
  'zk:FleetingNote': 'urn:sempkm:model:zettelkasten:FleetingNote',
  'zk:PermanentNote': 'urn:sempkm:model:zettelkasten:PermanentNote',
  'res:Paper': 'urn:sempkm:model:research:Paper',
  'res:Claim': 'urn:sempkm:model:research:Claim',
};

/** Seed objects with trigger data — one per model for lint validation. */
const SEED_LINT_TARGETS: Record<string, { iri: string; label: string }> = {
  'basic-pkm': {
    iri: 'urn:sempkm:model:basic-pkm:seed-task-fix-validation',
    label: 'overdue task',
  },
  crm: {
    iri: 'urn:sempkm:model:crm:seed-contact-marcus',
    label: 'stale contact',
  },
  zettelkasten: {
    iri: 'urn:sempkm:model:zettelkasten:seed-fleeting-unprocessed',
    label: 'unprocessed fleeting note',
  },
  research: {
    iri: 'urn:sempkm:model:research:seed-claim-kg-reduce-silos',
    label: 'unsupported claim',
  },
};

/**
 * One object per model to verify SHACL form rendering in the UI.
 * Keys must be present in NEW_TYPES.
 */
const FORM_VERIFICATION_TYPES = [
  'bpkm:Task',
  'crm:Contact',
  'zk:FleetingNote',
  'res:Paper',
];

// ---- Helpers ----

/**
 * Best-effort pre-clean: attempt to remove a model via the admin API.
 * The /api/sparql endpoint does not support SPARQL UPDATE, so we cannot
 * delete user/seed data instances. The admin DELETE endpoint may return
 * an error-box if instances exist — we ignore that and proceed.
 *
 * On a fresh test stack (docker compose down/up), no stale models exist.
 * This only matters for repeated runs against the same stack.
 */
async function tryRemoveModel(
  ownerRequest: any,
  modelId: string,
): Promise<void> {
  try {
    await ownerRequest.delete(`${BASE_URL}/admin/models/${modelId}`);
  } catch {
    // Silently ignore — best-effort cleanup
  }
}

// ---- Test Suite ----

test.describe('Mental Model Expansion', () => {
  // This is a long integration test — model installs take 3-10s each
  test.setTimeout(120_000);

  test('install, create, verify forms, infer, lint, and clean up all 4 M011 models', async ({
    ownerPage,
    ownerRequest,
    ownerSessionToken,
  }) => {
    // Accept any confirm dialogs (hx-confirm on model actions)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Track created object IRIs for cleanup
    const createdIris: string[] = [];

    // ================================================================
    // STEP 1: Install CRM, Zettelkasten, and Research models
    // ================================================================
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15_000 });

    // Pre-clean: If any of the 3 models are already installed (from prior run),
    // attempt removal (may fail if seed data exists — that's OK)
    for (const modelId of [...MODELS_TO_INSTALL].reverse()) {
      const existingRow = ownerPage
        .locator(`${SEL.admin.modelList} tbody tr`)
        .filter({ hasText: new RegExp(MODEL_DISPLAY_NAMES[modelId], 'i') });
      if ((await existingRow.count()) > 0) {
        await tryRemoveModel(ownerRequest, modelId);
        await ownerPage.waitForTimeout(1000);
      }
    }

    // Reload after cleanup
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15_000 });

    // Verify basic-pkm is pre-installed
    const modelTable = ownerPage.locator(SEL.admin.modelList);
    await expect(modelTable).toContainText('Basic PKM');

    // Install each new model via the UI form (skip if already installed from prior run)
    for (const modelId of MODELS_TO_INSTALL) {
      // Check if already installed
      const alreadyInstalled = ownerPage
        .locator(`${SEL.admin.modelList} tbody tr`)
        .filter({ hasText: new RegExp(MODEL_DISPLAY_NAMES[modelId], 'i') });
      if ((await alreadyInstalled.count()) > 0) {
        continue; // Already installed from a prior run that couldn't clean up
      }
      const pathInput = ownerPage.locator('#model-path');
      await pathInput.fill(`/app/models/${modelId}`);
      await ownerPage.locator('button', { hasText: 'Install' }).click();
      // Model install involves triplestore writes + seed loading: 3-10s
      await ownerPage.waitForTimeout(5000);
      await waitForIdle(ownerPage);
    }

    // Reload and verify all 4 models appear
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForSelector(SEL.admin.modelList, { timeout: 15_000 });
    await waitForIdle(ownerPage);

    for (const modelId of MODELS_TO_INSTALL) {
      await expect(modelTable).toContainText(MODEL_DISPLAY_NAMES[modelId], {
        timeout: 10_000,
      });
    }
    await expect(modelTable).toContainText('Basic PKM');

    // ================================================================
    // STEP 2: Refresh basic-pkm to v2.0 via API
    // ================================================================
    const refreshResp = await ownerRequest.post(
      `${BASE_URL}/admin/models/basic-pkm/refresh-artifacts`,
    );
    expect(refreshResp.status()).toBe(200);

    // ================================================================
    // STEP 3: Create one object per new type via Command API
    // ================================================================
    for (const [typeName, typeIri] of Object.entries(NEW_TYPES)) {
      const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
        data: {
          command: 'object.create',
          params: {
            type: typeIri,
            properties: {
              'http://purl.org/dc/terms/title': `E2E Test ${typeName}`,
            },
          },
        },
      });
      expect(createResp.status()).toBe(200);

      const createData = await createResp.json();
      // Response may be { results: [{ iri }] } (batch) or { iri } (single)
      const iri =
        createData?.results?.[0]?.iri ?? createData?.iri ?? null;
      expect(iri).toBeTruthy();
      createdIris.push(iri);
    }

    // All 8 types should have objects
    expect(createdIris).toHaveLength(Object.keys(NEW_TYPES).length);

    // ================================================================
    // STEP 4: Verify SHACL forms render for one object per model
    // ================================================================
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const typeNames = Object.keys(NEW_TYPES);
    for (const typeName of FORM_VERIFICATION_TYPES) {
      const typeIndex = typeNames.indexOf(typeName);
      const objectIri = createdIris[typeIndex];
      expect(objectIri).toBeTruthy();

      // Open object tab via the window API
      await ownerPage.evaluate(
        ({ iri, label }) => {
          if (typeof (window as any).SemPKM.openTab === 'function') {
            (window as any).SemPKM.openTab(iri, label);
          }
        },
        { iri: objectIri, label: `E2E Test ${typeName}` },
      );

      await waitForIdle(ownerPage);
      await ownerPage.waitForTimeout(2000);

      // Verify the editor area has rendered content (not blank/error)
      const editorArea = ownerPage.locator(SEL.workspace.editorArea);
      await expect(editorArea).not.toBeEmpty({ timeout: 10_000 });
    }

    // ================================================================
    // STEP 5: Run inference via API and verify completion
    // ================================================================
    const inferResp = await ownerRequest.post(`${BASE_URL}/api/inference/run`, {
      timeout: 60_000,  // Inference with 4 models can take >10s
    });
    expect(inferResp.status()).toBe(200);

    const inferData = await inferResp.json();
    expect(inferData).toHaveProperty('total_inferred');
    expect(inferData).toHaveProperty('run_timestamp');
    expect(inferData.total_inferred).toBeGreaterThanOrEqual(0);

    // ================================================================
    // STEP 6: Lint API returns results for seed objects
    // ================================================================
    for (const [modelId, target] of Object.entries(SEED_LINT_TARGETS)) {
      const encodedIri = encodeURIComponent(target.iri);
      const lintResp = await ownerRequest.get(
        `${BASE_URL}/browser/lint/${encodedIri}`,
        {
          headers: { 'HX-Request': 'true' },
        },
      );
      // Lint endpoint should work for all model seed objects
      expect(lintResp.status()).toBe(200);

      const html = await lintResp.text();
      // Should return HTML content (lint panel or empty-state panel)
      expect(html.length).toBeGreaterThan(0);
    }

    // ================================================================
    // STEP 7: Cleanup — best-effort uninstall of 3 models
    // ================================================================
    // Note: The /api/sparql endpoint only supports SELECT/ASK/CONSTRUCT,
    // not SPARQL UPDATE/DELETE. Seed data instances in urn:sempkm:current
    // cannot be deleted via the API. Model removal may be blocked by
    // existing seed data. The pre-clean at the start of the test handles
    // stale models from prior runs, so this cleanup is best-effort.
    //
    // When the test stack is torn down (docker compose down), all data
    // is reset anyway. The important assertions are Steps 1-6 above.

    for (const modelId of [...MODELS_TO_INSTALL].reverse()) {
      // Attempt removal — may fail if seed data instances exist
      const delResp = await ownerRequest.delete(
        `${BASE_URL}/admin/models/${modelId}`,
      );
      // Log but don't assert — cleanup is best-effort
      if (delResp.status() === 200) {
        const delBody = await delResp.text();
        if (delBody.includes('error-box')) {
          // Model has seed data instances — expected, not a test failure
          console.log(`Cleanup: Could not remove ${modelId} (seed data exists)`);
        }
      }
      await ownerPage.waitForTimeout(500);
    }
  });
});
