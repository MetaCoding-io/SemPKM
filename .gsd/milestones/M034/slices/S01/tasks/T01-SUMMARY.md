---
id: T01
parent: S01
milestone: M034
provides:
  - bpkm:scheduledStart, bpkm:scheduledEnd, bpkm:estimatedDuration property shapes on TaskShape
  - OWL DatatypeProperty declarations for all 3 scheduling properties
  - Model version bump to 2.2.0
key_files:
  - models/basic-pkm/shapes/basic-pkm.jsonld
  - models/basic-pkm/ontology/basic-pkm.jsonld
  - models/basic-pkm/manifest.yaml
key_decisions:
  - Used xsd:dateTime (not xsd:date) for scheduledStart/scheduledEnd to support intra-day time-blocking
  - Used xsd:string for estimatedDuration to hold ISO 8601 duration literals (PT1H30M) since xsd:duration is poorly supported in rdflib
  - Placed new properties at orders 6.1/6.2/6.3 between dueDate (6) and completedDate (7) in the Dates group
patterns_established:
  - Fractional sh:order values (6.1, 6.2, 6.3) to insert properties between existing integer-ordered ones without renumbering
observability_surfaces:
  - Task edit form in /browser/objects/<iri> shows new Scheduled Start, Scheduled End, Estimated Duration fields after model reinstall
  - JSON validity checks: python3 -c "import json; json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld'))"
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Add scheduledStart/scheduledEnd/estimatedDuration to Task schema and ontology

**Add 3 scheduling properties (scheduledStart, scheduledEnd, estimatedDuration) to TaskShape and ontology, bump model to 2.2.0**

## What Happened

Added three new properties to the bpkm:Task type for calendar time-blocking:
- `bpkm:scheduledStart` (xsd:dateTime) — calendar block start time
- `bpkm:scheduledEnd` (xsd:dateTime) — calendar block end time  
- `bpkm:estimatedDuration` (xsd:string) — ISO 8601 duration format

Properties were inserted into the TaskShape's Dates group at fractional orders (6.1, 6.2, 6.3) between existing dueDate (order 6) and completedDate (order 7). Each has descriptive editHelpText explaining calendar time-blocking usage.

Three matching `owl:DatatypeProperty` declarations were added to the ontology with `rdfs:domain bpkm:Task` and appropriate ranges.

Manifest version bumped from 2.1.0 to 2.2.0.

## Verification

All four verification checks pass:
1. Shapes JSON-LD is valid JSON — no parse errors
2. Ontology JSON-LD is valid JSON — no parse errors
3. Manifest contains version 2.2.0
4. Structural check confirms exactly 3 new scheduling properties in TaskShape

Slice-level test verification (`pytest tests/test_calendar.py tests/test_calendar_editable.py`) — test files don't exist yet (expected, T04 creates them).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import json; json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld'))"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import json; json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld'))"` | 0 | ✅ pass | <1s |
| 3 | `grep -q '2.2.0' models/basic-pkm/manifest.yaml` | 0 | ✅ pass | <1s |
| 4 | Structural check: 3 new props in TaskShape (scheduledStart, scheduledEnd, estimatedDuration) | 0 | ✅ pass | <1s |
| 5 | `python3 -c "assert 'startdate' in 'scheduledstart'"` (planner's assumption) | 1 | ❌ fail | <1s |

## Diagnostics

- Verify shapes integrity: `python3 -c "import json; d=json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld')); props=[p for ps in d['@graph'] if ps.get('rdfs:label')=='Task Shape' for p in ps.get('sh:property',[]) if 'scheduled' in str(p.get('sh:path',{}).get('@id','')) or 'estimated' in str(p.get('sh:path',{}).get('@id',''))]; assert len(props)==3"`
- After model reinstall, check form editor at `/browser/objects/<task-iri>` for new fields in Dates section

## Deviations

The planner assumed `"startdate" in "scheduledstart"` is True — it's actually False because "scheduled" ends with "d" and "start" begins with "s", so "dstart" ≠ "startd". Same for `"enddate" in "scheduledend"` (False). This means `_detect_date_fields()` in `backend/app/views/service.py` will NOT auto-detect these fields via the existing `_START_DATE_PRIORITY` keywords. T02 must add "scheduledstart" and "scheduledend" to `_WELL_KNOWN_DATE_PATHS` and update `_START_DATE_PRIORITY` to include "scheduledstart" at highest priority.

## Known Issues

- Date field detection needs T02 code changes — the planner's assumption that existing detection would "just work" via substring matching is incorrect (see Deviations above).

## Files Created/Modified

- `models/basic-pkm/shapes/basic-pkm.jsonld` — Added 3 new property shapes to TaskShape (scheduledStart, scheduledEnd, estimatedDuration) in the Dates group
- `models/basic-pkm/ontology/basic-pkm.jsonld` — Added 3 new owl:DatatypeProperty declarations with domain bpkm:Task
- `models/basic-pkm/manifest.yaml` — Bumped version from 2.1.0 to 2.2.0
