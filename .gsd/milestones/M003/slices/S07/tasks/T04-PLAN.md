---
estimated_steps: 4
estimated_files: 4
---

# T04: Add unit tests and E2E test for ontology viewer

**Slice:** S07 — Ontology Viewer & Gist Foundation
**Milestone:** M003

## Description

Write the unit and E2E tests that prove the slice delivers at integration level. Unit tests verify SPARQL query construction, batch logic, and service correctness using pure-function testing (no Docker). The E2E test verifies the full user flow: opening the ontology viewer, seeing gist classes in TBox, checking ABox counts, and verifying RBox properties — all against the live Docker Compose stack.

## Steps

1. **Write unit tests in `backend/tests/test_ontology_service.py`** — Pure-function tests (no triplestore needed):
   - **Batch splitting:** `_split_into_batches(triples, batch_size=500)` with 4000 triples → 8 batches, 100 triples → 1 batch, 0 triples → 0 batches, 501 triples → 2 batches (500 + 1)
   - **INSERT DATA generation:** Given a small rdflib Graph (3 triples including a BNode), verify the generated SPARQL contains `GRAPH <urn:sempkm:ontology:gist>`, proper triple serialization, and blank node `_:` syntax
   - **Version check ASK query format:** Verify the ASK query string contains the gist ontology IRI and graph IRI
   - **FROM clause builder:** Given a list of model IDs + gist graph, verify FROM clauses are correctly assembled for TBox/ABox queries
   - **Root class SPARQL shape:** Verify the root class query filters `isIRI(?class)`, excludes blank nodes, handles both `skos:prefLabel` and `rdfs:label`
   - **ABox VALUES query construction:** Given a list of type IRIs, verify the VALUES clause is correctly built
   - **RBox property query shape:** Verify object and datatype property types are both included in VALUES filter

2. **Write E2E test in `e2e/tests/22-ontology/ontology-viewer.spec.ts`** — Against live Docker stack:
   - **Test: opens ontology viewer and shows TBox tree** — open workspace → command palette → "Open: Ontology Viewer" → verify TBox tab is active → verify at least one gist class is visible (e.g., text content containing "Person" or "Task" or "FormattedContent") → expand a gist class node → verify model subclass appears as child (e.g., "Project" under gist:Task or "Note" under gist:FormattedContent)
   - **Test: ABox tab shows instance counts** — switch to ABox tab → wait for content → verify at least one type with count is visible → click a type → verify instances list appears
   - **Test: RBox tab shows property table** — switch to RBox tab → wait for content → verify property table has at least one row → verify "Domain" and "Range" column headers visible
   - Use auth fixture (`ownerPage`) from existing E2E infrastructure
   - Stay within auth rate limit (5 magic-link calls/minute) — combine related assertions into single test cases, limit to ≤3 test cases

3. **Add ontology selectors to `e2e/helpers/selectors.ts`** — Under a new `ontology` key:
   - `ontologyPage: '[data-testid="ontology-page"]'`
   - `tboxTree: '[data-testid="tbox-tree"]'`
   - `tboxNode: '[data-testid="tbox-node"]'`
   - `aboxBrowser: '[data-testid="abox-browser"]'`
   - `aboxTypeRow: '[data-testid="abox-type-row"]'`
   - `rboxLegend: '[data-testid="rbox-legend"]'`
   - `tabTbox: '[data-testid="ontology-tab-tbox"]'`
   - `tabAbox: '[data-testid="ontology-tab-abox"]'`
   - `tabRbox: '[data-testid="ontology-tab-rbox"]'`

4. **Verify all tests pass** — Run unit tests and E2E tests. Fix any issues found. Ensure templates include the `data-testid` attributes that selectors reference.

## Must-Haves

- [ ] Unit tests cover batch splitting edge cases (0, 100, 500, 501, 4000 triples)
- [ ] Unit tests verify INSERT DATA SPARQL format including BNode handling
- [ ] Unit tests verify FROM clause assembly for cross-graph queries
- [ ] E2E test opens ontology viewer via command palette
- [ ] E2E test verifies TBox tree shows gist classes
- [ ] E2E test verifies ABox tab shows type counts
- [ ] E2E test verifies RBox tab shows property table
- [ ] All data-testid attributes added to templates for E2E selectors

## Verification

- `cd backend && python -m pytest tests/test_ontology_service.py -v` — all unit tests pass
- `cd e2e && npx playwright test tests/22-ontology/ontology-viewer.spec.ts` — all E2E tests pass against Docker stack

## Observability Impact

- Signals added/changed: None (test-only task)
- How a future agent inspects this: run the test commands above; check test output for specific failures
- Failure state exposed: test failures indicate which specific query, template, or UI interaction is broken

## Inputs

- `backend/app/ontology/service.py` — from T01+T02+T03, full OntologyService implementation
- `backend/app/ontology/router.py` — from T02+T03, all ontology routes
- `backend/app/templates/browser/ontology/*.html` — from T02+T03, all templates
- `frontend/static/js/workspace.js` — from T03, openOntologyTab + command palette
- `e2e/fixtures/auth.ts` — existing auth fixture for E2E
- `e2e/helpers/selectors.ts` — existing selector helper to extend
- `e2e/helpers/wait-for.ts` — existing wait helpers

## Expected Output

- `backend/tests/test_ontology_service.py` — comprehensive unit tests for ontology service
- `e2e/tests/22-ontology/ontology-viewer.spec.ts` — E2E tests for ontology viewer
- `e2e/helpers/selectors.ts` — extended with ontology selectors
- Templates updated with `data-testid` attributes if not already present from T02/T03
