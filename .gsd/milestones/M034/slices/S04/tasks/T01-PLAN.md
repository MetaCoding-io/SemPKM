---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T01: Add recurrence schema properties and python-dateutil dependency

**Slice:** S04 — Recurring Tasks & RRULE Expansion
**Milestone:** M034

## Description

Add two SHACL properties (`bpkm:recurrenceRule` and `bpkm:exceptionDates`) to TaskShape and their OWL declarations to the ontology. Add `python-dateutil~=2.9.0` to the backend dependencies. This is the foundation task — all subsequent tasks depend on the schema properties existing and the dateutil library being available.

Note: `bpkm:recurrenceRule` already exists on EventShape (order 13) and in the ontology (domain: `bpkm:Event`). We're extending it to Tasks and adding the new `exceptionDates` property.

**Docker rebuild required** after adding python-dateutil to pyproject.toml. The executor should note this but doesn't need to perform the rebuild — subsequent tasks' verification will handle that.

## Steps

1. **Edit `models/basic-pkm/shapes/basic-pkm.jsonld`** — Find the `bpkm:TaskShape` entry in the `@graph` array. After the `estimatedDuration` property (sh:order 6.3), add two new properties to the `sh:property` array:
   - `bpkm:recurrenceRule`: `sh:path {"@id": "bpkm:recurrenceRule"}`, `sh:datatype {"@id": "xsd:string"}`, `sh:maxCount 1`, `sh:order 6.4`, `sh:group {"@id": "bpkm:TaskDatesGroup"}`, `sh:name "Recurrence Rule"`, `sh:description "RFC 5545 RRULE string, e.g. FREQ=WEEKLY;BYDAY=FR"`
   - `bpkm:exceptionDates`: `sh:path {"@id": "bpkm:exceptionDates"}`, `sh:datatype {"@id": "xsd:string"}`, `sh:maxCount 1`, `sh:order 6.5`, `sh:group {"@id": "bpkm:TaskDatesGroup"}`, `sh:name "Exception Dates"`, `sh:description "Comma-separated ISO dates to skip, e.g. 2026-04-03,2026-04-10"`

2. **Edit `models/basic-pkm/ontology/basic-pkm.jsonld`** — Two changes:
   - **Update `bpkm:recurrenceRule`** domain from `{"@id": "bpkm:Event"}` to `{"owl:unionOf": {"@list": [{"@id": "bpkm:Event"}, {"@id": "bpkm:Task"}]}}` (or remove domain restriction entirely — simpler, since OWL open-world assumption means no domain is fine)
   - **Add `bpkm:exceptionDates`** entry: `{"@id": "bpkm:exceptionDates", "@type": "owl:DatatypeProperty", "rdfs:label": "Exception Dates", "rdfs:comment": "Comma-separated ISO date strings for excluded recurrence instances", "rdfs:domain": {"@id": "bpkm:Task"}, "rdfs:range": {"@id": "xsd:string"}}`

3. **Edit `backend/pyproject.toml`** — Add `"python-dateutil~=2.9.0"` to the `dependencies` list.

4. **Validate** — Parse the modified JSON-LD files to ensure they're valid JSON. Verify the new properties appear at correct positions.

## Must-Haves

- [ ] TaskShape has `bpkm:recurrenceRule` property at sh:order 6.4 in TaskDatesGroup
- [ ] TaskShape has `bpkm:exceptionDates` property at sh:order 6.5 in TaskDatesGroup
- [ ] Ontology has `bpkm:exceptionDates` as owl:DatatypeProperty
- [ ] Ontology `bpkm:recurrenceRule` domain includes bpkm:Task (not just bpkm:Event)
- [ ] `python-dateutil~=2.9.0` in pyproject.toml dependencies

## Verification

- `python3 -c "import json; d=json.load(open('models/basic-pkm/shapes/basic-pkm.jsonld')); ts=[i for i in d['@graph'] if i.get('@id')=='bpkm:TaskShape'][0]; paths=[p['sh:path']['@id'] for p in ts['sh:property']]; assert 'bpkm:recurrenceRule' in paths; assert 'bpkm:exceptionDates' in paths; print('TaskShape OK')"` — prints "TaskShape OK"
- `python3 -c "import json; d=json.load(open('models/basic-pkm/ontology/basic-pkm.jsonld')); items={i['@id']:i for i in d['@graph']}; assert 'bpkm:exceptionDates' in items; print('Ontology OK')"` — prints "Ontology OK"
- `grep -q 'python-dateutil' backend/pyproject.toml` — exits 0

## Inputs

- `models/basic-pkm/shapes/basic-pkm.jsonld` — existing TaskShape to extend
- `models/basic-pkm/ontology/basic-pkm.jsonld` — existing ontology to extend
- `backend/pyproject.toml` — existing dependencies list

## Expected Output

- `models/basic-pkm/shapes/basic-pkm.jsonld` — TaskShape with 2 new recurrence properties
- `models/basic-pkm/ontology/basic-pkm.jsonld` — exceptionDates declaration + recurrenceRule domain update
- `backend/pyproject.toml` — python-dateutil added
