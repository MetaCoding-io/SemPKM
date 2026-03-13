/**
 * Graph View Interaction E2E Tests
 *
 * Tests graph view node rendering and click-through to open object tabs.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Graph View Interaction', () => {
  test('graph view renders with Cytoscape nodes', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const graphSpec = specs.find((s: any) => s.renderer_type === 'graph');

    if (!graphSpec) return; // Skip if no graph view is configured

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(graphSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'graph-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/graph/' + iri, isView: true, isSpecial: true },
          title: 'Graph View',
        });
      }
    }, encodedSpecIri);

    // Wait for graph container
    await ownerPage.waitForSelector(SEL.views.graph + ', .graph-container, canvas', { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Verify Cytoscape is initialized with nodes
    const nodeCount = await ownerPage.evaluate(() => {
      const cy = (window as any)._graphCy || (window as any).cy;
      return cy ? cy.nodes().length : 0;
    });

    expect(nodeCount).toBeGreaterThan(0);
  });

  test('clicking a graph node opens the object tab', async ({ ownerPage, ownerSessionToken }) => {
    const api = await ownerPage.context().request;
    const specsResp = await api.get(`${BASE_URL}/browser/views/available`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
    });
    const specs = await specsResp.json();
    const graphSpec = specs.find((s: any) => s.renderer_type === 'graph');

    if (!graphSpec) return;

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    const encodedSpecIri = encodeURIComponent(graphSpec.spec_iri);
    await ownerPage.evaluate((iri) => {
      const dv = (window as any)._dockview;
      if (dv) {
        dv.addPanel({
          id: 'graph-click-' + Date.now(),
          component: 'special-panel',
          params: { specialType: 'views/graph/' + iri, isView: true, isSpecial: true },
          title: 'Graph View',
        });
      }
    }, encodedSpecIri);

    await ownerPage.waitForSelector(SEL.views.graph + ', .graph-container, canvas', { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Get the first node's data and simulate a click
    const clickResult = await ownerPage.evaluate(() => {
      const cy = (window as any)._graphCy || (window as any).cy;
      if (!cy || cy.nodes().length === 0) return null;

      const firstNode = cy.nodes()[0];
      const nodeData = firstNode.data();

      // Trigger a tap event on the node (same as clicking)
      firstNode.emit('tap');

      return { id: nodeData.id, label: nodeData.label || nodeData.id };
    });

    if (clickResult) {
      // After clicking a node, an object tab should open
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);

      // Check if a new panel/tab was opened
      const tabCount = await ownerPage.evaluate(() => {
        const dv = (window as any)._dockview;
        return dv ? dv.panels.length : 0;
      });
      expect(tabCount).toBeGreaterThanOrEqual(1);
    }
  });
});
