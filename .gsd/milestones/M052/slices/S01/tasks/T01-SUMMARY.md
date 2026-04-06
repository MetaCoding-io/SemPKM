---
id: T01
parent: S01
milestone: M052
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/tests/test_kanban.py
key_decisions:
  - Enrichment detection reuses _detect_date_fields() for date and scans form properties for priority — no new SHACL queries needed
  - Priority detection excludes the status field by path comparison to avoid treating status as priority
  - _build_enrichment_metadata() factored as static helper for reuse in both success and error paths
duration: 
verification_result: passed
completed_at: 2026-04-06T01:55:34.824Z
blocker_discovered: false
---

# T01: Added _detect_enrichment_fields() to kanban backend, extended SPARQL with OPTIONAL priority/date clauses, and enriched item dicts with priority and due_date keys

**Added _detect_enrichment_fields() to kanban backend, extended SPARQL with OPTIONAL priority/date clauses, and enriched item dicts with priority and due_date keys**

## What Happened

Added _detect_enrichment_fields() method to ViewSpecService that scans SHACL shapes for priority (sh:in with 'priority' in path or fallback non-status sh:in) and date (reuses _detect_date_fields start field) properties. Extended _build_kanban_select() with optional priority_path and date_path parameters that add OPTIONAL SPARQL clauses. Updated execute_kanban_query() to auto-detect enrichment, include priority/due_date in item dicts, and return enrichment metadata. Router now passes enrichment to kanban template context. Added 15 new tests covering all enrichment functionality.

## Verification

Ran full kanban test suite: cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v — all 33 tests pass (18 existing + 15 new). LSP diagnostics confirmed no new type errors in modified files.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v` | 0 | ✅ pass | 640ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/tests/test_kanban.py`
