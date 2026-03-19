# S01: bpkm:Event type in basic-pkm — UAT

**Milestone:** M018
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice is offline-only — no Docker, no API, no runtime. Model files are validated statically via pyshacl and structural assertions. All invariants can be checked by running the test suite.

## Preconditions

- Python 3.12+ with `backend/.venv` activated
- `pyshacl`, `rdflib`, `pyyaml` installed in venv (part of project dependencies)
- No Docker or running server needed

## Smoke Test

Run `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v` — all 22 tests should pass in under 1 second.

## Test Cases

### 1. Manifest version is 2.1.0

1. Run: `python3 -c "import yaml; print(yaml.safe_load(open('models/basic-pkm/manifest.yaml'))['version'])"`
2. **Expected:** Output is `2.1.0`

### 2. Manifest includes Event type with calendar icon

1. Run: `python3 -c "import yaml; m=yaml.safe_load(open('models/basic-pkm/manifest.yaml')); icons={t['type']:t['icon'] for t in m.get('icons',[])}; print(icons.get('bpkm:Event'))"`
2. **Expected:** Output is `calendar`

### 3. Ontology has exactly 7 bpkm: OWL classes

1. Run: `python3 -c "import json; d=json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld')); classes=[x['@id'] for x in d['@graph'] if x.get('@type')=='owl:Class' and 'bpkm:' in x.get('@id','')]; print(len(classes), sorted(classes))"`
2. **Expected:** Count is 7. Classes are: bpkm:Concept, bpkm:Event, bpkm:Milestone, bpkm:Note, bpkm:Person, bpkm:Project, bpkm:Task

### 4. Event class is subclass of gist:Event

1. Run: `python3 -c "import json; d=json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld')); evt=[x for x in d['@graph'] if x.get('@id')=='bpkm:Event']; print(evt[0].get('rdfs:subClassOf'))"`
2. **Expected:** Output contains `gist:Event`

### 5. Shapes file has 7 NodeShapes

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_shapes_has_seven_nodeshapes -v`
2. **Expected:** Test passes

### 6. EventShape has 5 property groups

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_event_shape_has_five_groups -v`
2. **Expected:** Test passes. Groups: Event Info, Schedule, Attendees, Sync, Metadata

### 7. eventStatus enum includes confirmed/tentative/cancelled

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_event_shape_has_status_enum -v`
2. **Expected:** Test passes. Enum values: confirmed, tentative, cancelled

### 8. showAs enum includes Outlook-specific values

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_event_shape_has_show_as_enum -v`
2. **Expected:** Test passes. Enum values include: free, tentative, busy, out-of-office, working-elsewhere

### 9. responseStatus enum includes needs-action/accepted/declined/tentative

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_event_shape_has_response_status_enum -v`
2. **Expected:** Test passes

### 10. Views file has 21 ViewSpecs and 8 SavedQueries

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_views_has_21_viewspecs tests/test_basic_pkm_event.py::test_views_has_8_saved_queries -v`
2. **Expected:** Both tests pass

### 11. Seed has 4 Event instances covering all variations

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_seed_has_four_event_instances tests/test_basic_pkm_event.py::test_seed_event_types -v`
2. **Expected:** Both tests pass. Seed contains: timed event, all-day event, recurring master, recurring exception

### 12. Seed event date types match shape expectations

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_seed_event_date_types_match_shapes -v`
2. **Expected:** Test passes. Timed events use xsd:dateTime, all-day events use xsd:date.

### 13. pyshacl validates seed data with zero errors

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py::test_pyshacl_zero_errors_on_events -v`
2. **Expected:** Test passes. Zero sh:Violation results. sh:Warning for overdue-task rule is expected.

### 14. v2 regression suite still passes

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_v2.py -v`
2. **Expected:** All 10 tests pass. The suite uses `>=` assertions and remains green as the model grows.

## Edge Cases

### All JSON-LD files parse without error

1. Run each: `python3 -c "import json; json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld'))"`
2. Repeat for shapes, views, seed JSON-LD files
3. **Expected:** No exceptions raised for any file

### Rules TTL parses via rdflib

1. Run: `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(len(g), 'triples')"`
2. **Expected:** Parses successfully, prints 35+ triples

### Recurring exception references master via recurringEventId

1. Inspect seed data for the recurring exception instance
2. **Expected:** It has `bpkm:recurringEventId` value matching the recurring master's `bpkm:externalId`

## Failure Signals

- Any test failure in `test_basic_pkm_event.py` — indicates structural invariant broken
- pyshacl sh:Violation — indicates seed data violates shape constraints (focus node and path printed)
- JSON parse error — indicates malformed JSON-LD file
- rdflib TTL parse error — indicates malformed Turtle syntax in rules file
- `test_basic_pkm_v2.py` failure — indicates the Event additions broke existing model structure

## Requirements Proved By This UAT

- EVENT-01 — Complete bpkm:Event type with OWL ontology (20 properties, gist:Event subclass), SHACL shapes (5 groups, 30 property shapes, 4 enum constraints including D212 cross-provider superset), ViewSpecs (table/cards/graph), SavedQueries (upcoming/past), seed data (4 instances covering timed/all-day/recurring/exception), and Lucide icon. All validated by pyshacl and 22 structural tests.

## Not Proven By This UAT

- Runtime Docker install lifecycle (model installs and seed data loads in running system) — deferred to S03/S05
- Google Calendar field mapping correctness against these properties — S03 scope
- RSVP push-back using responseStatus enum — S04 scope
- Recurrence handling with recurrenceRule/recurringEventId — S04 scope

## Notes for Tester

- The `sh:Warning` results from pyshacl about overdue tasks are expected and correct — they come from the existing SHACL-AF rule for bpkm:Task, not from Event data.
- startDate/endDate shapes intentionally lack `sh:datatype` because they must accept both `xsd:date` and `xsd:dateTime`. This is by design, not a gap.
- The 20-property count is lower than the plan's ~22 estimate because shared properties (externalId, externalUrl, externalUuid) already exist from Task and didn't need redefinition.
