/**
 * App Platform E2E Tests
 *
 * Proves the full app platform vertical:
 *   install → admin detail → workspace page → right pane → command palette API
 *   → stop/restart lifecycle → uninstall
 *
 * Uses a single test() to maintain sequential execution and avoid
 * rate-limit issues (matching admin-model-lifecycle.spec.ts pattern).
 *
 * Runs against the Docker test stack on port 3901.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('App Platform', () => {
  test('full lifecycle: install → workspace → admin → uninstall', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on uninstall button)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations (install includes venv creation)
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Cleanup: If test-app is already installed from a prior run, remove it
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Test Application/i });
    if (await existingCard.count() > 0) {
      // Uninstall via form submission on the detail page
      await ownerPage.goto(`${BASE_URL}/admin/apps/test-app`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/test-app/uninstall"] button[type="submit"]');
      if (await uninstallBtn.count() > 0) {
        await uninstallBtn.click();
        await ownerPage.waitForLoadState('domcontentloaded');
        await ownerPage.waitForTimeout(2000);
      }
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // ──────────────────────────────────────────
    // Phase 1: Install test app via admin form
    // ──────────────────────────────────────────
    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/test-app');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();

    // After form submit, server redirects 303 → /admin/apps with ?success= message
    await ownerPage.waitForLoadState('domcontentloaded');

    // App install includes venv creation + SDK install + subprocess start + health check
    // Poll the admin list page until the app appears with "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Test Application/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    // Final assertion — the app card exists and shows running
    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Test Application/i });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.status-badge')).toContainText(/running/i);

    // ──────────────────────────────────────────
    // Phase 2: Verify admin detail page
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/test-app`);
    await ownerPage.waitForLoadState('domcontentloaded');

    // App name in title
    await expect(ownerPage.locator('h1')).toContainText('Test Application', { timeout: 15000 });

    // Status badge shows running
    await expect(ownerPage.locator('.model-title-row .status-badge')).toContainText(/running/i);

    // PID is visible in the stats bar — should be a number, not "—"
    const pidStat = ownerPage.locator('.stat-box').filter({ hasText: 'PID' });
    await expect(pidStat).toBeVisible();
    await expect(pidStat.locator('.stat-value')).not.toContainText('—');

    // Permissions section visible with object.create
    const permissionsSection = ownerPage.locator('.detail-section').filter({ hasText: 'Permissions' });
    await expect(permissionsSection).toBeVisible();
    await expect(permissionsSection).toContainText('object.create');

    // Task History section visible with heartbeat
    const taskSection = ownerPage.locator('.detail-section').filter({ hasText: 'Task History' });
    await expect(taskSection).toBeVisible();
    await expect(taskSection).toContainText('heartbeat');

    // ──────────────────────────────────────────
    // Phase 3: Verify app page in workspace
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage, 20000);
    await waitForIdle(ownerPage);

    // Find the APPS section in the sidebar
    const appsSidebar = ownerPage.locator('#section-apps');
    await expect(appsSidebar).toBeVisible({ timeout: 10000 });

    // Wait for the htmx-loaded content to appear (loads from /browser/apps/explorer)
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Explorer sections start collapsed — expand the APPS section if needed
    const isExpanded = await appsSidebar.evaluate(el => el.classList.contains('expanded'));
    if (!isExpanded) {
      await appsSidebar.locator('.explorer-section-header').click();
      await ownerPage.waitForTimeout(1000);
      await waitForIdle(ownerPage);
    }

    // The tree-leaf for "Test App" should appear inside the APPS section
    const testAppLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'Test App' });
    await expect(testAppLeaf).toBeVisible({ timeout: 15000 });

    // Click to open the app page tab
    await testAppLeaf.click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify the app page fragment loaded — #test-app-main should be visible
    await expect(ownerPage.locator(SEL.apps.workspaceAppMain)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.apps.workspaceAppMain)).toContainText('Test Application');

    // ──────────────────────────────────────────
    // Phase 4: Verify right pane API endpoint
    // ──────────────────────────────────────────
    // The right pane sections endpoint returns HTML fragments from running apps
    // that target "*" (all types). Verify via API for reliability.
    const rightPaneResp = await ownerRequest.get(
      `${BASE_URL}/browser/apps/right-pane-sections?iri=urn:sempkm:test:example`
    );
    expect(rightPaneResp.status()).toBe(200);
    const rightPaneHtml = await rightPaneResp.text();
    expect(rightPaneHtml).toContain('test-app-right-pane');
    expect(rightPaneHtml).toContain('Test Info');

    // ──────────────────────────────────────────
    // Phase 5: Verify command palette API
    // ──────────────────────────────────────────
    const commandsResp = await ownerRequest.get(`${BASE_URL}/api/apps/commands`);
    expect(commandsResp.status()).toBe(200);

    const commands = await commandsResp.json();
    expect(Array.isArray(commands)).toBe(true);

    const testCommand = commands.find((c: any) => c.id === 'test-command');
    expect(testCommand).toBeDefined();
    expect(testCommand.label).toBe('Test App Command');
    expect(testCommand.appId).toBe('test-app');

    // ──────────────────────────────────────────
    // Phase 6: Admin actions — stop and restart
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/test-app`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('.model-title-row .status-badge')).toContainText(/running/i, { timeout: 15000 });

    // Stop the app
    const stopForm = ownerPage.locator('form[action="/admin/apps/test-app/stop"]');
    await expect(stopForm).toBeVisible();
    await stopForm.locator('button[type="submit"]').click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Verify status shows stopped
    await expect(ownerPage.locator('.model-title-row .status-badge')).toContainText(/stopped/i, { timeout: 15000 });

    // Start the app back up
    const startForm = ownerPage.locator('form[action="/admin/apps/test-app/start"]');
    await expect(startForm).toBeVisible();
    await startForm.locator('button[type="submit"]').click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Wait for the app to come back to running (health check takes time)
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps/test-app`);
      await ownerPage.waitForLoadState('domcontentloaded');
      await expect(ownerPage.locator('.model-title-row .status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 60_000, intervals: [3000, 5000, 5000, 5000] });

    // ──────────────────────────────────────────
    // Phase 7: Uninstall and verify removal
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/test-app`);
    await ownerPage.waitForLoadState('domcontentloaded');

    // Click the uninstall button — has hx-confirm so dialog handler will accept
    const uninstallForm = ownerPage.locator('form[action="/admin/apps/test-app/uninstall"]');
    await expect(uninstallForm).toBeVisible();
    await uninstallForm.locator('button[type="submit"]').click();

    // After confirm dialog accepted and form submitted, server redirects 303 → /admin/apps
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    // Ensure we're on the list page
    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify the test app no longer appears in the list
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Test Application/i });
    await expect(removedCard).toHaveCount(0, { timeout: 10000 });

    // Verify workspace APPS section no longer shows the app
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage, 20000);
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    const appsSection = ownerPage.locator('#section-apps');
    if (await appsSection.count() > 0) {
      // Expand if collapsed
      const appsExpanded = await appsSection.evaluate(el => el.classList.contains('expanded'));
      if (!appsExpanded) {
        await appsSection.locator('.explorer-section-header').click();
        await ownerPage.waitForTimeout(1000);
        await waitForIdle(ownerPage);
      }
      const testLeaf = appsSection.locator('.tree-leaf', { hasText: 'Test App' });
      await expect(testLeaf).toHaveCount(0, { timeout: 10000 });
    }

    // Command palette API should no longer return test-command
    const postUninstallCmds = await ownerRequest.get(`${BASE_URL}/api/apps/commands`);
    expect(postUninstallCmds.status()).toBe(200);
    const postCmds = await postUninstallCmds.json();
    const removedCmd = postCmds.find((c: any) => c.id === 'test-command');
    expect(removedCmd).toBeUndefined();
  });
});
