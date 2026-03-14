# S05: Docs & Test Coverage — Research

**Date:** 2026-03-14

## Summary

S05 is the final slice of M004. Its job is twofold: (1) update the user guide to document all M004 features — property creation, class/property editing, class/property deletion with instance warnings, and the Custom section on Mental Models — and (2) ensure unit test coverage for all new service methods. The scope is well-bounded because S01-S04 already wrote significant tests (114 tests across `test_ontology_service.py` and `test_class_creation.py`), and the docs structure is clear (chapter 10 already has an Ontology Viewer section that needs extending).

The primary risk is a pre-existing test regression in `TestCreateClassEndpoint` (3 failing tests) caused by missing `description`/`example` string params when calling the route handler directly — the `Form("")` defaults don't produce strings when bypassing FastAPI's DI. This must be fixed as part of test coverage work.

No active requirements in REQUIREMENTS.md need to be owned by this slice — the M004 features need to have requirements added and validated as part of this slice's definition of done.

## Recommendation

**Approach: Two tasks — Documentation (T01) + Test Coverage & Requirements (T02)**

**T01 — Documentation:** Extend chapter 10's Ontology Viewer section with subsections for: Creating Properties, Editing Classes, Editing Properties, Deleting Classes (with instance warning flow), Deleting Properties, and the Custom Section on Mental Models. Keep the existing "Creating Custom Classes" section and add the new sections after it. No new chapter needed — all M004 features are extensions of the existing Ontology Viewer and Mental Models management documentation.

**T02 — Test Coverage + Requirements:** Fix the 3 broken `TestCreateClassEndpoint` tests (add `description=""` and `example=""` params). Audit test coverage against M004 service methods — current coverage is actually good (all methods have tests), but verify edge cases and add any missing coverage. Add M004 requirements to REQUIREMENTS.md and validate them. Update STATE.md and roadmap.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Test mocking for OntologyService | `_make_ontology_service()` helper in test_class_creation.py | Standardized mock factory already used by 40+ tests |
| Route handler testing without HTTP client | Direct `await handler(request=mock, ...)` pattern | Already established in TestEditPropertyRoute, TestCreateClassEndpoint — no need for TestClient |
| User guide chapter structure | Existing chapter 10 sections | Follow heading levels, cross-reference style, and tip/warning blocks from existing sections |

## Existing Code and Patterns

### Documentation

- `docs/guide/10-managing-mental-models.md` — Lines 260-303 cover Ontology Viewer with TBox, RBox, and "Creating Custom Classes". New M004 sections go here after the existing content.
- `docs/guide/README.md` — Table of contents. No new chapters needed — content extends chapter 10.
- `docs/guide/appendix-d-glossary.md` — Already has entries for TBox, RBox, ABox, SHACL, OWL, Ontology. No new glossary entries needed.

### Tests

- `backend/tests/test_ontology_service.py` — 82 tests across 20 test classes covering service methods: batch splitting, SPARQL generation, TBox/ABox/RBox queries, mint helpers, create/edit/get methods.
- `backend/tests/test_class_creation.py` — 32 tests covering OWL+SHACL generation, IRI minting, validation, delete SPARQL, icon service, search, endpoint behavior, property source, delete property/class endpoints.
- Pattern: pure-function unit tests with `AsyncMock` for triplestore client. No Docker/triplestore needed. Tests run in <3s.

### M004 Service Methods (all have tests)

| Method | Test Location | Test Class | Test Count |
|--------|--------------|------------|------------|
| `create_property()` | test_ontology_service.py | TestCreatePropertyValidation | 4 |
| `_mint_property_iri()` | test_ontology_service.py | TestMintPropertyIri | 4 |
| `_generate_property_triples()` | test_ontology_service.py | TestGeneratePropertyTriples | 3 |
| `edit_class()` | test_ontology_service.py | TestEditClass | 2 |
| `get_class_for_edit()` | test_ontology_service.py | TestGetClassForEdit | 2 |
| `delete_property()` | test_class_creation.py | TestDeleteProperty | 2 |
| `get_delete_class_info()` | test_class_creation.py | TestGetDeleteClassInfo | 3 |
| `_property_source()` | test_class_creation.py | TestPropertySource | 6 |
| `list_user_types()` | test_ontology_service.py | TestListUserTypes | 4 |
| `get_property_for_edit()` | test_ontology_service.py | TestGetPropertyForEdit | 3 |
| `edit_property()` | test_ontology_service.py | TestEditProperty | 5 |

### M004 Route Endpoints (all have tests)

| Route | Test Location | Test Class | Test Count |
|-------|--------------|------------|------------|
| `POST /ontology/create-class` | test_class_creation.py | TestCreateClassEndpoint | 4 (3 FAILING) |
| `DELETE /ontology/delete-class` | test_class_creation.py | TestDeleteClassEndpoint | 2 |
| `DELETE /ontology/delete-property` | test_class_creation.py | TestDeletePropertyEndpoint | 3 |
| `GET /ontology/delete-class-check` | test_class_creation.py | TestDeleteClassCheckEndpoint | 3 |
| `GET /ontology/edit-property-form` | test_ontology_service.py | TestEditPropertyFormRoute | 3 |
| `POST /ontology/edit-property` | test_ontology_service.py | TestEditPropertyRoute | 4 |

### Pre-existing Test Failure (must fix)

`TestCreateClassEndpoint` — 3 tests fail because the `create_class` route gained `description: str = Form("")` and `example: str = Form("")` params (added in M004/S01). The tests call the handler directly without FastAPI DI, so `Form("")` defaults aren't resolved to strings. Fix: add `description=""` and `example=""` to all test calls.

## Constraints

- **No Docker/triplestore needed for tests** — All tests are pure-function unit tests with mocked triplestore client (D011).
- **User guide follows existing structure** — Chapter 10 already has the Ontology Viewer section; new M004 docs extend it.
- **Test run budget** — All 386 tests must pass in <5s (`cd backend && .venv/bin/pytest tests/ -q`).
- **README.md TOC** — No new chapters needed, so no TOC update required.

## Common Pitfalls

- **Form default resolution in direct handler tests** — When calling FastAPI route handlers directly (not via TestClient), `Form("")` defaults produce `Form` objects, not strings. Always pass explicit string values for all `Form()`-annotated parameters.
- **Documentation scope creep** — S05 docs cover M004 features only (property CRUD, class edit/delete, Custom section). Do not re-document existing M003 features (class creation, gist loading) — those are already documented.
- **Test file organization** — M004 tests are split across two files: `test_ontology_service.py` (service methods + edit-property routes) and `test_class_creation.py` (class lifecycle + delete/property-source + delete routes). New tests for any gaps should go in the appropriate file.

## Open Risks

- **Pre-existing 3-test failure** — `TestCreateClassEndpoint` failures must be fixed. The fix is straightforward (add missing params) but needs verification that it doesn't change the tested behavior.
- **Documentation accuracy** — Docs describe UI flows that were verified in browser during S01-S04 but may have subtle differences if subsequent slices altered the UI. A quick browser spot-check of each documented flow is recommended during doc writing.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| pytest | — | No specialized skill needed; standard patterns |
| Markdown docs | — | No specialized skill needed; follows existing guide structure |

No external skills are relevant for this slice. The work is entirely internal documentation and unit test maintenance.

## Sources

- Task summaries from M004/S01-S04 (inlined above) — primary source for what was built
- `docs/guide/10-managing-mental-models.md` lines 260-303 — existing Ontology Viewer docs
- `backend/tests/test_ontology_service.py` — 82 existing tests
- `backend/tests/test_class_creation.py` — 32 existing tests
- Test run: 383 passed, 3 failed (TestCreateClassEndpoint) in 3.32s
