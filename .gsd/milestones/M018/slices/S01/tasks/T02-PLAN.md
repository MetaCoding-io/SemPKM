---
estimated_steps: 4
estimated_files: 1
---

# T02: Write offline validation tests for bpkm:Event type

**Slice:** S01 — bpkm:Event type in basic-pkm
**Milestone:** M018

## Description

Write the offline validation test suite that proves the Event type is structurally correct. This follows the exact pattern of `backend/tests/test_basic_pkm_v2.py` (the M011/S01 acceptance test for Task/Milestone types). The tests exercise the model loading pipeline (`parse_manifest → load_archive → validate_archive`) and run pyshacl to prove shapes match data.

This test file is the primary evidence for requirement EVENT-01.

## Steps

1. **Create `backend/tests/test_basic_pkm_event.py`:**
   - Import pattern: copy from `backend/tests/test_basic_pkm_v2.py` — use `parse_manifest`, `load_archive`, `validate_archive` from `app.models.*`, pyshacl, rdflib namespaces.
   - Same MODULE_DIR fixture pointing to `models/basic-pkm`.
   - Same `manifest` and `archive` fixtures (scope=module).

2. **Write structural tests (≥8 tests):**
   - `test_manifest_parses_v21` — version is "2.1.0", 7 icon entries, "bpkm:Event" in icon types
   - `test_archive_loads_all_graphs` — all 5 graphs non-empty (ontology, shapes, views, seed, rules)
   - `test_archive_validates_zero_errors` — `validate_archive()` report has zero errors
   - `test_ontology_has_seven_classes` — 7 OWL classes in bpkm namespace: Project, Person, Note, Concept, Task, Milestone, Event
   - `test_shapes_has_seven_nodeshapes` — 7 NodeShapes, EventShape targets bpkm:Event
   - `test_views_has_all_viewspecs_and_queries` — 21 ViewSpecs (7 × 3) + 8 SavedQueries
   - `test_seed_has_event_instances` — seed has ≥ 4 Event instances, at least one with allDay=true, at least one with recurrenceRule
   - `test_pyshacl_zero_errors` — full pyshacl validation (data=seed+ontology, shapes=shapes+rules, advanced=True) conforms with allow_warnings=True. Zero sh:Violation results.

3. **Write enum constraint tests:**
   - `test_event_shape_has_status_enum` — EventShape has a property shape for bpkm:eventStatus with sh:in list containing "confirmed", "tentative", "cancelled"
   - `test_event_shape_has_show_as_enum` — EventShape has bpkm:showAs with sh:in including "free", "busy", "out-of-office", "working-elsewhere" (proves D212 cross-provider superset)
   - `test_event_shape_has_response_status_enum` — EventShape has bpkm:responseStatus with sh:in including "needs-action", "accepted", "declined", "tentative"

4. **Run tests and verify:**
   - `cd backend && python -m pytest tests/test_basic_pkm_event.py -v`
   - All tests pass with zero failures
   - Confirm pyshacl fires zero Violations (warnings from existing overdue-task rule are OK and expected)

## Must-Haves

- [ ] Test file follows test_basic_pkm_v2.py pattern exactly (same fixtures, same import structure)
- [ ] ≥ 8 tests covering manifest, ontology, shapes, views, seed, pyshacl
- [ ] Enum constraint tests prove D212 cross-provider superset is present
- [ ] pyshacl validation passes (zero Violations)
- [ ] All tests pass on first run after T01 is complete

## Verification

- `cd backend && python -m pytest tests/test_basic_pkm_event.py -v` — all tests pass
- Test count ≥ 8

## Inputs

- `backend/tests/test_basic_pkm_v2.py` — reference test file to follow (fixture pattern, import structure, pyshacl invocation)
- `models/basic-pkm/` — model files modified by T01 (ontology, shapes, views, seed, rules, manifest)
- The T01 task plan specifies exactly what should be in each file (class count, shape count, ViewSpec count, seed instances)

## Expected Output

- `backend/tests/test_basic_pkm_event.py` — ≥ 8 passing tests proving Event type correctness, pyshacl validation, and enum constraints
