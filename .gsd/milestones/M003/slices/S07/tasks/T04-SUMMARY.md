---
id: T04
parent: S07
milestone: M003
provides:
  - 29 unit tests covering OntologyService batch splitting, INSERT DATA generation, term serialization, version check, FROM clause assembly, TBox/ABox/RBox SPARQL query shapes
  - 3 E2E tests (×2 browsers) verifying ontology viewer TBox tree, ABox instance counts, and RBox property table
  - Ontology selectors in e2e/helpers/selectors.ts
  - data-testid attributes on all ontology viewer template elements
key_files:
  - backend/tests/test_ontology_service.py
  - e2e/tests/22-ontology/ontology-viewer.spec.ts
  - e2e/helpers/selectors.ts
  - backend/app/templates/browser/ontology/ontology_page.html
  - backend/app/templates/browser/ontology/abox_browser.html
  - docker-compose.test.yml
key_decisions:
  - Added ontologies volume mount to docker-compose.test.yml so gist loads in the E2E test stack
  - Used openOntologyTab() JS API instead of command palette UI for E2E test reliability
  - Renamed data-testid="abox-type" to data-testid="abox-type-row" for naming consistency with selector plan
patterns_established:
  - Mock-based SPARQL query shape testing: use AsyncMock side_effect to capture and assert SPARQL query strings without a running triplestore
  - E2E ontology viewer testing pattern: open via JS API, wait for htmx content, assert visible elements
observability_surfaces:
  - none (test-only task)
duration: 30m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T04: Add unit tests and E2E test for ontology viewer

**Added 29 unit tests for OntologyService and 3 E2E tests verifying the full ontology viewer flow against the live Docker stack.**

## What Happened

Extended `backend/tests/test_ontology_service.py` from 16 to 29 tests by adding test classes for FROM clause assembly (4 tests), root class SPARQL shape (2 tests), ABox query construction (3 tests), RBox property query shape (2 tests), and batch has_subclasses (2 tests). The new tests use AsyncMock to capture SPARQL queries and verify structural properties without a running triplestore.

Created `e2e/tests/22-ontology/ontology-viewer.spec.ts` with 3 tests: TBox tree rendering, ABox tab with type counts and drill-down, and RBox tab with property table columns. Tests run across Chromium and Firefox (6 total).

Added `ontology` selectors block to `e2e/helpers/selectors.ts` with 9 data-testid selectors.

Added all required `data-testid` attributes to ontology templates (ontology_page.html, abox_browser.html). Also fixed docker-compose.test.yml to mount the ontologies volume so gist loads in the E2E test stack.

## Verification

- `cd backend && python -m pytest tests/test_ontology_service.py -v` — **29 passed** in 0.18s
- `cd e2e && npx playwright test tests/22-ontology/ontology-viewer.spec.ts` — **6 passed** (3 Chromium + 3 Firefox) in 38.7s

### Slice-level verification:
- ✅ `cd backend && python -m pytest tests/test_ontology_service.py -v` — 29 passed
- ✅ `cd e2e && npx playwright test tests/22-ontology/ontology-viewer.spec.ts` — 6 passed
- Manual verification not run (requires human judgment on gist alignment quality)

## Diagnostics

Run the test commands above. Test failures indicate which specific query, template, or UI interaction is broken. Unit test names map directly to the OntologyService method being tested.

## Deviations

- Added `./backend/ontologies:/app/ontologies:ro` volume mount to `docker-compose.test.yml` — was missing, causing gist load failure in the E2E test stack. This is infrastructure required for the tests to work, not a deviation from the task plan itself.
- Renamed `data-testid="abox-type"` to `data-testid="abox-type-row"` in abox_browser.html to match the planned selector naming convention.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_ontology_service.py` — extended with 13 new tests covering FROM clauses, TBox/ABox/RBox query shapes, batch has_subclasses
- `e2e/tests/22-ontology/ontology-viewer.spec.ts` — new E2E test file with 3 test cases
- `e2e/helpers/selectors.ts` — added `ontology` selectors block
- `backend/app/templates/browser/ontology/ontology_page.html` — added data-testid on viewer container, tab buttons, and tab panes
- `backend/app/templates/browser/ontology/abox_browser.html` — renamed data-testid from abox-type to abox-type-row
- `docker-compose.test.yml` — added ontologies volume mount for E2E gist loading
