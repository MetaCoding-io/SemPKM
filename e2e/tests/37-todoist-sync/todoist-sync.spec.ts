/**
 * Todoist Sync E2E Tests
 *
 * Proves the full Todoist sync vertical against a mock Todoist API:
 *   install basic-pkm → install todoist-sync → connect PAT →
 *   select project → configure sync → Sync Now → verify tasks via SPARQL →
 *   verify priority mapping → admin detail → cleanup
 *
 * Runs against the Docker test stack on port 3901 with the mock-todoist
 * service providing canned REST responses on port 8080.
 *
 * Mock server dependency: mock-todoist Docker service
 *   (e2e/mock-todoist-api/server.py) accepting token
 *   "test-todoist-pat-token-abc123".
 *
 * Known limitation: Phase 2 (app install) may hit the pre-existing
 *   subprocess 500 error documented across M016-M018. This is not
 *   Todoist-specific — all app installs may encounter it.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('Todoist Sync', () => {
  test('full lifecycle: install → connect → sync → verify → cleanup', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on disconnect/uninstall)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Phase 0 — Cleanup: remove todoist-sync if installed from prior run
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Todoist Sync/i });
    if (await existingCard.count() > 0) {
      await ownerPage.goto(`${BASE_URL}/admin/apps/todoist-sync`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/todoist-sync/uninstall"] button[type="submit"]');
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
    // Phase 2 — Install todoist-sync app
    // NOTE: This phase may hit the pre-existing subprocess 500 error
    //       documented across M016-M018. The error is not Todoist-specific;
    //       all app installs may encounter it. The test is structurally
    //       complete regardless.
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/todoist-sync');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll until todoist-sync shows "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Todoist Sync/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Todoist Sync/i });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.status-badge')).toContainText(/running/i);

    // Give the app subprocess time to fully start and open its UDS socket
    await ownerPage.waitForTimeout(5000);

    // ──────────────────────────────────────────
    // Phase 3 — Open app settings page in workspace
    // Per KNOWLEDGE.md: workspace explorer sections start collapsed.
    // Must click section header to add .expanded class.
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

    // Click the "Todoist Sync" leaf to open the app settings tab
    // Apps are loaded via htmx hx-trigger="load" — wait for loading to finish
    const todoistLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'Todoist Sync' });
    await expect(todoistLeaf).toBeVisible({ timeout: 30000 });
    await todoistLeaf.click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Wait for the connect fragment to load (may need retry if app subprocess was still starting)
    await expect(async () => {
      const content = ownerPage.locator('#connect-content');
      if (await content.count() === 0) {
        // Fragment may have failed — reload and retry
        await ownerPage.goto(`${BASE_URL}/browser/`);
        await waitForWorkspace(ownerPage, 20000);
        await waitForIdle(ownerPage);
        // Re-expand APPS and re-click Todoist Sync
        const appsSection = ownerPage.locator('#section-apps');
        const expanded = await appsSection.evaluate(el => el.classList.contains('expanded'));
        if (!expanded) {
          await appsSection.locator('.explorer-section-header').click();
          await ownerPage.waitForTimeout(1000);
        }
        const leaf = appsSection.locator('.tree-leaf', { hasText: 'Todoist Sync' });
        await leaf.click();
        await ownerPage.waitForTimeout(3000);
        await waitForIdle(ownerPage);
      }
      await expect(ownerPage.locator('#connect-content')).toBeVisible();
    }).toPass({ timeout: 60_000, intervals: [5000, 10000, 10000] });

    // Verify the PAT form is visible
    await expect(ownerPage.locator(SEL.todoistSync.patInput)).toBeVisible({ timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 4 — Connect via PAT
    // Token must match mock server's VALID_TOKEN = "test-todoist-pat-token-abc123"
    // ──────────────────────────────────────────
    await ownerPage.locator(SEL.todoistSync.patInput).fill('test-todoist-pat-token-abc123');
    await ownerPage.locator(SEL.todoistSync.connectBtn).click();

    // Wait for connected status — htmx swaps the content
    await expect(ownerPage.locator(SEL.todoistSync.connectStatus)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.todoistSync.connectStatus)).toContainText('Connected');

    // Verify token preview is visible
    await expect(ownerPage.locator(SEL.todoistSync.tokenPreview)).toBeVisible({ timeout: 5000 });

    // ──────────────────────────────────────────
    // Phase 5 — Select project
    // Projects are loaded via htmx hx-trigger="load" into #projects-list
    // ──────────────────────────────────────────
    const firstProjectCheckbox = ownerPage.locator(SEL.todoistSync.projectCheckbox).first();
    await expect(firstProjectCheckbox).toBeVisible({ timeout: 15000 });
    await firstProjectCheckbox.check();
    await ownerPage.locator(SEL.todoistSync.saveProjectsBtn).click();

    // Wait for htmx swap to complete
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify connection persisted after re-render
    await expect(ownerPage.locator(SEL.todoistSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 6 — Configure sync direction
    // ──────────────────────────────────────────
    const bidirectionalRadio = ownerPage.locator(SEL.todoistSync.syncDirectionBidirectional);
    await expect(bidirectionalRadio).toBeVisible({ timeout: 10000 });
    await bidirectionalRadio.check();
    await ownerPage.locator(SEL.todoistSync.saveConfigBtn).click();

    // Wait for htmx swap
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify still connected after config save
    await expect(ownerPage.locator(SEL.todoistSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 7 — Sync Now
    // ──────────────────────────────────────────
    const syncNowBtn = ownerPage.locator(SEL.todoistSync.syncNowBtn);
    await expect(syncNowBtn).toBeVisible({ timeout: 10000 });
    await syncNowBtn.click();

    // Wait for sync to complete — involves mock API calls and object creation
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify sync stats section appeared with results
    await expect(ownerPage.locator(SEL.todoistSync.syncStats)).toBeVisible({ timeout: 60000 });

    // Check for "Last Pull" section — should show "success" status
    const pullSection = ownerPage.locator('.stat-group').filter({ hasText: 'Last Pull' });
    await expect(pullSection).toBeVisible({ timeout: 10000 });
    const pullStatus = pullSection.locator('.stat-row').filter({ hasText: 'Status' }).locator('.stat-value');
    await expect(pullStatus).toContainText(/success|ok/);

    // Check for created count — mock API returns 2 tasks (one priority 4, one priority 1)
    const createdRow = pullSection.locator('.stat-row').filter({ hasText: 'Created' });
    await expect(createdRow).toBeVisible();
    const createdValue = createdRow.locator('.stat-value');
    const createdText = await createdValue.textContent();
    const createdNum = parseInt(createdText?.trim() || '0', 10);
    expect(createdNum).toBeGreaterThanOrEqual(1);

    // ──────────────────────────────────────────
    // Phase 8 — Verify tasks via SPARQL
    // Check that tasks with externalProvider = "todoist" were created
    // and verify priority inversion: Todoist priority 4 → bpkm "critical"
    // ──────────────────────────────────────────

    // 8a — Count todoist tasks
    const countQuery = `
      SELECT (COUNT(?s) AS ?count) WHERE {
        ?s a <urn:sempkm:model:basic-pkm:Task> .
        ?s <urn:sempkm:model:basic-pkm:externalProvider> "todoist" .
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
    // Mock API returns 2 tasks — at least 1 should have been synced
    expect(taskCount).toBeGreaterThanOrEqual(1);

    // 8b — Verify priority mapping: Todoist priority 4 → bpkm "critical"
    const priorityQuery = `
      ASK WHERE {
        ?task a <urn:sempkm:model:basic-pkm:Task> .
        ?task <urn:sempkm:model:basic-pkm:externalProvider> "todoist" .
        ?task <urn:sempkm:model:basic-pkm:priority> "critical" .
      }
    `;

    const priorityResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `query=${encodeURIComponent(priorityQuery)}`,
    });
    expect(priorityResp.status()).toBe(200);
    const priorityData = await priorityResp.json();
    // The mock server's first task has priority 4 which maps to "critical"
    expect(priorityData?.boolean).toBe(true);

    // ──────────────────────────────────────────
    // Phase 9 — Admin detail page verification
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/todoist-sync`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Todoist Sync', { timeout: 15000 });

    // ──────────────────────────────────────────
    // Phase 10 — Cleanup: uninstall todoist-sync
    // ──────────────────────────────────────────
    const uninstallForm = ownerPage.locator('form[action="/admin/apps/todoist-sync/uninstall"]');
    await expect(uninstallForm).toBeVisible({ timeout: 10000 });
    await uninstallForm.locator('button[type="submit"]').click();

    // Wait for redirect to apps list
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify todoist-sync no longer appears
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Todoist Sync/i });
    await expect(removedCard).toHaveCount(0, { timeout: 10000 });
  });
});
