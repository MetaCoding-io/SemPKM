/**
 * Spatial Canvas Property Flip E2E Tests
 *
 * Tests the /api/canvas/properties endpoint and the UI flip button that
 * toggles between markdown body and SHACL-derived property table.
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

test.describe('Spatial Canvas: Property Flip', () => {

  // ========== API-level tests ==========

  test('API: properties endpoint returns data for valid IRI, 400 for invalid', async ({ ownerRequest }) => {
    // --- Valid IRI — should return 200 with properties array and type_label ---
    const validResp = await ownerRequest.get(
      `${BASE_URL}/api/canvas/properties?iri=${encodeURIComponent(SEED.notes.architecture.iri)}`,
    );
    expect(validResp.ok()).toBeTruthy();
    const data = await validResp.json();
    expect(data.properties).toBeDefined();
    expect(Array.isArray(data.properties)).toBe(true);
    expect(data.properties.length).toBeGreaterThan(0);
    expect(typeof data.type_label).toBe('string');
    expect(data.type_label.length).toBeGreaterThan(0);

    // Verify property shape — each should have name and values/value
    const firstProp = data.properties[0];
    expect(firstProp.name).toBeTruthy();

    // --- Another valid IRI (concept) — also returns data ---
    const conceptResp = await ownerRequest.get(
      `${BASE_URL}/api/canvas/properties?iri=${encodeURIComponent(SEED.concepts.eventSourcing.iri)}`,
    );
    expect(conceptResp.ok()).toBeTruthy();
    const conceptData = await conceptResp.json();
    expect(Array.isArray(conceptData.properties)).toBe(true);
    expect(typeof conceptData.type_label).toBe('string');

    // --- Invalid IRI (no iri param) — should return 4xx ---
    const noIriResp = await ownerRequest.get(`${BASE_URL}/api/canvas/properties`);
    expect(noIriResp.status()).toBeGreaterThanOrEqual(400);
    expect(noIriResp.status()).toBeLessThan(500);

    // --- Invalid IRI (empty) — should return 400 ---
    const emptyIriResp = await ownerRequest.get(`${BASE_URL}/api/canvas/properties?iri=`);
    expect(emptyIriResp.status()).toBe(400);
  });

  // ========== UI tests ==========

  test('UI: flip button toggle, property table, showProperties persistence, backward compat', async ({ ownerPage }) => {
    await openCanvas(ownerPage);

    // ========== PART 1: Import a node and verify flip button exists ==========

    await ownerPage.evaluate((iri) => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({
        nodes: [
          { id: iri, title: 'Architecture', uri: iri, x: 120, y: 120 },
        ],
        edges: [],
      });
    }, SEED.notes.architecture.iri);

    // Wait for node to render
    const nodeSelector = `.spatial-node[data-node-id="${SEED.notes.architecture.iri}"]`;
    await ownerPage.waitForSelector(nodeSelector, { timeout: 5000 });

    // Wait for flip button to appear (renderNodes may take a moment)
    const flipBtnSelector = `${nodeSelector} .spatial-node-flip`;
    await ownerPage.waitForSelector(flipBtnSelector, { timeout: 5000 });

    // Initially should show markdown body, not property table
    const initialState = await ownerPage.evaluate((iri) => {
      const node = document.querySelector(`.spatial-node[data-node-id="${iri}"]`);
      return {
        hasMarkdown: !!node?.querySelector('.spatial-node-markdown'),
        hasProperties: !!node?.querySelector('.spatial-node-properties'),
      };
    }, SEED.notes.architecture.iri);
    expect(initialState.hasMarkdown).toBe(true);
    expect(initialState.hasProperties).toBe(false);

    // ========== PART 2: Click flip — property table appears ==========

    await ownerPage.click(flipBtnSelector);

    // Wait for the property table to appear (fetch + render)
    await ownerPage.waitForFunction((iri) => {
      const node = document.querySelector(`.spatial-node[data-node-id="${iri}"]`);
      return !!node?.querySelector('.spatial-node-properties');
    }, SEED.notes.architecture.iri, { timeout: 10000 });

    // Verify property table has content
    const flippedState = await ownerPage.evaluate((iri) => {
      const node = document.querySelector(`.spatial-node[data-node-id="${iri}"]`);
      const props = node?.querySelector('.spatial-node-properties');
      const typeHeader = props?.querySelector('.prop-type-header');
      const propRows = props?.querySelectorAll('.prop-row');
      const flipBtn = node?.querySelector('.spatial-node-flip');
      return {
        hasProperties: !!props,
        typeLabel: typeHeader?.textContent || null,
        propRowCount: propRows?.length || 0,
        isFlippedClass: flipBtn?.classList.contains('is-flipped') || false,
      };
    }, SEED.notes.architecture.iri);

    expect(flippedState.hasProperties).toBe(true);
    expect(flippedState.typeLabel).toBeTruthy();
    expect(flippedState.propRowCount).toBeGreaterThan(0);
    expect(flippedState.isFlippedClass).toBe(true);

    // Verify exportState reflects showProperties: true
    const exportedFlipped = await ownerPage.evaluate((iri) => {
      const state = (window as any).SemPKMCanvas.exportState();
      const node = state.nodes.find((n: any) => n.id === iri);
      return { showProperties: node?.showProperties };
    }, SEED.notes.architecture.iri);
    expect(exportedFlipped.showProperties).toBe(true);

    // ========== PART 3: Click flip again — markdown body returns ==========

    await ownerPage.click(flipBtnSelector);

    // Wait for property table to disappear and markdown to return
    await ownerPage.waitForFunction((iri) => {
      const node = document.querySelector(`.spatial-node[data-node-id="${iri}"]`);
      return !!node?.querySelector('.spatial-node-markdown') && !node?.querySelector('.spatial-node-properties');
    }, SEED.notes.architecture.iri, { timeout: 5000 });

    // Verify exportState reflects showProperties gone or false
    const exportedUnflipped = await ownerPage.evaluate((iri) => {
      const state = (window as any).SemPKMCanvas.exportState();
      const node = state.nodes.find((n: any) => n.id === iri);
      return { showProperties: node?.showProperties, hasKey: 'showProperties' in (node || {}) };
    }, SEED.notes.architecture.iri);
    // showProperties should be absent or false in exported state
    expect(!exportedUnflipped.showProperties).toBe(true);

    // ========== PART 4: Persistence — import with showProperties: true ==========

    await ownerPage.evaluate((iri) => {
      const canvas = (window as any).SemPKMCanvas;
      canvas.importState({
        nodes: [
          { id: iri, title: 'Architecture', uri: iri, x: 120, y: 120, showProperties: true },
        ],
        edges: [],
      });
    }, SEED.notes.architecture.iri);

    // Property table should be fetched and rendered for the flipped node
    await ownerPage.waitForFunction((iri) => {
      const node = document.querySelector(`.spatial-node[data-node-id="${iri}"]`);
      return !!node?.querySelector('.spatial-node-properties');
    }, SEED.notes.architecture.iri, { timeout: 10000 });

    const persistedState = await ownerPage.evaluate((iri) => {
      const node = document.querySelector(`.spatial-node[data-node-id="${iri}"]`);
      const flipBtn = node?.querySelector('.spatial-node-flip');
      return {
        hasProperties: !!node?.querySelector('.spatial-node-properties'),
        isFlippedClass: flipBtn?.classList.contains('is-flipped') || false,
      };
    }, SEED.notes.architecture.iri);
    expect(persistedState.hasProperties).toBe(true);
    expect(persistedState.isFlippedClass).toBe(true);

    // ========== PART 5: Backward compatibility — no showProperties field ==========

    const compatResult = await ownerPage.evaluate((iri) => {
      const canvas = (window as any).SemPKMCanvas;
      // Import a node without showProperties — should default to markdown body
      canvas.importState({
        nodes: [
          { id: iri, title: 'Old Style Node', uri: iri, x: 120, y: 120 },
        ],
        edges: [],
      });
      const node = document.querySelector(`.spatial-node[data-node-id="${iri}"]`);
      return {
        hasMarkdown: !!node?.querySelector('.spatial-node-markdown'),
        hasProperties: !!node?.querySelector('.spatial-node-properties'),
        noErrors: true, // If we got here without throwing, no JS errors
      };
    }, SEED.concepts.eventSourcing.iri);

    expect(compatResult.hasMarkdown).toBe(true);
    expect(compatResult.hasProperties).toBe(false);
    expect(compatResult.noErrors).toBe(true);
  });
});
