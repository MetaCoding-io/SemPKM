/**
 * Jira Sync E2E Tests
 *
 * Proves the full Jira sync vertical against a mock Jira REST API:
 *   install basic-pkm → install jira-sync → connect (email + token + site URL) →
 *   select project → configure sync → Sync Now → verify tasks via SPARQL →
 *   verify Epic→Milestone → verify dependsOn edge → admin detail → cleanup
 *
 * Runs against the Docker test stack on port 3901 with the mock-jira
 * service providing canned REST responses.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('Jira Sync', () => {
  test('full lifecycle: install → connect → sync → verify → cleanup', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on disconnect/uninstall)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Phase 0 — Cleanup: remove jira-sync if installed from prior run
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Jira Sync/i });
    if (await existingCard.count() > 0) {
      await ownerPage.goto(`${BASE_URL}/admin/apps/jira-sync`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/jira-sync/uninstall"] button[type="submit"]');
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
    // Phase 2 — Install jira-sync app
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/jira-sync');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll until jira-sync shows "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Jira Sync/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Jira Sync/i });
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

    // Click the "Jira Sync" leaf to open the app settings tab
    // Apps are loaded via htmx hx-trigger="load" — wait for loading to finish
    const jiraLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'Jira Sync' });
    await expect(jiraLeaf).toBeVisible({ timeout: 30000 });
    await jiraLeaf.click();
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
        // Re-expand APPS and re-click Jira Sync
        const appsSection = ownerPage.locator('#section-apps');
        const expanded = await appsSection.evaluate(el => el.classList.contains('expanded'));
        if (!expanded) {
          await appsSection.locator('.explorer-section-header').click();
          await ownerPage.waitForTimeout(1000);
        }
        const leaf = appsSection.locator('.tree-leaf', { hasText: 'Jira Sync' });
        await leaf.click();
        await ownerPage.waitForTimeout(3000);
        await waitForIdle(ownerPage);
      }
      await expect(ownerPage.locator('#connect-content')).toBeVisible();
    }).toPass({ timeout: 60_000, intervals: [5000, 10000, 10000] });

    // Verify the credentials form is visible (3-field connect — key difference from GitHub)
    await expect(ownerPage.locator(SEL.jiraSync.emailInput)).toBeVisible({ timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 4 — Connect via Jira Cloud credentials (email + token + site URL)
    // ──────────────────────────────────────────
    await ownerPage.locator(SEL.jiraSync.emailInput).fill('test@example.com');
    await ownerPage.locator(SEL.jiraSync.tokenInput).fill('fake-jira-token-12345');
    await ownerPage.locator(SEL.jiraSync.siteUrlInput).fill('testcompany.atlassian.net');
    await ownerPage.locator(SEL.jiraSync.connectBtn).click();

    // Wait for connected status — htmx swaps the content
    await expect(ownerPage.locator(SEL.jiraSync.connectStatus)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.jiraSync.connectStatus)).toContainText('Connected');
    await expect(ownerPage.locator(SEL.jiraSync.siteUrl)).toContainText('testcompany.atlassian.net');

    // ──────────────────────────────────────────
    // Phase 5 — Select project
    // ──────────────────────────────────────────
    // Project checkboxes should be visible after connecting
    const firstProjectCheckbox = ownerPage.locator(SEL.jiraSync.projectCheckbox).first();
    await expect(firstProjectCheckbox).toBeVisible({ timeout: 10000 });
    await firstProjectCheckbox.check();
    await ownerPage.locator(SEL.jiraSync.saveProjectsBtn).click();

    // Wait for htmx swap to complete
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify connection persisted after re-render
    await expect(ownerPage.locator(SEL.jiraSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 6 — Configure sync direction
    // ──────────────────────────────────────────
    const bidirectionalRadio = ownerPage.locator(SEL.jiraSync.syncDirectionBidirectional);
    await expect(bidirectionalRadio).toBeVisible({ timeout: 10000 });
    await bidirectionalRadio.check();
    await ownerPage.locator(SEL.jiraSync.saveConfigBtn).click();

    // Wait for htmx swap
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify still connected after config save
    await expect(ownerPage.locator(SEL.jiraSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 7 — Sync Now
    // ──────────────────────────────────────────
    const syncNowBtn = ownerPage.locator(SEL.jiraSync.syncNowBtn);
    await expect(syncNowBtn).toBeVisible({ timeout: 10000 });
    await syncNowBtn.click();

    // Wait for sync to complete — involves mock API calls and object creation
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify sync stats section appeared with results
    await expect(ownerPage.locator(SEL.jiraSync.syncStats)).toBeVisible({ timeout: 60000 });

    // Check for "Last Pull" section — should show "success" status
    const pullSection = ownerPage.locator('.stat-group').filter({ hasText: 'Last Pull' });
    await expect(pullSection).toBeVisible({ timeout: 10000 });
    const pullStatus = pullSection.locator('.stat-row').filter({ hasText: 'Status' }).locator('.stat-value');
    await expect(pullStatus).toContainText(/success|ok/);

    // Check for created count — mock API returns 3 issues (2 Task + 1 Epic→Milestone)
    const createdRow = pullSection.locator('.stat-row').filter({ hasText: 'Created' });
    await expect(createdRow).toBeVisible();
    const createdValue = createdRow.locator('.stat-value');
    // Should show ≥ 2 created objects (PROJ-1 + PROJ-2 become Tasks, PROJ-3 Epic becomes Milestone)
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
    // PROJ-1 + PROJ-2 = 2 Task objects minimum (PROJ-3 Epic → Milestone, not Task)
    expect(taskCount).toBeGreaterThanOrEqual(2);

    // ──────────────────────────────────────────
    // Phase 9 — Verify Epic→Milestone via SPARQL (ASK)
    // ──────────────────────────────────────────
    const milestoneQuery = `
      ASK WHERE {
        ?m a <urn:sempkm:model:basic-pkm:Milestone> .
        ?m <urn:sempkm:model:basic-pkm:externalProvider> "jira" .
      }
    `;

    const milestoneResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `query=${encodeURIComponent(milestoneQuery)}`,
    });
    expect(milestoneResp.status()).toBe(200);
    const milestoneData = await milestoneResp.json();
    expect(milestoneData?.boolean).toBe(true);

    // ──────────────────────────────────────────
    // Phase 9b — Verify dependsOn edge via SPARQL (ASK)
    // ──────────────────────────────────────────
    const dependsOnQuery = `
      ASK WHERE {
        ?blocked <urn:sempkm:model:basic-pkm:dependsOn> ?blocker .
        ?blocked <urn:sempkm:model:basic-pkm:externalProvider> "jira" .
      }
    `;

    const dependsOnResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `query=${encodeURIComponent(dependsOnQuery)}`,
    });
    expect(dependsOnResp.status()).toBe(200);
    const dependsOnData = await dependsOnResp.json();
    expect(dependsOnData?.boolean).toBe(true);

    // ──────────────────────────────────────────
    // Phase 10 — Admin detail page verification
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const runningCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Jira Sync/i });
    await expect(runningCard).toBeVisible({ timeout: 15000 });
    await expect(runningCard.locator('.status-badge')).toContainText(/running/i);

    // ──────────────────────────────────────────
    // Phase 11 — Cleanup: uninstall jira-sync
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/jira-sync`);
    await ownerPage.waitForLoadState('domcontentloaded');

    await expect(ownerPage.locator('h1')).toContainText('Jira Sync', { timeout: 15000 });

    const uninstallForm = ownerPage.locator('form[action="/admin/apps/jira-sync/uninstall"]');
    await expect(uninstallForm).toBeVisible();
    await uninstallForm.locator('button[type="submit"]').click();

    // Wait for redirect to apps list
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify jira-sync no longer appears
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Jira Sync/i });
    await expect(removedCard).toHaveCount(0, { timeout: 10000 });
  });
});
