/**
 * Edge Deletion E2E Tests
 *
 * Tests edge deletion via POST /browser/edge/delete.
 * Creates an edge between objects, deletes it, and verifies it is gone.
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S10
 *
 * edge.create produces a first-class edge resource with its own IRI
 * (sempkm:source, sempkm:target, sempkm:predicate triples).
 * edge/delete expects { subject, predicate, target } to find and remove
 * the edge resource and any direct triples.
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S03
=======
>>>>>>> gsd/M003/S10
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';

test.describe('Edge Deletion', () => {
  test('delete an edge via API and verify it is removed', async ({ ownerRequest }) => {
    // Create two objects
    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: [
        { command: 'object.create', params: { type: TYPES.Note, properties: { 'http://purl.org/dc/terms/title': 'Edge Del Source' } } },
        { command: 'object.create', params: { type: TYPES.Concept, properties: { 'http://www.w3.org/2004/02/skos/core#prefLabel': 'Edge Del Target' } } },
      ],
    });
    expect(createResp.ok()).toBeTruthy();
    const { results } = await createResp.json();
    const sourceIri = results[0].iri;
    const targetIri = results[1].iri;

<<<<<<< HEAD
<<<<<<< HEAD
    // Create an edge (produces a first-class edge resource)
=======
    // Create an edge
>>>>>>> gsd/M003/S03
=======
    // Create an edge (produces a first-class edge resource)
>>>>>>> gsd/M003/S10
    const edgeResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'edge.create',
        params: {
          source: sourceIri,
          target: targetIri,
          predicate: 'http://purl.org/dc/terms/subject',
        },
      },
    });
    expect(edgeResp.ok()).toBeTruthy();
<<<<<<< HEAD
<<<<<<< HEAD
    const edgeData = await edgeResp.json();
    const edgeIri = edgeData.results[0].iri;
    expect(edgeIri).toBeTruthy();

    // Verify edge resource exists via SPARQL (check the resource's structural triples)
    const checkResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `ASK FROM <urn:sempkm:current> {
          <${edgeIri}> a <urn:sempkm:Edge> ;
                       <urn:sempkm:source> <${sourceIri}> ;
                       <urn:sempkm:target> <${targetIri}> ;
                       <urn:sempkm:predicate> <http://purl.org/dc/terms/subject> .
        }`,
=======
=======
    const edgeData = await edgeResp.json();
    const edgeIri = edgeData.results[0].iri;
    expect(edgeIri).toBeTruthy();
>>>>>>> gsd/M003/S10

    // Verify edge resource exists via SPARQL (check the resource's structural triples)
    const checkResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
<<<<<<< HEAD
        query: `ASK FROM <urn:sempkm:current> { <${sourceIri}> <http://purl.org/dc/terms/subject> <${targetIri}> }`,
>>>>>>> gsd/M003/S03
=======
        query: `ASK FROM <urn:sempkm:current> {
          <${edgeIri}> a <urn:sempkm:Edge> ;
                       <urn:sempkm:source> <${sourceIri}> ;
                       <urn:sempkm:target> <${targetIri}> ;
                       <urn:sempkm:predicate> <http://purl.org/dc/terms/subject> .
        }`,
>>>>>>> gsd/M003/S10
      },
    });
    const checkData = await checkResp.json();
    expect(checkData.boolean).toBe(true);

<<<<<<< HEAD
<<<<<<< HEAD
    // Delete the edge (endpoint expects subject/predicate/target)
    const deleteResp = await ownerRequest.post(`${BASE_URL}/browser/edge/delete`, {
      data: {
        subject: sourceIri,
=======
    // Delete the edge
    const deleteResp = await ownerRequest.post(`${BASE_URL}/browser/edge/delete`, {
      data: {
        source: sourceIri,
>>>>>>> gsd/M003/S03
=======
    // Delete the edge (endpoint expects subject/predicate/target)
    const deleteResp = await ownerRequest.post(`${BASE_URL}/browser/edge/delete`, {
      data: {
        subject: sourceIri,
>>>>>>> gsd/M003/S10
        target: targetIri,
        predicate: 'http://purl.org/dc/terms/subject',
      },
    });
    expect(deleteResp.ok()).toBeTruthy();

<<<<<<< HEAD
<<<<<<< HEAD
    // Verify edge resource is gone
    const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `ASK FROM <urn:sempkm:current> { <${edgeIri}> ?p ?o }`,
=======
    // Verify edge is gone
    const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `ASK FROM <urn:sempkm:current> { <${sourceIri}> <http://purl.org/dc/terms/subject> <${targetIri}> }`,
>>>>>>> gsd/M003/S03
=======
    // Verify edge resource is gone
    const verifyResp = await ownerRequest.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `ASK FROM <urn:sempkm:current> { <${edgeIri}> ?p ?o }`,
>>>>>>> gsd/M003/S10
      },
    });
    const verifyData = await verifyResp.json();
    expect(verifyData.boolean).toBe(false);
  });
});
