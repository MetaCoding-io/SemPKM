---
estimated_steps: 6
estimated_files: 5
---

# T02: Bulk EventStore commit and SDK bulk context manager

**Slice:** S05 — Scheduler, Permissions, Bulk EventStore & browserVisible
**Milestone:** M009

## Description

The RSS app (M010) will create 50-150 objects per feed poll. Per-operation metadata in EventStore creates ~5N triples — unacceptable overhead for batch ingestion. This task adds `EventStore.commit_bulk()` which records ~10 summary triples per batch instead, plus a platform endpoint and SDK context manager.

The bulk approach: data triples and materialization (INSERT/DELETE into `urn:sempkm:current`) are identical to `commit()`. Only the event metadata differs — one summary event graph instead of per-operation metadata. Undo granularity is all-or-nothing.

## Steps

1. **Add bulk event constants** to `backend/app/events/models.py`:
   - `BULK_EVENT_TYPE = SEMPKM.BulkEvent`
   - `BULK_SUMMARY = SEMPKM.summary`
   - `BULK_SOURCE = SEMPKM.source`
   - `BULK_OP_COUNT = SEMPKM.operationCount`
   - `BULK_AFFECTED_COUNT = SEMPKM.affectedCount`

2. **Add `commit_bulk()` to `EventStore`** (`backend/app/events/store.py`):
   - Same core pattern as `commit()` — accepts `operations: list[Operation]`, `user_iri: str`, `user_role: str`
   - Additional params: `summary: str`, `source: str`
   - Enforce max batch size: `if len(operations) > 1000: raise ValueError("Bulk commit limited to 1000 operations")`
   - Create event IRI via `mint_event_iri()`
   - Build event graph with summary metadata only:
     - `event_iri rdf:type sempkm:BulkEvent`
     - `event_iri prov:startedAtTime timestamp`
     - `event_iri prov:wasAssociatedWith user_iri`
     - `event_iri sempkm:performedByRole user_role`
     - `event_iri rdfs:label summary`
     - `event_iri sempkm:summary summary`
     - `event_iri sempkm:source source`
     - `event_iri sempkm:operationCount len(operations)`
     - `event_iri sempkm:affectedCount len(all_affected_iris)`
   - Add data triples from all operations (same as `commit()`)
   - Build materialization SPARQL (same INSERT/DELETE logic as `commit()`)
   - Execute in single transaction (same as `commit()`)
   - Return `EventResult`

3. **Add `POST /api/commands/bulk` endpoint** to `backend/app/commands/router.py`:
   - Accept body: `{"commands": [...], "summary": "...", "source": "..."}`
   - Dispatch each command through existing handler pipeline (same as single `/api/commands`)
   - Collect all resulting `Operation` objects
   - Call `EventStore.commit_bulk()` with the collected operations, summary, and source
   - Return `{"event_iri": "...", "operation_count": N}`
   - Require authentication (same as existing `/api/commands`)

4. **Add `bulk()` async context manager** to SDK `CommandClient` (`backend/sdk/sempkm_app_sdk/clients/commands.py`):
   - `bulk(summary: str, source: str)` returns an async context manager
   - The context manager object has an `add(command_type, params)` method
   - `add()` enforces permissions immediately (command whitelist + IRI prefix) — fail fast, don't wait until commit
   - On `__aexit__`, POST all collected commands to `/api/commands/bulk` with summary and source
   - If the collection is empty on exit, skip the HTTP call

5. **Write tests** (`backend/tests/test_bulk_eventstore.py`):
   - Test `commit_bulk()` creates event graph with `sempkm:BulkEvent` type (mock triplestore)
   - Test summary metadata triples present (summary, source, operationCount, affectedCount)
   - Test materialization identical to `commit()` (same INSERT/DELETE SPARQL patterns)
   - Test batch over 1000 raises `ValueError`
   - Test empty operations list is handled gracefully
   - Test SDK `bulk()` context manager: collects commands, posts to bulk endpoint
   - Test SDK `bulk()` enforces permissions per-add (raises PermissionError immediately)
   - Test SDK `bulk()` with empty batch skips HTTP call
   - Note: The SDK bulk tests will need T01's permission enforcement. If running T02 before T01, mock the permission checks or use `allowed_commands=["*"]` equivalent.

6. **Verify**: `cd backend && python -m pytest tests/test_bulk_eventstore.py -v`

## Must-Haves

- [ ] `commit_bulk()` creates summary-only event metadata (~10 triples, not ~5N)
- [ ] Data triples and materialization identical to `commit()`
- [ ] Batch size limit enforced (1000 max) with clear error
- [ ] Platform `/api/commands/bulk` endpoint dispatches and commits
- [ ] SDK `ctx.commands.bulk()` context manager collects and posts
- [ ] SDK bulk `add()` enforces permissions per-add (fail fast)

## Verification

- `cd backend && python -m pytest tests/test_bulk_eventstore.py -v` — all pass
- Bulk event graph has `rdf:type sempkm:BulkEvent` and summary predicates
- Materialization SPARQL matches `commit()` pattern

## Observability Impact

- Signals added: `sempkm:BulkEvent` type distinguishes bulk from standard events in event log
- How a future agent inspects this: SPARQL query for `?e a sempkm:BulkEvent` returns bulk events with summary, source, operation count
- Failure state exposed: `ValueError` on oversized batch with clear message and count

## Inputs

- `backend/app/events/store.py` — existing `EventStore.commit()` method (365 lines total) — the bulk variant mirrors its structure
- `backend/app/events/models.py` — existing event vocabulary constants
- `backend/app/commands/router.py` — existing `POST /api/commands` endpoint pattern to mirror for bulk
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — CommandClient (T01 adds permission enforcement; bulk builds on top)
- `backend/app/rdf/namespaces.py` — `SEMPKM` namespace for new predicates

## Expected Output

- `backend/app/events/models.py` — 5 new constants for bulk event vocabulary
- `backend/app/events/store.py` — new `commit_bulk()` method alongside existing `commit()`
- `backend/app/commands/router.py` — new `POST /api/commands/bulk` endpoint
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — `bulk()` async context manager added
- `backend/tests/test_bulk_eventstore.py` — ~10-15 tests covering commit, endpoint, and SDK
