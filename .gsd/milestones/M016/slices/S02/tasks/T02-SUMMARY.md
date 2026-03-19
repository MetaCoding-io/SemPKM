---
id: T02
parent: S02
milestone: M016
provides:
  - PersonMatcher class for resolving Linear assignees to SemPKM Person IRIs via SPARQL lookup and command API creation
  - In-memory email→IRI cache for deduplication within a sync run
key_files:
  - apps/linear-sync/services/person_matcher.py
  - backend/tests/test_person_matcher.py
key_decisions:
  - Case-insensitive cache keying via email.lower() — avoids duplicate SPARQL queries for mixed-case emails
  - Slug fallback to email local part when display_name is absent — keeps IRIs readable
patterns_established:
  - MockGraphClient / MockCommandClient stubs for async SDK client testing
observability_surfaces:
  - Logger linear_sync.person_matcher — DEBUG on cache hits and person creation (email + slug)
  - PersonMatcher._cache dict inspectable during sync for email→IRI mappings
duration: 12m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Build person matcher with unit tests

**Implemented PersonMatcher class with SPARQL email lookup, command API person creation, and in-memory cache — 12 unit tests all passing.**

## What Happened

Built `PersonMatcher` with a single public method `match_or_create(email, display_name)` that follows a three-step resolution: (1) check in-memory cache, (2) SPARQL query for existing Person by `foaf:mbox` or `crm:email` with case-insensitive matching, (3) create new Person via `object.create` command on miss. Cache keys are lowercased emails so mixed-case lookups share entries.

The slugify helper strips non-alphanumeric characters and collapses whitespace to hyphens. When no display name is provided, the email local part (before `@`) is used for both the slug and the `dcterms:title`.

Tests use the same importlib loading pattern as T01's field mapper tests. Mock clients record all calls for assertion — `MockGraphClient.queries` and `MockCommandClient.commands` lists.

## Verification

- `cd backend && .venv/bin/pytest tests/test_person_matcher.py -v` — 12/12 passed
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/person_matcher.py').read())"` — syntax OK
- `cd backend && .venv/bin/pytest tests/test_field_mapper.py tests/test_person_matcher.py -v` — 61/61 passed (combined suite)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/pytest tests/test_person_matcher.py -v` | 0 | ✅ pass | 0.03s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/person_matcher.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/pytest tests/test_field_mapper.py tests/test_person_matcher.py -v` | 0 | ✅ pass | 0.06s |
| 4 | `cd backend && .venv/bin/pytest tests/test_sync_engine.py -v` | — | ⏳ pending T03 | — |

## Diagnostics

- `PersonMatcher._cache` — in-memory dict, inspectable during debugging. Keys are lowercased emails, values are Person IRIs.
- Logger `linear_sync.person_matcher` — DEBUG level messages for cache hits and person creation events.
- Mock clients in tests record all calls: `MockGraphClient.queries` (list of SPARQL strings), `MockCommandClient.commands` (list of `{command, params}` dicts).

## Deviations

- Added 2 extra tests beyond the plan's ~10: `test_slugify_special_characters` and `test_email_local_part` — direct unit tests of helper functions for robustness. Total: 12 tests.

## Known Issues

None.

## Files Created/Modified

- `apps/linear-sync/services/person_matcher.py` — PersonMatcher class (~120 lines) with SPARQL lookup, command creation, slugify, and caching
- `backend/tests/test_person_matcher.py` — 12 unit tests with MockGraphClient and MockCommandClient
- `.gsd/milestones/M016/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section per pre-flight requirement
