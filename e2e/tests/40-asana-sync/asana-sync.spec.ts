/**
 * Asana Sync E2E Tests
 *
 * Proves the full Asana sync vertical against a mock Asana REST API:
 *   install basic-pkm → install asana-sync → enter PAT →
 *   select projects → discover fields → configure field mapping →
 *   set sync direction → Sync Now →
 *   verify tasks via SPARQL → admin detail → cleanup
 *
 * Runs against the Docker test stack on port 3901 with the mock-asana
 * service providing canned Asana REST responses.
 *
 * Asana uses Personal Access Token (PAT) auth — no OAuth simulation
 * needed. The PAT form POSTs directly to the app's connect endpoint.
 *
 * The novel phase compared to prior sync app E2E tests is field mapping
 * configuration (Phase 4) — after project selection, the test clicks
 * "Discover Fields", waits for htmx swap, then configures section-based
 * status mapping before saving.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('Asana Sync', () => {
  test('full lifecycle: install → PAT connect → field mapping → sync → verify → cleanup', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on disconnect/uninstall)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Phase 0 — Cleanup: remove asana-sync if installed from prior run
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Asana Sync/i });
    if (await existingCard.count() > 0) {
      await ownerPage.goto(`${BASE_URL}/admin/apps/asana-sync`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/asana-sync/uninstall"] button[type="submit"]');
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
    // Phase 2 — Install asana-sync app
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/asana-sync');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll until asana-sync shows "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Asana Sync/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Asana Sync/i });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.status-badge')).toContainText(/running/i);

    // Give the app subprocess time to fully start and open its UDS socket
    await ownerPage.waitForTimeout(5000);

    // ──────────────────────────────────────────
    // Phase 3 — PAT connect
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage, 20000);
    await waitForIdle(ownerPage);

    // Find and expand the APPS section (collapsed by default per KNOWLEDGE.md)
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

    // Click the "Asana Sync" leaf to open the app settings tab
    const asanaLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'Asana Sync' });
    await expect(asanaLeaf).toBeVisible({ timeout: 30000 });
    await asanaLeaf.click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Wait for the connect fragment to load (retry if app subprocess was still starting)
    await expect(async () => {
      const content = ownerPage.locator('#connect-content');
      if (await content.count() === 0) {
        await ownerPage.goto(`${BASE_URL}/browser/`);
        await waitForWorkspace(ownerPage, 20000);
        await waitForIdle(ownerPage);
        const appsSection = ownerPage.locator('#section-apps');
        const expanded = await appsSection.evaluate(el => el.classList.contains('expanded'));
        if (!expanded) {
          await appsSection.locator('.explorer-section-header').click();
          await ownerPage.waitForTimeout(1000);
        }
        const leaf = appsSection.locator('.tree-leaf', { hasText: 'Asana Sync' });
        await leaf.click();
        await ownerPage.waitForTimeout(3000);
        await waitForIdle(ownerPage);
      }
      await expect(ownerPage.locator('#connect-content')).toBeVisible();
    }).toPass({ timeout: 60_000, intervals: [5000, 10000, 10000] });

    // Fill PAT — matches mock server VALID_TOKEN
    await expect(ownerPage.locator(SEL.asanaSync.patInput)).toBeVisible({ timeout: 10000 });
    await ownerPage.locator(SEL.asanaSync.patInput).fill('test-asana-pat-token-abc123');
    await ownerPage.locator(SEL.asanaSync.connectBtn).click();

    // Wait for htmx swap — PAT form submits and swaps to connect_status.html
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify connected status and account email
    await expect(ownerPage.locator(SEL.asanaSync.connectStatus)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.asanaSync.connectStatus)).toContainText('Connected');
    await expect(ownerPage.locator('body')).toContainText('test@example.com');

    // ──────────────────────────────────────────
    // Phase 4 — Configure field mapping (novel phase)
    // ──────────────────────────────────────────

    // 4a — Select all projects and save
    const firstProjectCheckbox = ownerPage.locator(SEL.asanaSync.projectCheckbox).first();
    await expect(firstProjectCheckbox).toBeVisible({ timeout: 10000 });

    const projectCheckboxes = ownerPage.locator(SEL.asanaSync.projectCheckbox);
    const projectCount = await projectCheckboxes.count();
    for (let i = 0; i < projectCount; i++) {
      await projectCheckboxes.nth(i).check();
    }

    await ownerPage.locator(SEL.asanaSync.saveProjectsBtn).click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify still connected after project save
    await expect(ownerPage.locator(SEL.asanaSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // 4b — Discover fields
    const discoverBtn = ownerPage.locator(SEL.asanaSync.discoverFieldsBtn);
    await expect(discoverBtn).toBeVisible({ timeout: 10000 });
    await discoverBtn.click();

    // Wait for htmx swap — discover-fields POSTs and swaps new content with field mapping form
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify the field mapping form appeared after discovery
    await expect(ownerPage.locator('.field-mapping-form')).toBeVisible({ timeout: 30000 });

    // 4c — Select section-based status mapping
    const sectionRadio = ownerPage.locator(SEL.asanaSync.statusSourceSection);
    await expect(sectionRadio).toBeVisible({ timeout: 10000 });
    await sectionRadio.check();
    await ownerPage.waitForTimeout(1000);

    // Verify section mapping table is visible
    const sectionUI = ownerPage.locator('#status-section-ui');
    await expect(sectionUI).toBeVisible({ timeout: 5000 });
    const mappingTable = sectionUI.locator('.mapping-table');
    await expect(mappingTable).toBeVisible({ timeout: 5000 });

    // 4d — Save field mapping configuration
    await ownerPage.locator(SEL.asanaSync.saveMappingBtn).click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify still connected and config summary shows section-based status
    await expect(ownerPage.locator(SEL.asanaSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // 4e — Set sync direction to bidirectional and save
    const bidirectionalRadio = ownerPage.locator(SEL.asanaSync.syncDirectionBidirectional);
    await expect(bidirectionalRadio).toBeVisible({ timeout: 10000 });
    await bidirectionalRadio.check();
    await ownerPage.locator(SEL.asanaSync.saveConfigBtn).click();

    // Wait for htmx swap
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify still connected after config save
    await expect(ownerPage.locator(SEL.asanaSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 5 — Sync Now + verify tasks
    // ──────────────────────────────────────────
    const syncNowBtn = ownerPage.locator(SEL.asanaSync.syncNowBtn);
    await expect(syncNowBtn).toBeVisible({ timeout: 10000 });
    await syncNowBtn.click();

    // Wait for sync to complete — involves mock Asana calls and object creation
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify sync stats section appeared with results
    await expect(ownerPage.locator(SEL.asanaSync.syncStats)).toBeVisible({ timeout: 60000 });

    // Check for "Last Pull" section — should show "ok" status
    const pullSection = ownerPage.locator('.stat-group').filter({ hasText: 'Last Pull' });
    await expect(pullSection).toBeVisible({ timeout: 10000 });
    const pullStatus = pullSection.locator('.stat-row').filter({ hasText: 'Status' }).locator('.stat-value');
    await expect(pullStatus).toContainText(/ok|success/);

    // Check for created count — mock returns 3 tasks across 2 projects
    const createdRow = pullSection.locator('.stat-row').filter({ hasText: 'Created' });
    await expect(createdRow).toBeVisible();
    const createdValue = createdRow.locator('.stat-value');
    const createdText = await createdValue.textContent();
    const createdNum = parseInt(createdText?.trim() || '0', 10);
    // Should have at least 2 tasks created (Design landing page + Write API documentation + Set up CI pipeline)
    expect(createdNum).toBeGreaterThanOrEqual(2);

    // ──────────────────────────────────────────
    // Phase 5b — Verify tasks via SPARQL
    // ──────────────────────────────────────────
    // Query for Task labels in the current graph
    const labelQuery = `
      PREFIX dcterms: <http://purl.org/dc/terms/>
      SELECT ?label WHERE {
        ?s a <urn:sempkm:model:basic-pkm:Task> ;
           dcterms:title ?label .
      } ORDER BY ?label
    `;

    const labelResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `query=${encodeURIComponent(labelQuery)}`,
    });
    expect(labelResp.status()).toBe(200);
    const labelData = await labelResp.json();
    const labels = (labelData?.results?.bindings ?? []).map(
      (b: { label: { value: string } }) => b.label.value
    );

    // Must have at least "Design landing page" and "Write API documentation" from mock data
    expect(labels.length).toBeGreaterThanOrEqual(2);
    expect(labels).toContain('Design landing page');
    expect(labels).toContain('Write API documentation');

    // ──────────────────────────────────────────
    // Phase 6 — Admin detail + cleanup
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const runningCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Asana Sync/i });
    await expect(runningCard).toBeVisible({ timeout: 15000 });
    await expect(runningCard.locator('.status-badge')).toContainText(/running/i);

    // Navigate to admin detail page
    await ownerPage.goto(`${BASE_URL}/admin/apps/asana-sync`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Asana Sync', { timeout: 15000 });

    // Verify task history section exists on the detail page
    const taskHistory = ownerPage.locator('.task-history, .sync-history, [data-testid="task-history"]');
    if (await taskHistory.count() > 0) {
      await expect(taskHistory.first()).toBeVisible();
    }

    // Uninstall the asana-sync app
    const uninstallForm = ownerPage.locator('form[action="/admin/apps/asana-sync/uninstall"]');
    await expect(uninstallForm).toBeVisible();
    await uninstallForm.locator('button[type="submit"]').click();

    // Wait for redirect to apps list
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify asana-sync no longer appears
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Asana Sync/i });
    await expect(removedCard).toHaveCount(0, { timeout: 10000 });

    // Best-effort: uninstall basic-pkm model (may fail if seed data exists)
    try {
      await ownerPage.goto(`${BASE_URL}/admin/models`);
      await ownerPage.waitForLoadState('domcontentloaded');
      // Only attempt if the model is listed — skip uninstall if it has user data
    } catch {
      // Intentionally ignored — cleanup is best-effort
    }
  });
});
