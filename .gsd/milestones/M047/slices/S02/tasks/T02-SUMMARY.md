---
id: T02
parent: S02
milestone: M047
key_files:
  - models/ppv/views/ppv.jsonld
  - models/ppv/rules/ppv.ttl
  - backend/tests/test_ppv_ontology.py
key_decisions:
  - Kanban ViewSpecs omit columns/sortDefault since kanban renderer auto-detects status field via SHACL sh:in
  - PillarScoreDateDenormRule uses schema:startDate to enable calendar/timeline views for PillarScore
duration: 
verification_result: passed
completed_at: 2026-04-04T23:43:13.146Z
blocker_discovered: false
---

# T02: Added 4 new ViewSpecs, PillarScoreDateDenormRule with schema prefix, and 99-test validation suite for all PPV ontology expansion artifacts

**Added 4 new ViewSpecs, PillarScoreDateDenormRule with schema prefix, and 99-test validation suite for all PPV ontology expansion artifacts**

## What Happened

Added 4 new ViewSpecs to the PPV views file (pillarscore table, action kanban, project kanban, action-by-context table) bringing total to 23. Added schema prefix and PillarScoreDateDenormRule to the rules file — a SHACL-AF SPARQLRule that derives schema:startDate on PillarScore from linked WeeklyReview. Created comprehensive test_ppv_ontology.py with 99 tests across 9 test classes covering ontology classes, 25 properties, SHACL shapes, score constraints, PropertyGroups, ViewSpecs, rules, manifest icons, combined graph parse, and cross-reference validation.

## Verification

Rules file parses as valid Turtle (63 triples). All 99 pytest tests pass in 0.29s covering ontology, shapes, views, rules, manifest, and cross-references.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g=Graph(); g.parse('../models/ppv/rules/ppv.ttl', format='turtle'); print(f'Rules OK: {len(g)} triples')"` | 0 | ✅ pass | 500ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_ppv_ontology.py -v` | 0 | ✅ pass | 290ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `models/ppv/views/ppv.jsonld`
- `models/ppv/rules/ppv.ttl`
- `backend/tests/test_ppv_ontology.py`
