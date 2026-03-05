/**
 * Graph View E2E Tests
 *
 * Tests the Cytoscape.js graph view: container rendering, data loading,
 * layout switching, and node interaction.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Graph View', () => {
  test('graph view renders Cytoscape container', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const graphSpec = specs.find((s: any) => s.renderer_type === 'graph');

    if (!graphSpec) {
      test.skip();
      return;
    }

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(graphSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'view-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/graph/' + iri, isView: true, isSpecial: true },
          title: 'View',
        });
      }
    }, encodedSpecIri);

    // Wait for graph container
    await ownerPage.waitForSelector(SEL.views.graph, { timeout: 15000 });
    await expect(ownerPage.locator('#cy-container')).toBeVisible();
  });

  test('graph data endpoint returns nodes and edges', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const graphSpec = specs.find((s: any) => s.renderer_type === 'graph');

    if (!graphSpec) {
      test.skip();
      return;
    }

    const encodedSpecIri = encodeURIComponent(graphSpec.spec_iri);
    const dataResp = await api.get(
      `${BASE_URL}/browser/views/graph/${encodedSpecIri}/data`,
      {
        headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      },
    );

    expect(dataResp.ok()).toBeTruthy();
    const data = await dataResp.json();
    expect(data.nodes).toBeDefined();
    expect(Array.isArray(data.nodes)).toBeTruthy();
    expect(data.nodes.length).toBeGreaterThan(0);
  });

  test('graph view has layout picker', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const graphSpec = specs.find((s: any) => s.renderer_type === 'graph');

    if (!graphSpec) {
      test.skip();
      return;
    }

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(graphSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'view-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/graph/' + iri, isView: true, isSpecial: true },
          title: 'View',
        });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector('#layout-picker', { timeout: 15000 });

    // Layout picker should have at least the built-in layouts
    const layoutPicker = ownerPage.locator('#layout-picker');
    const options = layoutPicker.locator('option:not([disabled])');
    const optionCount = await options.count();
    expect(optionCount).toBeGreaterThanOrEqual(3); // fcose, dagre, concentric
  });

  test('graph view has fit button', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const graphSpec = specs.find((s: any) => s.renderer_type === 'graph');

    if (!graphSpec) {
      test.skip();
      return;
    }

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(graphSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'view-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/graph/' + iri, isView: true, isSpecial: true },
          title: 'View',
        });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector('.graph-fit-btn', { timeout: 15000 });
    const fitBtn = ownerPage.locator('.graph-fit-btn');
    await expect(fitBtn).toBeVisible();
    await expect(fitBtn).toContainText('Fit');
  });
});
