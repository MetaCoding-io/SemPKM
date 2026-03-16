---
id: T01
parent: S02
milestone: M008
provides:
  - GET /api/canvas/properties endpoint returning SHACL-derived property JSON
  - build_property_list pure-function helper for property data transformation
key_files:
  - backend/app/canvas/router.py
  - backend/tests/test_canvas_properties.py
key_decisions:
  - Extracted property-building logic into pure-function `build_property_list()` for direct unit testing without mocks
patterns_established:
  - Pure-function extraction pattern for complex endpoint logic in canvas router
observability_surfaces:
  - GET /api/canvas/properties?iri=<IRI> returns structured JSON for debugging
  - Warning-level logs on triplestore query failures
duration: 15min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Backend Properties Endpoint and Unit Tests

**Added `GET /api/canvas/properties?iri=<IRI>` endpoint with SHACL-derived property JSON and 26 passing unit tests.**

## What Happened

Added the properties endpoint to `backend/app/canvas/router.py`. The endpoint queries both `urn:sempkm:current` and `urn:sempkm:inferred` graphs, resolves types via `ShapesService.get_form_for_type()`, builds an ordered property list from SHACL form properties, appends unmatched predicates with local-name labels, tags inferred properties, and resolves IRI reference labels via `LabelService.resolve_batch()`.

Extracted the core logic into `build_property_list()` — a pure function that takes parsed bindings, form, and labels as input. This made all 26 tests pure-function tests with zero mocking.

## Verification

- `cd backend && .venv/bin/pytest tests/test_canvas_properties.py -v` — **26/26 passed** (0.49s)
- `python -c "from app.canvas.router import router; print('OK')"` — imports clean
- LSP diagnostics: no new errors (1 pre-existing Pyright type hint in `list_canvas_sessions`)

### Slice-level verification (partial — T01 is backend only):
- ✅ `cd backend && .venv/bin/pytest tests/test_canvas_properties.py -v` — all unit tests pass
- ⏳ Browser: flip button, property table rendering — T02 (frontend)
- ⏳ Browser: save/reload persistence — T02 (frontend)
- ⏳ Browser: old session backward compat — T02 (frontend)

## Diagnostics

- `curl /api/canvas/properties?iri=<IRI>` returns `{type_label, properties: [{name, path, values, datatype, source}]}`
- Invalid IRI → HTTP 400 with `{"detail": "Invalid IRI"}`
- Unknown IRI → `{type_label: null, properties: []}`
- Triplestore failures → warning logs with exc_info, graceful degradation to empty results

## Deviations

None — plan followed exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/canvas/router.py` — Added imports, `build_property_list()` helper, `get_node_properties()` endpoint, constants
- `backend/tests/test_canvas_properties.py` — New file with 26 unit tests across 9 test classes
