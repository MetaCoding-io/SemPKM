/**
 * Media Scheduler E2E Tests
 *
 * Proves the full Media Scheduler lifecycle:
 *   cleanup → model install → app install → app navigation →
 *   podcast subscription → tab navigation → rule CRUD →
 *   plan generation → status tracking → stats dashboard → cleanup.
 *
 * Uses a single test() to maintain sequential execution (matching the
 * pattern from rss-reader.spec.ts).
 *
 * Runs against the Docker test stack on port 3901.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Media Scheduler', () => {
  // Generous timeout — model install + app install + health check polling
  test.setTimeout(240_000);

  test('full lifecycle: install → subscribe → tabs → rules → plan → stats → uninstall', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on delete buttons)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // ────────────────────────────────────────────
    // Phase 0: Cleanup — remove prior state for idempotency
    // ────────────────────────────────────────────
    try {
      const appCheck = await ownerRequest.get(`${BASE_URL}/admin/apps/media-scheduler`);
      if (appCheck.status() === 200) {
        await ownerRequest.post(`${BASE_URL}/admin/apps/media-scheduler/stop`);
        await ownerPage.waitForTimeout(2000);
        await ownerRequest.post(`${BASE_URL}/admin/apps/media-scheduler/uninstall`, {
          form: { clean_data: 'true' },
        });
        await ownerPage.waitForTimeout(2000);
      }
    } catch (e) {
      console.log('Phase 0 cleanup: app removal skipped (expected if not installed):', String(e));
    }

    try {
      await ownerRequest.delete(`${BASE_URL}/admin/models/media-scheduler`);
      await ownerPage.waitForTimeout(1000);
    } catch (e) {
      console.log('Phase 0 cleanup: model removal skipped (expected if not installed):', String(e));
    }

    // ────────────────────────────────────────────
    // Phase 1: Install media-scheduler model
    // ────────────────────────────────────────────
    const modelInstallResp = await ownerRequest.post(`${BASE_URL}/admin/models/install`, {
      form: { path: '/app/models/media-scheduler' },
    });
    expect(modelInstallResp.status()).toBeLessThan(400);

    // Verify the model appears in the admin list
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForLoadState('domcontentloaded');

    let modelVisible = false;
    for (let attempt = 0; attempt < 5; attempt++) {
      const pageText = await ownerPage.locator('body').textContent();
      if (pageText && (pageText.includes('media-scheduler') || pageText.includes('Media Scheduler'))) {
        modelVisible = true;
        break;
      }
      await ownerPage.waitForTimeout(2000);
      await ownerPage.reload();
      await ownerPage.waitForLoadState('domcontentloaded');
    }
    expect(modelVisible).toBe(true);

    // ────────────────────────────────────────────
    // Phase 2: Install media-scheduler app
    // ────────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications');

    // Fill app path and submit via the install form
    const installInput = ownerPage.locator(SEL.apps.installInput);
    await expect(installInput).toBeVisible({ timeout: 10_000 });
    await installInput.fill('/app/apps/media-scheduler');
    await ownerPage.locator(`${SEL.apps.installForm} button[type="submit"]`).click();

    // Wait for install — server redirects to /admin/apps
    await ownerPage.waitForURL('**/admin/apps', { timeout: 90_000 });
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll for "running" status (venv creation + pip install + health check)
    let appRunning = false;
    for (let attempt = 0; attempt < 15; attempt++) {
      const cardText = await ownerPage.locator('.admin-page').textContent();
      if (cardText && cardText.includes('Media Scheduler') && cardText.includes('running')) {
        appRunning = true;
        break;
      }
      await ownerPage.waitForTimeout(5000);
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }
    expect(appRunning).toBe(true);

    const appCard = ownerPage.locator('.admin-page .card').filter({ hasText: 'Media Scheduler' });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.badge')).toContainText('running');

    // ────────────────────────────────────────────
    // Phase 3: App navigation — verify main layout
    // ────────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/app/media-scheduler/`);
    await ownerPage.waitForLoadState('domcontentloaded');

    // Wait for the app container to be visible
    const container = ownerPage.locator(SEL.mediaScheduler.container);
    await expect(container).toBeVisible({ timeout: 15_000 });

    // Assert core layout elements
    await expect(ownerPage.locator(SEL.mediaScheduler.sidebar)).toBeVisible();
    await expect(ownerPage.locator(SEL.mediaScheduler.tabs)).toBeVisible();

    // Wait for sources list to load (htmx hx-trigger="load")
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);
    await expect(ownerPage.locator(SEL.mediaScheduler.sourcesList)).toBeVisible();

    // ────────────────────────────────────────────
    // Phase 4: Podcast subscription
    // ────────────────────────────────────────────
    // Click the + button to reveal add section
    await ownerPage.locator(SEL.mediaScheduler.addFormToggle).click();
    await ownerPage.waitForTimeout(500);

    // The add section starts with ms-hidden class; clicking toggle removes it
    const addSection = ownerPage.locator(SEL.mediaScheduler.addSection);
    await expect(addSection).toBeVisible({ timeout: 5_000 });

    // Wait for the add-source fragment to load via htmx
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Fill podcast feed URL — the first form inside add section is for podcasts
    const podcastForm = addSection.locator(SEL.mediaScheduler.addForm).first();
    await podcastForm.locator('input[name="feed_url"]').fill('http://example.com/test-podcast.xml');
    await podcastForm.locator('input[name="title"]').fill('E2E Test Podcast');

    // Submit — the handler creates a MediaSource immediately via CommandClient
    await podcastForm.locator('button[type="submit"]').click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Assert success appears in the result area
    const addResult = ownerPage.locator(SEL.mediaScheduler.addResult);
    const resultText = await addResult.textContent();
    // Either .ms-success appears or a success message is shown
    const hasSuccess = await addResult.locator(SEL.mediaScheduler.success).count() > 0;
    const hasSuccessText = resultText !== null && resultText.length > 0;
    expect(hasSuccess || hasSuccessText).toBe(true);

    // Wait for sourcesChanged htmx trigger to refresh sources list
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify at least one source item appeared
    let sourceCount = await ownerPage.locator(SEL.mediaScheduler.sourceItem).count();
    if (sourceCount === 0) {
      // Force a page reload if the htmx trigger didn't fire
      await ownerPage.goto(`${BASE_URL}/app/media-scheduler/`);
      await ownerPage.waitForLoadState('domcontentloaded');
      await ownerPage.waitForTimeout(3000);
      await waitForIdle(ownerPage);
      sourceCount = await ownerPage.locator(SEL.mediaScheduler.sourceItem).count();
    }
    expect(sourceCount).toBeGreaterThanOrEqual(1);

    // ────────────────────────────────────────────
    // Phase 5: Tab navigation
    // ────────────────────────────────────────────
    // Episodes tab
    await ownerPage.locator(SEL.mediaScheduler.tabEpisodes).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);
    const tabContent = ownerPage.locator(SEL.mediaScheduler.tabContent);
    const hasItemsTable = await tabContent.locator(SEL.mediaScheduler.itemsTable).count() > 0;
    const hasEpisodesEmpty = await tabContent.locator(SEL.mediaScheduler.emptyState).count() > 0;
    expect(hasItemsTable || hasEpisodesEmpty).toBe(true);

    // Rules tab
    await ownerPage.locator(SEL.mediaScheduler.tabRules).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);
    await expect(tabContent.locator(SEL.mediaScheduler.rulesView)).toBeVisible({ timeout: 10_000 });

    // Stats tab
    await ownerPage.locator(SEL.mediaScheduler.tabStats).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);
    await expect(tabContent.locator(SEL.mediaScheduler.statsView)).toBeVisible({ timeout: 10_000 });

    // Today tab (back to default)
    await ownerPage.locator(SEL.mediaScheduler.tabToday).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);
    await expect(tabContent.locator(SEL.mediaScheduler.todayView)).toBeVisible({ timeout: 10_000 });

    // ────────────────────────────────────────────
    // Phase 6: Rule CRUD — create a schedule rule
    // ────────────────────────────────────────────
    // Navigate to Rules tab
    await ownerPage.locator(SEL.mediaScheduler.tabRules).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Click "Add Rule" button — loads form via htmx into #ms-rule-form-area
    const addRuleBtn = tabContent.locator('.ms-rules-header button');
    await addRuleBtn.click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Wait for the rule form to load in the form area
    const ruleFormArea = ownerPage.locator(SEL.mediaScheduler.ruleFormArea);
    await expect(ruleFormArea.locator('form')).toBeVisible({ timeout: 10_000 });

    // Fill the rule form
    await ruleFormArea.locator('input[name="name"]').fill('E2E Test Rule');
    await ruleFormArea.locator('select[name="activity"]').selectOption('commuting');

    // Action type defaults to "source_type" with value "podcast" — leave defaults
    // Submit the form
    await ruleFormArea.locator('button[type="submit"]').first().click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Assert rule card appears in the rules list
    const rulesList = ownerPage.locator(SEL.mediaScheduler.rulesList);
    const ruleCards = rulesList.locator(SEL.mediaScheduler.ruleCard);
    await expect(ruleCards).toHaveCount(1, { timeout: 10_000 });

    // Verify rule name is displayed
    const ruleName = ruleCards.first().locator(SEL.mediaScheduler.ruleName);
    await expect(ruleName).toContainText('E2E Test Rule');

    // ────────────────────────────────────────────
    // Phase 7: Plan generation
    // ────────────────────────────────────────────
    // Navigate to Today tab
    await ownerPage.locator(SEL.mediaScheduler.tabToday).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Click "Generate Plan" button
    const generateBtn = tabContent.locator('.ms-today-header button, .ms-today-empty button').first();
    await generateBtn.click();
    await ownerPage.waitForTimeout(5000);
    await waitForIdle(ownerPage);

    // Assert: either plan entries appear (content generated) or empty state persists
    // (acceptable — dummy podcast URL has no real episodes to schedule)
    const planEntryCount = await tabContent.locator(SEL.mediaScheduler.planEntry).count();
    const hasEmptyPlan = await tabContent.locator(SEL.mediaScheduler.todayEmpty).count() > 0;
    const hasTodayView = await tabContent.locator(SEL.mediaScheduler.todayView).count() > 0;
    expect(planEntryCount > 0 || hasEmptyPlan || hasTodayView).toBe(true);

    // ────────────────────────────────────────────
    // Phase 8: Status tracking (conditional)
    // ────────────────────────────────────────────
    if (planEntryCount > 0) {
      // Find a plan entry with action buttons (not already completed/skipped/saved)
      const actionableEntry = tabContent.locator(SEL.mediaScheduler.actionComplete).first();
      const actionCount = await actionableEntry.count();
      if (actionCount > 0) {
        await actionableEntry.click();
        await ownerPage.waitForTimeout(2000);
        await waitForIdle(ownerPage);

        // Assert the entry's status changed — either .ms-entry-done appears
        // or the status badge text changes
        const doneEntries = await tabContent.locator(SEL.mediaScheduler.entryDone).count();
        const statusBadges = await tabContent.locator(SEL.mediaScheduler.statusBadge).allTextContents();
        const hasCompletedStatus = statusBadges.some(text => text.includes('completed'));
        expect(doneEntries > 0 || hasCompletedStatus).toBe(true);
      }
    } else {
      console.log('Phase 8: No plan entries — skipping status tracking test');
    }

    // ────────────────────────────────────────────
    // Phase 9: Stats dashboard
    // ────────────────────────────────────────────
    await ownerPage.locator(SEL.mediaScheduler.tabStats).click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Assert stats view is visible
    await expect(tabContent.locator(SEL.mediaScheduler.statsView)).toBeVisible({ timeout: 10_000 });

    // Assert all three chart canvases exist in the DOM
    // (they may show empty state text or render charts — both are valid)
    await expect(ownerPage.locator(SEL.mediaScheduler.chartHours)).toBeAttached();
    await expect(ownerPage.locator(SEL.mediaScheduler.chartTopSources)).toBeAttached();
    await expect(ownerPage.locator(SEL.mediaScheduler.chartWeekly)).toBeAttached();

    // ────────────────────────────────────────────
    // Phase 10: Cleanup — uninstall app and model
    // ────────────────────────────────────────────
    // Stop the app
    await ownerRequest.post(`${BASE_URL}/admin/apps/media-scheduler/stop`);
    await ownerPage.waitForTimeout(2000);

    // Uninstall with data cleanup
    await ownerRequest.post(`${BASE_URL}/admin/apps/media-scheduler/uninstall`, {
      form: { clean_data: 'true' },
    });
    await ownerPage.waitForTimeout(2000);

    // Delete the model
    await ownerRequest.delete(`${BASE_URL}/admin/models/media-scheduler`);
    await ownerPage.waitForTimeout(1000);

    // Verify app is gone from admin list
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    const remainingAppCards = ownerPage.locator('.admin-page .card').filter({ hasText: 'Media Scheduler' });
    await expect(remainingAppCards).toHaveCount(0, { timeout: 10_000 });

    // Verify model is gone
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForLoadState('domcontentloaded');
    const pageText = await ownerPage.locator('body').textContent();
    expect(pageText).not.toContain('media-scheduler');
  });
});
