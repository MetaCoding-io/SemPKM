---
id: T01
parent: S04
milestone: M034
provides:
  - bpkm:recurrenceRule SHACL property on TaskShape (sh:order 6.4)
  - bpkm:exceptionDates SHACL property on TaskShape (sh:order 6.5)
  - bpkm:exceptionDates OWL DatatypeProperty in ontology
  - bpkm:recurrenceRule domain expanded to Event + Task
  - python-dateutil~=2.9.0 backend dependency
key_files:
  - models/basic-pkm/shapes/basic-pkm.jsonld
  - models/basic-pkm/ontology/basic-pkm.jsonld
  - backend/pyproject.toml
key_decisions:
  - Used owl:unionOf for recurrenceRule domain (Event + Task) rather than removing domain — preserves semantic clarity
  - exceptionDates uses comma-separated ISO date string rather than multi-valued property — simpler parsing for EXDATE expansion
patterns_established:
  - Recurrence properties sit at sh:order 6.4/6.5 in TaskDatesGroup, between estimatedDuration (6.3) and completedDate (7)
observability_surfaces:
  - none (schema-only change; runtime observability comes in T02)
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Add recurrence schema properties and python-dateutil dependency

**Added bpkm:recurrenceRule and bpkm:exceptionDates SHACL properties to TaskShape, expanded recurrenceRule ontology domain to cover Task, and added python-dateutil~=2.9.0 dependency**

## What Happened

Three files edited:
1. **Shapes** — Added two properties to TaskShape's `sh:property` array after `estimatedDuration` (order 6.3): `recurrenceRule` at order 6.4 and `exceptionDates` at order 6.5, both in `TaskDatesGroup` with `xsd:string` datatype and `maxCount 1`. Included descriptive `sempkm:editHelpText` for the SHACL form renderer.
2. **Ontology** — Changed `bpkm:recurrenceRule` domain from `{"@id": "bpkm:Event"}` to `owl:unionOf [Event, Task]`. Added new `bpkm:exceptionDates` as `owl:DatatypeProperty` with domain `bpkm:Task` and range `xsd:string`.
3. **Dependencies** — Added `"python-dateutil~=2.9.0"` to pyproject.toml. Docker rebuild needed before T02 can use dateutil at runtime.

## Verification

All five must-haves confirmed via programmatic checks:
- TaskShape contains `bpkm:recurrenceRule` at order 6.4 in TaskDatesGroup
- TaskShape contains `bpkm:exceptionDates` at order 6.5 in TaskDatesGroup
- Ontology has `bpkm:exceptionDates` as `owl:DatatypeProperty`
- Ontology `bpkm:recurrenceRule` domain is `owl:unionOf [Event, Task]`
- `python-dateutil~=2.9.0` appears in pyproject.toml dependencies

Both JSON-LD files parse as valid JSON.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "...assert 'bpkm:recurrenceRule' in paths; assert 'bpkm:exceptionDates' in paths; print('TaskShape OK')"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "...assert 'bpkm:exceptionDates' in items; print('Ontology OK')"` | 0 | ✅ pass | <1s |
| 3 | `grep -q 'python-dateutil' backend/pyproject.toml` | 0 | ✅ pass | <1s |
| 4 | Detailed must-have validation (orders, groups, domain union, types) | 0 | ✅ pass | <1s |

## Diagnostics

Schema-only change — no runtime diagnostics. To inspect the schema properties:
- `python3 -c "import json; d=json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld')); ts=[i for i in d['@graph'] if i.get('@id')=='bpkm:TaskShape'][0]; [print(f\"{p['sh:path']['@id']}: order={p.get('sh:order')}\") for p in ts['sh:property'] if 'recurrence' in p['sh:path']['@id'].lower() or 'exception' in p['sh:path']['@id'].lower()]"`
- After model reinstall, the properties will appear in the SHACL form for Task objects.

## Deviations

None — all edits matched the plan exactly.

## Known Issues

- Docker rebuild required before `python-dateutil` is available at runtime. T02 will handle this.

## Files Created/Modified

- `models/basic-pkm/shapes/basic-pkm.jsonld` — Added recurrenceRule (order 6.4) and exceptionDates (order 6.5) to TaskShape
- `models/basic-pkm/ontology/basic-pkm.jsonld` — Added exceptionDates property; expanded recurrenceRule domain to Event + Task
- `backend/pyproject.toml` — Added python-dateutil~=2.9.0 dependency
