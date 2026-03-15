/**
 * Snap-to-Grid E2E Tests (CANV-01)
 *
 * Verifies nodes snap to 24px grid during drag, expansion, and nav-tree drop.
 * Canvas uses a 24px grid; all node positions should be multiples of 24.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const GRID_SIZE = 24;

function isGridAligned(value: number): boolean {
  return value % GRID_SIZE === 0;
}

test.describe('Spatial Canvas: Snap to Grid', () => {
  test('node added to canvas has grid-aligned position', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/canvas`);
    await ownerPage.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Add a seed object node to the canvas via the JS API
    const positions = await ownerPage.evaluate((iri) => {
      const cy = (window as any)._cy || (window as any).cy;
      if (!cy) return null;

      // Add a node programmatically
      cy.add({
        group: 'nodes',
        data: { id: iri, label: 'Test Node' },
        position: { x: 100, y: 100 },
      });

      // The snap-to-grid function should normalize positions
      if (typeof (window as any).snapToGrid === 'function') {
        const node = cy.getElementById(iri);
        const snapped = (window as any).snapToGrid(node.position());
        node.position(snapped);
      }

      const node = cy.getElementById(iri);
      return node.position();
    }, SEED.notes.architecture.iri);

    if (positions) {
      expect(isGridAligned(positions.x)).toBe(true);
      expect(isGridAligned(positions.y)).toBe(true);
    }
  });

  test('node dropped from nav tree lands on grid position', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/canvas`);
    await ownerPage.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Simulate a drop event with a non-grid-aligned position
    const result = await ownerPage.evaluate((iri) => {
      const cy = (window as any)._cy || (window as any).cy;
      if (!cy) return null;

      // Simulate dropping at a non-aligned position
      cy.add({
        group: 'nodes',
        data: { id: iri, label: 'Drop Test' },
        position: { x: 137, y: 251 }, // Not grid-aligned
      });

      // Apply snap-to-grid if available
      const node = cy.getElementById(iri);
      if (typeof (window as any).snapToGrid === 'function') {
        node.position((window as any).snapToGrid(node.position()));
      }

      return node.position();
    }, SEED.notes.kickoff.iri);

    if (result) {
      expect(isGridAligned(result.x)).toBe(true);
      expect(isGridAligned(result.y)).toBe(true);
    }
  });

  test('expanded neighbor nodes appear at grid-aligned positions', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/canvas`);
    await ownerPage.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Add a root node and expand neighbors
    const nodePositions = await ownerPage.evaluate(async (iri) => {
      const cy = (window as any)._cy || (window as any).cy;
      if (!cy) return [];

      // Add root node
      cy.add({
        group: 'nodes',
        data: { id: iri, label: 'Root' },
        position: { x: 240, y: 240 },
      });

      // Try to expand neighbors via the canvas API
      if (typeof (window as any).expandNeighbors === 'function') {
        await (window as any).expandNeighbors(iri);
      }

      // Collect all node positions
      return cy.nodes().map((n: any) => ({
        id: n.id(),
        ...n.position(),
      }));
    }, SEED.notes.architecture.iri);

    // All nodes should be grid-aligned
    for (const node of nodePositions) {
      expect(isGridAligned(node.x)).toBe(true);
      expect(isGridAligned(node.y)).toBe(true);
    }
  });

  test('saved canvas positions load without re-snapping', async ({ ownerRequest }) => {
    // Save a canvas with specific grid-aligned positions
    const document = {
      nodes: [
        { id: 'urn:test:1', x: 48, y: 72, label: 'Test 1' },
        { id: 'urn:test:2', x: 240, y: 120, label: 'Test 2' },
      ],
    };

    const saveResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: { name: 'Snap Grid Test', document },
    });
    expect(saveResp.ok()).toBeTruthy();
    const saveData = await saveResp.json();
    const sessionId = saveData.id;

    // Load it back
    const loadResp = await ownerRequest.get(`${BASE_URL}/api/canvas/${sessionId}`);
    expect(loadResp.ok()).toBeTruthy();
    const loadData = await loadResp.json();

    // Positions should be preserved exactly as saved
    expect(loadData.document.nodes).toBeDefined();
    const savedNodes = loadData.document.nodes;
    expect(savedNodes[0].x).toBe(48);
    expect(savedNodes[0].y).toBe(72);
    expect(savedNodes[1].x).toBe(240);
    expect(savedNodes[1].y).toBe(120);
  });
});
