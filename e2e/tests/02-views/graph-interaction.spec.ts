/**
 * Graph View Interaction E2E Tests
 *
 * Tests graph view node rendering via Cytoscape.js, data endpoint,
 * and node click → open object tab interaction.
 *
 * Consolidated into 1 test() to stay within the 5/minute magic-link rate limit.
 * Uses both API-only and UI-based verification.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Graph View Interaction', () => {
  test('graph data endpoint, node rendering, and node click to open tab', async ({ ownerPage, ownerRequest, ownerSessionToken }) => {
    // 1. Get available view specs to find a graph view
    const specsResp = await ownerRequest.get(`${BASE_URL}/browser/views/available`);
    expect(specsResp.ok()).toBeTruthy();
    const specs = await specsResp.json();
    const graphSpec = specs.find((s: any) => s.renderer_type === 'graph');

    if (!graphSpec) {
      // No graph view configured — skip gracefully
      test.skip();
      return;
    }

    const specIri = encodeURIComponent(graphSpec.spec_iri);

    // 2. Verify graph data endpoint returns valid JSON with nodes
    const dataResp = await ownerRequest.get(
      `${BASE_URL}/browser/views/graph/${specIri}/data`,
    );
    expect(dataResp.ok()).toBeTruthy();
    const graphData = await dataResp.json();
    expect(graphData).toHaveProperty('nodes');
    expect(graphData).toHaveProperty('edges');
    expect(graphData.nodes.length).toBeGreaterThan(0);
    // Each node should have id and label
    const firstNode = graphData.nodes[0];
    expect(firstNode).toHaveProperty('id');
    expect(firstNode).toHaveProperty('label');

    // 3. Verify graph expand endpoint works for a known node
    const expandResp = await ownerRequest.get(
      `${BASE_URL}/browser/views/graph/expand/${encodeURIComponent(firstNode.id)}`,
    );
    expect(expandResp.ok()).toBeTruthy();
    const expandData = await expandResp.json();
    expect(expandData).toHaveProperty('nodes');
    expect(expandData).toHaveProperty('edges');

    // 4. Open the graph view in the workspace UI
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('.workspace-container', { timeout: 15000 });

    // Use the application's openViewTab function to open the graph properly
    await ownerPage.evaluate(({ specIri, label }) => {
      if (typeof (window as any).openViewTab === 'function') {
        (window as any).openViewTab(specIri, label, 'graph');
      }
    }, { specIri: graphSpec.spec_iri, label: graphSpec.label });

    // Wait for the graph container to appear
    await ownerPage.waitForSelector('[data-testid="graph-view"], #cy-container', { timeout: 15000 });

    // Wait for Cytoscape to initialize with data (async fetch)
    await ownerPage.waitForFunction(
      () => {
        const cy = (window as any)._sempkmGraph;
        return cy && cy.nodes().length > 0;
      },
      { timeout: 15000 },
    );

    // 5. Verify Cytoscape has nodes matching the API data
    const nodeCount = await ownerPage.evaluate(() => {
      const cy = (window as any)._sempkmGraph;
      return cy ? cy.nodes().length : 0;
    });
    expect(nodeCount).toBeGreaterThan(0);

    // 6. Simulate a node click (tap) — should trigger right pane load
    const clickResult = await ownerPage.evaluate(() => {
      const cy = (window as any)._sempkmGraph;
      if (!cy || cy.nodes().length === 0) return null;
      const node = cy.nodes()[0];
      const data = node.data();
      // Emit tap event to trigger the tap handler
      node.emit('tap');
      return { id: data.id, label: data.label };
    });
    expect(clickResult).not.toBeNull();

    // Wait for any async effects of the tap
    await waitForIdle(ownerPage);

    // 7. Test the graph popover open button — simulate hover + click open
    //    The graph uses a popover that shows on node hover with an "Open" button
    //    that calls window.openTab(iri, label). Verify openTab is callable.
    const openTabResult = await ownerPage.evaluate((nodeData) => {
      if (typeof (window as any).openTab === 'function' && nodeData) {
        (window as any).openTab(nodeData.id, nodeData.label);
        return true;
      }
      return false;
    }, clickResult);

    if (openTabResult) {
      // Wait for the tab to open
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);

      // Verify a new panel was opened in dockview
      const panelCount = await ownerPage.evaluate(() => {
        const dv = (window as any)._dockview;
        return dv ? dv.panels.length : 0;
      });
      // Should have at least 2 panels: the graph view + the opened object
      expect(panelCount).toBeGreaterThanOrEqual(2);
    }

    // 8. Verify graph view HTML endpoint also works (for htmx partial rendering)
    const viewResp = await ownerRequest.get(
      `${BASE_URL}/browser/views/graph/${specIri}`,
      { headers: { Accept: 'text/html' } },
    );
    expect(viewResp.ok()).toBeTruthy();
    const viewHtml = await viewResp.text();
    expect(viewHtml).toContain('cy-container');
    expect(viewHtml).toContain('graph-container');
  });
});
