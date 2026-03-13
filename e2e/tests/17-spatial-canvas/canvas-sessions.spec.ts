/**
 * Canvas Sessions E2E Tests
 *
 * Tests canvas session save/load via POST /api/canvas/sessions,
 * GET /api/canvas/{id}, and subgraph loading via GET /api/canvas/subgraph.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';

test.describe('Spatial Canvas: Sessions', () => {
  test('create a canvas session via API', async ({ ownerRequest }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: {
        name: 'Test Session',
        document: {
          nodes: [
            { id: SEED.notes.architecture.iri, x: 120, y: 120, label: 'Architecture' },
            { id: SEED.concepts.eventSourcing.iri, x: 360, y: 120, label: 'Event Sourcing' },
          ],
          edges: [],
        },
      },
    });
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.id).toBeTruthy();
    expect(data.name).toBe('Test Session');
  });

  test('list canvas sessions', async ({ ownerRequest }) => {
    // Ensure at least one session exists
    await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: { name: 'List Test Session', document: { nodes: [] } },
    });

    const resp = await ownerRequest.get(`${BASE_URL}/api/canvas/sessions/list`);
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.sessions).toBeDefined();
    expect(Array.isArray(data.sessions)).toBe(true);
    expect(data.sessions.length).toBeGreaterThan(0);
  });

  test('load a saved canvas session by ID', async ({ ownerRequest }) => {
    // Create a session
    const createResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: {
        name: 'Load Test Session',
        document: {
          nodes: [
            { id: 'urn:test:load-1', x: 48, y: 96, label: 'Load Node' },
          ],
        },
      },
    });
    const { id: sessionId } = await createResp.json();

    // Load it back
    const loadResp = await ownerRequest.get(`${BASE_URL}/api/canvas/${sessionId}`);
    expect(loadResp.ok()).toBeTruthy();
    const loadData = await loadResp.json();
    expect(loadData.canvas_id).toBe(sessionId);
    expect(loadData.document).toBeDefined();
    expect(loadData.document.nodes).toBeDefined();
    expect(loadData.document.nodes[0].id).toBe('urn:test:load-1');
  });

  test('update an existing canvas session', async ({ ownerRequest }) => {
    // Create
    const createResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: { name: 'Update Test', document: { nodes: [] } },
    });
    const { id: sessionId } = await createResp.json();

    // Update with new document
    const updateResp = await ownerRequest.put(`${BASE_URL}/api/canvas/${sessionId}`, {
      data: {
        document: {
          nodes: [
            { id: 'urn:test:updated', x: 240, y: 240, label: 'Updated Node' },
          ],
        },
      },
    });
    expect(updateResp.ok()).toBeTruthy();

    // Verify update persisted
    const loadResp = await ownerRequest.get(`${BASE_URL}/api/canvas/${sessionId}`);
    const loadData = await loadResp.json();
    expect(loadData.document.nodes[0].id).toBe('urn:test:updated');
  });

  test('delete a canvas session', async ({ ownerRequest }) => {
    // Create
    const createResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: { name: 'Delete Test', document: { nodes: [] } },
    });
    const { id: sessionId } = await createResp.json();

    // Delete
    const deleteResp = await ownerRequest.delete(`${BASE_URL}/api/canvas/sessions/${sessionId}`);
    expect(deleteResp.ok()).toBeTruthy();

    // Verify it's gone (should 404)
    const loadResp = await ownerRequest.get(`${BASE_URL}/api/canvas/${sessionId}`);
    expect(loadResp.status()).toBe(404);
  });

  test('subgraph endpoint returns neighbors for a root URI', async ({ ownerRequest }) => {
    const resp = await ownerRequest.get(
      `${BASE_URL}/api/canvas/subgraph?root_uri=${encodeURIComponent(SEED.notes.architecture.iri)}&depth=1`,
    );
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();

    // Subgraph should return nodes and/or edges
    expect(data).toBeDefined();
    // Response should have some structure (nodes, edges, or items)
    expect(typeof data).toBe('object');
  });

  test('activate a canvas session', async ({ ownerRequest }) => {
    // Create
    const createResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: { name: 'Activate Test', document: { nodes: [] } },
    });
    const { id: sessionId } = await createResp.json();

    // Activate
    const activateResp = await ownerRequest.put(`${BASE_URL}/api/canvas/sessions/${sessionId}/activate`);
    expect(activateResp.ok()).toBeTruthy();

    // Verify it's active in the session list
    const listResp = await ownerRequest.get(`${BASE_URL}/api/canvas/sessions/list`);
    const listData = await listResp.json();
    expect(listData.active_session_id).toBe(sessionId);
  });
});
