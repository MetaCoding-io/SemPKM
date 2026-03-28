/**
 * Linear Sync E2E Tests
 *
 * Proves the full Linear sync vertical against a mock Linear API:
 *   install basic-pkm → install linear-sync → connect API key →
 *   select team → configure sync → Sync Now → verify tasks via SPARQL →
 *   admin detail → cleanup
 *
 * Runs against the Docker test stack on port 3901 with the mock-linear
 * service providing canned GraphQL responses.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('Linear Sync', () => {
  test('full lifecycle: install → connect → sync → verify → cleanup', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on disconnect/uninstall)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Phase 0 — Cleanup: remove linear-sync if installed from prior run
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingLinearCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Linear Sync/i });
    if (await existingLinearCard.count() > 0) {
      await ownerPage.goto(`${BASE_URL}/admin/apps/linear-sync`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/linear-sync/uninstall"] button[type="submit"]');
      if (await uninstallBtn.count() > 0) {
        await uninstallBtn.click();
        await ownerPage.waitForLoadState('domcontentloaded');
        await ownerPage.waitForTimeout(3000);
      }
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // ──────────────────────────────────────────
    // Phase 1 — Prerequisite: install basic-pkm model
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Mental Models', { timeout: 15000 });

    const bpkmCard = ownerPage.locator('.card').filter({ hasText: /basic-pkm/i });
    if (await bpkmCard.count() === 0) {
      // Install basic-pkm
      const modelInstallInput = ownerPage.locator('#model_path');
      await expect(modelInstallInput).toBeVisible({ timeout: 10000 });
      await modelInstallInput.fill('/app/models/basic-pkm');
      await ownerPage.locator('form.install-form button[type="submit"]').click();
      await ownerPage.waitForLoadState('domcontentloaded');

      // Wait for model to appear in the list
      await expect(async () => {
        await ownerPage.goto(`${BASE_URL}/admin/models`);
        await ownerPage.waitForLoadState('domcontentloaded');
        const card = ownerPage.locator('.card').filter({ hasText: /basic-pkm/i });
        await expect(card).toBeVisible();
      }).toPass({ timeout: 30_000, intervals: [3000, 5000, 5000] });
    }

    // ──────────────────────────────────────────
    // Phase 2 — Install linear-sync app
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/linear-sync');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll until linear-sync shows "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Linear Sync/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Linear Sync/i });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.status-badge')).toContainText(/running/i);

    // ──────────────────────────────────────────
    // Phase 3 — Open app settings page in workspace
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage, 20000);
    await waitForIdle(ownerPage);

    // Find and expand the APPS section
    const appsSidebar = ownerPage.locator('#section-apps');
    await expect(appsSidebar).toBeVisible({ timeout: 10000 });
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    const isExpanded = await appsSidebar.evaluate(el => el.classList.contains('expanded'));
    if (!isExpanded) {
      await appsSidebar.locator('.explorer-section-header').click();
      await ownerPage.waitForTimeout(1000);
      await waitForIdle(ownerPage);
    }

    // Click the "Linear Sync" leaf to open the app page tab
    const linearLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'Linear Sync' });
    await expect(linearLeaf).toBeVisible({ timeout: 15000 });
    await linearLeaf.click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Wait for the connect fragment to load
    await expect(ownerPage.locator('#connect-content')).toBeVisible({ timeout: 30000 });

    // Verify the API key form is visible
    await expect(ownerPage.locator(SEL.linearSync.apiKeyInput)).toBeVisible({ timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 4 — Connect via API key
    // ──────────────────────────────────────────
    await ownerPage.locator(SEL.linearSync.apiKeyInput).fill('lin_api_test_mock_key');
    await ownerPage.locator(SEL.linearSync.connectBtn).click();

    // Wait for connected status — htmx swaps the content
    await expect(ownerPage.locator(SEL.linearSync.connectStatus)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.linearSync.connectStatus)).toContainText('Connected');
    await expect(ownerPage.locator(SEL.linearSync.workspaceName)).toContainText('Test Workspace');

    // ──────────────────────────────────────────
    // Phase 5 — Select team
    // ──────────────────────────────────────────
    // Team checkboxes should be visible after connecting
    const firstTeamCheckbox = ownerPage.locator(SEL.linearSync.teamCheckbox).first();
    await expect(firstTeamCheckbox).toBeVisible({ timeout: 10000 });
    await firstTeamCheckbox.check();
    await ownerPage.locator(SEL.linearSync.saveTeamsBtn).click();

    // Wait for htmx swap to complete
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify connection persisted after re-render
    await expect(ownerPage.locator(SEL.linearSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 6 — Configure sync
    // ──────────────────────────────────────────
    const bidirectionalRadio = ownerPage.locator(SEL.linearSync.syncDirectionBidirectional);
    await expect(bidirectionalRadio).toBeVisible({ timeout: 10000 });
    await bidirectionalRadio.check();
    await ownerPage.locator(SEL.linearSync.saveConfigBtn).click();

    // Wait for htmx swap
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify still connected after config save
    await expect(ownerPage.locator(SEL.linearSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 7 — Sync Now
    // ──────────────────────────────────────────
    const syncNowBtn = ownerPage.locator(SEL.linearSync.syncNowBtn);
    await expect(syncNowBtn).toBeVisible({ timeout: 10000 });
    await syncNowBtn.click();

    // Wait for sync to complete — the page re-renders with sync stats.
    // Sync involves calling the mock Linear API and creating objects,
    // so give it generous time.
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify sync stats section appeared with results
    await expect(ownerPage.locator(SEL.linearSync.syncStats)).toBeVisible({ timeout: 60000 });

    // Check for "Last Pull" section — should show "ok" status
    const pullSection = ownerPage.locator('.stat-group').filter({ hasText: 'Last Pull' });
    await expect(pullSection).toBeVisible({ timeout: 10000 });
    await expect(pullSection.locator('.stat-value').first()).toContainText('ok');

    // Check for created count — mock API returns 3 issues
    const createdRow = pullSection.locator('.stat-row').filter({ hasText: 'Created' });
    await expect(createdRow).toBeVisible();
    const createdValue = createdRow.locator('.stat-value');
    // Should show 3 (created from mock issues)
    await expect(createdValue).toContainText('3');

    // ──────────────────────────────────────────
    // Phase 8 — Verify tasks via SPARQL
    // ──────────────────────────────────────────
    const sparqlQuery = `
      PREFIX bpkm: <https://test.example.org/data/vocab/bpkm/>
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      SELECT (COUNT(?s) AS ?count) WHERE { ?s rdf:type bpkm:Task }
    `;

    const sparqlResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `query=${encodeURIComponent(sparqlQuery)}`,
    });
    expect(sparqlResp.status()).toBe(200);
    const sparqlData = await sparqlResp.json();

    // The query returns { results: { bindings: [{ count: { value: "3" } }] } }
    const bindings = sparqlData?.results?.bindings ?? [];
    expect(bindings.length).toBeGreaterThan(0);
    const taskCount = parseInt(bindings[0]?.count?.value ?? '0', 10);
    expect(taskCount).toBeGreaterThanOrEqual(3);

    // ──────────────────────────────────────────
    // Phase 9 — Admin detail page
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/linear-sync`);
    await ownerPage.waitForLoadState('domcontentloaded');

    await expect(ownerPage.locator('h1')).toContainText('Linear Sync', { timeout: 15000 });
    await expect(ownerPage.locator('.model-title-row .status-badge')).toContainText(/running/i);

    // ──────────────────────────────────────────
    // Phase 10 — Cleanup: uninstall linear-sync
    // ──────────────────────────────────────────
    const uninstallForm = ownerPage.locator('form[action="/admin/apps/linear-sync/uninstall"]');
    await expect(uninstallForm).toBeVisible();
    await uninstallForm.locator('button[type="submit"]').click();

    // Wait for redirect to apps list
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify linear-sync no longer appears
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Linear Sync/i });
    await expect(removedCard).toHaveCount(0, { timeout: 10000 });
  });
});
