---
id: S01
parent: M048
milestone: M048
provides:
  - Table View renders objects with labels, types, created, and modified columns
  - Cards View renders cards with data
  - Newly created objects have dcterms:created and dcterms:modified timestamps
requires:
  []
affects:
  - S03
key_files:
  - backend/app/views/service.py
  - backend/app/commands/handlers/object_create.py
  - backend/tests/test_view_prefix_fix.py
  - backend/tests/test_object_create_timestamps.py
key_decisions:
  - Applied inject_prefixes() at each query construction site rather than at _client.query() call level to keep the fix surgical
  - Track user-supplied predicates in a set during the property loop to detect duplicates for timestamp precedence
  - Define DCTERMS_CREATED and DCTERMS_MODIFIED as module-level URIRef constants for reuse
patterns_established:
  - inject_prefixes() must be applied to any reconstructed SPARQL query that uses prefixed names — the pattern of extracting WHERE body and rebuilding queries drops PREFIX declarations
  - Auto-injected metadata triples (dcterms:created, dcterms:modified) should respect user-supplied values by tracking predicates in a set during property iteration
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M048/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M048/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T18:13:32.866Z
blocker_discovered: false
---

# S01: Fix Table & Cards Views + Creation Timestamps

**Fixed Table and Cards views rendering zero results due to missing PREFIX declarations in reconstructed SPARQL queries, and added automatic dcterms:created/dcterms:modified timestamps to object creation.**

## What Happened

Two root causes were fixed in this slice:

**T01 — SPARQL PREFIX injection for views:** The `execute_table_query` and `execute_cards_query` methods in `backend/app/views/service.py` extract the WHERE body from the original scoped SPARQL query and reconstruct new count/data/subjects queries. These reconstructed queries dropped all PREFIX declarations from the original query. Since the WHERE body uses prefixed names (`rdf:type`, `rdfs:label|dcterms:title`, `dcterms:created`, `dcterms:modified`), RDF4J rejected them with SPARQL parse errors. The exceptions were silently caught and logged as warnings, resulting in zero results and the "No objects found" empty state. The fix imported `inject_prefixes` from `app.sparql.client` and wrapped all 4 reconstructed queries before sending to the triplestore. 6 unit tests verify prefix injection and non-empty results.

**T02 — Creation timestamps:** The `handle_object_create` handler created objects with `rdf:type` and user-supplied properties but never added `dcterms:created` or `dcterms:modified` timestamps. This left the Table View's "created" and "modified" columns permanently empty for all UI-created objects. The fix adds both timestamps as `xsd:dateTime` literals (UTC ISO 8601) after the property triples loop, with user-supplied value precedence tracked via a `user_predicates` set. 10 unit tests cover timestamp presence, format, datatype, and user-supplied precedence via both compact and full IRI keys.

## Verification

All 41 tests pass across 3 test files:

- `cd backend && .venv/bin/python -m pytest tests/test_view_prefix_fix.py -v` → 6 passed (prefix injection)
- `cd backend && .venv/bin/python -m pytest tests/test_object_create_timestamps.py -v` → 10 passed (timestamps)
- `cd backend && .venv/bin/python -m pytest tests/test_view_scope.py -v` → 25 passed (no regressions)

Total: 41 passed, 0 failed, 0 regressions.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

ViewSpec dataclass field names differed from plan assumptions (renderer_type/target_class instead of view_type/model_id) — test helper adapted. Tests use async def with await due to project's pytest-asyncio mode=AUTO. Both deviations are minor implementation details with no impact on functionality.

## Known Limitations

None. Both fixes are complete and tested.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/views/service.py` — Added inject_prefixes import and wrapped all 4 reconstructed SPARQL queries (2 in execute_table_query, 2 in execute_cards_query) with inject_prefixes() before triplestore execution
- `backend/app/commands/handlers/object_create.py` — Added auto-injection of dcterms:created and dcterms:modified timestamps (UTC ISO 8601, xsd:dateTime) with user-supplied value precedence
- `backend/tests/test_view_prefix_fix.py` — New test file: 6 tests verifying PREFIX injection in reconstructed table and cards queries
- `backend/tests/test_object_create_timestamps.py` — New test file: 10 tests verifying timestamp presence, format, datatype, and user-supplied precedence
