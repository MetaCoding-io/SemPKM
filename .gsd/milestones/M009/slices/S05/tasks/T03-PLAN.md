---
estimated_steps: 5
estimated_files: 5
---

# T03: Bulk EventStore extension and SDK bulk context manager

**Slice:** S05 — Scheduler, Permissions, Bulk EventStore & browserVisible
**Milestone:** M009

## Description

Extend `EventStore` with `commit_bulk()` that records summary metadata (~10 triples per batch instead of ~5N per operation). Add a `POST /api/commands/bulk` endpoint. Add `bulk()` async context manager on SDK `CommandClient` that accumulates operations and sends as a batch.

## Steps

1. Add vocabulary constants in `backend/app/events/models.py`: `BULK_EVENT_TYPE = "sempkm:BulkEvent"`, `EVENT_SUMMARY = "sempkm:summary"`, `EVENT_SOURCE = "sempkm:source"`, `EVENT_OPERATION_COUNT = "sempkm:operationCount"`, `EVENT_AFFECTED_COUNT = "sempkm:affectedCount"`.
2. Implement `EventStore.commit_bulk(operations: list[dict], performed_by: str, summary: str, source: str)` in `store.py`. Same transactional pattern as `commit()` — mint event IRI, create named graph. Metadata: event type `sempkm:BulkEvent`, timestamp, actor, summary, source, operation_count, affected_count (count of unique subject IRIs). Accumulate data triples from all operations (dispatch each through existing handler logic). Materialize identically to single commit. Raise `ValueError` if `len(operations) > 1000`.
3. Add `POST /api/commands/bulk` endpoint in `backend/app/commands/router.py` (or a new file). Accepts `{"commands": [...], "summary": str, "source": str}`. Validates each command. Routes through `EventStore.commit_bulk()`. Returns event IRI.
4. Add `bulk()` async context manager on SDK `CommandClient`. On enter, start accumulating operations in a list. On exit, POST to `/api/commands/bulk` with the batch. On exception, discard batch. Expose `operation_count` property during accumulation.
5. Write `test_bulk_eventstore.py` — summary metadata structure, operation count, affected count, batch size limit enforcement (>1000 raises), all-or-nothing undo semantics (mock transaction failure).

## Must-Haves

- [ ] `commit_bulk()` produces BulkEvent type with summary metadata (~10 triples)
- [ ] Operation count and affected count are correct in metadata
- [ ] Batch size limit enforced (>1000 raises ValueError)
- [ ] Data triples still materialize correctly
- [ ] Bulk API endpoint accepts and processes command batches
- [ ] SDK `bulk()` context manager accumulates and sends

## Verification

- `cd backend && .venv/bin/pytest tests/test_bulk_eventstore.py -v` — all pass
- `cd backend && .venv/bin/pytest tests/ -v` — full suite, zero regressions

## Inputs

- `backend/app/events/store.py` — existing `commit()` method (base pattern for `commit_bulk()`)
- `backend/app/events/models.py` — existing vocabulary constants
- `backend/app/commands/router.py` — existing single-command dispatch endpoint
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — existing CommandClient (add bulk method)

## Expected Output

- `backend/app/events/store.py` — modified, `commit_bulk()` method added
- `backend/app/events/models.py` — modified, bulk vocabulary constants
- `backend/app/commands/router.py` — modified, bulk endpoint
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — modified, `bulk()` context manager
- `backend/tests/test_bulk_eventstore.py` — new, ~10-12 tests

## Observability Impact

- **Logger:** `app.events.store` — INFO on bulk commit completion with operation count, affected count, and source identifier.
- **API response:** `POST /api/commands/bulk` returns `operation_count` and `affected_count` in the JSON response for client-side observability.
- **Event metadata:** Bulk events are typed `sempkm:BulkEvent` (distinguishable from regular `sempkm:Event`) with `sempkm:operationCount`, `sempkm:affectedCount`, `sempkm:summary`, and `sempkm:source` predicates — queryable via SPARQL for audit/debug.
- **Failure visibility:** Batch size >1000 returns HTTP 400 with descriptive error. Transaction failures trigger rollback (same pattern as single commit). Invalid commands in bulk batch return HTTP 400 identifying the offending command.
