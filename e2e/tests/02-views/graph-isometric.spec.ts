/**
 * Graph Isometric Layout & Icon Toggle E2E Tests
 *
 * Tests the S02 additions to the graph view:
 * - Isometric 2.5D layout option in the layout picker
 * - CSS 3D perspective transform activation
 * - Lucide SVG icon toggle button and node background-image injection
 * - Combined isometric + icon mode interaction
 *
 * Follows the patterns from graph-view.spec.ts and graph-interaction.spec.ts.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

/** Open a graph view panel in the workspace and wait for Cytoscape to initialise. */
async function openGraphPanel(
  ownerPage: any,
  ownerRequest: any,
): Promise<{ specIri: string; label: string } | null> {
  const specsResp = await ownerRequest.get(`${BASE_URL}/browser/views/available`);
  expect(specsResp.ok()).toBeTruthy();
  const specs = await specsResp.json();
  const graphSpec = specs.find((s: any) => s.renderer_type === 'graph');
  if (!graphSpec) return null;

  await ownerPage.goto(`${BASE_URL}/browser/`);
  await ownerPage.waitForSelector('.workspace-container', { timeout: 15000 });

  await ownerPage.evaluate(
    ({ specIri, label }: { specIri: string; label: string }) => {
      if (typeof (window as any).SemPKM.openViewTab === 'function') {
        (window as any).SemPKM.openViewTab(specIri, label, 'graph');
      }
    },
    { specIri: graphSpec.spec_iri, label: graphSpec.label },
  );

  // Wait for graph container and Cytoscape init
  await ownerPage.waitForSelector('#cy-container', { timeout: 15000 });
  await ownerPage.waitForFunction(
    () => {
      const cy = (window as any).SemPKM._sempkmGraph;
      return cy && cy.nodes().length > 0;
    },
    { timeout: 15000 },
  );

  return { specIri: graphSpec.spec_iri, label: graphSpec.label };
}

test.describe('Graph Isometric Layout & Icon Toggle', () => {
  test('layout picker includes Isometric 2.5D option', async ({
    ownerPage,
    ownerRequest,
  }) => {
    const spec = await openGraphPanel(ownerPage, ownerRequest);
    if (!spec) {
      test.skip();
      return;
    }

    await ownerPage.waitForSelector('#layout-picker', { timeout: 15000 });

    // Find the isometric option in the layout picker
    const isometricOption = ownerPage.locator(
      '#layout-picker option[value="isometric"]',
    );
    await expect(isometricOption).toBeAttached();

    // Verify the label text contains "Isometric"
    const text = await isometricOption.textContent();
    expect(text).toContain('Isometric');
  });

  test('selecting isometric applies CSS 3D transform', async ({
    ownerPage,
    ownerRequest,
  }) => {
    const spec = await openGraphPanel(ownerPage, ownerRequest);
    if (!spec) {
      test.skip();
      return;
    }

    await ownerPage.waitForSelector('#layout-picker', { timeout: 15000 });

    // Select the isometric layout
    await ownerPage.selectOption('#layout-picker', 'isometric');

    // Wait for the fcose layout run + CSS transform to apply
    // The isometric handler runs fcose first, then applies the class on layoutstop
    await ownerPage.waitForTimeout(2000);

    // Verify the wrapper has the isometric-active class
    const wrapper = ownerPage.locator(SEL.views.isometricWrapper);
    await expect(wrapper).toBeAttached();
    await expect(wrapper).toHaveClass(/isometric-active/);

    // Also verify the cy instance flag via JS
    const isActive = await ownerPage.evaluate(() => {
      const cy = (window as any).SemPKM._sempkmGraph;
      return cy ? cy._isometricActive === true : false;
    });
    expect(isActive).toBe(true);
  });

  test('icon toggle button is present and visible', async ({
    ownerPage,
    ownerRequest,
  }) => {
    const spec = await openGraphPanel(ownerPage, ownerRequest);
    if (!spec) {
      test.skip();
      return;
    }

    const iconBtn = ownerPage.locator(SEL.views.iconToggle);
    await expect(iconBtn).toBeVisible({ timeout: 10000 });

    // Button should contain "Icons" text
    await expect(iconBtn).toContainText('Icons');

    // Initially should NOT have .active class (default is shape mode)
    await expect(iconBtn).not.toHaveClass(/active/);
  });

  test('icon toggle activates icon mode on nodes', async ({
    ownerPage,
    ownerRequest,
  }) => {
    const spec = await openGraphPanel(ownerPage, ownerRequest);
    if (!spec) {
      test.skip();
      return;
    }

    // Wait for canvas to be rendered (Cytoscape draws on <canvas>)
    await ownerPage.waitForSelector('#cy-container canvas', { timeout: 15000 });

    const iconBtn = ownerPage.locator(SEL.views.iconToggle);
    await expect(iconBtn).toBeVisible({ timeout: 10000 });

    // Click the icon toggle
    await iconBtn.click();

    // Button should now have .active class
    await expect(iconBtn).toHaveClass(/active/, { timeout: 5000 });

    // Verify the icon mode flag is set via JS
    const iconModeActive = await ownerPage.evaluate(() => {
      // Check either the exposed variable or localStorage
      const stored = localStorage.getItem('sempkm_graph_icon_mode');
      return stored === 'icon';
    });
    expect(iconModeActive).toBe(true);

    // Verify at least one node has a background-image set (Lucide SVG data URI)
    const hasBgImage = await ownerPage.evaluate(() => {
      const cy = (window as any).SemPKM._sempkmGraph;
      if (!cy || cy.nodes().length === 0) return false;
      const bgImg = cy.nodes()[0].style('background-image');
      // background-image could be a string or array depending on Cytoscape version
      if (Array.isArray(bgImg)) return bgImg.length > 0 && bgImg[0] !== 'none';
      return bgImg && bgImg !== 'none' && bgImg !== '';
    });
    expect(hasBgImage).toBe(true);
  });

  test('isometric and icon toggle work together', async ({
    ownerPage,
    ownerRequest,
  }) => {
    const spec = await openGraphPanel(ownerPage, ownerRequest);
    if (!spec) {
      test.skip();
      return;
    }

    await ownerPage.waitForSelector('#layout-picker', { timeout: 15000 });
    await ownerPage.waitForSelector('#cy-container canvas', { timeout: 15000 });

    // Activate isometric layout
    await ownerPage.selectOption('#layout-picker', 'isometric');
    await ownerPage.waitForTimeout(2000);

    // Activate icon mode
    const iconBtn = ownerPage.locator(SEL.views.iconToggle);
    await iconBtn.click();
    await ownerPage.waitForTimeout(500);

    // Both should be active simultaneously
    const wrapper = ownerPage.locator(SEL.views.isometricWrapper);
    await expect(wrapper).toHaveClass(/isometric-active/);
    await expect(iconBtn).toHaveClass(/active/);

    // Verify both JS flags
    const state = await ownerPage.evaluate(() => {
      const cy = (window as any).SemPKM._sempkmGraph;
      return {
        isometric: cy ? cy._isometricActive === true : false,
        iconMode: localStorage.getItem('sempkm_graph_icon_mode') === 'icon',
      };
    });
    expect(state.isometric).toBe(true);
    expect(state.iconMode).toBe(true);
  });
});
