---
estimated_steps: 4
estimated_files: 2
---

# T03: Batch event log user lookup

**Slice:** S05 — Dependency Pinning & Cleanup
**Milestone:** M002

## Description

Replace the N+1 SQL query pattern in the event log endpoint's user display name resolution with a single batched `SELECT ... WHERE id IN (...)` query. Write a unit test that verifies the batched lookup helper. This satisfies PERF-01.

## Steps

1. In `backend/app/browser/events.py`, extract user IRI resolution into a standalone async helper function `resolve_user_names(db: AsyncSession, user_iris: list[str]) -> dict[str, str]` that:
   - Parses UUIDs from `urn:sempkm:user:{uuid}` IRIs
   - Skips IRIs that don't match the pattern or have invalid UUIDs
   - Guards against empty list (returns `{}` immediately, no query)
   - Executes a single `select(User).where(User.id.in_(uuid_list))` query
   - Returns a `{iri: display_name_or_email}` dict
2. Replace the for-loop in `event_log()` (lines ~62-79) with a call to `resolve_user_names(db, user_iris)`
3. Write `backend/tests/test_event_user_lookup.py` that tests `resolve_user_names` with:
   - Empty list → returns empty dict, no query executed
   - Invalid URIs (no match, bad UUID) → skipped gracefully
   - Valid URIs → correct dict mapping (using a mock or in-memory SQLite session)
4. Run the test and verify it passes

## Must-Haves

- [ ] `resolve_user_names()` extracted as a reusable async function
- [ ] Single `WHERE id IN (...)` query replaces N individual queries
- [ ] Empty user_iris list does not execute any SQL query
- [ ] Invalid URIs are skipped without raising exceptions
- [ ] Unit test covers empty, invalid, and valid cases
- [ ] Event log endpoint behavior is unchanged (same template context)

## Verification

- `cd backend && .venv/bin/pytest tests/test_event_user_lookup.py -v` — all tests pass
- Manual code inspection: no for-loop with individual `SELECT ... WHERE id = ?` remains in event_log()

## Observability Impact

- Signals added/changed: The existing `logger.warning("Failed to resolve user IRI %s", ...)` is preserved for individual parse failures; the overall query is now a single round-trip visible in SQLAlchemy query logging
- How a future agent inspects this: Enable `echo=True` on the SQLAlchemy engine and observe a single `SELECT ... WHERE id IN (...)` in logs when viewing event log
- Failure state exposed: Individual IRI parse failures still logged at WARNING level; the batch query itself uses standard SQLAlchemy error handling

## Inputs

- `backend/app/browser/events.py` — current N+1 pattern (lines 62-79)
- `backend/app/auth/models.py` — `User` model with `id: UUID`, `display_name`, `email`

## Expected Output

- `backend/app/browser/events.py` — refactored with `resolve_user_names()` helper and batched query
- `backend/tests/test_event_user_lookup.py` — unit tests for the helper function
