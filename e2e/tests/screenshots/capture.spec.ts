/**
 * Screenshot capture suite for the SemPKM marketing website.
 *
 * Navigates through the live app, interacts with seed data, and captures
 * full-page and element-level screenshots for use on sempkm.metacoding.io.
 *
 * Prerequisites:
 *   - Test Docker stack running (npm run env:start)
 *   - Instance set up and owner authenticated (auth fixture handles this)
 *
 * Run with:
 *   npx playwright test tests/screenshots/capture.spec.ts --project=screenshots
 *
 * Output lands in e2e/screenshots/ (committed to the repo for website builds).
 */
import { test, expect, OWNER_EMAIL } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle, waitForElement } from '../../helpers/wait-for';
import { SEL } from '../../helpers/selectors';
import path from 'path';

const SCREENSHOTS_DIR = path.resolve(__dirname, '../../screenshots');

/** Standard viewport for consistent marketing screenshots (16:9). */
const VIEWPORT = { width: 1440, height: 900 };

/** Shared setup: resize viewport and navigate to workspace. */
async function openWorkspace(page: import('@playwright/test').Page) {
  await page.setViewportSize(VIEWPORT);
  await page.goto('/browser/');
  await waitForWorkspace(page);
  await waitForIdle(page);
  // Let Lucide icons render and any layout settle
  await page.waitForTimeout(1500);
}

/**
 * Expand all nav tree type sections so the sidebar is fully populated.
 * Clicks each collapsed tree-node header to trigger htmx child loading.
 */
async function expandNavTree(page: import('@playwright/test').Page) {
  const sections = page.locator('[data-testid="nav-section"]');
  const count = await sections.count();
  for (let i = 0; i < count; i++) {
    const section = sections.nth(i);
    // Click to expand (triggers htmx load of children)
    await section.click();
    await page.waitForTimeout(600);
  }
  await waitForIdle(page);
  await page.waitForTimeout(500);
}

/**
 * Open a seed object by clicking its nav tree leaf.
 * Returns after the object tab has loaded.
 */
async function openObjectByLabel(page: import('@playwright/test').Page, label: string) {
  const leaf = page.locator(`[data-testid="nav-item"]`, { hasText: label });
  await leaf.first().click();
  // Wait for the object tab content to appear in the editor
  await page.waitForSelector('.object-tab', { state: 'attached', timeout: 10000 });
  await waitForIdle(page);
  await page.waitForTimeout(800);
}

// ─────────────────────────────────────────────────────────────────────────────
// Screenshot tests
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Marketing screenshots', () => {
  test.describe.configure({ mode: 'serial' });

  // ── 1. Full workspace overview ──────────────────────────────────────────

  test('01 — workspace overview with nav tree expanded', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '01-workspace-overview.png'),
      fullPage: false,
    });
  });

  // ── 2. Object browser — read-only view ─────────────────────────────────

  test('02 — object read view (Project)', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.projects.sempkm.title);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '02-object-read-project.png'),
      fullPage: false,
    });
  });

  // ── 3. Object edit mode with SHACL form ────────────────────────────────

  test('03 — object edit mode (Project)', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.projects.sempkm.title);

    // Toggle to edit mode
    const editBtn = page.locator('.mode-toggle').first();
    await editBtn.click();
    await page.waitForTimeout(1200);
    await waitForIdle(page);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '03-object-edit-form.png'),
      fullPage: false,
    });
  });

  // ── 4. Type picker ─────────────────────────────────────────────────────

  test('04 — type picker overlay', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // Open type picker via Ctrl+N (or click "New" button)
    await page.keyboard.press('Control+n');
    await waitForElement(page, '[data-testid="type-picker"]');
    await page.waitForTimeout(600);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '04-type-picker.png'),
      fullPage: false,
    });
  });

  // ── 5. Create new object form ──────────────────────────────────────────

  test('05 — create new object form (Note)', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // Open type picker and select Note
    await page.keyboard.press('Control+n');
    await waitForElement(page, '[data-testid="type-picker"]');
    await page.waitForTimeout(400);

    const noteOption = page.locator('[data-testid="type-option"]', { hasText: 'Note' });
    await noteOption.first().click();
    await waitForElement(page, '[data-testid="object-form"]');
    await waitForIdle(page);
    await page.waitForTimeout(600);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '05-create-note-form.png'),
      fullPage: false,
    });
  });

  // ── 6. Table view ──────────────────────────────────────────────────────

  test('06 — table view', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // Click the Views section to expand it, then click a table view
    const viewsSection = page.locator('#section-views');
    await viewsSection.locator('.explorer-section-header').click();
    await page.waitForTimeout(800);
    await waitForIdle(page);

    // Look for a table-type view link in the views tree
    const tableViewLink = page.locator('#views-tree a', { hasText: /table|Table|All/i });
    if (await tableViewLink.count() > 0) {
      await tableViewLink.first().click();
      await waitForIdle(page);
      await page.waitForTimeout(1000);
    }

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '06-table-view.png'),
      fullPage: false,
    });
  });

  // ── 7. Cards view ──────────────────────────────────────────────────────

  test('07 — cards view', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    const viewsSection = page.locator('#section-views');
    await viewsSection.locator('.explorer-section-header').click();
    await page.waitForTimeout(800);
    await waitForIdle(page);

    const cardsViewLink = page.locator('#views-tree a', { hasText: /card|Card/i });
    if (await cardsViewLink.count() > 0) {
      await cardsViewLink.first().click();
      await waitForIdle(page);
      await page.waitForTimeout(1000);
    }

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '07-cards-view.png'),
      fullPage: false,
    });
  });

  // ── 8. Graph view ──────────────────────────────────────────────────────

  test('08 — graph view', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    const viewsSection = page.locator('#section-views');
    await viewsSection.locator('.explorer-section-header').click();
    await page.waitForTimeout(800);
    await waitForIdle(page);

    const graphViewLink = page.locator('#views-tree a', { hasText: /graph|Graph/i });
    if (await graphViewLink.count() > 0) {
      await graphViewLink.first().click();
      await waitForIdle(page);
      // Graph needs extra time for Cytoscape layout
      await page.waitForTimeout(2500);
    }

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '08-graph-view.png'),
      fullPage: false,
    });
  });

  // ── 9. Command palette ─────────────────────────────────────────────────

  test('09 — command palette', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);

    // Open command palette
    await page.keyboard.press('Control+k');
    await page.waitForTimeout(800);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '09-command-palette.png'),
      fullPage: false,
    });
  });

  // ── 10. Settings page ──────────────────────────────────────────────────

  test('10 — settings page', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // Open settings via Ctrl+,
    await page.keyboard.press('Control+,');
    await page.waitForTimeout(1500);
    await waitForIdle(page);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '10-settings-page.png'),
      fullPage: false,
    });
  });

  // ── 11. Dark mode ──────────────────────────────────────────────────────

  test('11 — dark mode workspace', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.projects.sempkm.title);

    // Switch to dark mode via JS
    await page.evaluate(() => {
      localStorage.setItem('sempkm_theme', 'dark');
      document.documentElement.setAttribute('data-theme', 'dark');
      // Fire the theme change event if the app listens for it
      window.dispatchEvent(new CustomEvent('sempkm:theme-changed', { detail: { theme: 'dark' } }));
    });
    await page.waitForTimeout(800);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '11-dark-mode.png'),
      fullPage: false,
    });

    // Reset to light for subsequent tests
    await page.evaluate(() => {
      localStorage.setItem('sempkm_theme', 'light');
      document.documentElement.setAttribute('data-theme', 'light');
    });
  });

  // ── 12. Dark mode — graph view ─────────────────────────────────────────

  test('12 — dark mode graph view', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // Switch to dark mode first
    await page.evaluate(() => {
      localStorage.setItem('sempkm_theme', 'dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await page.waitForTimeout(400);

    const viewsSection = page.locator('#section-views');
    await viewsSection.locator('.explorer-section-header').click();
    await page.waitForTimeout(800);
    await waitForIdle(page);

    const graphViewLink = page.locator('#views-tree a', { hasText: /graph|Graph/i });
    if (await graphViewLink.count() > 0) {
      await graphViewLink.first().click();
      await waitForIdle(page);
      await page.waitForTimeout(2500);
    }

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '12-dark-mode-graph.png'),
      fullPage: false,
    });

    // Reset
    await page.evaluate(() => {
      localStorage.setItem('sempkm_theme', 'light');
      document.documentElement.setAttribute('data-theme', 'light');
    });
  });

  // ── 13. Admin — Mental Models page ─────────────────────────────────────

  test('13 — admin mental models page', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await page.goto('/admin/models');
    await waitForIdle(page);
    await page.waitForTimeout(1200);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '13-admin-models.png'),
      fullPage: false,
    });
  });

  // ── 14. Admin — Webhooks page ──────────────────────────────────────────

  test('14 — admin webhooks page', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await page.goto('/admin/webhooks');
    await waitForIdle(page);
    await page.waitForTimeout(1200);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '14-admin-webhooks.png'),
      fullPage: false,
    });
  });

  // ── 15. Multiple tabs open ─────────────────────────────────────────────

  test('15 — multiple tabs with split view', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);

    // Open several seed objects as tabs
    await openObjectByLabel(page, SEED.projects.sempkm.title);
    await openObjectByLabel(page, SEED.people.alice.name);
    await openObjectByLabel(page, SEED.notes.architecture.title);

    await page.waitForTimeout(600);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '15-multiple-tabs.png'),
      fullPage: false,
    });
  });

  // ── 16. Validation / lint panel ────────────────────────────────────────

  test('16 — lint panel with validation results', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.projects.sempkm.title);

    // The lint panel is in the right-pane Details section
    // Wait for lint content to load
    await page.waitForTimeout(1500);

    // Capture just the right pane (properties + lint)
    const rightPane = page.locator('[data-testid="properties-panel"]');
    if (await rightPane.isVisible()) {
      await rightPane.screenshot({
        path: path.join(SCREENSHOTS_DIR, '16-lint-panel.png'),
      });
    } else {
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, '16-lint-panel.png'),
        fullPage: false,
      });
    }
  });

  // ── 17. Person read view ───────────────────────────────────────────────

  test('17 — object read view (Person)', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.people.alice.name);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '17-object-read-person.png'),
      fullPage: false,
    });
  });

  // ── 18. Concept read view ──────────────────────────────────────────────

  test('18 — object read view (Concept)', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.concepts.semanticWeb.label);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '18-object-read-concept.png'),
      fullPage: false,
    });
  });

  // ── 19. Setup page (unauthenticated) ───────────────────────────────────

  test('19 — login page', async ({ browser }) => {
    // Use a fresh context with no auth cookies
    const context = await browser.newContext({
      viewport: VIEWPORT,
    });
    const page = await context.newPage();
    await page.goto('/login.html');
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '19-login-page.png'),
      fullPage: false,
    });

    await context.close();
  });

  // ── 20. Bottom panel (SPARQL / Event Log) ──────────────────────────────

  test('20 — bottom panel open', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.projects.sempkm.title);

    // Open bottom panel via Ctrl+J
    await page.keyboard.press('Control+j');
    await page.waitForTimeout(800);

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '20-bottom-panel.png'),
      fullPage: false,
    });
  });
});
