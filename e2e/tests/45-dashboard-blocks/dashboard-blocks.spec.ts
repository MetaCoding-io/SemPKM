/**
 * Dashboard Block Rendering E2E Tests
 *
 * Verifies that dashboard blocks render with live data:
 * - stat-card: executes SPARQL query, displays numeric count
 * - chart: loads Chart.js from CDN, renders bar chart on canvas
 * - heading: displays configured heading text and subtitle
 * - multiple blocks: all types render simultaneously in one dashboard
 *
 * Each test creates a dashboard via the API, opens it in the workspace
 * via openDashboardTab(), and waits for async block loading (htmx lazy-load
 * → SPARQL fetch → DOM update / Chart.js initialization).
 *
 * Timing: Dashboard blocks load lazily. The stat-card and chart blocks
 * set data-sparql-loaded / data-chart-loaded attributes as dedup guards
 * BEFORE the async fetch starts. Tests must wait for actual content
 * (stat value changes from "…", canvas gets non-zero dimensions) rather
 * than relying on those attributes alone.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
import { openDashboardTab } from '../../helpers/dockview';
import { SEL } from '../../helpers/selectors';

/** Helper: create a dashboard via API, return { id, name }. */
async function createDashboard(
  page: import('@playwright/test').Page,
  sessionToken: string,
  payload: { name: string; layout: string; blocks: any[] },
): Promise<{ id: string; name: string }> {
  const resp = await page.context().request.post(`${BASE_URL}/api/dashboard`, {
    headers: { Cookie: `sempkm_session=${sessionToken}` },
    data: payload,
  });
  expect(resp.ok(), `Dashboard creation failed: ${resp.status()}`).toBeTruthy();
  return resp.json();
}

/** Helper: delete a dashboard via API (best-effort cleanup). */
async function deleteDashboard(
  page: import('@playwright/test').Page,
  sessionToken: string,
  dashboardId: string,
): Promise<void> {
  try {
    await page.context().request.delete(`${BASE_URL}/api/dashboard/${dashboardId}`, {
      headers: { Cookie: `sempkm_session=${sessionToken}` },
    });
  } catch {
    // Best-effort cleanup — don't fail tests on cleanup errors
  }
}

/** Helper: navigate to workspace and open a dashboard tab. */
async function navigateAndOpenDashboard(
  page: import('@playwright/test').Page,
  dashboardId: string,
  dashboardName: string,
) {
  await page.goto(`${BASE_URL}/browser/`);
  await waitForWorkspace(page);
  await openDashboardTab(page, dashboardId, dashboardName);
  // Wait for htmx to finish loading all block fragments
  await waitForIdle(page, 15000);
}

/**
 * Wait for a stat-card's value to be populated with a number.
 * The initial placeholder is "…" (ellipsis). After the SPARQL fetch,
 * it's replaced with the query result (a number) or "Error" / "0".
 */
async function waitForStatCardValue(page: import('@playwright/test').Page, timeoutMs = 15000) {
  await page.waitForFunction(
    (sel) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      const text = (el.textContent || '').trim();
      // Wait until it's no longer the loading placeholder
      return text !== '' && text !== '…' && text !== '\u2026';
    },
    SEL.dashboard.statValue,
    { timeout: timeoutMs },
  );
}

/**
 * Wait for Chart.js to finish rendering on a canvas element.
 * Chart.js 4.x stores the instance accessible via Chart.getChart().
 * Fallback: check the canvas has been drawn on (non-zero data URL).
 */
async function waitForChartRendered(page: import('@playwright/test').Page, timeoutMs = 20000) {
  await page.waitForFunction(
    (sel) => {
      const canvas = document.querySelector(sel) as HTMLCanvasElement | null;
      if (!canvas) return false;
      // Check if Chart.js has populated the canvas
      if (typeof (window as any).Chart?.getChart === 'function') {
        return !!(window as any).Chart.getChart(canvas);
      }
      // Fallback: canvas has been drawn on (data URL is longer than blank)
      try {
        const dataUrl = canvas.toDataURL();
        return dataUrl.length > 500; // Blank canvas is ~100-200 chars
      } catch {
        return false;
      }
    },
    SEL.dashboard.chartCanvas,
    { timeout: timeoutMs },
  );
}

test.describe('Dashboard Block Rendering', () => {
  let dashboardIds: string[] = [];

  test.afterEach(async ({ ownerPage, ownerSessionToken }) => {
    // Clean up any dashboards created during the test
    for (const id of dashboardIds) {
      await deleteDashboard(ownerPage, ownerSessionToken, id);
    }
    dashboardIds = [];
  });

  test('stat-card renders live SPARQL count', async ({ ownerPage, ownerSessionToken }) => {
    // Create dashboard with a stat-card that counts all objects in the current graph
    const dashboard = await createDashboard(ownerPage, ownerSessionToken, {
      name: 'E2E Stat Test',
      layout: 'gridstack',
      blocks: [
        {
          type: 'stat-card',
          config: {
            query: 'SELECT (COUNT(*) AS ?count) WHERE { GRAPH <urn:sempkm:current> { ?s a ?type } }',
            label: 'Total Objects',
            icon: 'database',
            color: '',
          },
          x: 0,
          y: 0,
          w: 4,
          h: 2,
        },
      ],
    });
    dashboardIds.push(dashboard.id);

    await navigateAndOpenDashboard(ownerPage, dashboard.id, dashboard.name);

    // Wait for the stat-card to appear
    const statCard = ownerPage.locator(SEL.dashboard.statCard);
    await expect(statCard).toBeVisible({ timeout: 15000 });

    // Wait for the stat value to be populated (async SPARQL fetch)
    await waitForStatCardValue(ownerPage);

    // Assert the stat value is a number > 0 (seed data has 11+ objects)
    const statValue = ownerPage.locator(SEL.dashboard.statValue);
    const text = await statValue.textContent();
    expect(text).toBeTruthy();
    const numValue = Number(text!.trim());
    expect(numValue).toBeGreaterThan(0);
  });

  test('chart block renders Chart.js visualization', async ({ ownerPage, ownerSessionToken }) => {
    // Create dashboard with a chart block — query returns ?label and ?value columns
    const dashboard = await createDashboard(ownerPage, ownerSessionToken, {
      name: 'E2E Chart Test',
      layout: 'gridstack',
      blocks: [
        {
          type: 'chart',
          config: {
            query:
              'SELECT ?label (COUNT(*) AS ?value) WHERE { GRAPH <urn:sempkm:current> { ?s a ?type } BIND(STRAFTER(STR(?type), "#") AS ?label) } GROUP BY ?label',
            chart_type: 'bar',
            label: 'Objects by Type',
          },
          x: 0,
          y: 0,
          w: 6,
          h: 4,
        },
      ],
    });
    dashboardIds.push(dashboard.id);

    await navigateAndOpenDashboard(ownerPage, dashboard.id, dashboard.name);

    // Wait for the chart block to appear
    const chartBlock = ownerPage.locator(SEL.dashboard.chart);
    await expect(chartBlock).toBeVisible({ timeout: 15000 });

    // Wait for the canvas to exist (Chart.js CDN + SPARQL fetch can be slow)
    const canvas = ownerPage.locator(SEL.dashboard.chartCanvas);
    await expect(canvas).toBeVisible({ timeout: 20000 });

    // Wait for Chart.js to actually render on the canvas
    await waitForChartRendered(ownerPage);

    // Verify the canvas has non-zero dimensions
    const dims = await canvas.evaluate((el: HTMLCanvasElement) => ({
      width: el.width,
      height: el.height,
    }));
    expect(dims.width).toBeGreaterThan(0);
    expect(dims.height).toBeGreaterThan(0);
  });

  test('heading block renders configured text', async ({ ownerPage, ownerSessionToken }) => {
    const dashboard = await createDashboard(ownerPage, ownerSessionToken, {
      name: 'E2E Heading Test',
      layout: 'gridstack',
      blocks: [
        {
          type: 'heading',
          config: {
            text: 'E2E Test Dashboard',
            level: '2',
            subtitle: 'Automated verification',
            align: 'left',
          },
          x: 0,
          y: 0,
          w: 12,
          h: 2,
        },
      ],
    });
    dashboardIds.push(dashboard.id);

    await navigateAndOpenDashboard(ownerPage, dashboard.id, dashboard.name);

    // Wait for the heading block to appear
    const headingBlock = ownerPage.locator(SEL.dashboard.heading);
    await expect(headingBlock).toBeVisible({ timeout: 15000 });

    // Assert h2 with the configured text exists within the heading block
    const h2 = headingBlock.locator('h2');
    await expect(h2).toBeVisible();
    await expect(h2).toHaveText('E2E Test Dashboard');

    // Assert subtitle text is visible
    const subtitle = headingBlock.locator('.heading-subtitle');
    await expect(subtitle).toBeVisible();
    await expect(subtitle).toHaveText('Automated verification');
  });

  test('multiple block types render in one dashboard', async ({ ownerPage, ownerSessionToken }) => {
    // Create a dashboard with stat-card + heading + chart at different positions
    const dashboard = await createDashboard(ownerPage, ownerSessionToken, {
      name: 'E2E Multi-Block Test',
      layout: 'gridstack',
      blocks: [
        {
          type: 'heading',
          config: {
            text: 'Multi-Block Dashboard',
            level: '1',
            subtitle: '',
            align: 'center',
          },
          x: 0,
          y: 0,
          w: 12,
          h: 2,
        },
        {
          type: 'stat-card',
          config: {
            query: 'SELECT (COUNT(*) AS ?count) WHERE { GRAPH <urn:sempkm:current> { ?s a ?type } }',
            label: 'Object Count',
            icon: 'hash',
            color: '',
          },
          x: 0,
          y: 2,
          w: 4,
          h: 2,
        },
        {
          type: 'chart',
          config: {
            query:
              'SELECT ?label (COUNT(*) AS ?value) WHERE { GRAPH <urn:sempkm:current> { ?s a ?type } BIND(STRAFTER(STR(?type), "#") AS ?label) } GROUP BY ?label',
            chart_type: 'bar',
            label: 'Type Distribution',
          },
          x: 4,
          y: 2,
          w: 8,
          h: 4,
        },
      ],
    });
    dashboardIds.push(dashboard.id);

    await navigateAndOpenDashboard(ownerPage, dashboard.id, dashboard.name);

    // Wait for all async blocks to finish loading
    await waitForStatCardValue(ownerPage);
    await waitForChartRendered(ownerPage);

    // Assert all three block types are present simultaneously
    await expect(ownerPage.locator(SEL.dashboard.heading)).toBeVisible();
    await expect(ownerPage.locator(SEL.dashboard.statCard)).toBeVisible();
    await expect(ownerPage.locator(SEL.dashboard.chart)).toBeVisible();

    // Verify heading content
    await expect(ownerPage.locator(`${SEL.dashboard.heading} h1`)).toHaveText('Multi-Block Dashboard');

    // Verify stat-card has a numeric value
    const statText = await ownerPage.locator(SEL.dashboard.statValue).textContent();
    expect(Number(statText!.trim())).toBeGreaterThan(0);

    // Verify chart canvas exists
    await expect(ownerPage.locator(SEL.dashboard.chartCanvas)).toBeVisible();
  });
});
