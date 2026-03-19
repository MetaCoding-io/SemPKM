---
estimated_steps: 7
estimated_files: 6
---

# T01: Build complete bpkm:Event type in basic-pkm model files

**Slice:** S01 — bpkm:Event type in basic-pkm
**Milestone:** M018

## Description

Add the `bpkm:Event` type to basic-pkm, upgrading it from v2.0.0 to v2.1.0. This is the foundation for all calendar sync in M018 (Google), M020 (Outlook), and M021 (CalDAV). The property set is the cross-provider superset per decision D212 — all enum values from all three providers are included even if a single provider doesn't use them all.

The complete Event type specification comes from `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §5–§8, specifically the "Field Coverage Matrix" at §8 which shows the cross-provider superset. Existing types (Task, Milestone, Person) in the model files demonstrate the exact JSON-LD patterns to follow.

## Steps

1. **Update `models/basic-pkm/manifest.yaml`:**
   - Change `version: "2.0.0"` → `version: "2.1.0"`
   - Add icon entry for `bpkm:Event` with `icon: "calendar"`, `color: "#8b5cf6"` (purple, distinct from all existing icons)

2. **Add Event class + properties to `models/basic-pkm/ontology/basic-pkm.jsonld`:**
   - Add `bpkm:Event` as OWL class with `rdfs:subClassOf: gist:Event`
   - Add these OWL properties (DatatypeProperty unless noted):
     - `bpkm:eventStatus` — xsd:string, domain bpkm:Event (confirmed/tentative/cancelled)
     - `bpkm:location` — xsd:string, domain bpkm:Event
     - `bpkm:timeZone` — xsd:string, domain bpkm:Event (IANA identifier)
     - `bpkm:allDay` — xsd:boolean, domain bpkm:Event
     - `bpkm:visibility` — xsd:string, domain bpkm:Event
     - `bpkm:showAs` — xsd:string, domain bpkm:Event
     - `bpkm:conferenceUrl` — xsd:anyURI, domain bpkm:Event
     - `bpkm:recurrenceRule` — xsd:string, domain bpkm:Event (RFC 5545 RRULE)
     - `bpkm:recurringEventId` — xsd:string, domain bpkm:Event
     - `bpkm:responseStatus` — xsd:string, domain bpkm:Event
     - `bpkm:reminderMinutes` — xsd:integer, domain bpkm:Event
     - `bpkm:calendarName` — xsd:string, domain bpkm:Event
     - `bpkm:meetingNotes` — xsd:string, domain bpkm:Event (SemPKM-only)
     - `bpkm:attendee` — ObjectProperty, domain bpkm:Event, range bpkm:Person
     - `bpkm:organizer` — ObjectProperty, domain bpkm:Event, range bpkm:Person, maxCount 1
     - `bpkm:eventProject` — ObjectProperty, domain bpkm:Event, range bpkm:Project (with inverseOf `bpkm:hasEvents`)
     - `bpkm:hasEvents` — ObjectProperty, domain bpkm:Project, range bpkm:Event (inverseOf `bpkm:eventProject`)
     - `bpkm:generatedTask` — ObjectProperty, domain bpkm:Event, range bpkm:Task
     - `bpkm:eventNote` — ObjectProperty, domain bpkm:Event, range bpkm:Note
   - Reuse existing shared properties: `dcterms:title`, `dcterms:description`, `schema:startDate`, `schema:endDate`, `bpkm:externalId`, `bpkm:externalUrl`, `bpkm:externalProvider`, `bpkm:lastSyncedAt`, `bpkm:tags`, `bpkm:body`
   - **Do NOT redefine** shared properties that already exist — only add new Event-specific ones

3. **Add EventShape to `models/basic-pkm/shapes/basic-pkm.jsonld`:**
   - Create 5 property groups: `EventInfoGroup` (order 1), `EventScheduleGroup` (order 2), `EventAttendeesGroup` (order 3), `EventSyncGroup` (order 4), `EventMetadataGroup` (order 5)
   - Create `bpkm:EventShape` targeting `bpkm:Event`
   - Property shapes with these groups:
     - **Event Info** (group 1): title (required), description, eventStatus (enum: confirmed/tentative/cancelled, default: confirmed), location, visibility (enum: public/private/confidential), showAs (enum: free/tentative/busy/out-of-office/working-elsewhere, default: busy), conferenceUrl, meetingNotes
     - **Schedule** (group 2): startDate (required), endDate, allDay (default: false), timeZone, recurrenceRule, recurringEventId, reminderMinutes
     - **Attendees** (group 3): attendee (→ Person), organizer (→ Person, maxCount 1), responseStatus (enum: needs-action/accepted/declined/tentative, default: needs-action)
     - **Sync** (group 4): externalProvider (reuse Task's enum + add "google-calendar", "outlook", "caldav"), externalId, externalUrl, lastSyncedAt, calendarName
     - **Metadata** (group 5): tags, body, eventProject (→ Project), generatedTask (→ Task), eventNote (→ Note), created, modified
   - All properties need `sh:description` and `sempkm:editHelpText`
   - **externalProvider enum expansion:** The Task shape has `["asana", "linear", "jira", "github", "todoist", "trello", "manual"]`. The Event shape should use `["google-calendar", "outlook", "caldav", "manual"]` since events come from calendar providers, not PM tools.

4. **Add Event ViewSpecs + SavedQueries to `models/basic-pkm/views/basic-pkm.jsonld`:**
   - 3 ViewSpecs following existing pattern:
     - `bpkm:view-event-table` — SELECT: title, eventStatus, startDate, endDate, location, calendarName. Sort by startDate.
     - `bpkm:view-event-card` — SELECT: title, eventStatus, startDate, location, description. Card title=title, subtitle=eventStatus.
     - `bpkm:view-event-graph` — CONSTRUCT: Event with attendees (Person names), organizer, eventProject.
   - 2 SavedQueries:
     - `urn:sempkm:model:basic-pkm:query:upcoming-events` — Events where startDate >= today (use STRDT/SUBSTR pattern from K001)
     - `urn:sempkm:model:basic-pkm:query:past-events` — Events where endDate < today, ordered by endDate DESC

5. **Add Event seed instances to `models/basic-pkm/seed/basic-pkm.jsonld`:**
   - `bpkm:seed-event-standup` — timed event (daily standup), confirmed, busy, with attendees Alice and Bob, conference URL
   - `bpkm:seed-event-offsite` — all-day event (team offsite), confirmed, bpkm:allDay=true, with location
   - `bpkm:seed-event-review` — recurring master event with recurrenceRule (RRULE:FREQ=WEEKLY;BYDAY=FR), organizer Carol
   - `bpkm:seed-event-review-exception` — recurring exception linked to master via recurringEventId, different location
   - **Important (K002):** Match seed data date types to shape constraints. Use `xsd:date` for date-only fields, `xsd:dateTime` for datetime fields. Check the EventShape's `sh:datatype` for each property before authoring seed values.
   - Set `dcterms:created` to `xsd:dateTime` (matching existing seed pattern)
   - Set `schema:startDate` / `schema:endDate` to `xsd:dateTime` for timed events, `xsd:date` for all-day events
   - Use future dates (2026-04-xx) to avoid triggering any date-based warnings

6. **Review `models/basic-pkm/rules/basic-pkm.ttl`:**
   - No new inference or validation rules needed for Event in S01. The existing prefix declarations already include bpkm and xsd. No changes required unless a validation rule is appropriate (none is — overdue check is Task-specific, and calendar-specific rules belong in the sync app).

7. **Self-verify all 6 files parse correctly:**
   - Run `python -c "import json; json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld'))"` for each JSON-LD file
   - Run `python -c "from rdflib import Graph; g = Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(len(g))"` for the TTL file
   - Run `python -c "import yaml; yaml.safe_load(open('models/basic-pkm/manifest.yaml'))"` for the manifest

## Must-Haves

- [ ] bpkm:Event OWL class with rdfs:subClassOf gist:Event
- [ ] All ~22 cross-provider superset properties defined (D212) — matching the design doc's Field Coverage Matrix
- [ ] EventShape with 5 property groups, enum constraints for eventStatus/visibility/showAs/responseStatus
- [ ] showAs enum includes out-of-office and working-elsewhere (Outlook values per D212)
- [ ] 3 ViewSpecs (table/cards/graph) for Event type
- [ ] 2 SavedQueries (upcoming-events, past-events) using STRDT/SUBSTR date pattern
- [ ] 4 seed Event instances (timed, all-day, recurring master, recurring exception)
- [ ] Seed data types match SHACL shape constraints (K002)
- [ ] Manifest version 2.1.0 with calendar icon entry
- [ ] All JSON-LD files parse without errors

## Verification

- All 4 JSON-LD files parse: `python -c "import json; json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld'))"`
- Rules TTL parses: `python -c "from rdflib import Graph; g = Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle')"`
- Manifest parses: `python -c "import yaml; yaml.safe_load(open('models/basic-pkm/manifest.yaml'))"`
- Event class count: ontology has 7 bpkm: OWL classes

## Inputs

- `models/basic-pkm/ontology/basic-pkm.jsonld` — existing v2.0 ontology with 6 classes (Project, Person, Note, Concept, Task, Milestone)
- `models/basic-pkm/shapes/basic-pkm.jsonld` — existing shapes with 6 NodeShapes. Follow TaskShape/MilestoneShape pattern for groups, enums, helptext.
- `models/basic-pkm/views/basic-pkm.jsonld` — existing 18 ViewSpecs (6 × 3) + 6 SavedQueries. Follow exact SPARQL pattern with full URIs.
- `models/basic-pkm/seed/basic-pkm.jsonld` — existing seed data. Follow date typing patterns (K002).
- `models/basic-pkm/manifest.yaml` — current v2.0.0 manifest with 6 icon entries.
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §5–§8 — authoritative source for the Event property superset and enum values.
- Decision D212 — cross-provider superset design: include all enum values from Google + Outlook + CalDAV.

## Expected Output

- `models/basic-pkm/manifest.yaml` — version 2.1.0, 7 icon entries
- `models/basic-pkm/ontology/basic-pkm.jsonld` — 7 OWL classes, ~15 new properties for Event
- `models/basic-pkm/shapes/basic-pkm.jsonld` — 7 NodeShapes with EventShape having 5 groups and ~22 property shapes
- `models/basic-pkm/views/basic-pkm.jsonld` — 21 ViewSpecs (7 × 3) + 8 SavedQueries
- `models/basic-pkm/seed/basic-pkm.jsonld` — 4 new Event instances
- `models/basic-pkm/rules/basic-pkm.ttl` — unchanged

## Observability Impact

- **New signals:** 19 pytest assertions in `test_basic_pkm_event.py` covering manifest version, class/shape/view counts, enum constraints, seed data types, and pyshacl validation.
- **Inspection:** `python3 -c "import json; ..."` one-liners verify each JSON-LD file parses. `rdflib` verifies the TTL rules file.
- **Failure visibility:** pyshacl violations surface as structured `sh:Violation` results with focus node, constraint path, and human-readable message. Test failures include the full pyshacl results text.
- **No runtime signals:** This task is model-file-only. No API endpoints, logs, or runtime metrics change.
