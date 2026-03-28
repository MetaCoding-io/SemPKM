/**
 * GitHub Sync E2E Tests
 *
 * Proves the full GitHub sync vertical against a mock GitHub REST API:
 *   install basic-pkm → install github-sync → connect PAT →
 *   select repo → configure sync → Sync Now → verify tasks via SPARQL →
 *   verify PR→issue edge → admin detail → cleanup
 *
 * Runs against the Docker test stack on port 3901 with the mock-github
 * service providing canned REST responses.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('GitHub Sync', () => {
  test('full lifecycle: install → connect → sync → verify → cleanup', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on disconnect/uninstall)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Phase 0 — Cleanup: remove github-sync if installed from prior run
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /GitHub Sync/i });
    if (await existingCard.count() > 0) {
      await ownerPage.goto(`${BASE_URL}/admin/apps/github-sync`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/github-sync/uninstall"] button[type="submit"]');
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

    const bpkmRow = ownerPage.locator('#model-table tr, #model-table .card').filter({ hasText: /basic.pkm/i });
    if (await bpkmRow.count() === 0) {
      const modelInstallInput = ownerPage.locator('#model-path');
      await expect(modelInstallInput).toBeVisible({ timeout: 10000 });
      await modelInstallInput.fill('/app/models/basic-pkm');
      await ownerPage.locator('form button[type="submit"]').first().click();
      await ownerPage.waitForLoadState('domcontentloaded');

      // Wait for model to appear in the list
      await expect(async () => {
        await ownerPage.goto(`${BASE_URL}/admin/models`);
        await ownerPage.waitForLoadState('domcontentloaded');
        const row = ownerPage.locator('#model-table tr, #model-table .card').filter({ hasText: /basic.pkm/i });
        await expect(row).toBeVisible();
      }).toPass({ timeout: 30_000, intervals: [3000, 5000, 5000] });
    }

    // ──────────────────────────────────────────
    // Phase 2 — Install github-sync app
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/github-sync');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll until github-sync shows "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /GitHub Sync/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /GitHub Sync/i });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.status-badge')).toContainText(/running/i);

    // Give the app subprocess time to fully start and open its UDS socket
    await ownerPage.waitForTimeout(5000);

    // ──────────────────────────────────────────
    // Phase 3 — Open app settings page in workspace
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage, 20000);
    await waitForIdle(ownerPage);

    // Find and expand the APPS section (collapsed by default)
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

    // Click the "GitHub Sync" leaf to open the app settings tab
    // Apps are loaded via htmx hx-trigger="load" — wait for loading to finish
    const githubLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'GitHub Sync' });
    await expect(githubLeaf).toBeVisible({ timeout: 30000 });
    await githubLeaf.click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Wait for the connect fragment to load (may need retry if app subprocess was still starting)
    await expect(async () => {
      const content = ownerPage.locator('#connect-content');
      if (await content.count() === 0) {
        // Fragment may have failed — reload the page to retry
        await ownerPage.goto(`${BASE_URL}/browser/`);
        await waitForWorkspace(ownerPage, 20000);
        await waitForIdle(ownerPage);
        // Re-expand APPS and re-click GitHub Sync
        const appsSection = ownerPage.locator('#section-apps');
        const expanded = await appsSection.evaluate(el => el.classList.contains('expanded'));
        if (!expanded) {
          await appsSection.locator('.explorer-section-header').click();
          await ownerPage.waitForTimeout(1000);
        }
        const leaf = appsSection.locator('.tree-leaf', { hasText: 'GitHub Sync' });
        await leaf.click();
        await ownerPage.waitForTimeout(3000);
        await waitForIdle(ownerPage);
      }
      await expect(ownerPage.locator('#connect-content')).toBeVisible();
    }).toPass({ timeout: 60_000, intervals: [5000, 10000, 10000] });

    // Verify the PAT form is visible
    await expect(ownerPage.locator(SEL.githubSync.patInput)).toBeVisible({ timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 4 — Connect via PAT
    // ──────────────────────────────────────────
    await ownerPage.locator(SEL.githubSync.patInput).fill('ghp_testtoken123456789');
    await ownerPage.locator(SEL.githubSync.connectBtn).click();

    // Wait for connected status — htmx swaps the content
    await expect(ownerPage.locator(SEL.githubSync.connectStatus)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.githubSync.connectStatus)).toContainText('Connected');
    await expect(ownerPage.locator(SEL.githubSync.username)).toContainText('test-user');

    // ──────────────────────────────────────────
    // Phase 5 — Select repository
    // ──────────────────────────────────────────
    // Repo checkboxes should be visible after connecting
    const firstRepoCheckbox = ownerPage.locator(SEL.githubSync.repoCheckbox).first();
    await expect(firstRepoCheckbox).toBeVisible({ timeout: 10000 });
    await firstRepoCheckbox.check();
    await ownerPage.locator(SEL.githubSync.saveReposBtn).click();

    // Wait for htmx swap to complete
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify connection persisted after re-render
    await expect(ownerPage.locator(SEL.githubSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 6 — Configure sync direction
    // ──────────────────────────────────────────
    const bidirectionalRadio = ownerPage.locator(SEL.githubSync.syncDirectionBidirectional);
    await expect(bidirectionalRadio).toBeVisible({ timeout: 10000 });
    await bidirectionalRadio.check();
    await ownerPage.locator(SEL.githubSync.saveConfigBtn).click();

    // Wait for htmx swap
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify still connected after config save
    await expect(ownerPage.locator(SEL.githubSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 7 — Sync Now
    // ──────────────────────────────────────────
    const syncNowBtn = ownerPage.locator(SEL.githubSync.syncNowBtn);
    await expect(syncNowBtn).toBeVisible({ timeout: 10000 });
    await syncNowBtn.click();

    // Wait for sync to complete — involves mock API calls and object creation
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify sync stats section appeared with results
    await expect(ownerPage.locator(SEL.githubSync.syncStats)).toBeVisible({ timeout: 60000 });

    // Check for "Last Pull" section — should show "success" status
    const pullSection = ownerPage.locator('.stat-group').filter({ hasText: 'Last Pull' });
    await expect(pullSection).toBeVisible({ timeout: 10000 });
    const pullStatus = pullSection.locator('.stat-row').filter({ hasText: 'Status' }).locator('.stat-value');
    await expect(pullStatus).toContainText(/success|ok/);

    // Check for created count — mock API returns 3 issues (2 regular + 1 PR)
    const createdRow = pullSection.locator('.stat-row').filter({ hasText: 'Created' });
    await expect(createdRow).toBeVisible();
    const createdValue = createdRow.locator('.stat-value');
    // Should show ≥ 2 created objects (issues + PR all become bpkm:Task)
    const createdText = await createdValue.textContent();
    const createdNum = parseInt(createdText?.trim() || '0', 10);
    expect(createdNum).toBeGreaterThanOrEqual(2);

    // ──────────────────────────────────────────
    // Phase 8 — Verify tasks via SPARQL (count)
    // ──────────────────────────────────────────
    const countQuery = `
      SELECT (COUNT(?s) AS ?count) WHERE {
        ?s a <urn:sempkm:model:basic-pkm:Task> .
      }
    `;

    const countResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `query=${encodeURIComponent(countQuery)}`,
    });
    expect(countResp.status()).toBe(200);
    const countData = await countResp.json();

    const bindings = countData?.results?.bindings ?? [];
    expect(bindings.length).toBeGreaterThan(0);
    const taskCount = parseInt(bindings[0]?.count?.value ?? '0', 10);
    // 2 issues + 1 PR = 3 Task objects minimum
    expect(taskCount).toBeGreaterThanOrEqual(3);

    // ──────────────────────────────────────────
    // Phase 9 — Verify PR-to-issue edge via SPARQL (ASK)
    // ──────────────────────────────────────────
    const edgeQuery = `
      ASK WHERE {
        ?pr <urn:sempkm:model:basic-pkm:dependsOn> ?issue .
        ?pr <urn:sempkm:model:basic-pkm:externalProvider> "github-pr" .
      }
    `;

    const edgeResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `query=${encodeURIComponent(edgeQuery)}`,
    });
    expect(edgeResp.status()).toBe(200);
    const edgeData = await edgeResp.json();
    expect(edgeData?.boolean).toBe(true);

    // ──────────────────────────────────────────
    // Phase 10 — Admin detail page verification
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const runningCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /GitHub Sync/i });
    await expect(runningCard).toBeVisible({ timeout: 15000 });
    await expect(runningCard.locator('.status-badge')).toContainText(/running/i);

    // ──────────────────────────────────────────
    // Phase 11 — Cleanup: uninstall github-sync
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/github-sync`);
    await ownerPage.waitForLoadState('domcontentloaded');

    await expect(ownerPage.locator('h1')).toContainText('GitHub Sync', { timeout: 15000 });

    const uninstallForm = ownerPage.locator('form[action="/admin/apps/github-sync/uninstall"]');
    await expect(uninstallForm).toBeVisible();
    await uninstallForm.locator('button[type="submit"]').click();

    // Wait for redirect to apps list
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify github-sync no longer appears
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /GitHub Sync/i });
    await expect(removedCard).toHaveCount(0, { timeout: 10000 });
  });
});
