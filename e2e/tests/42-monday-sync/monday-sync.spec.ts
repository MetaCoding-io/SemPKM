/**
 * Monday.com Sync E2E Tests
 *
 * Proves the full Monday.com sync vertical against a mock Monday.com GraphQL API:
 *   install basic-pkm → install monday-sync → connect (single API token) →
 *   select board → configure columns → configure labels →
 *   set sync direction → Sync Now → verify tasks via SPARQL →
 *   verify admin page → cleanup uninstall
 *
 * Key differences from Jira E2E:
 *   - Single API token (not 3-field: email + token + site URL)
 *   - Extra column mapping phase after board selection
 *   - Extra label mapping phase after column mapping
 *   - Board checkboxes use `.board-checkbox-item` (not `.project-checkbox-item`)
 *
 * Runs against the Docker test stack on port 3901 with the mock-monday
 * service providing canned GraphQL responses.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('Monday.com Sync', () => {
  test('full lifecycle: install → connect → column-map → sync → verify → cleanup', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on disconnect/uninstall)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Phase 0 — Cleanup: remove monday-sync if installed from prior run
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Monday\.com Sync/i });
    if (await existingCard.count() > 0) {
      await ownerPage.goto(`${BASE_URL}/admin/apps/monday-sync`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/monday-sync/uninstall"] button[type="submit"]');
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
    // Phase 2 — Install monday-sync app
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/monday-sync');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll until monday-sync shows "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Monday\.com Sync/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Monday\.com Sync/i });
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

    // Click the "Monday.com Sync" leaf to open the app settings tab
    // Apps are loaded via htmx hx-trigger="load" — wait for loading to finish
    const mondayLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'Monday.com Sync' });
    await expect(mondayLeaf).toBeVisible({ timeout: 30000 });
    await mondayLeaf.click();
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
        // Re-expand APPS and re-click Monday.com Sync
        const appsSection = ownerPage.locator('#section-apps');
        const expanded = await appsSection.evaluate(el => el.classList.contains('expanded'));
        if (!expanded) {
          await appsSection.locator('.explorer-section-header').click();
          await ownerPage.waitForTimeout(1000);
        }
        const leaf = appsSection.locator('.tree-leaf', { hasText: 'Monday.com Sync' });
        await leaf.click();
        await ownerPage.waitForTimeout(3000);
        await waitForIdle(ownerPage);
      }
      await expect(ownerPage.locator('#connect-content')).toBeVisible();
    }).toPass({ timeout: 60_000, intervals: [5000, 10000, 10000] });

    // Verify the credentials form is visible (single token field — key difference from Jira)
    await expect(ownerPage.locator(SEL.mondaySync.tokenInput)).toBeVisible({ timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 4 — Connect via API token (single field, not 3-field like Jira)
    // ──────────────────────────────────────────
    await ownerPage.locator(SEL.mondaySync.tokenInput).fill('fake-monday-token-12345');
    await ownerPage.locator(SEL.mondaySync.connectBtn).click();

    // Wait for connected status — htmx swaps the content
    await expect(ownerPage.locator(SEL.mondaySync.connectStatus)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.mondaySync.connectStatus)).toContainText('Connected');

    // ──────────────────────────────────────────
    // Phase 5 — Select board
    // ──────────────────────────────────────────
    // Board checkboxes should be visible after connecting
    const firstBoardCheckbox = ownerPage.locator(SEL.mondaySync.boardCheckbox).first();
    await expect(firstBoardCheckbox).toBeVisible({ timeout: 10000 });
    await firstBoardCheckbox.check();
    await ownerPage.locator(SEL.mondaySync.saveBoardsBtn).click();

    // Wait for htmx swap to complete
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify connection persisted after re-render
    await expect(ownerPage.locator(SEL.mondaySync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 6 — Configure columns
    // ──────────────────────────────────────────
    // Find the "Configure Columns" link in the board mapping row
    const configureColumnsBtn = ownerPage.locator('.board-mapping-row a.btn').filter({ hasText: /Configure Columns/i }).first();
    await expect(configureColumnsBtn).toBeVisible({ timeout: 10000 });
    await configureColumnsBtn.click();

    // Wait for the column mapping form to load via htmx
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // The column mapping form should now be visible with <select> dropdowns
    const columnMappingForm = ownerPage.locator('form[hx-post*="save-column-mapping"]');
    await expect(columnMappingForm).toBeVisible({ timeout: 15000 });

    // The form has select dropdowns for each bpkm property — they may have defaults pre-selected
    // Simply save the current mapping (which may be auto-detected or defaults)
    const columnSelects = columnMappingForm.locator('select.config-select');
    const selectCount = await columnSelects.count();
    // If there are selects, try to pick the first non-empty option for each
    for (let i = 0; i < selectCount; i++) {
      const sel = columnSelects.nth(i);
      const options = sel.locator('option');
      const optionCount = await options.count();
      // Pick the first non-empty option (index 1, since index 0 is "— None —")
      if (optionCount > 1) {
        const firstOptionValue = await options.nth(1).getAttribute('value');
        if (firstOptionValue) {
          await sel.selectOption(firstOptionValue);
        }
      }
    }

    // Click save column mapping
    await ownerPage.locator(SEL.mondaySync.saveColumnMappingBtn).click();

    // Wait for htmx swap back to connect_status
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify we're back to the connected state
    await expect(ownerPage.locator(SEL.mondaySync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 7 — Configure labels
    // ──────────────────────────────────────────
    // After column mapping is configured, the "Configure Labels" button should appear
    const configureLabelsBtn = ownerPage.locator('.board-mapping-row a.btn').filter({ hasText: /Configure Labels/i }).first();
    await expect(configureLabelsBtn).toBeVisible({ timeout: 10000 });
    await configureLabelsBtn.click();

    // Wait for the label mapping form to load via htmx
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // The label mapping form should now be visible
    const labelMappingForm = ownerPage.locator('form[hx-post*="save-label-mapping"]');
    await expect(labelMappingForm).toBeVisible({ timeout: 15000 });

    // The form has select dropdowns mapping Monday.com labels to bpkm values
    // Leave the defaults (auto-matched) and save
    const labelSelects = labelMappingForm.locator('select.config-select');
    const labelSelectCount = await labelSelects.count();
    // If there are selects, try to pick the first option for each
    for (let i = 0; i < labelSelectCount; i++) {
      const sel = labelSelects.nth(i);
      const options = sel.locator('option');
      const optionCount = await options.count();
      if (optionCount > 1) {
        const firstOptionValue = await options.nth(1).getAttribute('value');
        if (firstOptionValue) {
          await sel.selectOption(firstOptionValue);
        }
      }
    }

    // Click save label mapping
    await ownerPage.locator(SEL.mondaySync.saveLabelMappingBtn).click();

    // Wait for htmx swap back to connect_status
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify we're back to the connected state
    await expect(ownerPage.locator(SEL.mondaySync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 8 — Configure sync direction
    // ──────────────────────────────────────────
    const bidirectionalRadio = ownerPage.locator(SEL.mondaySync.syncDirectionBidirectional);
    await expect(bidirectionalRadio).toBeVisible({ timeout: 10000 });
    await bidirectionalRadio.check();
    await ownerPage.locator(SEL.mondaySync.saveConfigBtn).click();

    // Wait for htmx swap
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify still connected after config save
    await expect(ownerPage.locator(SEL.mondaySync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 9 — Sync Now
    // ──────────────────────────────────────────
    const syncNowBtn = ownerPage.locator(SEL.mondaySync.syncNowBtn);
    await expect(syncNowBtn).toBeVisible({ timeout: 10000 });
    await syncNowBtn.click();

    // Wait for sync to complete — involves mock API calls and object creation
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify sync stats section appeared with results
    await expect(ownerPage.locator(SEL.mondaySync.syncStats)).toBeVisible({ timeout: 60000 });

    // Check for "Last Pull" section — should show "success" status
    const pullSection = ownerPage.locator('.stat-group').filter({ hasText: 'Last Pull' });
    await expect(pullSection).toBeVisible({ timeout: 10000 });
    const pullStatus = pullSection.locator('.stat-row').filter({ hasText: 'Status' }).locator('.stat-value');
    await expect(pullStatus).toContainText(/success|ok/);

    // Check for created count — mock API returns items that become Tasks
    const createdRow = pullSection.locator('.stat-row').filter({ hasText: 'Created' });
    await expect(createdRow).toBeVisible();
    const createdValue = createdRow.locator('.stat-value');
    const createdText = await createdValue.textContent();
    const createdNum = parseInt(createdText?.trim() || '0', 10);
    expect(createdNum).toBeGreaterThanOrEqual(2);

    // ──────────────────────────────────────────
    // Phase 10 — Verify tasks via SPARQL (count)
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
    // Mock Monday.com API returns items that should create ≥ 2 Task objects
    expect(taskCount).toBeGreaterThanOrEqual(2);

    // ──────────────────────────────────────────
    // Phase 11 — Admin detail page verification
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const runningCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Monday\.com Sync/i });
    await expect(runningCard).toBeVisible({ timeout: 15000 });
    await expect(runningCard.locator('.status-badge')).toContainText(/running/i);

    // ──────────────────────────────────────────
    // Phase 12 — Cleanup: uninstall monday-sync
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/monday-sync`);
    await ownerPage.waitForLoadState('domcontentloaded');

    await expect(ownerPage.locator('h1')).toContainText('Monday.com Sync', { timeout: 15000 });

    const uninstallForm = ownerPage.locator('form[action="/admin/apps/monday-sync/uninstall"]');
    await expect(uninstallForm).toBeVisible();
    await uninstallForm.locator('button[type="submit"]').click();

    // Wait for redirect to apps list
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify monday-sync no longer appears
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Monday\.com Sync/i });
    await expect(removedCard).toHaveCount(0, { timeout: 10000 });
  });
});
