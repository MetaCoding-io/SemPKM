/**
 * Screenshot capture suite for the SemPKM User Guide.
 *
 * Captures light-mode screenshots of key features documented in the guide,
 * outputting to docs/screenshots/ for embedding in documentation.
 *
 * Prerequisites:
 *   - Test Docker stack running (npm run env:start)
 *   - Instance set up and owner authenticated (auth fixture handles this)
 *
 * Run with:
 *   npx playwright test tests/screenshots/guide-capture.spec.ts --project=screenshots
 *
 * Output lands in docs/screenshots/ (committed to the repo for guide builds).
 */
import { test, expect } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle, waitForElement } from '../../helpers/wait-for';
import path from 'path';

const GUIDE_SCREENSHOTS = path.resolve(__dirname, '../../../docs/screenshots');

/** Standard viewport for consistent guide screenshots (16:9). */
const VIEWPORT = { width: 1440, height: 900 };

/** Force light mode for all guide screenshots. */
async function forceLightMode(page: import('@playwright/test').Page) {
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'light');
    localStorage.setItem('sempkm_theme', 'light');
  });
}

/** Shared setup: resize viewport, navigate to workspace, force light mode. */
async function openWorkspace(page: import('@playwright/test').Page) {
  await page.setViewportSize(VIEWPORT);
  await page.goto('/browser/');
  await waitForWorkspace(page);
  await forceLightMode(page);
  await waitForIdle(page);
  await page.waitForTimeout(1000);
}

/**
 * Expand all nav tree type sections so the sidebar is fully populated.
 */
async function expandNavTree(page: import('@playwright/test').Page) {
  const sections = page.locator('[data-testid="nav-section"]');
  const count = await sections.count();
  for (let i = 0; i < count; i++) {
    const section = sections.nth(i);
    await section.click();
    await page.waitForTimeout(600);
  }
  await waitForIdle(page);
  await page.waitForTimeout(500);
}

/**
 * Open a seed object by clicking its nav tree leaf.
 */
async function openObjectByLabel(page: import('@playwright/test').Page, label: string) {
  const leaf = page.locator('[data-testid="nav-item"]', { hasText: label });
  await leaf.first().click();
  await page.waitForSelector('.object-tab', { state: 'attached', timeout: 10000 });
  await waitForIdle(page);
  await page.waitForTimeout(800);
}

/** Take a light-mode-only screenshot. */
async function screenshotLight(
  page: import('@playwright/test').Page,
  filename: string,
) {
  await forceLightMode(page);
  await page.waitForTimeout(300);
  await page.screenshot({
    path: path.join(GUIDE_SCREENSHOTS, filename),
    fullPage: false,
  });
}

// ---------------------------------------------------------------------------
// Guide screenshot tests
// ---------------------------------------------------------------------------

test.describe('User guide screenshots', () => {
  test.describe.configure({ mode: 'serial' });

  // 1. Workspace with multiple tabs in dockview groups
  test('guide-workspace-dockview', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);

    // Open several objects as tabs
    await openObjectByLabel(page, SEED.projects.sempkm.title);
    await openObjectByLabel(page, SEED.people.alice.name);
    await openObjectByLabel(page, SEED.notes.architecture.title);

    await page.waitForTimeout(500);
    await screenshotLight(page, 'guide-workspace-dockview.png');
  });

  // 2. Object read view
  test('guide-object-read-view', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.projects.sempkm.title);

    await screenshotLight(page, 'guide-object-read-view.png');
  });

  // 3. Object edit view with helptext
  test('guide-object-edit-view', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);
    await openObjectByLabel(page, SEED.projects.sempkm.title);

    // Toggle to edit mode
    const editBtn = page.locator('.mode-toggle').first();
    await editBtn.click();
    await page.waitForTimeout(1200);
    await waitForIdle(page);

    await screenshotLight(page, 'guide-object-edit-view.png');
  });

  // 4. Carousel views (type browser with view tabs)
  test('guide-carousel-views', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // Open views section and click a view with carousel tabs
    const viewsSection = page.locator('#section-views');
    await viewsSection.locator('.explorer-section-header').click();
    await page.waitForTimeout(800);
    await waitForIdle(page);

    // Click first available view
    const viewLink = page.locator('#views-tree a').first();
    if (await viewLink.count() > 0) {
      await viewLink.click();
      await waitForIdle(page);
      await page.waitForTimeout(1000);
    }

    await screenshotLight(page, 'guide-carousel-views.png');
  });

  // 5. Nav tree with expanded types
  test('guide-nav-tree', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);

    await screenshotLight(page, 'guide-nav-tree.png');
  });

  // 6. Command palette with search results
  test('guide-command-palette', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await expandNavTree(page);

    await page.keyboard.press('Alt+k');
    await page.waitForTimeout(800);

    await screenshotLight(page, 'guide-command-palette.png');
  });

  // 7. SPARQL Console with query and results
  test('guide-sparql-console', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // Open bottom panel
    await page.keyboard.press('Alt+j');
    await page.waitForTimeout(800);

    // Click SPARQL tab if available
    const sparqlTab = page.locator('.bottom-panel-tab', { hasText: /SPARQL/i });
    if (await sparqlTab.count() > 0) {
      await sparqlTab.first().click();
      await page.waitForTimeout(500);
    }

    await screenshotLight(page, 'guide-sparql-console.png');
  });

  // 8. Keyword search results
  test('guide-keyword-search', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await forceLightMode(page);
    await page.goto('/search/?q=knowledge');
    await waitForIdle(page);
    await page.waitForTimeout(1000);

    await screenshotLight(page, 'guide-keyword-search.png');
  });

  // 9. Global lint dashboard
  test('guide-lint-dashboard', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await forceLightMode(page);
    await page.goto('/lint/');
    await waitForIdle(page);
    await page.waitForTimeout(1000);

    await screenshotLight(page, 'guide-lint-dashboard.png');
  });

  // 10. Settings > Entailment / Inference configuration
  test('guide-data-model-inference', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // Open settings
    await page.keyboard.press('Control+,');
    await page.waitForTimeout(1500);
    await waitForIdle(page);

    await screenshotLight(page, 'guide-data-model-inference.png');
  });

  // 11. Obsidian import upload page
  test('guide-obsidian-upload', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await forceLightMode(page);
    await page.goto('/tools/obsidian-import');
    await waitForIdle(page);
    await page.waitForTimeout(1000);

    await screenshotLight(page, 'guide-obsidian-upload.png');
  });

  // 12. Obsidian type mapping step (may need a vault uploaded first)
  test('guide-obsidian-mapping', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await forceLightMode(page);
    await page.goto('/tools/obsidian-import');
    await waitForIdle(page);
    await page.waitForTimeout(1000);

    // Capture whatever state is visible (upload or mapping)
    await screenshotLight(page, 'guide-obsidian-mapping.png');
  });

  // 13. WebID profile page
  test('guide-webid-profile', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await forceLightMode(page);
    // Owner email is owner@test.local, username might be derived
    // Try the /id/ endpoint
    await page.goto('/id/owner');
    await page.waitForTimeout(1000);

    await screenshotLight(page, 'guide-webid-profile.png');
  });

  // 14. IndieAuth consent screen (skip if not accessible without full OAuth flow)
  test('guide-indieauth-consent', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await forceLightMode(page);

    // IndieAuth consent requires a full OAuth flow with client_id, redirect_uri, etc.
    // Attempt to load the authorize page with minimal params
    await page.goto('/auth/authorize?client_id=https://example.com&redirect_uri=https://example.com/callback&response_type=code&state=test&code_challenge=test&code_challenge_method=S256&scope=profile');
    await page.waitForTimeout(1000);

    await screenshotLight(page, 'guide-indieauth-consent.png');
  });

  // 15. Settings > Identity section
  test('guide-settings-identity', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    await page.keyboard.press('Control+,');
    await page.waitForTimeout(1500);
    await waitForIdle(page);

    await screenshotLight(page, 'guide-settings-identity.png');
  });

  // 16. VFS file browser view
  test('guide-vfs-browser', async ({ ownerPage: page }) => {
    await page.setViewportSize(VIEWPORT);
    await forceLightMode(page);
    await page.goto('/tools/vfs');
    await waitForIdle(page);
    await page.waitForTimeout(1000);

    await screenshotLight(page, 'guide-vfs-browser.png');
  });
});
