/**
 * Screenshot capture for the persona walkthroughs ("A Day in the Graph").
 *
 * Drives the real Driver.js chapters registered in tutorials.js and captures
 * the picker plus representative steps of Alice's and Maya's days.
 *
 * Prerequisites:
 *   - Test stack running with the Research Mental Model installed
 *     (POST /api/models/install {"path": "/app/models/research"}) — Maya's
 *     chapters open Research seed objects.
 *
 * Run with:
 *   npx playwright test tests/screenshots/walkthroughs-capture.spec.ts --project=screenshots
 *
 * Output lands in e2e/screenshots/ as 24-…/43-… PNGs (light + dark for the
 * picker and chapter card, light for the in-tour steps).
 */
import { test, expect, type Page } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import path from 'path';

const SCREENSHOTS_DIR = path.resolve(__dirname, '../../screenshots');
const VIEWPORT = { width: 1440, height: 900 };

function shot(name: string) {
  return path.join(SCREENSHOTS_DIR, name);
}

async function setTheme(page: Page, theme: 'light' | 'dark') {
  await page.evaluate((t) => {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('sempkm_theme', t);
  }, theme);
  await page.waitForTimeout(300);
}

async function screenshotBoth(page: Page, basePath: string) {
  await setTheme(page, 'light');
  await page.screenshot({ path: basePath, fullPage: false });
  await setTheme(page, 'dark');
  await page.screenshot({ path: basePath.replace(/\.png$/, '-dark.png'), fullPage: false });
  await setTheme(page, 'light');
}

async function openWorkspace(page: Page) {
  await page.setViewportSize(VIEWPORT);
  await page.goto('/browser/');
  await waitForWorkspace(page);
  await waitForIdle(page);
  await setTheme(page, 'light');
  await page.waitForTimeout(1200);
}

async function openDocsTab(page: Page) {
  await page.evaluate(() => {
    const w = window as any;
    if (typeof w.openDocsTab === 'function') w.openDocsTab();
  });
  await waitForIdle(page);
  const picker = page.locator('#docs-walkthroughs .wt-picker');
  await expect(picker).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(600);
  return picker;
}

/** Start a chapter via the public API and wait for its chapter card. */
async function startChapter(page: Page, persona: string, chapter: string) {
  await page.evaluate(
    ([p, c]) => (window as any).SemPKM.startWalkthrough(p, c),
    [persona, chapter],
  );
  const popover = page.locator('.driver-popover');
  await expect(popover).toBeVisible({ timeout: 10000 });
  await page.waitForTimeout(500);
  return popover;
}

/** Advance the running tour and let navigation + highlight settle. */
async function next(page: Page, settleMs = 1600) {
  await page.locator('.driver-popover-next-btn').click();
  await page.waitForTimeout(settleMs);
  await waitForIdle(page).catch(() => undefined);
  await page.waitForTimeout(400);
}

async function endTour(page: Page) {
  await page.keyboard.press('Escape');
  await expect(page.locator('.driver-popover')).toBeHidden({ timeout: 5000 });
  await page.waitForTimeout(300);
}

test.describe('Persona walkthrough screenshots', () => {
  test.describe.configure({ mode: 'serial' });

  test('24 — walkthrough picker (Alice selected, fresh)', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await page.evaluate(() => {
      localStorage.removeItem('sempkm_walkthrough_progress');
      localStorage.removeItem('sempkm_walkthrough_persona');
    });
    const picker = await openDocsTab(page);
    await picker.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await screenshotBoth(page, shot('24-walkthrough-picker.png'));

    // Maya tab
    await picker.locator('[data-wt-persona="maya"]').click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: shot('25-walkthrough-picker-maya.png') });
    await picker.locator('[data-wt-persona="alice"]').click();
  });

  test('26 — Alice: chapter card, 9:02 capture, 9:15 "Give it a type"', async ({ ownerPage: page }) => {
    await openWorkspace(page);

    // 9:02 — the capture chapter opens the type picker (htmx-gated step)
    await startChapter(page, 'alice', 'capture');
    await next(page, 800);
    await next(page, 1800);
    await expect(page.locator('.type-picker')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: shot('44-walkthrough-alice-capture-type-picker.png') });
    await endTour(page);

    await startChapter(page, 'alice', 'type');
    await screenshotBoth(page, shot('26-walkthrough-alice-chapter-card.png'));
    await next(page);
    await page.screenshot({ path: shot('27-walkthrough-alice-typed-object.png') });
    await next(page, 800);
    await page.screenshot({ path: shot('28-walkthrough-alice-edit-toggle.png') });
    await endTour(page);
  });

  test('29 — Alice: 11:30 relations and inference', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await startChapter(page, 'alice', 'connect');
    await next(page);
    await page.screenshot({ path: shot('29-walkthrough-alice-relations.png') });
    await next(page);
    await page.screenshot({ path: shot('30-walkthrough-alice-inference.png') });
    await endTour(page);
  });

  test('31 — Alice: 14:00 table, kanban, graph', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await startChapter(page, 'alice', 'views');
    await next(page, 2200);
    await page.screenshot({ path: shot('31-walkthrough-alice-table.png') });
    await next(page, 2200);
    await page.screenshot({ path: shot('32-walkthrough-alice-kanban.png') });
    await next(page, 2600);
    await page.screenshot({ path: shot('33-walkthrough-alice-graph.png') });
    await endTour(page);
  });

  test('34 — Alice: 16:45 lint and 18:00 event log', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await startChapter(page, 'alice', 'validate');
    await next(page, 2200);
    await page.screenshot({ path: shot('34-walkthrough-alice-lint.png') });
    await endTour(page);

    await startChapter(page, 'alice', 'trust');
    await next(page, 2200);
    await page.screenshot({ path: shot('35-walkthrough-alice-event-log.png') });
    await next(page, 600);
    await page.screenshot({ path: shot('36-walkthrough-alice-day-done.png') });
    await endTour(page);
  });

  test('37 — Maya: claims, debate graph, SPARQL', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    await startChapter(page, 'maya', 'claims');
    await screenshotBoth(page, shot('37-walkthrough-maya-chapter-card.png'));
    await next(page);
    await page.screenshot({ path: shot('38-walkthrough-maya-claim.png') });
    await next(page, 800);
    await page.screenshot({ path: shot('39-walkthrough-maya-evidence.png') });
    await endTour(page);

    await startChapter(page, 'maya', 'debate');
    await next(page, 2600);
    await page.screenshot({ path: shot('40-walkthrough-maya-graph.png') });
    await endTour(page);

    await startChapter(page, 'maya', 'query');
    await next(page, 2200);
    await page.screenshot({ path: shot('41-walkthrough-maya-sparql.png') });
    await endTour(page);
  });

  test('42 — picker with progress ticks', async ({ ownerPage: page }) => {
    await openWorkspace(page);
    // Each test gets a fresh browser context, so complete a few chapters here
    // (progress is marked when a chapter's last step is reached).
    await page.evaluate(() => localStorage.removeItem('sempkm_walkthrough_progress'));
    for (const [persona, chapter, steps] of [
      ['alice', 'type', 2], ['alice', 'connect', 2], ['alice', 'trust', 2], ['maya', 'debate', 1],
    ] as const) {
      await startChapter(page, persona, chapter);
      for (let i = 0; i < steps; i++) await next(page, 1200);
      await endTour(page);
    }
    const picker = await openDocsTab(page);
    await picker.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await page.screenshot({ path: shot('42-walkthrough-picker-progress.png') });
    await picker.locator('[data-wt-persona="maya"]').click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: shot('43-walkthrough-picker-progress-maya.png') });
  });
});
