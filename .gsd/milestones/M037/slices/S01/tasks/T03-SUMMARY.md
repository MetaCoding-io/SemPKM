---
id: T03
parent: S01
milestone: M037
provides:
  - 13 service-level tests covering upsert, partial update, staleness, TTL, defaults, and row uniqueness
  - 15 router-level tests covering POST/GET success, auth enforcement, SSE content type, validation, and stale context
key_files:
  - backend/tests/test_context_service.py
  - backend/tests/test_context_router.py
key_decisions:
  - Used zero-TTL technique to prove staleness without sleeps — instant, deterministic, no timing flakes
  - Direct DB row count assertion for upsert uniqueness rather than relying on ContextData return values alone
patterns_established:
  - SSE stream content-type test uses shutdown_event.set() before request to terminate the generator immediately — avoids hanging tests
  - Auth enforcement tests create a separate FastAPI app without the auth dependency override to prove 401 paths
observability_surfaces:
  - Test failures surface via pytest with full assertion diffs — run `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v`
duration: 8m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Unit tests for ContextService and context API endpoints

**Expanded context test suite to 28 tests (13 service, 15 router) proving upsert uniqueness, TTL staleness transitions, partial-update semantics, SSE stream content type, and auth enforcement**

## What Happened

T02 had already created both test files with 20 tests. Audited coverage against the T03 plan's must-haves and added 8 missing tests:

**Service tests added (6):**
- `test_update_partial_only_location` — partial update preserves untouched fields
- `test_calendar_busy_default_false` — new context defaults calendar_busy to False
- `test_device_id_persists_across_updates` — device_id survives subsequent updates
- `test_upsert_one_row_per_user` — queries DB directly to prove 3 updates = 1 row
- `test_includes_ttl_seconds` — custom TTL value flows through to ContextData
- `test_update_returns_all_fields` — all ContextData fields present after full update

**Router tests added (2):**
- `test_stream_requires_auth` — GET /api/context/stream returns 401 without auth
- `test_stream_content_type` — GET /api/context/stream returns `text/event-stream`

## Verification

All 28 tests pass with 0 failures in 0.81s.

Must-haves checklist:
- ≥8 service tests: ✅ (13)
- ≥6 router tests: ✅ (15)
- TTL staleness transition: ✅ (`test_stale_with_zero_ttl` proves False→True)
- Upsert one-row: ✅ (`test_upsert_one_row_per_user` queries DB count)
- All tests pass: ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v` | 0 | ✅ pass | 0.81s |

## Diagnostics

Run `cd backend && .venv/bin/python -m pytest tests/test_context_service.py tests/test_context_router.py -v` to verify the full context domain contract. Failures produce pytest assertion diffs showing expected vs actual values.

## Deviations

- T02 had already created both test files with 20 tests; T03 focused on gap analysis and adding 8 missing tests rather than writing from scratch.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_context_service.py` — Added 6 tests: partial update, calendar_busy default, device_id persistence, upsert row count, TTL passthrough, all-fields coverage (13 total)
- `backend/tests/test_context_router.py` — Added 2 tests: stream auth enforcement, SSE content-type verification (15 total)
- `.gsd/milestones/M037/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section per pre-flight requirement
