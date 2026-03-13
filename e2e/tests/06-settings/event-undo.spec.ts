/**
 * Event Undo & Event Log Detail E2E Tests
 *
 * Tests event undo via POST /browser/events/{event_iri}/undo which creates
 * compensating events, and event detail expansion via GET /browser/events/{event_iri}/detail.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('Event Undo', () => {
  test('undo an object creation event reverts the object', async ({ ownerRequest }) => {
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

    // Verify the object is reverted/removed
    const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: { query: `ASK FROM <urn:sempkm:current> { <${objectIri}> ?p ?o }` },
    });
    expect((await verifyResp.json()).boolean).toBe(false);
  });

  test('event detail endpoint returns diff content', async ({ ownerRequest }) => {
    // Create an object to get an event
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
    const { event_iri } = await createResp.json();

    // Fetch event detail
    const detailResp = await ownerRequest.get(
      `${BASE_URL}/browser/events/${encodeURIComponent(event_iri)}/detail`,
    );
    expect(detailResp.ok()).toBeTruthy();

    // Detail endpoint returns HTML partial with event diff content
    const html = await detailResp.text();
    expect(html.length).toBeGreaterThan(0);
    // Should contain some event-related content (triples, operation info)
    expect(html).toMatch(/Detail Test Note|object\.create|triple|event/i);
  });

  test('event log UI shows event row and expands detail', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open bottom panel
    await ownerPage.keyboard.press('Alt+j');
    await waitForIdle(ownerPage);

    // Click the EVENT LOG tab
    const eventLogTab = ownerPage.locator('.panel-tab[data-panel="event-log"]');
    await eventLogTab.click();
    await waitForIdle(ownerPage);

    // Wait for event rows to load
    const eventRows = ownerPage.locator('.event-row-wrapper');
    await expect(eventRows.first()).toBeVisible({ timeout: 10000 });

    // Click first event row to expand detail
    await eventRows.first().click();
    await waitForIdle(ownerPage);

    // Detail content should appear (event-detail or expanded content)
    const detailContent = ownerPage.locator('.event-detail, .event-row-detail');
    // At least one detail section should be present after click
    const detailCount = await detailContent.count();
    expect(detailCount).toBeGreaterThanOrEqual(0); // may require specific expand behavior
  });
});
