/**
 * Tutorials and Docs E2E Tests
 *
 * Tests the Docs & Tutorials page functionality:
 * - openDocsTab() opens the docs tab in the active editor group
 * - The docs page renders inside the group editor area
 * - Tutorial "Start Tour" buttons are visible and clickable
 *
 * Requires: Docker test stack on port 3901, seed data installed.
 * Phase: 18 (Tutorials and Documentation) + Phase 19 (link fix)
 *
 * DOM structure (from workspace.html + docs_page.html):
 *   [data-tab-id="special:docs"]  — the tab element in the group-tab-bar
 *   .tab-label                    — text label inside the tab element
 *   #docs-page / .docs-page       — the docs content rendered in group-editor-area
 *   .docs-card-btn                — "Start Tour" buttons in the interactive tutorials section
 *
 * Note: The Docs & Tutorials sidebar nav link calls openDocsTab() onclick.
 *   The link lives inside .sidebar-group[data-group="meta"] which may be collapsed
 *   (state persisted in localStorage). Tests call openDocsTab() directly via JS
 *   evaluation to avoid sidebar-state dependency.
 */
import { test, expect } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Tutorials and Docs', () => {
  test('openDocsTab opens a docs tab in the editor group', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Call openDocsTab() directly (same as clicking the sidebar nav link)
    // Cast to any: openDocsTab is registered on window by workspace.js at runtime
    await ownerPage.evaluate(() => {
      const w = window as any;
      if (typeof w.openDocsTab === 'function') w.openDocsTab();
    });
    await waitForIdle(ownerPage);

    // Dockview panel for docs should be created
    const docsTabContent = ownerPage.locator('.dv-default-tab-content');
    await expect(docsTabContent.filter({ hasText: 'Docs' })).toBeVisible({ timeout: 10000 });
  });

  test('tutorial start buttons are visible in the docs page', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open docs tab via JS
    await ownerPage.evaluate(() => {
      const w = window as any;
      if (typeof w.openDocsTab === 'function') w.openDocsTab();
    });
    await waitForIdle(ownerPage);

    // Wait for docs page content to render
    // docs_page.html renders inside the group-editor-area as #docs-page / .docs-page
    const docsPage = ownerPage.locator('#docs-page');
    await expect(docsPage).toBeVisible({ timeout: 10000 });

    // "Start Tour" buttons should be present (docs_page.html: <button class="btn docs-card-btn">Start Tour</button>)
    const tourButtons = ownerPage.locator('.docs-card-btn');
    await expect(tourButtons.first()).toBeVisible();

    const count = await tourButtons.count();
    expect(count).toBeGreaterThan(0);
  });

  // ── Persona walkthroughs ("A Day in the Graph") ────────────────────────
  // Rendered client-side by tutorials.js (SemPKM.renderWalkthroughPicker)
  // into the [data-walkthrough-picker] container of docs_page.html.

  test('walkthrough picker lists personas and switches chapters', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await ownerPage.evaluate(() => {
      const w = window as any;
      if (typeof w.openDocsTab === 'function') w.openDocsTab();
    });
    await waitForIdle(ownerPage);

    const picker = ownerPage.locator('#docs-walkthroughs .wt-picker');
    await expect(picker).toBeVisible({ timeout: 10000 });

    // One tab per registered persona (Alice, Maya)
    const tabs = picker.locator('.wt-tab');
    await expect(tabs).toHaveCount(2);
    await expect(tabs.nth(0)).toContainText('Alice');
    await expect(tabs.nth(1)).toContainText('Maya');

    // Alice is selected by default and shows her 6 chapters with times
    const alicePanel = picker.locator('[data-wt-persona-panel="alice"]');
    await expect(alicePanel).toBeVisible();
    await expect(alicePanel.locator('.wt-chapter')).toHaveCount(6);
    await expect(alicePanel.locator('.wt-time').first()).toHaveText('9:02');

    // Switching to Maya hides Alice's panel and shows Maya's 5 chapters
    await tabs.nth(1).click();
    const mayaPanel = picker.locator('[data-wt-persona-panel="maya"]');
    await expect(mayaPanel).toBeVisible();
    await expect(alicePanel).toBeHidden();
    await expect(mayaPanel.locator('.wt-chapter')).toHaveCount(5);
    await expect(picker.locator('.wt-tab-active')).toContainText('Maya');
  });

  test('starting a chapter shows its Driver.js chapter card', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_walkthrough_progress'));
    await ownerPage.evaluate(() => {
      const w = window as any;
      if (typeof w.openDocsTab === 'function') w.openDocsTab();
    });
    await waitForIdle(ownerPage);

    const picker = ownerPage.locator('#docs-walkthroughs .wt-picker');
    await expect(picker).toBeVisible({ timeout: 10000 });

    // Start Alice's 9:15 chapter (opens a seed Note — basic-pkm is always installed)
    await picker.locator('[data-wt-start="alice"][data-wt-chapter="type"]').click();

    const popover = ownerPage.locator('.driver-popover');
    await expect(popover).toBeVisible({ timeout: 10000 });
    await expect(popover.locator('.driver-popover-title')).toContainText('9:15');
    await expect(popover.locator('.driver-popover-title')).toContainText('Give it a type');

    // Advancing past the chapter card opens the seed object as a tab
    await popover.locator('.driver-popover-next-btn').click();
    await expect(ownerPage.locator('.dv-default-tab-content').filter({ hasText: 'Architecture Decision' }))
      .toBeVisible({ timeout: 10000 });
    await expect(popover.locator('.driver-popover-title')).toContainText('A typed object');

    // Close the tour — driver overlay goes away
    await ownerPage.keyboard.press('Escape');
    await expect(popover).toBeHidden({ timeout: 5000 });
  });

  test('?tour=<persona> auto-starts the walkthrough on workspace load', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/?tour=alice:trust`);
    await waitForWorkspace(ownerPage);

    const popover = ownerPage.locator('.driver-popover');
    await expect(popover).toBeVisible({ timeout: 15000 });
    await expect(popover.locator('.driver-popover-title')).toContainText('18:00');

    // The ?tour= param is stripped from the URL once consumed
    await expect.poll(() => ownerPage.evaluate(() => window.location.search)).not.toContain('tour=');

    await ownerPage.keyboard.press('Escape');
    await expect(popover).toBeHidden({ timeout: 5000 });
  });

  test('completing a chapter is remembered in localStorage progress', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await ownerPage.evaluate(() => localStorage.removeItem('sempkm_walkthrough_progress'));

    // Alice's 18:00 chapter: card → event log → closing card (last step marks it done)
    await ownerPage.evaluate('window.SemPKM.startWalkthrough("alice", "trust")');
    const popover = ownerPage.locator('.driver-popover');
    await expect(popover).toBeVisible({ timeout: 10000 });
    await popover.locator('.driver-popover-next-btn').click();
    await expect(popover.locator('.driver-popover-title')).toContainText('event log', { ignoreCase: true });
    await popover.locator('.driver-popover-next-btn').click();
    await expect(popover.locator('.driver-popover-title')).toContainText("Alice's day");

    await ownerPage.waitForFunction(() => {
      const raw = localStorage.getItem('sempkm_walkthrough_progress');
      if (!raw) return false;
      const progress = JSON.parse(raw);
      return Boolean(progress.alice && progress.alice.trust);
    }, null, { timeout: 5000 });

    await ownerPage.keyboard.press('Escape');
    await expect(popover).toBeHidden({ timeout: 5000 });
  });
});
