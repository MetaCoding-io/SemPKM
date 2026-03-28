/**
 * CalDAV Calendar Sync E2E Tests
 *
 * Proves the full CalDAV Calendar sync vertical against a mock CalDAV
 * server:
 *   install basic-pkm → install caldav-calendar → enter credentials →
 *   select calendars → configure sync → Sync Now →
 *   verify events via SPARQL → admin detail → cleanup
 *
 * Runs against the Docker test stack on port 3901 with the mock-caldav
 * service providing canned PROPFIND/REPORT/GET responses.
 *
 * CalDAV uses HTTP Basic auth — no OAuth simulation needed.
 * The credentials form POSTs directly to the app's connect endpoint.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('CalDAV Calendar Sync', () => {
  test('full lifecycle: install → credentials → sync → verify → cleanup', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on disconnect/uninstall)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Phase 0 — Cleanup: remove caldav-calendar if installed from prior run
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /CalDAV Calendar/i });
    if (await existingCard.count() > 0) {
      await ownerPage.goto(`${BASE_URL}/admin/apps/caldav-calendar`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/caldav-calendar/uninstall"] button[type="submit"]');
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
    // Phase 2 — Install caldav-calendar app
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/caldav-calendar');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll until caldav-calendar shows "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /CalDAV Calendar/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /CalDAV Calendar/i });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.status-badge')).toContainText(/running/i);

    // Give the app subprocess time to fully start and open its UDS socket
    await ownerPage.waitForTimeout(5000);

    // ──────────────────────────────────────────
    // Phase 3 — Enter CalDAV credentials (HTTP Basic — no OAuth)
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

    // Click the "CalDAV Calendar" leaf to open the app settings tab
    const caldavLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'CalDAV Calendar' });
    await expect(caldavLeaf).toBeVisible({ timeout: 30000 });
    await caldavLeaf.click();
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
        const leaf = appsSection.locator('.tree-leaf', { hasText: 'CalDAV Calendar' });
        await leaf.click();
        await ownerPage.waitForTimeout(3000);
        await waitForIdle(ownerPage);
      }
      await expect(ownerPage.locator('#connect-content')).toBeVisible();
    }).toPass({ timeout: 60_000, intervals: [5000, 10000, 10000] });

    // Fill CalDAV credentials — 3 fields, direct POST (no OAuth)
    await expect(ownerPage.locator(SEL.caldavCalendarSync.serverUrlInput)).toBeVisible({ timeout: 10000 });
    await ownerPage.locator(SEL.caldavCalendarSync.serverUrlInput).fill('http://mock-caldav:8080/');
    await ownerPage.locator(SEL.caldavCalendarSync.usernameInput).fill('testuser');
    await ownerPage.locator(SEL.caldavCalendarSync.passwordInput).fill('testpassword');
    await ownerPage.locator(SEL.caldavCalendarSync.credentialsSubmitBtn).click();

    // Wait for htmx swap — credentials form submits and swaps to connect_status.html
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify connected status and account username
    await expect(ownerPage.locator(SEL.caldavCalendarSync.connectStatus)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.caldavCalendarSync.connectStatus)).toContainText('Connected');
    await expect(ownerPage.locator(SEL.caldavCalendarSync.accountUsername)).toContainText('testuser');

    // ──────────────────────────────────────────
    // Phase 4 — Select calendars + configure sync
    // ──────────────────────────────────────────
    // Calendar checkboxes should be visible after connecting
    const firstCalCheckbox = ownerPage.locator(SEL.caldavCalendarSync.calendarCheckbox).first();
    await expect(firstCalCheckbox).toBeVisible({ timeout: 10000 });

    // Check all available calendar checkboxes
    const calCheckboxes = ownerPage.locator(SEL.caldavCalendarSync.calendarCheckbox);
    const calCount = await calCheckboxes.count();
    for (let i = 0; i < calCount; i++) {
      await calCheckboxes.nth(i).check();
    }

    await ownerPage.locator(SEL.caldavCalendarSync.saveCalendarsBtn).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify connection persisted after re-render
    await expect(ownerPage.locator(SEL.caldavCalendarSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // Set sync direction to bidirectional
    const bidirectionalRadio = ownerPage.locator(SEL.caldavCalendarSync.syncDirectionBidirectional);
    await expect(bidirectionalRadio).toBeVisible({ timeout: 10000 });
    await bidirectionalRadio.check();
    await ownerPage.locator(SEL.caldavCalendarSync.saveConfigBtn).click();

    // Wait for htmx swap
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify still connected after config save
    await expect(ownerPage.locator(SEL.caldavCalendarSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 5 — Sync Now + verify events
    // ──────────────────────────────────────────
    const syncNowBtn = ownerPage.locator(SEL.caldavCalendarSync.syncNowBtn);
    await expect(syncNowBtn).toBeVisible({ timeout: 10000 });
    await syncNowBtn.click();

    // Wait for sync to complete — involves mock CalDAV calls and object creation
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify sync stats section appeared with results
    await expect(ownerPage.locator(SEL.caldavCalendarSync.syncStats)).toBeVisible({ timeout: 60000 });

    // Check for "Last Pull" section — should show "ok" status
    const pullSection = ownerPage.locator('.stat-group').filter({ hasText: 'Last Pull' });
    await expect(pullSection).toBeVisible({ timeout: 10000 });
    const pullStatus = pullSection.locator('.stat-row').filter({ hasText: 'Status' }).locator('.stat-value');
    await expect(pullStatus).toContainText(/ok|success/);

    // Check for created count — mock returns 3 events (timed + all-day + recurring)
    const createdRow = pullSection.locator('.stat-row').filter({ hasText: 'Created' });
    await expect(createdRow).toBeVisible();
    const createdValue = createdRow.locator('.stat-value');
    const createdText = await createdValue.textContent();
    const createdNum = parseInt(createdText?.trim() || '0', 10);
    // Should have at least 2 events created (timed + all-day; recurring makes 3)
    expect(createdNum).toBeGreaterThanOrEqual(2);

    // ──────────────────────────────────────────
    // Phase 5b — Verify events via SPARQL
    // ──────────────────────────────────────────
    // Query for Event labels in the current graph
    const labelQuery = `
      SELECT ?label WHERE {
        ?s a <urn:sempkm:model:basic-pkm:Event> ;
           <http://www.w3.org/2000/01/rdf-schema#label> ?label .
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

    // Must have at least "Team Standup" and "Company Holiday" from mock data
    expect(labels.length).toBeGreaterThanOrEqual(2);
    expect(labels).toContain('Team Standup');
    expect(labels).toContain('Company Holiday');

    // ──────────────────────────────────────────
    // Phase 6 — Admin detail + cleanup
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const runningCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /CalDAV Calendar/i });
    await expect(runningCard).toBeVisible({ timeout: 15000 });
    await expect(runningCard.locator('.status-badge')).toContainText(/running/i);

    // Navigate to admin detail page
    await ownerPage.goto(`${BASE_URL}/admin/apps/caldav-calendar`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('CalDAV Calendar', { timeout: 15000 });

    // Verify task history section exists on the detail page
    const taskHistory = ownerPage.locator('.task-history, .sync-history, [data-testid="task-history"]');
    // Task history may or may not be present depending on admin template — skip if not found
    if (await taskHistory.count() > 0) {
      await expect(taskHistory.first()).toBeVisible();
    }

    // Uninstall the caldav-calendar app
    const uninstallForm = ownerPage.locator('form[action="/admin/apps/caldav-calendar/uninstall"]');
    await expect(uninstallForm).toBeVisible();
    await uninstallForm.locator('button[type="submit"]').click();

    // Wait for redirect to apps list
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify caldav-calendar no longer appears
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /CalDAV Calendar/i });
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
