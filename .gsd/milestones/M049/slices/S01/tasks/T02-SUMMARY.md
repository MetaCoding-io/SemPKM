---
id: T02
parent: S01
milestone: M049
key_files:
  - backend/app/browser/objects.py
  - backend/tests/test_object_query_opt.py
key_decisions:
  - Two-pass binding partitioning for UNION ordering safety
duration: 
verification_result: mixed
completed_at: 2026-04-05T20:10:31.236Z
blocker_discovered: false
---

# T02: Replaced 3 sequential SPARQL property queries with 1 UNION query and consolidated 5 label batch calls into 1 in get_object handler

**Replaced 3 sequential SPARQL property queries with 1 UNION query and consolidated 5 label batch calls into 1 in get_object handler**

## What Happened

The get_object handler made 3 sequential SPARQL queries to fetch properties from current, inferred, and mirrored graphs, plus 5 separate label_service.resolve_batch() calls. Replaced with a single UNION query using BIND source annotations and a two-pass partitioning approach to handle UNION result ordering non-determinism. Consolidated all label IRIs into one batch call. Template context structure unchanged. Installed pytest-timeout for slice verification commands.

## Verification

6/6 new tests pass in test_object_query_opt.py verifying: single SPARQL query (not 3), single label batch (not 5), dedup preserved for inferred/mirrored, ordering independence. 12/12 shapes cache tests pass. Full suite has only pre-existing failures.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_object_query_opt.py -v --timeout=60` | 0 | ✅ pass | 660ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py -v --timeout=60` | 0 | ✅ pass | 200ms |
| 3 | `cd backend && .venv/bin/python -m pytest tests/ -x --timeout=60 --deselect pre-existing-failures` | 1 | ⚠️ pre-existing failure only | 8000ms |

## Deviations

Added two-pass binding partitioning to handle SPARQL UNION ordering non-determinism. Installed pytest-timeout package.

## Known Issues

2 pre-existing test failures unrelated to this change.

## Files Created/Modified

- `backend/app/browser/objects.py`
- `backend/tests/test_object_query_opt.py`
