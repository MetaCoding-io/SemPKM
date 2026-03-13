/**
 * Spatial Canvas API E2E Tests
 *
 * Tests canvas API endpoints via ownerRequest (no browser needed):
 * - Session CRUD: create, list, load, update, activate, delete
 * - Subgraph expansion: /api/canvas/subgraph
 * - Batch edge discovery: /api/canvas/batch-edges
 * - Wiki-link resolution: /api/canvas/resolve-wikilinks
 * - Node body: /api/canvas/body
 *
 * Combined into a single test function to respect magic-link rate limits.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';

test.describe('Spatial Canvas: API', () => {
  test('session lifecycle, subgraph, batch-edges, resolve-wikilinks, body', async ({ ownerRequest }) => {
    const ts = Date.now();

    // ========== SESSION CRUD ==========

    // CREATE
    const createResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: {
        name: 'Lifecycle Test ' + ts,
        document: {
          nodes: [
            { id: SEED.notes.architecture.iri, x: 120, y: 120, title: 'Architecture', uri: SEED.notes.architecture.iri },
            { id: SEED.concepts.eventSourcing.iri, x: 360, y: 120, title: 'Event Sourcing', uri: SEED.concepts.eventSourcing.iri },
          ],
          edges: [],
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    expect(createData.session_id).toBeTruthy();
    const sessionId = createData.session_id;

    // LIST
    const listResp = await ownerRequest.get(`${BASE_URL}/api/canvas/sessions/list`);
    expect(listResp.ok()).toBeTruthy();
    const listData = await listResp.json();
    expect(listData.sessions).toBeDefined();
    expect(Array.isArray(listData.sessions)).toBe(true);
    expect(listData.sessions.find((s: any) => s.id === sessionId)).toBeTruthy();

    // LOAD
    const loadResp = await ownerRequest.get(`${BASE_URL}/api/canvas/${sessionId}`);
    expect(loadResp.ok()).toBeTruthy();
    const loadData = await loadResp.json();
    expect(loadData.canvas_id).toBe(sessionId);
    expect(loadData.document.nodes.length).toBe(2);
    expect(loadData.document.nodes[0].id).toBe(SEED.notes.architecture.iri);

    // UPDATE
    const updateResp = await ownerRequest.put(`${BASE_URL}/api/canvas/${sessionId}`, {
      data: {
        document: {
          nodes: [{ id: 'urn:test:updated', x: 240, y: 240, title: 'Updated', uri: 'urn:test:updated' }],
          edges: [],
        },
      },
    });
    expect(updateResp.ok()).toBeTruthy();
    const reloadData = await (await ownerRequest.get(`${BASE_URL}/api/canvas/${sessionId}`)).json();
    expect(reloadData.document.nodes[0].id).toBe('urn:test:updated');

    // ACTIVATE
    const activateResp = await ownerRequest.put(`${BASE_URL}/api/canvas/sessions/${sessionId}/activate`);
    expect(activateResp.ok()).toBeTruthy();
    const listData2 = await (await ownerRequest.get(`${BASE_URL}/api/canvas/sessions/list`)).json();
    expect(listData2.active_session_id).toBe(sessionId);

    // Position persistence (grid alignment test)
    const snapDoc = {
      nodes: [
        { id: 'urn:test:snap-1', x: 48, y: 72, title: 'T1', uri: 'urn:test:snap-1' },
        { id: 'urn:test:snap-2', x: 240, y: 120, title: 'T2', uri: 'urn:test:snap-2' },
      ],
      edges: [],
    };
    const snapResp = await ownerRequest.post(`${BASE_URL}/api/canvas/sessions`, {
      data: { name: 'Snap Test ' + ts, document: snapDoc },
    });
    const snapId = (await snapResp.json()).session_id;
    const snapLoad = await (await ownerRequest.get(`${BASE_URL}/api/canvas/${snapId}`)).json();
    expect(snapLoad.document.nodes[0].x).toBe(48);
    expect(snapLoad.document.nodes[0].y).toBe(72);

    // DELETE
    const deleteResp = await ownerRequest.delete(`${BASE_URL}/api/canvas/sessions/${sessionId}`);
    expect(deleteResp.ok()).toBeTruthy();
    // After deletion, GET returns 200 with empty document (graceful canvas design)
    const goneResp = await ownerRequest.get(`${BASE_URL}/api/canvas/${sessionId}`);
    expect(goneResp.ok()).toBeTruthy();
    const goneData = await goneResp.json();
    expect(goneData.document.nodes).toEqual([]);
    // Session should no longer appear in list
    const listAfterDelete = await (await ownerRequest.get(`${BASE_URL}/api/canvas/sessions/list`)).json();
    expect(listAfterDelete.sessions.find((s: any) => s.id === sessionId)).toBeFalsy();

    // ========== SUBGRAPH ==========
    const subResp = await ownerRequest.get(
      `${BASE_URL}/api/canvas/subgraph?root_uri=${encodeURIComponent(SEED.notes.architecture.iri)}&depth=1`,
    );
    expect(subResp.ok()).toBeTruthy();
    const subData = await subResp.json();
    expect(subData.root_uri).toBe(SEED.notes.architecture.iri);
    expect(subData.depth).toBe(1);
    expect(Array.isArray(subData.nodes)).toBe(true);
    expect(Array.isArray(subData.edges)).toBe(true);

    // ========== BATCH EDGES ==========
    const batchResp = await ownerRequest.post(`${BASE_URL}/api/canvas/batch-edges`, {
      data: { iris: [SEED.notes.architecture.iri, SEED.concepts.eventSourcing.iri] },
    });
    expect(batchResp.ok()).toBeTruthy();
    const batchData = await batchResp.json();
    expect(Array.isArray(batchData.edges)).toBe(true);
    if (batchData.edges.length > 0) {
      for (const edge of batchData.edges) {
        // Every edge should have a predicate_label (may be a local name fallback)
        expect(edge.predicate_label).toBeTruthy();
        // Edge response shape should include source, target, predicate
        expect(edge.source).toBeTruthy();
        expect(edge.target).toBeTruthy();
        expect(edge.predicate).toBeTruthy();
      }
    }

    // ========== RESOLVE WIKILINKS ==========
    const resolveResp = await ownerRequest.post(`${BASE_URL}/api/canvas/resolve-wikilinks`, {
      data: { titles: [SEED.notes.architecture.title, 'Nonexistent Page XYZ'] },
    });
    expect(resolveResp.ok()).toBeTruthy();
    const resolveData = await resolveResp.json();
    expect(resolveData.resolved[SEED.notes.architecture.title]).toBe(SEED.notes.architecture.iri);
    expect(resolveData.resolved['Nonexistent Page XYZ']).toBeNull();

    // ========== BODY ==========
    const bodyResp = await ownerRequest.get(
      `${BASE_URL}/api/canvas/body?iri=${encodeURIComponent(SEED.notes.architecture.iri)}`,
    );
    expect(bodyResp.ok()).toBeTruthy();
    const bodyData = await bodyResp.json();
    expect(bodyData.iri).toBe(SEED.notes.architecture.iri);
    expect(typeof bodyData.body).toBe('string');
  });
});
