/**
 * Spatial Canvas Embeds E2E Tests
 *
 * Tests embed node serialization round-trip, X-Embed-Mode header, toolbar
 * picker placement, max-8 enforcement, and mixed regular+embed save/load.
 *
 * Combined into a single test function per group to respect magic-link
 * rate limits (5/minute).
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForWorkspace } from '../../helpers/wait-for';

/** Open the canvas tab and wait for SemPKMCanvas to be available */
async function openCanvas(page: any) {
  await page.goto(`${BASE_URL}/browser/`);
  await waitForWorkspace(page);
  await page.evaluate(() => {
    if (typeof (window as any).SemPKM.openCanvasTab === 'function') {
      (window as any).SemPKM.openCanvasTab();
    }
  });
  await page.waitForSelector('#spatial-canvas-root', { timeout: 15000 });
  await page.waitForFunction(() => !!(window as any).SemPKMCanvas, { timeout: 10000 });
}

test.describe('Spatial Canvas: Embeds', () => {

  // ========== API-level tests ==========

  test('API: embed node round-trip, backward compat, X-Embed-Mode header', async ({ ownerRequest }) => {
    const ts = Date.now();

    // --- Create a session with an embed node ---
    const createResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: {
        name: 'Embed API Test ' + ts,
        document: {
          nodes: [
            {
              id: 'embed-test-1',
              x: 120, y: 120,
              title: 'Table View',
              uri: 'embed:table-view',
              nodeType: 'embed',
              embedConfig: {
                type: 'view',
                id: 'table',
                url: '/browser/views/generic/table?embed=1',
                label: 'Table View',
              },
              width: 400,
              height: 300,
            },
            {
              id: SEED.notes.architecture.iri,
              x: 600, y: 120,
              title: 'Architecture',
              uri: SEED.notes.architecture.iri,
              // Regular node — no nodeType
            },
          ],
          edges: [],
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const { session_id: sessionId } = await createResp.json();

    // --- Load session back, verify embed fields preserved ---
    const loadResp = await ownerRequest.get(`${BASE_URL}/api/canvas/${sessionId}`);
    expect(loadResp.ok()).toBeTruthy();
    const loadData = await loadResp.json();
    const nodes = loadData.document.nodes;

    const embedNode = nodes.find((n: any) => n.id === 'embed-test-1');
    expect(embedNode).toBeTruthy();
    expect(embedNode.nodeType).toBe('embed');
    expect(embedNode.embedConfig).toBeDefined();
    expect(embedNode.embedConfig.type).toBe('view');
    expect(embedNode.embedConfig.id).toBe('table');
    expect(embedNode.embedConfig.url).toBe('/browser/views/generic/table?embed=1');
    expect(embedNode.embedConfig.label).toBe('Table View');
    expect(embedNode.width).toBe(400);
    expect(embedNode.height).toBe(300);

    // Regular node should NOT have nodeType
    const regularNode = nodes.find((n: any) => n.id === SEED.notes.architecture.iri);
    expect(regularNode).toBeTruthy();
    expect(regularNode.nodeType).toBeUndefined();
    expect(regularNode.embedConfig).toBeUndefined();

    // --- Backward compat: session without nodeType fields loads cleanly ---
    const oldStyleResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: {
        name: 'Old Style Test ' + ts,
        document: {
          nodes: [
            { id: 'old-1', x: 48, y: 96, title: 'Old Node', uri: 'urn:test:old' },
          ],
          edges: [],
        },
      },
    });
    expect(oldStyleResp.ok()).toBeTruthy();
    const { session_id: oldId } = await oldStyleResp.json();
    const oldLoad = await (await ownerRequest.get(`${BASE_URL}/api/canvas/${oldId}`)).json();
    const oldNode = oldLoad.document.nodes[0];
    expect(oldNode.nodeType).toBeUndefined();
    expect(oldNode.embedConfig).toBeUndefined();
    expect(oldNode.title).toBe('Old Node');

    // --- X-Embed-Mode header on embed endpoints ---
    const embedResp = await ownerRequest.get(`${BASE_URL}/browser/views/generic/table?embed=1`);
    expect(embedResp.ok()).toBeTruthy();
    const embedModeHeader = embedResp.headers()['x-embed-mode'];
    expect(embedModeHeader).toBe('1');

    // Non-embed request should NOT have the header
    const normalResp = await ownerRequest.get(`${BASE_URL}/browser/views/generic/table`);
    expect(normalResp.ok()).toBeTruthy();
    const normalHeader = normalResp.headers()['x-embed-mode'];
    expect(normalHeader).toBeFalsy();

    // Cleanup
    await ownerRequest.delete(`${BASE_URL}/api/canvas/sessions/${sessionId}`);
    await ownerRequest.delete(`${BASE_URL}/api/canvas/sessions/${oldId}`);
  });

  // ========== UI tests ==========

  test('UI: toolbar picker, embed placement, max-8 enforcement, mixed save/load', async ({ ownerPage }) => {
    await openCanvas(ownerPage);

    // ========== PART 1: Verify Embed toolbar button exists ==========

    const hasEmbedBtn = await ownerPage.evaluate(
      () => !!document.querySelector('.canvas-embed-picker-btn'),
    );
    expect(hasEmbedBtn).toBe(true);

    // ========== PART 2: Click Embed button — picker opens with 3 tabs ==========

    await ownerPage.click('.canvas-embed-picker-btn');
    await ownerPage.waitForSelector('.canvas-embed-picker', { timeout: 5000 });

    const pickerState = await ownerPage.evaluate(() => {
      const picker = document.querySelector('.canvas-embed-picker');
      const tabs = picker?.querySelectorAll('.canvas-embed-picker-tabs button');
      const tabLabels = Array.from(tabs || []).map((t: any) => t.textContent.trim());
      return {
        isVisible: !!picker,
        tabCount: tabs?.length || 0,
        tabLabels,
      };
    });
    expect(pickerState.isVisible).toBe(true);
    expect(pickerState.tabCount).toBe(3);
    expect(pickerState.tabLabels).toContain('Views');
    expect(pickerState.tabLabels).toContain('Dashboards');
    expect(pickerState.tabLabels).toContain('Queries');

    // ========== PART 3: Click Views tab and wait for items, place an embed ==========

    // Views tab should be active by default — wait for items to load
    await ownerPage.waitForFunction(() => {
      const picker = document.querySelector('.canvas-embed-picker');
      const items = picker?.querySelectorAll('.canvas-embed-picker-item');
      return items && items.length > 0;
    }, undefined, { timeout: 10000 });

    // Read the config from the first item and place via JS API (more reliable than click)
    const embedPlaced = await ownerPage.evaluate(() => {
      const picker = document.querySelector('.canvas-embed-picker');
      const item = picker?.querySelector('.canvas-embed-picker-item');
      if (!item) return { placed: false, reason: 'no item' };
      let config;
      try { config = JSON.parse((item as HTMLElement).dataset.config || ''); } catch { return { placed: false, reason: 'bad config' }; }
      const canvas = (window as any).SemPKMCanvas;
      canvas.addEmbed(config, 400, 300);
      return { placed: true, config };
    });
    expect(embedPlaced.placed).toBe(true);

    // Close the picker (it may still be open since we bypassed its click handler)
    await ownerPage.evaluate(() => {
      const picker = document.querySelector('.canvas-embed-picker');
      if (picker) picker.remove();
    });

    // Verify exportState has an embed node
    const afterPlace = await ownerPage.evaluate(() => {
      const state = (window as any).SemPKMCanvas.exportState();
      const embedNodes = state.nodes.filter((n: any) => n.nodeType === 'embed');
      return {
        totalNodes: state.nodes.length,
        embedCount: embedNodes.length,
        firstEmbed: embedNodes[0] || null,
      };
    });
    expect(afterPlace.embedCount).toBeGreaterThanOrEqual(1);
    expect(afterPlace.firstEmbed).not.toBeNull();
    expect(afterPlace.firstEmbed.nodeType).toBe('embed');
    expect(afterPlace.firstEmbed.embedConfig).toBeDefined();
    expect(afterPlace.firstEmbed.embedConfig.type).toBeTruthy();
    expect(afterPlace.firstEmbed.embedConfig.url).toBeTruthy();
    expect(afterPlace.firstEmbed.embedConfig.label).toBeTruthy();

    // ========== PART 4: Max-8 enforcement ==========

    // Clear canvas and add 8 embeds programmatically
    await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({ nodes: [], edges: [] });
    });

    // Add 8 embeds via the public API
    const addResult = await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      const results: boolean[] = [];
      for (let i = 0; i < 8; i++) {
        try {
          canvas.addEmbed(
            {
              type: 'view',
              id: 'table',
              url: '/browser/views/generic/table?embed=1',
              label: 'Embed ' + (i + 1),
            },
            100 + i * 50,
            100,
          );
          results.push(true);
        } catch {
          results.push(false);
        }
      }
      const state = canvas.exportState();
      const embedCount = state.nodes.filter((n: any) => n.nodeType === 'embed').length;
      return { results, embedCount };
    });
    expect(addResult.embedCount).toBe(8);

    // Try adding a 9th — should be rejected
    const ninthResult = await ownerPage.evaluate(() => {
      const canvas = (window as any).SemPKMCanvas;
      const beforeCount = canvas.exportState().nodes.filter((n: any) => n.nodeType === 'embed').length;
      try {
        canvas.addEmbed(
          {
            type: 'view',
            id: 'table',
            url: '/browser/views/generic/table?embed=1',
            label: 'Embed 9 (should fail)',
          },
          600,
          100,
        );
      } catch {
        // rejection may throw or silently skip
      }
      const afterCount = canvas.exportState().nodes.filter((n: any) => n.nodeType === 'embed').length;
      return { beforeCount, afterCount };
    });
    // Count should stay at 8
    expect(ninthResult.afterCount).toBe(8);

    // ========== PART 5: Mixed save/load — regular + embed nodes ==========

    const mixedResult = await ownerPage.evaluate((data) => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({
        nodes: [
          {
            id: data.regularIri1,
            title: 'Architecture',
            uri: data.regularIri1,
            x: 120, y: 120,
          },
          {
            id: data.regularIri2,
            title: 'Event Sourcing',
            uri: data.regularIri2,
            x: 400, y: 120,
          },
          {
            id: 'mixed-embed-1',
            title: 'Table View',
            uri: 'embed:table',
            x: 120, y: 400,
            nodeType: 'embed',
            embedConfig: {
              type: 'view',
              id: 'table',
              url: '/browser/views/generic/table?embed=1',
              label: 'Table View',
            },
            width: 400,
            height: 300,
          },
        ],
        edges: [],
      });

      const state = canvas.exportState();
      const regularNodes = state.nodes.filter((n: any) => !n.nodeType);
      const embedNodes = state.nodes.filter((n: any) => n.nodeType === 'embed');

      return {
        totalNodes: state.nodes.length,
        regularCount: regularNodes.length,
        embedCount: embedNodes.length,
        embedHasConfig: embedNodes.length > 0 && !!embedNodes[0].embedConfig,
        regularHasNoType: regularNodes.every((n: any) => !n.nodeType),
      };
    }, {
      regularIri1: SEED.notes.architecture.iri,
      regularIri2: SEED.concepts.eventSourcing.iri,
    });

    expect(mixedResult.totalNodes).toBe(3);
    expect(mixedResult.regularCount).toBe(2);
    expect(mixedResult.embedCount).toBe(1);
    expect(mixedResult.embedHasConfig).toBe(true);
    expect(mixedResult.regularHasNoType).toBe(true);

    // Verify embed renders in the DOM with an iframe
    const embedDom = await ownerPage.evaluate(() => {
      const embedLayer = document.querySelector('.spatial-canvas-embed-layer');
      const embedEls = embedLayer?.querySelectorAll('[data-embed-type]');
      const iframes = embedLayer?.querySelectorAll('iframe');
      return {
        hasEmbedLayer: !!embedLayer,
        embedElementCount: embedEls?.length || 0,
        iframeCount: iframes?.length || 0,
      };
    });
    expect(embedDom.hasEmbedLayer).toBe(true);
    expect(embedDom.embedElementCount).toBeGreaterThanOrEqual(1);
    expect(embedDom.iframeCount).toBeGreaterThanOrEqual(1);
  });
});
