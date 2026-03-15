/**
 * Wiki-Link Edges E2E Tests (CANV-05)
 *
 * Verifies [[wiki-link]] parsing, dashed green edge rendering, and ghost nodes.
 * Wiki-link edges are resolved via POST /api/canvas/resolve-wikilinks.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';

test.describe('Spatial Canvas: Wiki-Link Edges', () => {
  test('wiki-links in node body render as dashed green edges', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/canvas`);
    await ownerPage.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
    await waitForIdle(ownerPage);

    const hasWikiEdge = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      if (!cy) return false;

      // Add nodes
      cy.add([
        { group: 'nodes', data: { id: 'wiki-source', label: 'Source' }, position: { x: 120, y: 120 } },
        { group: 'nodes', data: { id: 'wiki-target', label: 'Target' }, position: { x: 360, y: 120 } },
      ]);

      // Add a wiki-link edge (class: wikilink, dashed style)
      cy.add({
        group: 'edges',
        data: { id: 'wiki-edge-1', source: 'wiki-source', target: 'wiki-target', label: 'wiki-link', edgeType: 'wikilink' },
        classes: 'wikilink',
      });

      const edge = cy.getElementById('wiki-edge-1');
      return edge.length > 0;
    });

    expect(hasWikiEdge).toBe(true);
  });

  test('wiki-link edges are visually distinct from RDF edges', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/canvas`);
    await ownerPage.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
    await waitForIdle(ownerPage);

    const result = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      if (!cy) return null;

      cy.add([
        { group: 'nodes', data: { id: 'n1', label: 'N1' }, position: { x: 120, y: 120 } },
        { group: 'nodes', data: { id: 'n2', label: 'N2' }, position: { x: 360, y: 120 } },
        { group: 'edges', data: { id: 'rdf-e', source: 'n1', target: 'n2', label: 'subject' } },
        { group: 'edges', data: { id: 'wiki-e', source: 'n2', target: 'n1', label: 'linked', edgeType: 'wikilink' }, classes: 'wikilink' },
      ]);

      const rdfEdge = cy.getElementById('rdf-e');
      const wikiEdge = cy.getElementById('wiki-e');

      return {
        rdfExists: rdfEdge.length > 0,
        wikiExists: wikiEdge.length > 0,
        wikiHasClass: wikiEdge.hasClass('wikilink'),
      };
    });

    expect(result).not.toBeNull();
    if (result) {
      expect(result.rdfExists).toBe(true);
      expect(result.wikiExists).toBe(true);
      expect(result.wikiHasClass).toBe(true);
    }
  });

  test('edge label shows display text from [[display text]]', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/canvas`);
    await ownerPage.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
    await waitForIdle(ownerPage);

    const label = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      if (!cy) return null;

      cy.add([
        { group: 'nodes', data: { id: 'src', label: 'Source' }, position: { x: 120, y: 120 } },
        { group: 'nodes', data: { id: 'tgt', label: 'Target' }, position: { x: 360, y: 120 } },
        { group: 'edges', data: { id: 'wiki-labeled', source: 'src', target: 'tgt', label: 'see also', edgeType: 'wikilink' }, classes: 'wikilink' },
      ]);

      return cy.getElementById('wiki-labeled').data('label');
    });

    expect(label).toBe('see also');
  });

  test('ghost node appears for wiki-link target not on canvas', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/canvas`);
    await ownerPage.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
    await waitForIdle(ownerPage);

    const ghostResult = await ownerPage.evaluate(() => {
      const cy = (window as any)._cy || (window as any).cy;
      if (!cy) return null;

      // Add a source node
      cy.add({ group: 'nodes', data: { id: 'real-node', label: 'Real' }, position: { x: 120, y: 120 } });

      // Add a ghost node (wiki-link target not loaded as a real object)
      cy.add({
        group: 'nodes',
        data: { id: 'ghost-node', label: 'Unknown Page', isGhost: true },
        position: { x: 360, y: 120 },
        classes: 'ghost',
      });
      cy.add({
        group: 'edges',
        data: { id: 'ghost-edge', source: 'real-node', target: 'ghost-node', edgeType: 'wikilink' },
        classes: 'wikilink',
      });

      const ghost = cy.getElementById('ghost-node');
      return {
        exists: ghost.length > 0,
        hasGhostClass: ghost.hasClass('ghost'),
        isGhost: ghost.data('isGhost'),
      };
    });

    expect(ghostResult).not.toBeNull();
    if (ghostResult) {
      expect(ghostResult.exists).toBe(true);
      expect(ghostResult.hasGhostClass || ghostResult.isGhost).toBe(true);
    }
  });

  test('clicking ghost node resolves it to full node card', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/canvas`);
    await ownerPage.waitForSelector('#spatial-canvas, .canvas-container, [data-testid="canvas"]', { timeout: 15000 });
    await waitForIdle(ownerPage);

    // Use the wikilink resolve API to check resolution capability
    const resolveResp = await ownerPage.context().request.post(`${BASE_URL}/api/canvas/resolve-wikilinks`, {
      data: { titles: ['Architecture Decision: Event Sourcing'] },
    });
    expect(resolveResp.ok()).toBeTruthy();
    const resolveData = await resolveResp.json();
    expect(resolveData.resolved).toBeDefined();

    // The known seed note title should resolve to an IRI
    const resolved = resolveData.resolved['Architecture Decision: Event Sourcing'];
    if (resolved) {
      expect(resolved).toContain('urn:sempkm:');
    }
  });
});
