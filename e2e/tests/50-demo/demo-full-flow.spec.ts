/**
 * Demo Instance E2E Tests — Full Demo Flow
 *
 * Exercises the complete demo experience against the live Docker demo stack:
 *   DEMO-03: Sample data is visible in the workspace browser
 *   DEMO-04: Demo tour triggers via startDemoTour() and completes (localStorage flag)
 *   DEMO-05: Demo dashboard renders with content
 *   DEMO-06: CTA banner is visible after tour completion
 *
 * Target: http://localhost:3902 (docker-compose.demo.yml)
 * Auth: None — fresh browser context with no cookies.
 *
 * Prerequisites:
 *   cd <repo-root> && docker compose -f docker-compose.demo.yml up -d --build
 *   Wait for all services healthy + seed data loaded before running.
 *
 * Run:
 *   npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo
 */
import { test, expect, type Page } from '@playwright/test';

const DEMO_URL = 'http://localhost:3902';
const DEMO_DASHBOARD_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';

test.describe('Demo Instance — Full Demo Flow', () => {
  test.describe.configure({ mode: 'serial' });

  /** Collect page errors across the serial test suite */
  const pageErrors: Error[] = [];
  let sharedPage: Page;

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    sharedPage = await context.newPage();
    sharedPage.on('pageerror', (err) => pageErrors.push(err));
  });

  test.afterAll(async () => {
    await sharedPage.context().close();
  });

  // ── DEMO-03: Anonymous workspace loads with sample data ─────────

  test('anonymous workspace loads with sample data visible', async () => {
    const response = await sharedPage.goto(`${DEMO_URL}/browser/`);

    // HTTP 200, no login redirect
    expect(response).not.toBeNull();
    expect(response!.status()).toBe(200);
    expect(sharedPage.url()).toContain('/browser');
    expect(sharedPage.url()).not.toContain('/login');

    // Workspace container renders
    await expect(
      sharedPage.locator('[data-testid="workspace"]')
    ).toBeVisible({ timeout: 15_000 });

    // Sample data is present — explorer sidebar has at least one tree item
    // The explorer section contains list items for each object type/group
    const explorerItems = sharedPage.locator('#section-objects li, #section-objects .tree-item, #explorer-panel li');
    await expect(explorerItems.first()).toBeVisible({ timeout: 15_000 });
    const itemCount = await explorerItems.count();
    expect(itemCount).toBeGreaterThan(0);
  });

  // ── DEMO-04: Demo tour completes via startDemoTour() ────────────

  test('demo tour triggers and completes via localStorage flag', async () => {
    // Clear any pre-existing state to simulate a fresh visitor
    await sharedPage.evaluate(() => {
      localStorage.removeItem('sempkm_demo_tour_done');
      localStorage.removeItem('sempkm_demo_cta_dismissed');
    });

    // Trigger the tour programmatically
    await sharedPage.evaluate('window.SemPKM.startDemoTour()');

    // Wait for the first Driver.js popover to appear
    await sharedPage.waitForSelector('.driver-popover', { timeout: 10_000 });

    // Click through all tour steps — each step has a Next or Done button.
    // Steps 1-6 show "Next"; step 7 shows "Done". Each onNextClick handler
    // navigates to the next view with a 500ms delay before advancing.
    // We loop until the localStorage flag is set (proves onDestroyStarted fired).
    const MAX_CLICKS = 15; // Safety limit — tour has 7 steps
    for (let i = 0; i < MAX_CLICKS; i++) {
      // Check if tour already completed
      const done = await sharedPage.evaluate(
        () => localStorage.getItem('sempkm_demo_tour_done') === '1'
      );
      if (done) break;

      // Find and click the Next or Done button (Driver.js uses these classes)
      const nextBtn = sharedPage.locator(
        '.driver-popover-next-btn, .driver-popover-done-btn'
      );
      await nextBtn.waitFor({ state: 'visible', timeout: 10_000 });
      await nextBtn.click();

      // Wait for the 500ms navigation delay + DOM update between steps
      await sharedPage.waitForTimeout(1000);
    }

    // Wait for localStorage completion flag — proves all 7 steps ran
    // (flag is only set in the onDestroyStarted callback after Done is clicked)
    await sharedPage.waitForFunction(
      () => localStorage.getItem('sempkm_demo_tour_done') === '1',
      null,
      { timeout: 30_000 }
    );

    // Verify the flag is set
    const tourDone = await sharedPage.evaluate(
      () => localStorage.getItem('sempkm_demo_tour_done')
    );
    expect(tourDone).toBe('1');
  });

  // ── DEMO-06: CTA banner visible after tour completion ───────────

  test('CTA banner is visible after tour completion', async () => {
    // The CTA banner appears via the sempkm:demo-tour-done event listener
    // which calls showDemoCta() with a 500ms setTimeout
    const ctaBanner = sharedPage.locator('#demo-cta-banner');
    await expect(ctaBanner).toBeVisible({ timeout: 10_000 });

    // Verify the banner contains the expected content
    await expect(ctaBanner.locator('.demo-cta-text strong')).toContainText('SemPKM');
    await expect(ctaBanner.locator('.demo-cta-button')).toContainText('Get Started');

    // Verify the Get Started link points to the GitHub repo
    const ctaLink = ctaBanner.locator('.demo-cta-button');
    await expect(ctaLink).toHaveAttribute('href', /github\.com/);
  });

  // ── DEMO-05: Demo dashboard renders with content ────────────────

  test('demo dashboard renders with content', async () => {
    // Open the demo dashboard tab via the workspace API
    await sharedPage.evaluate(
      (id) => {
        if (typeof (window as any).SemPKM.openDashboardTab === 'function') {
          (window as any).SemPKM.openDashboardTab(id, 'Demo Dashboard');
        }
      },
      DEMO_DASHBOARD_ID
    );

    // Wait for the dashboard tab to become active — look for the dashboard
    // content area which loads an iframe or inline content
    // The dashboard panel renders inside the dockview editor area
    await sharedPage.waitForSelector(
      `[data-testid="workspace"] iframe[src*="dashboard/${DEMO_DASHBOARD_ID}"], ` +
      `[data-testid="workspace"] .dashboard-container, ` +
      `[data-testid="workspace"] .dashboard-content`,
      { timeout: 15_000 }
    );

    // Verify dashboard has rendered content — either an iframe loaded or
    // dashboard blocks are present
    const dashboardFrame = sharedPage.locator(
      `iframe[src*="dashboard/${DEMO_DASHBOARD_ID}"]`
    );
    const dashboardContainer = sharedPage.locator('.dashboard-container, .dashboard-content');

    // At least one of these should be visible
    const frameVisible = await dashboardFrame.isVisible().catch(() => false);
    const containerVisible = await dashboardContainer.first().isVisible().catch(() => false);
    expect(frameVisible || containerVisible).toBeTruthy();

    // If it's an iframe, verify it loaded successfully (not empty/error)
    if (frameVisible) {
      const frameSrc = await dashboardFrame.getAttribute('src');
      expect(frameSrc).toContain(DEMO_DASHBOARD_ID);
    }
  });

  // ── Quality gate: No unhandled JS errors ────────────────────────

  test('no unhandled JavaScript errors during full flow', async () => {
    // Filter out known non-critical errors if any
    const criticalErrors = pageErrors.filter(
      (err) => !err.message.includes('ResizeObserver loop')
    );

    if (criticalErrors.length > 0) {
      console.error('Page errors captured during demo flow:');
      criticalErrors.forEach((err) => console.error(`  - ${err.message}`));
    }

    expect(criticalErrors).toHaveLength(0);
  });
});
