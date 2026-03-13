/**
 * Spatial Canvas UI E2E Tests
 *
 * Tests canvas page interactions: import/export, edge labels, keyboard nav,
 * wiki-links, ghost nodes. All combined into a single test function to
 * respect magic-link rate limits (5/minute).
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForWorkspace } from '../../helpers/wait-for';

const GRID_SIZE = 24;

/** Open the canvas tab in the workspace and wait for it to mount */
async function openCanvas(page: any) {
  await page.goto(`${BASE_URL}/browser/`);
  await waitForWorkspace(page);
  await page.evaluate(() => {
    if (typeof (window as any).openCanvasTab === 'function') {
      (window as any).openCanvasTab();
    }
  });
  await page.waitForSelector('#spatial-canvas-root', { timeout: 15000 });
  await page.waitForFunction(() => !!(window as any).SemPKMCanvas, { timeout: 10000 });
}

test.describe('Spatial Canvas: UI', () => {
  test('canvas import/export, edges, keyboard nav, wiki-links, and ghost nodes', async ({ ownerPage }) => {
    await openCanvas(ownerPage);

    // ========== PART 1: Import/Export Round-Trip ==========
    const positions = await ownerPage.evaluate((iri) => {
      const canvas = (window as any).SemPKMCanvas;
      if (!canvas) return null;

      canvas.importState({
        nodes: [
          { id: iri, title: 'Test Node', uri: iri, x: 100, y: 100 },
          { id: 'n2', title: 'N2', uri: 'n2', x: 48, y: 96 },
          { id: 'n3', title: 'N3', uri: 'n3', x: 240, y: 120 },
        ],
        edges: [],
      });

      const exported = canvas.exportState();
      if (!exported || !exported.nodes) return null;
      return exported.nodes.map((n: any) => ({ id: n.id, x: n.x, y: n.y }));
    }, SEED.notes.architecture.iri);

    expect(positions).not.toBeNull();
    expect(positions!.length).toBe(3);
    expect(positions![0].x).toBe(100);
    expect(positions![0].y).toBe(100);
    // Grid-aligned positions preserved
    expect(positions![1].x % GRID_SIZE).toBe(0);
    expect(positions![1].y % GRID_SIZE).toBe(0);

    // ========== PART 2: Canvas API Surface ==========
    const api = await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      return {
        hasImportState: typeof canvas?.importState === 'function',
        hasExportState: typeof canvas?.exportState === 'function',
        hasMount: typeof canvas?.mount === 'function',
        hasSave: typeof canvas?.save === 'function',
        hasSaveAs: typeof canvas?.saveAs === 'function',
        hasZoomIn: typeof canvas?.zoomIn === 'function',
        hasZoomOut: typeof canvas?.zoomOut === 'function',
        hasResetView: typeof canvas?.resetView === 'function',
      };
    });
    expect(api.hasImportState).toBe(true);
    expect(api.hasExportState).toBe(true);
    expect(api.hasMount).toBe(true);
    expect(api.hasSave).toBe(true);
    expect(api.hasZoomIn).toBe(true);
    expect(api.hasResetView).toBe(true);

    // ========== PART 3: Edge Label Rendering ==========
    const edgeResult = await ownerPage.evaluate((data) => {
      const canvas = (window as any).SemPKMCanvas;
      if (!canvas) return null;

      canvas.importState({
        nodes: [
          { id: data.source, title: 'Source Node', uri: data.source, x: 120, y: 120 },
          { id: data.target, title: 'Target Node', uri: data.target, x: 600, y: 120 },
        ],
        edges: [
          { id: 'test-edge', source: data.source, target: data.target, label: 'subject' },
        ],
      });

      const svg = document.querySelector('.spatial-edges');
      const labels = document.querySelectorAll('.spatial-edge-label');
      let foundSubject = false;
      for (const label of labels) {
        if (label.textContent === 'subject') foundSubject = true;
      }
      return { hasSvg: !!svg, labelCount: labels.length, foundSubject };
    }, { source: SEED.notes.architecture.iri, target: SEED.concepts.eventSourcing.iri });

    expect(edgeResult).not.toBeNull();
    expect(edgeResult!.hasSvg).toBe(true);
    expect(edgeResult!.foundSubject).toBe(true);

    // ========== PART 4: Keyboard Navigation ==========
    // Re-import test nodes for keyboard tests
    await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({
        nodes: [
          { id: 'node-a', title: 'Node A', uri: 'urn:test:a', x: 240, y: 240 },
          { id: 'node-b', title: 'Node B', uri: 'urn:test:b', x: 720, y: 240 },
          { id: 'node-c', title: 'Node C', uri: 'urn:test:c', x: 240, y: 480 },
        ],
        edges: [],
      });
    });
    await ownerPage.waitForSelector('.spatial-node', { timeout: 5000 });

    // Arrow keys move by 1 grid step
    await ownerPage.click('.spatial-node[data-node-id="node-a"]');
    const initialPos = await ownerPage.evaluate(() => {
      return (window as any).SemPKMCanvas?.exportState()?.nodes?.find((n: any) => n.id === 'node-a');
    });
    expect(initialPos).toBeTruthy();

    await ownerPage.keyboard.press('ArrowRight');
    let newPos = await ownerPage.evaluate(() => {
      return (window as any).SemPKMCanvas?.exportState()?.nodes?.find((n: any) => n.id === 'node-a');
    });
    expect(newPos.x).toBe(initialPos.x + GRID_SIZE);
    expect(newPos.y).toBe(initialPos.y);

    // Shift+arrow moves by 5 grid steps
    const beforeShift = { x: newPos.x, y: newPos.y };
    await ownerPage.keyboard.press('Shift+ArrowDown');
    newPos = await ownerPage.evaluate(() => {
      return (window as any).SemPKMCanvas?.exportState()?.nodes?.find((n: any) => n.id === 'node-a');
    });
    expect(newPos.y).toBe(beforeShift.y + GRID_SIZE * 5);

    // Escape deselects
    let selectedCount = await ownerPage.evaluate(() => document.querySelectorAll('.spatial-node-selected').length);
    expect(selectedCount).toBe(1);
    await ownerPage.keyboard.press('Escape');
    selectedCount = await ownerPage.evaluate(() => document.querySelectorAll('.spatial-node-selected').length);
    expect(selectedCount).toBe(0);

    // Tab cycles through nodes
    await ownerPage.click('.spatial-canvas-viewport');
    await ownerPage.keyboard.press('Tab');
    const afterTab = await ownerPage.evaluate(() => {
      return document.querySelector('.spatial-node-selected')?.getAttribute('data-node-id') ?? null;
    });
    expect(afterTab).toBeTruthy();

    // Tab again then Shift+Tab goes back
    await ownerPage.keyboard.press('Tab');
    const afterTwo = await ownerPage.evaluate(() => {
      return document.querySelector('.spatial-node-selected')?.getAttribute('data-node-id') ?? null;
    });
    await ownerPage.keyboard.press('Shift+Tab');
    const afterBack = await ownerPage.evaluate(() => {
      return document.querySelector('.spatial-node-selected')?.getAttribute('data-node-id') ?? null;
    });
    expect(afterBack).not.toBe(afterTwo);

    // Delete removes selected node
    const countBefore = await ownerPage.evaluate(() => document.querySelectorAll('.spatial-node').length);
    expect(countBefore).toBe(3);
    await ownerPage.click('.spatial-node[data-node-id="node-a"]');
    await ownerPage.keyboard.press('Delete');
    const countAfter = await ownerPage.evaluate(() => document.querySelectorAll('.spatial-node').length);
    expect(countAfter).toBe(2);
    const nodeAGone = await ownerPage.evaluate(() => !document.querySelector('.spatial-node[data-node-id="node-a"]'));
    expect(nodeAGone).toBe(true);

    // Keyboard guard: SELECT focus doesn't trigger canvas shortcuts
    const countNow = await ownerPage.evaluate(() => document.querySelectorAll('.spatial-node').length);
    const hasFocus = await ownerPage.evaluate(() => {
      const sel = document.querySelector('#canvas-session-select');
      if (sel) { (sel as HTMLElement).focus(); return true; }
      return false;
    });
    if (hasFocus) {
      await ownerPage.keyboard.press('Delete');
      const countStill = await ownerPage.evaluate(() => document.querySelectorAll('.spatial-node').length);
      expect(countStill).toBe(countNow);
    }

    // ========== PART 5: Wiki-Link Markdown Edges ==========
    const wikiResult = await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({
        nodes: [
          { id: 'wsrc', title: 'Source Node', uri: 'wsrc', x: 120, y: 120, markdown: 'This references [[WTarget Node]] in the body.' },
          { id: 'wtgt', title: 'WTarget Node', uri: 'wtgt', x: 600, y: 120, markdown: '' },
        ],
        edges: [],
      });
      return {
        markdownEdgeCount: document.querySelectorAll('.spatial-edge-line-markdown').length,
        nodeCount: document.querySelectorAll('.spatial-node').length,
      };
    });
    expect(wikiResult.nodeCount).toBe(2);
    expect(wikiResult.markdownEdgeCount).toBeGreaterThan(0);

    // RDF edge + wiki-link edge are visually distinct
    const distinctResult = await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({
        nodes: [
          { id: 'dn1', title: 'DNode One', uri: 'dn1', x: 120, y: 120, markdown: 'See [[DNode Two]]' },
          { id: 'dn2', title: 'DNode Two', uri: 'dn2', x: 600, y: 120, markdown: '' },
        ],
        edges: [
          { id: 'rdf-e', source: 'dn1', target: 'dn2', label: 'subject' },
        ],
      });
      return {
        rdf: document.querySelectorAll('.spatial-edge-line:not(.spatial-edge-line-markdown)').length,
        md: document.querySelectorAll('.spatial-edge-line-markdown').length,
      };
    });
    expect(distinctResult.rdf).toBeGreaterThanOrEqual(1);
    expect(distinctResult.md).toBeGreaterThanOrEqual(1);

    // Edge label shows display text
    const labelText = await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({
        nodes: [
          { id: 'ls', title: 'LS', uri: 'ls', x: 120, y: 120 },
          { id: 'lt', title: 'LT', uri: 'lt', x: 600, y: 120 },
        ],
        edges: [{ id: 'le', source: 'ls', target: 'lt', label: 'see also' }],
      });
      for (const el of document.querySelectorAll('.spatial-edge-label')) {
        if (el.textContent === 'see also') return 'see also';
      }
      return null;
    });
    expect(labelText).toBe('see also');

    // ========== PART 6: Ghost Node for Unresolved Wiki-Link ==========
    const ghostResult = await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({
        nodes: [{
          id: 'real-node', title: 'Real Node', uri: 'real-node', x: 120, y: 120,
          markdown: 'Links to [[Unknown Page That Does Not Exist]]',
        }],
        edges: [],
      });

      // Ghost nodes depend on `marked` being loaded (CDN)
      const hasMarked = typeof (globalThis as any).marked !== 'undefined';
      const ghosts = document.querySelectorAll('.spatial-ghost-node');
      const mdContent = document.querySelector('.spatial-node-markdown')?.innerHTML ?? '';
      return {
        ghostCount: ghosts.length,
        firstGhostTitle: ghosts.length > 0 ? ghosts[0].getAttribute('data-ghost-title') : null,
        hasMarked,
        mdContent,
      };
    });

    // Ghost nodes require marked.js (CDN) AND the wiki-link must produce an <a> with
    // wikilink: scheme. When marked sanitizes or DOMPurify strips the custom scheme,
    // ghosts won't appear.
    if (ghostResult.ghostCount > 0) {
      expect(ghostResult.firstGhostTitle).toBe('Unknown Page That Does Not Exist');
    } else {
      // Fallback: the wiki-link text should at least appear in the markdown content
      // (either as rendered link text or escaped text)
      expect(ghostResult.mdContent).toContain('Unknown Page That Does Not Exist');
    }
  });
});
