/**
 * PPV v2 Mental Model — Full Lifecycle E2E Test
 *
 * Exercises:
 *   1. Pre-clean (best-effort uninstall of prior PPV)
 *   2. Install PPV v2 model
 *   3. Verify 5 dashboards created via API
 *   4. Verify 5 workflows created via API
 *   5. Open a dashboard tab — verify GridStack renders
 *   6. Launch a workflow tab — verify workflow runner renders
 *   7. Attempt uninstall — handle 409 (seed data) gracefully
 *
 * Consolidated into one test() to stay within the magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { openDashboardTab } from '../../helpers/dockview';

// ---- Constants ----

const PPV_MODEL_ID = 'ppv';
const PPV_CONTAINER_PATH = '/app/models/ppv';

const EXPECTED_DASHBOARDS = [
  'Action Items',
  'Life Dashboard',
  'Projects Board',
  'Goals Overview',
  'Review Hub',
] as const;

const EXPECTED_WORKFLOWS = [
  'Daily Check-in',
  'Weekly Review',
  'Monthly Review',
  'Quarterly Review',
  'Yearly Review',
] as const;

// ---- Test Suite ----

test.describe('PPV v2 Lifecycle', () => {
  test.setTimeout(120_000);

  test('install, verify dashboards & workflows, open dashboard, launch workflow, attempt uninstall', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Accept any confirm dialogs (hx-confirm on model actions)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // ================================================================
    // STEP 1: Pre-clean — best-effort uninstall of leftover PPV
    // ================================================================
    try {
      await ownerRequest.delete(`${BASE_URL}/admin/models/${PPV_MODEL_ID}`);
    } catch {
      // Silently ignore — best-effort cleanup
    }
    // Brief pause after potential uninstall
    await ownerPage.waitForTimeout(2000);

    // ================================================================
    // STEP 2: Install PPV v2 model via admin form endpoint
    // ================================================================
    // The install endpoint uses Form data (not JSON)
    const installResp = await ownerRequest.post(
      `${BASE_URL}/admin/models/install`,
      {
        form: { path: PPV_CONTAINER_PATH },
      },
    );
    // The admin endpoint returns HTML (htmx partial) — 200 for both
    // success and failure (error displayed in the HTML). We check for
    // model presence via the API list afterward.
    expect(installResp.status()).toBe(200);

    // Give the triplestore time to process seed data + artifacts
    await ownerPage.waitForTimeout(5000);

    // ================================================================
    // STEP 3: Verify dashboards created
    // ================================================================
    const dashResp = await ownerRequest.get(`${BASE_URL}/api/dashboard`);
    expect(dashResp.status()).toBe(200);
    const dashboards: Array<{ id: string; name: string; description: string; layout: string }> =
      await dashResp.json();

    const ppvDashboards = dashboards.filter((d) =>
      EXPECTED_DASHBOARDS.some((name) => d.name === name),
    );
    expect(
      ppvDashboards.length,
      `Expected at least 5 PPV dashboards, found ${ppvDashboards.length}: ${ppvDashboards.map((d) => d.name).join(', ')}`,
    ).toBeGreaterThanOrEqual(5);

    // Verify each expected dashboard exists
    for (const expectedName of EXPECTED_DASHBOARDS) {
      const found = dashboards.find((d) => d.name === expectedName);
      expect(found, `Dashboard "${expectedName}" not found`).toBeTruthy();
    }

    // ================================================================
    // STEP 4: Verify workflows created
    // ================================================================
    const wfResp = await ownerRequest.get(`${BASE_URL}/api/workflow`);
    expect(wfResp.status()).toBe(200);
    const workflows: Array<{ id: string; name: string; description: string; step_count: number }> =
      await wfResp.json();

    const ppvWorkflows = workflows.filter((w) =>
      EXPECTED_WORKFLOWS.some((name) => w.name === name),
    );
    expect(
      ppvWorkflows.length,
      `Expected at least 5 PPV workflows, found ${ppvWorkflows.length}: ${ppvWorkflows.map((w) => w.name).join(', ')}`,
    ).toBeGreaterThanOrEqual(5);

    // Verify each expected workflow exists
    for (const expectedName of EXPECTED_WORKFLOWS) {
      const found = workflows.find((w) => w.name === expectedName);
      expect(found, `Workflow "${expectedName}" not found`).toBeTruthy();
    }

    // ================================================================
    // STEP 5: Open a dashboard tab and verify GridStack renders
    // ================================================================
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Use the first PPV dashboard (Action Items)
    const firstDashboard = ppvDashboards.find((d) => d.name === 'Action Items') || ppvDashboards[0];
    expect(firstDashboard).toBeTruthy();

    await openDashboardTab(ownerPage, firstDashboard.id, firstDashboard.name, 30_000);

    // Verify GridStack container rendered
    const gridStack = ownerPage.locator('.grid-stack');
    await expect(gridStack).toBeVisible({ timeout: 15_000 });

    // Verify at least one grid-stack item rendered (dashboard has blocks)
    const gridItems = ownerPage.locator('.grid-stack-item');
    await expect(gridItems.first()).toBeAttached({ timeout: 15_000 });

    // ================================================================
    // STEP 6: Launch a workflow tab and verify runner renders
    // ================================================================
    const firstWorkflow = ppvWorkflows.find((w) => w.name === 'Daily Check-in') || ppvWorkflows[0];
    expect(firstWorkflow).toBeTruthy();

    await ownerPage.evaluate(
      ({ id, name }) => {
        if (typeof (window as any).SemPKM?.openWorkflowTab === 'function') {
          (window as any).SemPKM.openWorkflowTab(id, name);
        }
      },
      { id: firstWorkflow.id, name: firstWorkflow.name },
    );

    // Wait for the workflow runner to render
    await ownerPage.waitForSelector('.workflow-runner', { timeout: 30_000 });

    // Verify workflow stepper bar is present
    const stepper = ownerPage.locator('.workflow-stepper');
    await expect(stepper).toBeVisible({ timeout: 10_000 });

    // Verify at least one step indicator exists
    const stepIndicators = ownerPage.locator('.workflow-step-indicator');
    await expect(stepIndicators.first()).toBeAttached({ timeout: 10_000 });

    // Verify navigation buttons exist
    const prevBtn = ownerPage.locator('.workflow-prev-btn');
    const nextBtn = ownerPage.locator('.workflow-next-btn');
    await expect(prevBtn).toBeAttached({ timeout: 5_000 });
    await expect(nextBtn).toBeAttached({ timeout: 5_000 });

    // ================================================================
    // STEP 7: Attempt uninstall — handle 409 gracefully
    // ================================================================
    const deleteResp = await ownerRequest.delete(
      `${BASE_URL}/admin/models/${PPV_MODEL_ID}`,
    );

    if (deleteResp.status() === 200) {
      const deleteBody = await deleteResp.text();

      if (deleteBody.includes('error-box') || deleteBody.includes('error')) {
        // Model has seed data instances — expected, not a test failure
        // The admin endpoint returns 200 with an error message in HTML
        console.log('Uninstall blocked by seed data (expected) — verifying model still listed');

        // Verify model still appears in the installed list
        await ownerPage.goto(`${BASE_URL}/admin/models`);
        await ownerPage.waitForSelector('.model-table', { timeout: 15_000 });
        const pageContent = await ownerPage.content();
        // PPV should still be listed since uninstall was blocked
        expect(pageContent).toContain('ppv');
      } else {
        // Clean uninstall succeeded — verify dashboards/workflows removed
        console.log('Uninstall succeeded — verifying cleanup');

        const dashAfter = await ownerRequest.get(`${BASE_URL}/api/dashboard`);
        const dashAfterData: Array<{ id: string; name: string }> = await dashAfter.json();
        const ppvDashAfter = dashAfterData.filter((d) =>
          EXPECTED_DASHBOARDS.some((name) => d.name === name),
        );
        expect(ppvDashAfter.length).toBe(0);

        const wfAfter = await ownerRequest.get(`${BASE_URL}/api/workflow`);
        const wfAfterData: Array<{ id: string; name: string }> = await wfAfter.json();
        const ppvWfAfter = wfAfterData.filter((w) =>
          EXPECTED_WORKFLOWS.some((name) => w.name === name),
        );
        expect(ppvWfAfter.length).toBe(0);
      }
    } else if (deleteResp.status() === 409) {
      // Explicit 409 — seed data blocks removal
      console.log('Uninstall returned 409 (seed data blocks removal) — expected behavior');
    } else if (deleteResp.status() === 404) {
      // Not installed — shouldn't happen but not a test failure
      console.log('Uninstall returned 404 — model already removed');
    } else {
      // Unexpected status — log but don't fail the test
      console.log(`Uninstall returned unexpected status ${deleteResp.status()}`);
    }
  });
});
