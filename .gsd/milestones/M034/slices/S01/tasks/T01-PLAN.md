---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T01: Add scheduledStart/scheduledEnd/estimatedDuration to Task schema and ontology

**Slice:** S01 — Editable Calendar & Task Time-Blocking
**Milestone:** M034

## Description

Add three new properties to the bpkm:Task type for calendar time-blocking: `bpkm:scheduledStart` (xsd:dateTime), `bpkm:scheduledEnd` (xsd:dateTime), and `bpkm:estimatedDuration` (xsd:string for ISO 8601 duration like "PT1H30M"). These go in the TaskShape's Dates group and in the ontology as OWL DatatypeProperty declarations. Bump the model version to 2.2.0.

The existing `_detect_date_fields()` in `backend/app/views/service.py` uses `_START_DATE_PRIORITY = ["startdate", "duedate", "targetdate", "created"]`. Since "scheduledstart" contains "startdate" as a substring, it will naturally match the highest-priority keyword. Verify this by confirming the local name `scheduledStart` lowercased contains `startdate`. Similarly, "scheduledend" contains "enddate" — the existing end-field detection checks for "enddate" in the local name.

## Steps

1. Edit `models/basic-pkm/shapes/basic-pkm.jsonld`: in the TaskShape's `sh:property` array, add three new property shape objects after the existing dueDate (order 6) and before completedDate (order 7):
   - `bpkm:scheduledStart`: name "Scheduled Start", datatype xsd:dateTime, maxCount 1, order 5.1, group TaskDatesGroup, description "When this task is scheduled to begin.", editHelpText explaining calendar time-blocking.
   - `bpkm:scheduledEnd`: name "Scheduled End", datatype xsd:dateTime, maxCount 1, order 5.2, group TaskDatesGroup, description "When this task is scheduled to end."
   - `bpkm:estimatedDuration`: name "Estimated Duration", datatype xsd:string, maxCount 1, order 5.3, group TaskDatesGroup, description "Expected duration in ISO 8601 format (e.g. PT1H30M)."
2. Edit `models/basic-pkm/ontology/basic-pkm.jsonld`: add three new entries to @graph:
   - `bpkm:scheduledStart` — owl:DatatypeProperty, label "Scheduled Start", domain bpkm:Task, range xsd:dateTime
   - `bpkm:scheduledEnd` — owl:DatatypeProperty, label "Scheduled End", domain bpkm:Task, range xsd:dateTime
   - `bpkm:estimatedDuration` — owl:DatatypeProperty, label "Estimated Duration", domain bpkm:Task, range xsd:string
3. Edit `models/basic-pkm/manifest.yaml`: change `version: "2.1.0"` to `version: "2.2.0"`.
4. Verify the date field detection priority: confirm that `"startdate" in "scheduledstart"` is True and `"enddate" in "scheduledend"` is True — meaning the existing `_detect_date_fields()` will correctly pick these fields with no code changes needed.

## Must-Haves

- [ ] TaskShape has 3 new properties: bpkm:scheduledStart, bpkm:scheduledEnd, bpkm:estimatedDuration
- [ ] Ontology has 3 new DatatypeProperty declarations with correct domains/ranges
- [ ] Manifest version is 2.2.0
- [ ] JSON-LD files are valid JSON (no syntax errors)

## Verification

- `python3 -c "import json; json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld'))"` — no error
- `python3 -c "import json; json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld'))"` — no error
- `grep -q '2.2.0' models/basic-pkm/manifest.yaml` — exits 0
- `python3 -c "assert 'startdate' in 'scheduledstart'; assert 'enddate' in 'scheduledend'; print('Date detection priority OK')"` — prints confirmation

## Inputs

- `models/basic-pkm/shapes/basic-pkm.jsonld` — existing TaskShape to extend
- `models/basic-pkm/ontology/basic-pkm.jsonld` — existing ontology to extend
- `models/basic-pkm/manifest.yaml` — existing manifest to version bump

## Expected Output

- `models/basic-pkm/shapes/basic-pkm.jsonld` — TaskShape with 3 new scheduling properties
- `models/basic-pkm/ontology/basic-pkm.jsonld` — 3 new DatatypeProperty declarations
- `models/basic-pkm/manifest.yaml` — version 2.2.0

## Observability Impact

- **What changes:** The Task type's SHACL shape now has 3 additional property shapes. When the model is installed, the form editor for Tasks will render 3 new fields in the Dates group. The ontology graph will have 3 new `owl:DatatypeProperty` triples.
- **How to inspect:** Load `/browser/objects/<task-iri>` — the edit form should show Scheduled Start, Scheduled End, and Estimated Duration fields in the Dates section. Query the SPARQL endpoint: `SELECT ?p WHERE { bpkm:scheduledStart a owl:DatatypeProperty }` should return a result after model install.
- **Failure visibility:** If properties are missing from the form editor, check the shapes file JSON validity (`python3 -c "import json; json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld'))"`). If the model fails to install, the backend log will show a shapes parse error with the JSON-LD file path.
- **Date field detection note:** The planner assumed `"startdate" in "scheduledstart"` is True — it's actually False. T02 must update `_START_DATE_PRIORITY` and `_WELL_KNOWN_DATE_PATHS` in `backend/app/views/service.py` for the calendar to detect these fields.
