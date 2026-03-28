/**
 * Google Calendar Sync E2E Tests
 *
 * Proves the full Google Calendar sync vertical against a mock Calendar API:
 *   install basic-pkm → install google-calendar → enter credentials →
 *   simulate OAuth → select calendars → configure sync → Sync Now →
 *   verify events via SPARQL → admin detail → cleanup
 *
 * Runs against the Docker test stack on port 3901 with the mock-google-calendar
 * service providing canned REST responses.
 *
 * OAuth simulation: The GOOGLE_AUTHORIZE_URL is hardcoded to accounts.google.com
 * (no env var override), so we cannot redirect the browser to the mock for the
 * authorize step. Instead we:
 *   1. POST to the app's connect/google endpoint via ownerRequest (returns 303)
 *   2. Extract the state param from the redirect Location header
 *   3. Navigate the browser directly to the OAuth callback URL with mock code + state
 *   4. The API container exchanges the code via the mock GOOGLE_TOKEN_URL
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('Google Calendar Sync', () => {
  test('full lifecycle: install → OAuth → sync → verify → cleanup', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on disconnect/uninstall)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // Generous timeout for Docker operations
    test.setTimeout(240_000);

    // ──────────────────────────────────────────
    // Phase 0 — Cleanup: remove google-calendar if installed from prior run
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });

    const existingCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Google Calendar/i });
    if (await existingCard.count() > 0) {
      await ownerPage.goto(`${BASE_URL}/admin/apps/google-calendar`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const uninstallBtn = ownerPage.locator('form[action="/admin/apps/google-calendar/uninstall"] button[type="submit"]');
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
    // Phase 2 — Install google-calendar app
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10000 });
    await installInput.fill('/app/apps/google-calendar');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll until google-calendar shows "Running" status
    await expect(async () => {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
      const card = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Google Calendar/i });
      await expect(card).toBeVisible();
      await expect(card.locator('.status-badge')).toContainText(/running/i);
    }).toPass({ timeout: 120_000, intervals: [5000, 5000, 10000, 10000, 10000] });

    const appCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Google Calendar/i });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.status-badge')).toContainText(/running/i);

    // Give the app subprocess time to fully start and open its UDS socket
    await ownerPage.waitForTimeout(5000);

    // ──────────────────────────────────────────
    // Phase 3 — Enter credentials + simulate OAuth
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

    // Click the "Google Calendar" leaf to open the app settings tab
    const gcalLeaf = appsSidebar.locator('.tree-leaf', { hasText: 'Google Calendar' });
    await expect(gcalLeaf).toBeVisible({ timeout: 30000 });
    await gcalLeaf.click();
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
        const leaf = appsSection.locator('.tree-leaf', { hasText: 'Google Calendar' });
        await leaf.click();
        await ownerPage.waitForTimeout(3000);
        await waitForIdle(ownerPage);
      }
      await expect(ownerPage.locator('#connect-content')).toBeVisible();
    }).toPass({ timeout: 60_000, intervals: [5000, 10000, 10000] });

    // Fill and submit the credentials form
    await expect(ownerPage.locator(SEL.googleCalendarSync.clientIdInput)).toBeVisible({ timeout: 10000 });
    await ownerPage.locator(SEL.googleCalendarSync.clientIdInput).fill('mock-client-id');
    await ownerPage.locator(SEL.googleCalendarSync.clientSecretInput).fill('mock-client-secret');
    await ownerPage.locator(SEL.googleCalendarSync.credentialsSubmitBtn).click();

    // Wait for credentials save — htmx swaps the content
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify "Connect with Google" button is now enabled
    await expect(ownerPage.locator(SEL.googleCalendarSync.connectGoogleBtn)).toBeEnabled({ timeout: 10000 });

    // ── Simulate OAuth flow ──
    // POST to the connect/google endpoint via ownerRequest (API-level, no browser redirect).
    // The endpoint returns a 303 redirect to Google's authorize URL.
    // We extract the state param and navigate the browser to the callback URL directly.
    const oauthResp = await ownerRequest.post(
      `${BASE_URL}/app/google-calendar/_fragments/connect/google`,
      {
        maxRedirects: 0,  // Don't follow the 303
      },
    );
    // Playwright's APIRequestContext follows redirects by default.
    // With maxRedirects: 0, we get the redirect response.
    // However, Playwright may still follow — check both cases.
    const locationHeader = oauthResp.headers()['location'] || '';
    let oauthState: string;

    if (locationHeader) {
      // Got the redirect — extract state from the Location URL
      const redirectUrl = new URL(locationHeader);
      oauthState = redirectUrl.searchParams.get('state') || '';
    } else {
      // Playwright may have followed the redirect — the response URL
      // won't help since Google isn't reachable. Fall back to reading
      // the oauth_state directly from the app's state via the API.
      // The app stores it in state.set("oauth_state", ...) before redirecting.
      // We can fetch the connect fragment which shows the state.
      // Actually, let's try a different approach — read the redirected URL.
      const respUrl = oauthResp.url();
      if (respUrl.includes('state=')) {
        const parsedUrl = new URL(respUrl);
        oauthState = parsedUrl.searchParams.get('state') || '';
      } else {
        // Last resort: the POST should have stored oauth_state in app state.
        // We don't have a direct API for that, so let's retry with fetch API.
        throw new Error(
          `OAuth redirect did not produce a Location header or state param. ` +
          `Status: ${oauthResp.status()}, URL: ${oauthResp.url()}`
        );
      }
    }

    expect(oauthState).toBeTruthy();

    // Navigate to the OAuth callback URL with the mock auth code + extracted state
    await ownerPage.goto(
      `${BASE_URL}/app/google-calendar/_fragments/oauth-callback?code=mock-auth-code&state=${oauthState}`
    );

    // Wait for the success page (shows "Connected") then auto-redirects to /browser/
    await expect(ownerPage.locator('h2.success, h2')).toContainText('Connected', { timeout: 15000 });

    // Wait for the auto-redirect (2 second JS timeout in _oauth_result_page)
    await ownerPage.waitForTimeout(3000);

    // Now navigate to the app page to verify connection status
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage, 20000);
    await waitForIdle(ownerPage);

    // Re-expand APPS section and open Google Calendar
    const appsSidebar2 = ownerPage.locator('#section-apps');
    await expect(appsSidebar2).toBeVisible({ timeout: 10000 });
    await ownerPage.waitForTimeout(2000);
    const isExpanded2 = await appsSidebar2.evaluate(el => el.classList.contains('expanded'));
    if (!isExpanded2) {
      await appsSidebar2.locator('.explorer-section-header').click();
      await ownerPage.waitForTimeout(1000);
    }
    await waitForIdle(ownerPage);

    const gcalLeaf2 = appsSidebar2.locator('.tree-leaf', { hasText: 'Google Calendar' });
    await expect(gcalLeaf2).toBeVisible({ timeout: 30000 });
    await gcalLeaf2.click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify connected status and account email
    await expect(ownerPage.locator(SEL.googleCalendarSync.connectStatus)).toBeVisible({ timeout: 30000 });
    await expect(ownerPage.locator(SEL.googleCalendarSync.connectStatus)).toContainText('Connected');
    await expect(ownerPage.locator(SEL.googleCalendarSync.accountEmail)).toContainText('test@example.com');

    // ──────────────────────────────────────────
    // Phase 4 — Select calendars + configure sync
    // ──────────────────────────────────────────
    // Calendar checkboxes should be visible after connecting
    const firstCalCheckbox = ownerPage.locator(SEL.googleCalendarSync.calendarCheckbox).first();
    await expect(firstCalCheckbox).toBeVisible({ timeout: 10000 });

    // Check all available calendar checkboxes
    const calCheckboxes = ownerPage.locator(SEL.googleCalendarSync.calendarCheckbox);
    const calCount = await calCheckboxes.count();
    for (let i = 0; i < calCount; i++) {
      await calCheckboxes.nth(i).check();
    }

    await ownerPage.locator(SEL.googleCalendarSync.saveCalendarsBtn).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify connection persisted after re-render
    await expect(ownerPage.locator(SEL.googleCalendarSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // Set sync direction to bidirectional
    const bidirectionalRadio = ownerPage.locator(SEL.googleCalendarSync.syncDirectionBidirectional);
    await expect(bidirectionalRadio).toBeVisible({ timeout: 10000 });
    await bidirectionalRadio.check();
    await ownerPage.locator(SEL.googleCalendarSync.saveConfigBtn).click();

    // Wait for htmx swap
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify still connected after config save
    await expect(ownerPage.locator(SEL.googleCalendarSync.connectStatus)).toContainText('Connected', { timeout: 10000 });

    // ──────────────────────────────────────────
    // Phase 5 — Sync Now + verify events
    // ──────────────────────────────────────────
    const syncNowBtn = ownerPage.locator(SEL.googleCalendarSync.syncNowBtn);
    await expect(syncNowBtn).toBeVisible({ timeout: 10000 });
    await syncNowBtn.click();

    // Wait for sync to complete — involves mock API calls and object creation
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Verify sync stats section appeared with results
    await expect(ownerPage.locator(SEL.googleCalendarSync.syncStats)).toBeVisible({ timeout: 60000 });

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
    // Query for Event labels
    const labelQuery = `
      SELECT ?label WHERE {
        ?s a <urn:sempkm:model:basic-pkm:Event> ;
           <http://www.w3.org/2000/01/rdf-schema#label> ?label .
      }
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

    // Must have at least "Team Standup" and "Company Holiday"
    expect(labels.length).toBeGreaterThanOrEqual(2);
    expect(labels).toContain('Team Standup');
    expect(labels).toContain('Company Holiday');

    // Query for RRULE property on recurring event
    const rruleQuery = `
      SELECT ?rule WHERE {
        ?s <urn:sempkm:model:basic-pkm:recurrenceRule> ?rule .
      }
    `;

    const rruleResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: `query=${encodeURIComponent(rruleQuery)}`,
    });
    expect(rruleResp.status()).toBe(200);
    const rruleData = await rruleResp.json();
    const rruleBindings = rruleData?.results?.bindings ?? [];

    // Should find at least one RRULE (from the "Weekly Review" recurring event)
    expect(rruleBindings.length).toBeGreaterThanOrEqual(1);
    const rruleValue = rruleBindings[0]?.rule?.value ?? '';
    expect(rruleValue).toContain('RRULE:FREQ=WEEKLY');

    // ──────────────────────────────────────────
    // Phase 6 — Admin detail + cleanup
    // ──────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');

    const runningCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Google Calendar/i });
    await expect(runningCard).toBeVisible({ timeout: 15000 });
    await expect(runningCard.locator('.status-badge')).toContainText(/running/i);

    // Navigate to admin detail page
    await ownerPage.goto(`${BASE_URL}/admin/apps/google-calendar`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Google Calendar', { timeout: 15000 });

    // Uninstall the google-calendar app
    const uninstallForm = ownerPage.locator('form[action="/admin/apps/google-calendar/uninstall"]');
    await expect(uninstallForm).toBeVisible();
    await uninstallForm.locator('button[type="submit"]').click();

    // Wait for redirect to apps list
    await ownerPage.waitForLoadState('domcontentloaded');
    await ownerPage.waitForTimeout(2000);

    if (!ownerPage.url().includes('/admin/apps')) {
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }

    // Verify google-calendar no longer appears
    await expect(ownerPage.locator('h1')).toContainText('Applications', { timeout: 15000 });
    const removedCard = ownerPage.locator(SEL.apps.appCard).filter({ hasText: /Google Calendar/i });
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
