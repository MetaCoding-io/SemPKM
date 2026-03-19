# S01: bpkm:Event type in basic-pkm

**Goal:** basic-pkm model gains a complete `bpkm:Event` type with OWL ontology, SHACL shapes (22+ properties), ViewSpecs (table/cards/graph), seed data, Lucide icon, and SHACL-AF rules — all passing offline pyshacl validation.
**Demo:** `pytest backend/tests/test_basic_pkm_event.py -v` passes with zero failures. pyshacl fires no errors. Model version is 2.1.0 with 7 types including Event.

## Must-Haves

- `bpkm:Event` OWL class subclassing `gist:Event`
- ~22 properties covering the cross-provider superset (Google/Outlook/CalDAV) per D212
- SHACL NodeShape with property groups (Event Info, Schedule, Attendees, Sync, Metadata), enum constraints for eventStatus/visibility/showAs/responseStatus
- ViewSpecs: Events Table, Events Cards, Events Graph + 2 saved queries (Upcoming Events, Past Events)
- Seed data: timed event, all-day event, recurring master, recurring exception — all passing SHACL validation
- Manifest updated to v2.1.0 with `calendar` icon for bpkm:Event
- Offline pyshacl validation passes with zero errors (warnings OK)

## Proof Level

- This slice proves: contract (offline model validation, no runtime)
- Real runtime required: no (pyshacl validates model correctness without Docker)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_basic_pkm_event.py -v` — all tests pass
- Tests assert: manifest v2.1.0, 7 OWL classes, 7 NodeShapes, 21 ViewSpecs (7 × 3), 8 SavedQueries, seed has Event instances, pyshacl fires zero errors

## Integration Closure

- Upstream surfaces consumed: none (first slice)
- New wiring introduced: bpkm:Event class + properties in ontology; EventShape in shapes; Event ViewSpecs/queries in views; Event seed instances in seed; Event icon in manifest
- What remains before the milestone is truly usable end-to-end: S02 (OAuth), S03 (sync engine maps to these properties), S04 (RSVP push + recurrence), S05 (E2E + docs)

## Observability / Diagnostics

- **Model validation:** `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v` — 22 tests covering manifest, ontology, shapes, views, seed, pyshacl validation, and enum constraints.
- **Quick structure check:** `python3 -c "import json; d=json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld')); print(len([x for x in d['@graph'] if x.get('@type')=='owl:Class' and 'bpkm:' in x.get('@id','')]))"` should print `7`.
- **SHACL validation:** pyshacl validates seed+ontology against shapes+rules with `allow_warnings=True`. Zero violations expected; overdue-task warnings are expected from existing seed data.
- **Manifest version:** `python3 -c "import yaml; print(yaml.safe_load(open('models/basic-pkm/manifest.yaml'))['version'])"` should print `2.1.0`.
- **Failure visibility:** If Event seed data violates shape constraints, pyshacl produces `sh:Violation` results with focus node, path, and message. Test `test_pyshacl_zero_errors_on_events` catches this.
- **No runtime signals:** This slice is offline-only (no Docker, no API). Model files are validated statically.

## Tasks

- [x] **T01: Build complete bpkm:Event type in basic-pkm model files** `est:2h`
  - Why: The Event type is the foundation for all calendar sync — S03 maps Google Calendar fields to these properties. The property set must be the cross-provider superset (D212) covering Google, Outlook, and CalDAV.
  - Files: `models/basic-pkm/ontology/basic-pkm.jsonld`, `models/basic-pkm/shapes/basic-pkm.jsonld`, `models/basic-pkm/views/basic-pkm.jsonld`, `models/basic-pkm/seed/basic-pkm.jsonld`, `models/basic-pkm/rules/basic-pkm.ttl`, `models/basic-pkm/manifest.yaml`
  - Do: Add Event class + ~22 properties to ontology, EventShape with 5 groups to shapes, 3 ViewSpecs + 2 SavedQueries to views, 4 seed events to seed, update manifest to v2.1.0 with calendar icon. Follow exact patterns from existing Task/Milestone types.
  - Verify: `python -c "import json; d=json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld')); print(len([x for x in d['@graph'] if x.get('@type')=='owl:Class' and 'bpkm:' in x.get('@id','')]))"` prints 7
  - Done when: All 6 model files updated, Event type fully defined with cross-provider superset properties

- [x] **T02: Write offline validation tests for bpkm:Event type** `est:45m`
  - Why: Proves the model is structurally correct — shapes match ontology, seed data conforms, pyshacl finds no errors. This is the slice's verification gate and EVENT-01 evidence.
  - Files: `backend/tests/test_basic_pkm_event.py`
  - Do: Write pytest test file following `test_basic_pkm_v2.py` pattern. Test manifest version, class count (7), NodeShape count (7), ViewSpec count (21), SavedQuery count (8), seed Event instances, pyshacl validation (zero errors), enum constraints present.
  - Verify: `cd backend && python -m pytest tests/test_basic_pkm_event.py -v`
  - Done when: All tests pass, pyshacl validates cleanly, test count ≥ 8

## Files Likely Touched

- `models/basic-pkm/ontology/basic-pkm.jsonld`
- `models/basic-pkm/shapes/basic-pkm.jsonld`
- `models/basic-pkm/views/basic-pkm.jsonld`
- `models/basic-pkm/seed/basic-pkm.jsonld`
- `models/basic-pkm/rules/basic-pkm.ttl`
- `models/basic-pkm/manifest.yaml`
- `backend/tests/test_basic_pkm_event.py`
