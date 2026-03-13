/**
 * Event Undo & Event Log Detail E2E Tests
 *
 * Tests:
 * - Event undo via POST /browser/events/{event_iri}/undo (compensating events)
 * - Event detail via GET /browser/events/{event_iri}/detail (diff HTML partial)
 * - Event log UI: event row display and detail expansion via Diff button
 *
 * Requires: Docker test stack on port 3901, seed data installed.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('Event Undo API', () => {
  test('undo an object.create event reverts the object and returns correct responses', async ({
    ownerRequest,
  }) => {
    // --- Round-trip: create → verify exists → undo → verify gone ---

    // Create an object
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Undo Test Note' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const objectIri = createData.results[0].iri;
    const eventIri = createData.event_iri;
    expect(eventIri).toBeTruthy();

    // Verify object exists
    const checkResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: { query: `ASK FROM <urn:sempkm:current> { <${objectIri}> ?p ?o }` },
    });
    expect((await checkResp.json()).boolean).toBe(true);

    // Undo the event
    const undoResp = await ownerRequest.post(
      `${BASE_URL}/browser/events/${encodeURIComponent(eventIri)}/undo`,
    );
    expect(undoResp.ok()).toBeTruthy();
    const undoData = await undoResp.json();
    expect(undoData.status).toBe('ok');

    // Verify the object is reverted/removed
    const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: { query: `ASK FROM <urn:sempkm:current> { <${objectIri}> ?p ?o }` },
    });
    expect((await verifyResp.json()).boolean).toBe(false);

    // --- Negative case: undo nonexistent event returns 404 ---
    const badUndoResp = await ownerRequest.post(
      `${BASE_URL}/browser/events/${encodeURIComponent('urn:sempkm:event:nonexistent-99999')}/undo`,
    );
    expect(badUndoResp.status()).toBe(404);
    const badData = await badUndoResp.json();
    expect(badData.error).toBeTruthy();
  });
});

test.describe('Event Detail API', () => {
  test('event detail returns diff content for create and patch events', async ({
    ownerRequest,
  }) => {
    // --- Test 1: object.create event detail ---
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'Detail Test Note' },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const createEventIri = createData.event_iri;
    const objectIri = createData.results[0].iri;

    // Fetch event detail for create event
    const createDetailResp = await ownerRequest.get(
      `${BASE_URL}/browser/events/${encodeURIComponent(createEventIri)}/detail`,
    );
    expect(createDetailResp.ok()).toBeTruthy();
    const createHtml = await createDetailResp.text();
    expect(createHtml.length).toBeGreaterThan(0);
    // Should contain the diff panel structure
    expect(createHtml).toContain('event-diff-panel');
    // For object.create, should show created triples
    expect(createHtml).toMatch(/Detail Test Note|diff-create|title/i);

    // --- Test 2: nonexistent event returns error HTML ---
    const badDetailResp = await ownerRequest.get(
      `${BASE_URL}/browser/events/${encodeURIComponent('urn:sempkm:event:nonexistent-99999')}/detail`,
    );
    expect(badDetailResp.ok()).toBeTruthy(); // returns 200 with error HTML
    const badHtml = await badDetailResp.text();
    expect(badHtml).toContain('Event not found');

    // --- Test 3: object.patch event shows before/after diff ---
    const patchResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.patch',
        params: {
          iri: objectIri,
          properties: { 'http://purl.org/dc/terms/title': 'Patched Detail Note' },
        },
      },
    });
    expect(patchResp.ok()).toBeTruthy();
    const patchEventIri = (await patchResp.json()).event_iri;
    expect(patchEventIri).toBeTruthy();

    const patchDetailResp = await ownerRequest.get(
      `${BASE_URL}/browser/events/${encodeURIComponent(patchEventIri)}/detail`,
    );
    expect(patchDetailResp.ok()).toBeTruthy();
    const patchHtml = await patchDetailResp.text();
    expect(patchHtml).toContain('event-diff-panel');
    // Patch events show before/after diff with property changes
    expect(patchHtml).toMatch(/title|Patched Detail Note/i);
  });
});

test.describe('Event Log UI', () => {
  test('event log panel shows events and Diff button expands detail', async ({ ownerPage }) => {
    // Create an object via API to ensure a fresh event exists
    const apiResp = await ownerPage.request.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TYPES.Note,
          properties: { 'http://purl.org/dc/terms/title': 'UI Event Test Note' },
        },
      },
    });
    expect(apiResp.ok()).toBeTruthy();

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Open bottom panel — call toggleBottomPanel directly for reliability
    await ownerPage.waitForFunction(
      () => typeof (window as any).toggleBottomPanel === 'function',
      { timeout: 10000 },
    );
    await ownerPage.evaluate(() => (window as any).toggleBottomPanel());
    await waitForIdle(ownerPage);

    // Wait for bottom panel to have a non-zero rendered height
    await ownerPage.waitForFunction(
      () => {
        const panel = document.getElementById('bottom-panel');
        if (!panel) return false;
        const rect = panel.getBoundingClientRect();
        return rect.height > 10;
      },
      { timeout: 5000 },
    );

    // Click EVENT LOG tab — use force in case of any layout overlap
    const eventLogTab = ownerPage.locator('.panel-tab[data-panel="event-log"]');
    await eventLogTab.click({ force: true });
    await waitForIdle(ownerPage);

    // Wait for event rows to load via htmx
    const eventRows = ownerPage.locator('.event-row-wrapper');
    await expect(eventRows.first()).toBeVisible({ timeout: 10000 });

    // Verify we have at least one event row
    const count = await eventRows.count();
    expect(count).toBeGreaterThan(0);

    // Each event row should have an op badge
    const firstRow = eventRows.first();
    await expect(firstRow.locator('.event-op-badge')).toBeVisible();

    // Verify action buttons exist on the row
    const diffBtn = firstRow.locator('.event-btn-diff');
    await expect(diffBtn).toBeVisible();

    // Click the "Diff" button to expand detail (loads via htmx)
    const isDiffEnabled = await diffBtn.isEnabled();
    if (isDiffEnabled) {
      await diffBtn.click();
      await waitForIdle(ownerPage);

      // The diff content loads into the event-diff-container
      const diffContainer = firstRow.locator('.event-diff-container');
      await expect(diffContainer.locator('.event-diff-panel')).toBeVisible({ timeout: 10000 });

      // Verify the close button exists in the diff panel
      await expect(diffContainer.locator('.event-diff-close')).toBeVisible();
    }
  });
});
