/**
 * Edge Creation E2E Tests
 *
 * Tests creating relationships between objects via the command API,
 * and verifying edges appear in the relations panel.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Edge (Relationship) Creation', () => {
  test('create edge between two seed objects via API', async ({ ownerPage, ownerSessionToken }) => {
    const context = ownerPage.context();
    const api = await context.request;

    // Create an edge from the architecture note to the event sourcing concept
    const resp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'edge.create',
        params: {
          source: SEED.notes.architecture.iri,
          target: SEED.concepts.eventSourcing.iri,
          predicate: 'http://purl.org/dc/terms/subject',
        },
      },
    });

    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.results.length).toBe(1);
    expect(data.event_iri).toBeTruthy();
  });

  test('edge appears in relations panel', async ({ ownerPage }) => {
    const noteIri = SEED.notes.architecture.iri;

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector(SEL.workspace.container, { timeout: 15000 });

    // Load the object to view it
    await ownerPage.evaluate((iri) => {
      if (typeof (window as any).SemPKM.openTab === 'function') {
        (window as any).SemPKM.openTab(iri, 'Architecture Decision');
      }
    }, noteIri);

    // Wait for the object tab to load first
    await ownerPage.waitForSelector('.object-tab', { timeout: 20000 });

    // The relations panel is loaded async by workspace-layout.js onDidActivePanelChange.
    // Give a short delay for the tab activation event to fire, then explicitly
    // trigger a refresh in case the initial one raced or was missed.
    await ownerPage.waitForTimeout(1000);
    await ownerPage.evaluate((iri) => {
      if (typeof (window as any).SemPKM.refreshRightPaneSection === 'function') {
        (window as any).SemPKM.refreshRightPaneSection(iri, 'relations');
      }
    }, noteIri);

    // Wait for the relations-panel to render (appears after async fetch completes)
    await ownerPage.waitForSelector('#relations-content .relations-panel', { timeout: 20000 });

    // Verify outbound section exists (the edge created in previous test should show)
    const relationsContent = ownerPage.locator('#relations-content');
    await expect(relationsContent).toContainText('Outbound', { timeout: 10000 });
  });

  test('create edge between newly created objects', async ({ ownerPage, ownerSessionToken }) => {
    const context = ownerPage.context();
    const api = await context.request;

    // Create two objects
    const batchResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: [
        {
          command: 'object.create',
          params: {
            type: 'Person',
            properties: { 'http://xmlns.com/foaf/0.1/name': 'Edge Test Person' },
          },
        },
        {
          command: 'object.create',
          params: {
            type: 'Project',
            properties: { 'http://purl.org/dc/terms/title': 'Edge Test Project' },
          },
        },
      ],
    });

    expect(batchResp.ok()).toBeTruthy();
    const batchData = await batchResp.json();
    const personIri = batchData.results[0].iri;
    const projectIri = batchData.results[1].iri;

    // Create an edge between them
    const edgeResp = await api.post(`${BASE_URL}/api/commands`, {
      headers: { Cookie: `sempkm_session=${ownerSessionToken}` },
      data: {
        command: 'edge.create',
        params: {
          source: projectIri,
          target: personIri,
          predicate: 'http://purl.org/dc/terms/contributor',
        },
      },
    });

    expect(edgeResp.ok()).toBeTruthy();
    const edgeData = await edgeResp.json();
    expect(edgeData.results[0].command).toBe('edge.create');
  });
});
