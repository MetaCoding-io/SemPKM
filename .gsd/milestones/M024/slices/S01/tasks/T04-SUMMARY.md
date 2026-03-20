---
id: T04
parent: S01
milestone: M024
provides:
  - PersonMatcher with 5-step resolution cascade (cache → email SPARQL → API fetch → externalId SPARQL → create)
  - LRU cache per sync run prevents duplicate API calls
  - Complete S01 slice: all 4 service modules + app routes + templates + 277 tests
key_files:
  - apps/monday-sync/services/person_matcher.py
  - backend/tests/test_monday_person_matcher.py
key_decisions:
  - Monday.com user_id converted to string for cache key and bpkm:externalId storage (numeric IDs stored as strings for SPARQL compatibility)
patterns_established:
  - PersonMatcher follows identical pattern to Jira's person_matcher.py — 5-step cascade with injected graph/command/provider clients, same SPARQL IRIs, same _slugify function
observability_surfaces:
  - Logger `monday_sync.person` at DEBUG (cache hits, creation params), INFO (not currently emitted in resolve path), WARNING (API fetch failures)
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T04: Person matcher, board selection routes, and connect_status wiring

**Created PersonMatcher with 5-step resolution cascade and 27 tests, completing S01 with 277 total tests across all 4 Monday.com Sync service modules.**

## What Happened

Created `person_matcher.py` following the exact Jira PersonMatcher pattern, adapted for Monday.com's numeric user IDs. The PersonMatcher resolves Monday.com users to SemPKM Person IRIs through a 5-step cascade: (1) in-memory cache hit, (2) SPARQL email lookup via foaf:mbox/crm:email UNION with case-insensitive FILTER, (3) Monday.com API fetch via `get_users([user_id])` when no email is provided, (4) SPARQL fallback via bpkm:externalId, (5) create new Person via command_client.

The app.py and connect_status.html were already fully wired from T01 with MondayClient import, board-fetching routes, sync-config, sync-now, and disconnect — no updates needed.

Wrote 27 tests covering all resolution paths: cache hits, email matches via both foaf:mbox and crm:email, API fetch when email not provided, externalId fallback, person creation on full miss, API failure graceful handling, empty API results, string/numeric cache key equivalence, case-insensitive email queries, and 8 _slugify edge cases.

## Verification

- 27 person matcher tests pass
- 277 total tests pass across all 4 test files (31 + 64 + 155 + 27)
- All Python files in apps/monday-sync/ parse without syntax errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_person_matcher.py -v` | 0 | ✅ pass | 1.7s |
| 2 | `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py tests/test_monday_client.py tests/test_monday_field_mapper.py tests/test_monday_person_matcher.py -v` | 0 | ✅ pass (277 tests) | 6.8s |
| 3 | `find apps/monday-sync -name "*.py" -exec python3 -c "import ast; ast.parse(open('{}').read())" \;` | 0 | ✅ pass | 3.3s |

## Diagnostics

- **Logger:** `monday_sync.person` — set to DEBUG to trace full resolution cascade per user_id
- **Cache inspection:** `PersonMatcher._cache` dict maps `str(user_id)` → Person IRI; populated during sync run, not persisted
- **API failure path:** When `monday_client.get_users()` raises, warning logged and resolution falls through to externalId SPARQL or person creation — never fatal
- **Person creation params:** Slug derived from display_name → email local part → user_id string; bpkm:externalId always stored as string

## Deviations

- app.py and connect_status.html required no updates — T01 already wired MondayClient import, board fetching, sync config routes, and the full template with board checkboxes, sync direction/interval, sync-now, sync stats, and disconnect sections.

## Known Issues

None.

## Files Created/Modified

- `apps/monday-sync/services/person_matcher.py` — PersonMatcher with 5-step cascade, LRU cache, SPARQL email/externalId lookup, person creation (~150 lines)
- `backend/tests/test_monday_person_matcher.py` — 27 tests with MockGraphClient, MockCommandClient, MockMondayClient (~400 lines)
- `.gsd/milestones/M024/slices/S01/tasks/T04-PLAN.md` — added Observability Impact section
- `.gsd/milestones/M024/slices/S01/S01-PLAN.md` — marked T04 as done
