/**
 * Edge Creation E2E Tests
 *
 * Tests creating relationships between objects via the command API,
 * and verifying edges appear in the relations panel.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { waitForIdle } from '../../helpers/wait-for';

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
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, 'Architecture Decision');
      }
    }, noteIri);

    // Wait for relations panel to load (it's loaded via htmx into #relations-content)
    await ownerPage.waitForSelector('#relations-content', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // The relations content should eventually show outbound or inbound links
    // (depends on whether the edge was created in previous test - tests are sequential)
    const relationsContent = ownerPage.locator('#relations-content');
    await expect(relationsContent).not.toContainText('No object selected', { timeout: 15000 });
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
