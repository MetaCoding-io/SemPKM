---
id: S01
parent: M018
milestone: M018
provides:
  - bpkm:Event OWL class with 20 properties (14 datatype + 6 object) in basic-pkm v2.1.0
  - EventShape with 5 property groups, 30 property shapes, and 4 enum constraints
  - 3 Event ViewSpecs (table/cards/graph) + 2 SavedQueries (upcoming/past events)
  - 4 seed Event instances (timed, all-day, recurring master, recurring exception)
  - Manifest v2.1.0 with calendar Lucide icon in purple (#8b5cf6)
  - 22-test offline validation suite (19 structural + 3 named enum constraint tests)
requires: []
affects:
  - S03
key_files:
  - models/basic-pkm/ontology/basic-pkm.jsonld
  - models/basic-pkm/shapes/basic-pkm.jsonld
  - models/basic-pkm/views/basic-pkm.jsonld
  - models/basic-pkm/seed/basic-pkm.jsonld
  - models/basic-pkm/manifest.yaml
  - backend/tests/test_basic_pkm_event.py
  - backend/tests/test_basic_pkm_v2.py
key_decisions:
  - D212: Event property set designed as cross-provider superset (Google + Outlook + CalDAV values included even if not all used by Google)
  - EventShape startDate/endDate omit sh:datatype to allow both xsd:date (all-day) and xsd:dateTime (timed events)
  - Event externalProvider enum uses calendar-specific values (google-calendar/outlook/caldav/manual) not Task's PM-provider values
patterns_established:
  - Multi-datatype date fields omit sh:datatype in shape and rely on seed data convention
  - Calendar event seed data uses xsd:dateTime for timed events, xsd:date for all-day events
  - _get_enum_values helper extracts sh:in values from property shapes for targeted enum assertions
observability_surfaces:
  - cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v — 22 tests covering all model file invariants
  - python3 -c "import json; d=json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld')); print(len([x for x in d['@graph'] if x.get('@type')=='owl:Class' and 'bpkm:' in x.get('@id','')]))" — prints 7
  - python3 -c "import yaml; print(yaml.safe_load(open('models/basic-pkm/manifest.yaml'))['version'])" — prints 2.1.0
drill_down_paths:
  - .gsd/milestones/M018/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M018/slices/S01/tasks/T02-SUMMARY.md
duration: 33m
verification_result: passed
completed_at: 2026-03-18
---

# S01: bpkm:Event type in basic-pkm

**basic-pkm upgraded from v2.0.0 to v2.1.0 with complete bpkm:Event type — 20 OWL properties, SHACL EventShape (5 groups, 30 property shapes, 4 enum constraints), 3 ViewSpecs, 2 SavedQueries, 4 seed instances, and 22 offline validation tests all passing.**

## What Happened

T01 built the entire bpkm:Event type across all 6 basic-pkm model files. The ontology adds `bpkm:Event` as an OWL class with `rdfs:subClassOf gist:Event`, plus 14 new DatatypeProperties (eventStatus, location, timeZone, allDay, visibility, showAs, conferenceUrl, recurrenceRule, recurringEventId, responseStatus, reminderMinutes, calendarName, meetingNotes) and 6 new ObjectProperties (attendee, organizer, eventProject/hasEvents inverse pair, generatedTask, eventNote). Shared properties (dcterms:title, schema:startDate, bpkm:externalId, etc.) are reused without redefinition — safe in RDF's open-world model.

The SHACL EventShape defines 30 property shapes organized into 5 groups (Event Info, Schedule, Attendees, Sync, Metadata). Four enum constraints enforce the D212 cross-provider superset: eventStatus (confirmed/tentative/cancelled), visibility (public/private/confidential), showAs (free/tentative/busy/out-of-office/working-elsewhere — includes Outlook values), and responseStatus (needs-action/accepted/declined/tentative). All properties have sh:description and sempkm:editHelpText annotations.

Views add 3 ViewSpecs (table sorted by startDate, cards with eventStatus subtitle, graph showing attendee/organizer/project edges) and 2 SavedQueries (upcoming-events and past-events using the STRDT/SUBSTR date pattern from K001).

Seed data covers the four key variations: timed event (daily standup with conferenceUrl and 2 attendees), all-day event (team offsite with physical location), recurring master (weekly design review with RRULE), and recurring exception (offsite edition linked via recurringEventId). Date types match shape expectations per K002.

T02 extended the test suite with 3 named enum constraint tests (`test_event_shape_has_status_enum`, `test_event_shape_has_show_as_enum`, `test_event_shape_has_response_status_enum`) and a `_get_enum_values()` helper. The v2 regression suite (`test_basic_pkm_v2.py`) was updated from exact-count to `>=` assertions so it survives model growth. Final count: 22 event tests + 10 v2 regression tests, all passing.

## Verification

- 22/22 event tests pass (`test_basic_pkm_event.py` in 0.36s)
- 10/10 v2 regression tests pass (`test_basic_pkm_v2.py` in 0.38s)
- pyshacl validates seed+ontology with zero sh:Violation results (expected sh:Warning for overdue-task rule)
- OWL class count: 7 (Project, Person, Note, Concept, Task, Milestone, Event)
- NodeShape count: 7
- ViewSpec count: 21 (7 types × 3 renderers)
- SavedQuery count: 8
- Manifest version: 2.1.0

## Requirements Advanced

- EVENT-01 — bpkm:Event type now exists with complete ontology, shapes, views, and seed data. Offline validation proves structural correctness.

## Requirements Validated

- EVENT-01 — 22 offline tests prove: correct OWL class hierarchy (subClassOf gist:Event), 20 properties defined, SHACL EventShape with 5 groups/30 shapes/4 enum constraints, 3 ViewSpecs + 2 SavedQueries, 4 seed instances pass pyshacl validation, manifest at v2.1.0 with calendar icon. The cross-provider property superset (D212) is confirmed by enum tests covering Google + Outlook + CalDAV values.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T01 created the test file (`test_basic_pkm_event.py`) with 19 tests rather than deferring to T02. T02 extended it to 22 tests by adding the plan-named enum tests.
- T01 updated `test_basic_pkm_v2.py` from exact-count to `>=` assertions so v2 regression suite survives model growth.
- EventShape `schema:startDate` and `schema:endDate` omit `sh:datatype` — the same property needs `xsd:date` for all-day and `xsd:dateTime` for timed events. Shape validates cardinality and required-ness but not specific date type.

## Known Limitations

- No runtime validation (Docker install lifecycle) — this is offline-only. S03 will exercise the Event type at runtime when the sync engine creates Event instances.
- startDate/endDate shapes cannot enforce date-type correctness since both `xsd:date` and `xsd:dateTime` must be accepted.

## Follow-ups

- none

## Files Created/Modified

- `models/basic-pkm/manifest.yaml` — version 2.0.0 → 2.1.0, added bpkm:Event icon (calendar, #8b5cf6)
- `models/basic-pkm/ontology/basic-pkm.jsonld` — added Event class + 20 properties
- `models/basic-pkm/shapes/basic-pkm.jsonld` — added 5 property groups + EventShape with 30 property shapes
- `models/basic-pkm/views/basic-pkm.jsonld` — added 3 Event ViewSpecs + 2 SavedQueries
- `models/basic-pkm/seed/basic-pkm.jsonld` — added 4 Event seed instances
- `backend/tests/test_basic_pkm_event.py` — created, 22 offline validation tests
- `backend/tests/test_basic_pkm_v2.py` — updated exact-count assertions to >=

## Forward Intelligence

### What the next slice should know
- S03 maps Google Calendar API fields to these bpkm:Event properties. The full property list is in the ontology (20 properties). Key mapping targets: schema:startDate, schema:endDate, bpkm:timeZone, bpkm:eventStatus, bpkm:allDay, bpkm:attendee (ObjectProperty → Person), bpkm:organizer (ObjectProperty → Person), bpkm:conferenceUrl, bpkm:recurrenceRule, bpkm:recurringEventId, bpkm:responseStatus, bpkm:location, bpkm:visibility, bpkm:showAs, bpkm:reminderMinutes, bpkm:calendarName.
- externalProvider enum for Google Calendar events should be `"google-calendar"` (not `"google"` or `"gcal"`).
- Shared properties (bpkm:externalId, bpkm:externalUrl, bpkm:externalUuid) are reused from Task — they already exist in the ontology and shapes from M011.

### What's fragile
- startDate/endDate lack `sh:datatype` in the shape — sync engine must ensure it writes `xsd:dateTime` for timed events and `xsd:date` for all-day events. No shape validation will catch a type mismatch.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v` — 22 tests covering every structural invariant. If an Event model file is modified and something breaks, this test will pinpoint it.

### What assumptions changed
- The plan estimated ~22 properties; actual count is 20 (some planned properties were already defined as shared properties on Task/Milestone and didn't need redefinition).
