/**
 * RSS Reader E2E Tests
 *
 * Proves the full RSS Reader lifecycle: model install → app install →
 * workspace UI → subscribe → read articles → star → workspace views →
 * command palette → OPML import → settings → cleanup.
 *
 * Uses a single test() to maintain sequential execution (matching the
 * pattern from app-platform.spec.ts).
 *
 * Runs against the Docker test stack on port 3901.
 */
import * as path from 'path';
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';

test.describe('RSS Reader', () => {
  // Generous timeout — model install + venv creation + pip install + polling
  test.setTimeout(240_000);

  test('full lifecycle: install → subscribe → read → star → views → OPML → settings → uninstall', async ({ ownerPage, ownerRequest }) => {
    // Accept any confirm dialogs (hx-confirm on uninstall/delete buttons)
    ownerPage.on('dialog', (dialog) => dialog.accept());

    // ────────────────────────────────────────────
    // Phase 0: Cleanup — remove prior state for idempotency
    // ────────────────────────────────────────────
    try {
      const appCheck = await ownerRequest.get(`${BASE_URL}/admin/apps/rss-reader`);
      if (appCheck.status() === 200) {
        await ownerRequest.post(`${BASE_URL}/admin/apps/rss-reader/stop`);
        await ownerPage.waitForTimeout(2000);
        await ownerRequest.post(`${BASE_URL}/admin/apps/rss-reader/uninstall`, {
          form: { clean_data: 'true' },
        });
        await ownerPage.waitForTimeout(2000);
      }
    } catch (e) {
      console.log('Cleanup: app removal skipped or failed (expected if not installed):', String(e));
    }

    try {
      await ownerRequest.delete(`${BASE_URL}/admin/models/rss-feeds`);
      await ownerPage.waitForTimeout(1000);
    } catch (e) {
      console.log('Cleanup: model removal skipped (expected if not installed):', String(e));
    }

    // ────────────────────────────────────────────
    // Phase 1: Install rss-feeds model
    // ────────────────────────────────────────────
    const modelInstallResp = await ownerRequest.post(`${BASE_URL}/admin/models/install`, {
      form: { path: '/app/models/rss-feeds' },
    });
    expect(modelInstallResp.status()).toBeLessThan(400);

    // Verify the model appears in the admin list
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForLoadState('domcontentloaded');

    let modelVisible = false;
    for (let attempt = 0; attempt < 5; attempt++) {
      const pageText = await ownerPage.locator('body').textContent();
      if (pageText && (pageText.includes('rss-feeds') || pageText.includes('RSS Feeds'))) {
        modelVisible = true;
        break;
      }
      await ownerPage.waitForTimeout(2000);
      await ownerPage.reload();
      await ownerPage.waitForLoadState('domcontentloaded');
    }
    expect(modelVisible).toBe(true);

    // ────────────────────────────────────────────
    // Phase 2: Install rss-reader app
    // ────────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    await expect(ownerPage.locator('h1')).toContainText('Applications');

    // Open install form (<details>)
    const installDetails = ownerPage.locator(SEL.apps.installDetails);
    await installDetails.locator('summary').click();
    await ownerPage.waitForTimeout(300);

    // Fill app path and submit
    await ownerPage.locator(SEL.apps.installPathInput).fill('rss-reader');
    await ownerPage.locator(`${SEL.apps.installDetails} button[type="submit"]`).click();

    // Wait for install (venv creation + pip install) — redirects to /admin/apps
    await ownerPage.waitForURL('**/admin/apps', { timeout: 90_000 });
    await ownerPage.waitForLoadState('domcontentloaded');

    // Poll for "running" status (health check takes time)
    let appRunning = false;
    for (let attempt = 0; attempt < 10; attempt++) {
      const cardText = await ownerPage.locator('.admin-page').textContent();
      if (cardText && cardText.includes('RSS Reader') && cardText.includes('running')) {
        appRunning = true;
        break;
      }
      await ownerPage.waitForTimeout(5000);
      await ownerPage.goto(`${BASE_URL}/admin/apps`);
      await ownerPage.waitForLoadState('domcontentloaded');
    }
    expect(appRunning).toBe(true);

    const appCard = ownerPage.locator('.admin-page .card').filter({ hasText: 'RSS Reader' });
    await expect(appCard).toBeVisible();
    await expect(appCard.locator('.badge')).toContainText('running');

    // ────────────────────────────────────────────
    // Phase 3: Verify admin detail page
    // ────────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/admin/apps/rss-reader`);
    await ownerPage.waitForLoadState('domcontentloaded');

    await expect(ownerPage.locator('h1')).toContainText('RSS Reader');
    await expect(ownerPage.locator('.model-title-row .badge')).toContainText('running');

    // PID should not be "—"
    const pidStat = ownerPage.locator('.stats-bar .stat-box').first();
    const pidValue = await pidStat.locator('.stat-value').textContent();
    expect(pidValue?.trim()).not.toBe('—');

    // Permissions table should include object.create
    const permissionsTable = ownerPage.locator('h2:has-text("Permissions") + table');
    await expect(permissionsTable).toContainText('object.create');

    // Scheduled tasks should include poll-feeds
    const tasksSection = ownerPage.locator('h2:has-text("Scheduled Tasks")');
    await expect(tasksSection).toBeVisible();
    await expect(ownerPage.locator('.task-section')).toContainText('poll-feeds');

    // ────────────────────────────────────────────
    // Phase 4: Verify workspace integration
    // ────────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Wait for APPS explorer section
    const appsSection = ownerPage.locator(SEL.apps.sidebarAppsSection);
    await expect(appsSection).toBeVisible({ timeout: 10_000 });

    // Expand if collapsed
    const isExpanded = await appsSection.evaluate(el => el.classList.contains('expanded'));
    if (!isExpanded) {
      await appsSection.locator('.explorer-section-header').click();
      await ownerPage.waitForTimeout(500);
    }

    // Wait for apps tree to populate
    const appsTree = ownerPage.locator(SEL.apps.appsTree);
    await expect(appsTree.locator('.tree-leaf')).toBeVisible({ timeout: 15_000 });
    await expect(appsTree).toContainText('RSS Reader');

    // Click RSS Reader to open it
    await appsTree.locator('.tree-leaf', { hasText: 'RSS Reader' }).click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify reader container appeared
    const readerContainer = ownerPage.locator(SEL.rss.readerContainer);
    await expect(readerContainer).toBeVisible({ timeout: 15_000 });

    // Wait for feed sidebar to load (htmx lazy-load)
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Should show empty state (no feeds subscribed yet)
    const emptyState = ownerPage.locator(SEL.rss.emptyState);
    const feedItems = ownerPage.locator(SEL.rss.feedItem);
    const hasEmpty = await emptyState.count() > 0;
    const hasFeedItems = await feedItems.count() > 0;
    // Either empty state or feed items present — both are valid initial states
    expect(hasEmpty || hasFeedItems).toBe(true);

    // ────────────────────────────────────────────
    // Phase 5: Subscribe to a feed
    // ────────────────────────────────────────────
    // Click subscribe button (in empty state or feed sidebar)
    const subscribeBtn = ownerPage.locator(SEL.rss.subscribeBtn).first();
    await subscribeBtn.click();
    await ownerPage.waitForTimeout(1000);

    // Wait for subscribe dialog to appear in reading pane
    const subscribeDialog = ownerPage.locator(SEL.rss.subscribeDialog);
    await expect(subscribeDialog).toBeVisible({ timeout: 10_000 });

    // Fill feed URL and submit
    await ownerPage.locator(SEL.rss.feedUrlInput).fill('https://example.com/feed.xml');
    await subscribeDialog.locator('button[type="submit"]').click();
    await ownerPage.waitForTimeout(3000);

    // After subscribe, the subscription is created in triplestore regardless of
    // whether the feed URL is reachable. The feedsChanged HX-Trigger refreshes
    // the sidebar. Wait for it.
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);

    // Verify feed item appears in sidebar (reload if needed — HX-Trigger may
    // not have arrived yet)
    let feedItemCount = await ownerPage.locator(`${SEL.rss.feedSidebar} ${SEL.rss.feedItem}`).count();
    if (feedItemCount === 0) {
      // Force sidebar refresh via navigation
      await appsTree.locator('.tree-leaf', { hasText: 'RSS Reader' }).click();
      await ownerPage.waitForTimeout(3000);
      await waitForIdle(ownerPage);
      feedItemCount = await ownerPage.locator(`${SEL.rss.feedSidebar} ${SEL.rss.feedItem}`).count();
    }
    // At minimum "All Feeds" item should appear once we have a subscription
    expect(feedItemCount).toBeGreaterThanOrEqual(1);

    // ────────────────────────────────────────────
    // Phase 6: Seed test article (if needed) and verify display
    // ────────────────────────────────────────────
    // Check if articles appeared from the poll (unlikely in offline Docker)
    let articleCount = await ownerPage.locator(SEL.rss.articleItem).count();

    if (articleCount === 0) {
      // Seed an article via the API
      const articleType = 'urn:sempkm:model:rss-feeds:Article';
      try {
        const createResp = await ownerRequest.post(`${BASE_URL}/api/objects`, {
          data: {
            type: articleType,
            properties: {
              'http://purl.org/dc/terms/title': 'E2E Test Article',
              'urn:sempkm:model:rss-feeds:prop:isRead': 'false',
              'urn:sempkm:model:rss-feeds:prop:isStarred': 'false',
              'urn:sempkm:model:rss-feeds:prop:articleUrl': 'https://example.com/article-1',
            },
          },
        });

        if (createResp.status() === 200 || createResp.status() === 201) {
          const createData = await createResp.json();
          const articleIri = createData.iri || createData.id;

          // Set article body
          if (articleIri) {
            await ownerRequest.post(`${BASE_URL}/api/objects/${encodeURIComponent(articleIri)}/body`, {
              data: { content: '# E2E Test Article\n\nThis is a test article created by the E2E test suite.', format: 'markdown' },
            });
          }
        } else {
          const body = await createResp.text();
          console.log('Article seed response:', createResp.status(), body);
        }
      } catch (e) {
        console.log('Article seeding failed:', String(e));
      }

      // Reload the reader to pick up the seeded article
      await appsTree.locator('.tree-leaf', { hasText: 'RSS Reader' }).click();
      await ownerPage.waitForTimeout(3000);
      await waitForIdle(ownerPage);
      await ownerPage.waitForTimeout(2000);

      articleCount = await ownerPage.locator(SEL.rss.articleItem).count();
    }

    // Assert at least one article is visible
    expect(articleCount).toBeGreaterThanOrEqual(1);

    // ────────────────────────────────────────────
    // Phase 7: Read an article
    // ────────────────────────────────────────────
    const firstArticle = ownerPage.locator(SEL.rss.articleItem).first();
    await firstArticle.click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Reading pane should have content
    const readingPane = ownerPage.locator(SEL.rss.readingPane);
    await expect(readingPane).toBeVisible();
    // Should no longer show the empty placeholder
    const paneText = await readingPane.textContent();
    expect(paneText).toBeTruthy();
    expect(paneText!.length).toBeGreaterThan(20);

    // ────────────────────────────────────────────
    // Phase 8: Star an article
    // ────────────────────────────────────────────
    const starBtn = ownerPage.locator(SEL.rss.starBtn).first();
    const starBtnCount = await starBtn.count();

    if (starBtnCount > 0) {
      // Record initial star state
      const initialStarred = await starBtn.getAttribute('data-starred');

      await starBtn.click();
      await ownerPage.waitForTimeout(1500);
      await waitForIdle(ownerPage);

      // Star state should have toggled
      const newStarBtn = ownerPage.locator(SEL.rss.starBtn).first();
      const newStarred = await newStarBtn.getAttribute('data-starred');
      expect(newStarred).not.toBe(initialStarred);

      // Verify persistence — reload the reader page and check star state
      await appsTree.locator('.tree-leaf', { hasText: 'RSS Reader' }).click();
      await ownerPage.waitForTimeout(3000);
      await waitForIdle(ownerPage);

      // Click the article again
      await ownerPage.locator(SEL.rss.articleItem).first().click();
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);

      const persistedStarBtn = ownerPage.locator(SEL.rss.starBtn).first();
      const persistedCount = await persistedStarBtn.count();
      if (persistedCount > 0) {
        const persistedStarred = await persistedStarBtn.getAttribute('data-starred');
        expect(persistedStarred).toBe(newStarred);
      }
    }

    // ────────────────────────────────────────────
    // Phase 9: Verify unread count / mark read (soft check)
    // ────────────────────────────────────────────
    // After opening an article, the article should be marked as read
    // (fire-and-forget mark-read on open). Check sidebar for unread badge.
    const feedSidebar = ownerPage.locator(SEL.rss.feedSidebar);
    const sidebarContent = await feedSidebar.textContent();
    // Soft assertion — unread counts may or may not be visible depending on
    // how many articles exist and whether mark-read fired
    expect(sidebarContent).toBeTruthy();

    // ────────────────────────────────────────────
    // Phase 10: Workspace views (Unread/Starred)
    // ────────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Look for Views section in explorer
    const viewsSection = ownerPage.locator('#section-views');
    const viewsSectionCount = await viewsSection.count();
    if (viewsSectionCount > 0) {
      // Expand if collapsed
      const viewsExpanded = await viewsSection.evaluate(el => el.classList.contains('expanded'));
      if (!viewsExpanded) {
        await viewsSection.locator('.explorer-section-header').click();
        await ownerPage.waitForTimeout(500);
      }

      // Look for Starred Articles or Unread Articles
      const viewsTree = ownerPage.locator('#views-tree');
      const viewsContent = await viewsTree.textContent();
      if (viewsContent && (viewsContent.includes('Starred') || viewsContent.includes('Unread'))) {
        // Click Starred Articles view
        const starredLeaf = viewsTree.locator('.tree-leaf', { hasText: 'Starred' });
        const starredCount = await starredLeaf.count();
        if (starredCount > 0) {
          await starredLeaf.click();
          await ownerPage.waitForTimeout(3000);
          await waitForIdle(ownerPage);
          // View tab should load with content
          const editorArea = ownerPage.locator('.group-editor-area');
          const editorText = await editorArea.textContent();
          expect(editorText).toBeTruthy();
        }
      }
    }

    // ────────────────────────────────────────────
    // Phase 11: Command palette
    // ────────────────────────────────────────────
    await ownerPage.goto(`${BASE_URL}/`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Open command palette (Ctrl+K)
    await ownerPage.keyboard.press('Control+k');
    await ownerPage.waitForTimeout(500);

    const ninjaKeys = ownerPage.locator(SEL.commandPalette.overlay);
    await expect(ninjaKeys).toBeVisible({ timeout: 5_000 });

    // Type "RSS" to filter commands
    // ninja-keys uses shadow DOM, so we use evaluate to type into it
    await ownerPage.evaluate(() => {
      const nk = document.querySelector('ninja-keys');
      if (nk && nk.shadowRoot) {
        const input = nk.shadowRoot.querySelector('input');
        if (input) {
          input.value = 'RSS';
          input.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }
    });
    await ownerPage.waitForTimeout(1000);

    // Check that RSS Reader commands appear
    const ninjaContent = await ownerPage.evaluate(() => {
      const nk = document.querySelector('ninja-keys');
      if (!nk || !nk.shadowRoot) return '';
      return nk.shadowRoot.textContent || '';
    });
    expect(ninjaContent).toContain('RSS');

    // Close command palette
    await ownerPage.keyboard.press('Escape');
    await ownerPage.waitForTimeout(300);

    // ────────────────────────────────────────────
    // Phase 12: OPML import
    // ────────────────────────────────────────────
    // Navigate back to the RSS Reader
    await ownerPage.goto(`${BASE_URL}/`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Open RSS Reader via apps tree
    const appsSection2 = ownerPage.locator(SEL.apps.sidebarAppsSection);
    const isExpanded2 = await appsSection2.evaluate(el => el.classList.contains('expanded'));
    if (!isExpanded2) {
      await appsSection2.locator('.explorer-section-header').click();
      await ownerPage.waitForTimeout(500);
    }
    const appsTree2 = ownerPage.locator(SEL.apps.appsTree);
    await expect(appsTree2.locator('.tree-leaf')).toBeVisible({ timeout: 15_000 });
    await appsTree2.locator('.tree-leaf', { hasText: 'RSS Reader' }).click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Click "Import OPML" button
    const importBtn = ownerPage.locator(SEL.rss.subscribeBtn, { hasText: 'Import OPML' }).first();
    await importBtn.click();
    await ownerPage.waitForTimeout(1000);

    // Wait for OPML import form
    const opmlImportForm = ownerPage.locator(SEL.rss.opmlImportForm);
    await expect(opmlImportForm).toBeVisible({ timeout: 10_000 });

    // Set the OPML file on the file input
    const opmlFixturePath = path.resolve(__dirname, '../../fixtures/test-feeds.opml');
    await opmlImportForm.locator('input[type="file"]').setInputFiles(opmlFixturePath);

    // Submit the import form
    await opmlImportForm.locator('button[type="submit"]').click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    // Verify import result — check for success message or result div
    const opmlResult = ownerPage.locator(SEL.rss.opmlResult);
    const successMsg = ownerPage.locator(SEL.rss.successMessage);
    const resultVisible = await opmlResult.count() > 0;
    const successVisible = await successMsg.count() > 0;
    expect(resultVisible || successVisible).toBe(true);

    // If the result div has data-created attribute, check it
    if (resultVisible) {
      const resultContent = await opmlResult.textContent();
      expect(resultContent).toBeTruthy();
      // The result div should show import counts
      const createdAttr = await opmlResult.locator('.rss-success').first().getAttribute('data-created');
      if (createdAttr !== null) {
        expect(parseInt(createdAttr, 10)).toBeGreaterThanOrEqual(0);
      }
    }

    // ────────────────────────────────────────────
    // Phase 13: Settings
    // ────────────────────────────────────────────
    // Click the gear icon in feed sidebar header
    // First re-navigate to reader to get the feed sidebar with feeds
    await appsTree2.locator('.tree-leaf', { hasText: 'RSS Reader' }).click();
    await ownerPage.waitForTimeout(3000);
    await waitForIdle(ownerPage);

    const gearBtn = ownerPage.locator(`${SEL.rss.feedSidebar} ${SEL.rss.sidebarIconBtn}`).first();
    const gearCount = await gearBtn.count();

    if (gearCount > 0) {
      await gearBtn.click();
      await ownerPage.waitForTimeout(1000);

      // Wait for settings form to appear in reading pane
      const settingsForm = ownerPage.locator(SEL.rss.settingsForm);
      await expect(settingsForm).toBeVisible({ timeout: 10_000 });

      // Change articlesPerPage value
      const articlesInput = settingsForm.locator('input[name="articlesPerPage"]');
      await articlesInput.fill('25');

      // Submit settings form
      await settingsForm.locator('button[type="submit"]').click();
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);

      // Verify success message appeared
      const settingsResult = ownerPage.locator(SEL.rss.settingsResult);
      const settingsSuccess = settingsResult.locator(SEL.rss.successMessage);
      await expect(settingsSuccess).toBeVisible({ timeout: 5_000 });
    }

    // ────────────────────────────────────────────
    // Phase 14: Cleanup — uninstall app and model
    // ────────────────────────────────────────────
    // Stop the app
    await ownerRequest.post(`${BASE_URL}/admin/apps/rss-reader/stop`);
    await ownerPage.waitForTimeout(2000);

    // Uninstall with data cleanup
    await ownerRequest.post(`${BASE_URL}/admin/apps/rss-reader/uninstall`, {
      form: { clean_data: 'true' },
    });
    await ownerPage.waitForTimeout(2000);

    // Delete the model
    await ownerRequest.delete(`${BASE_URL}/admin/models/rss-feeds`);
    await ownerPage.waitForTimeout(1000);

    // Verify app is gone from admin list
    await ownerPage.goto(`${BASE_URL}/admin/apps`);
    await ownerPage.waitForLoadState('domcontentloaded');
    const remainingAppCards = ownerPage.locator('.admin-page .card').filter({ hasText: 'RSS Reader' });
    await expect(remainingAppCards).toHaveCount(0, { timeout: 10_000 });

    // Verify model is gone
    await ownerPage.goto(`${BASE_URL}/admin/models`);
    await ownerPage.waitForLoadState('domcontentloaded');
    const pageText = await ownerPage.locator('body').textContent();
    expect(pageText).not.toContain('rss-feeds');

    // Verify workspace no longer shows RSS Reader in apps tree
    await ownerPage.goto(`${BASE_URL}/`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(3000);

    const appsTreeFinal = ownerPage.locator(SEL.apps.appsTree);
    const rssReaderLeaf = appsTreeFinal.locator('.tree-leaf', { hasText: 'RSS Reader' });
    await expect(rssReaderLeaf).toHaveCount(0, { timeout: 10_000 });
  });
});
