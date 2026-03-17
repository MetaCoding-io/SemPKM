---
id: T02
parent: S05
milestone: M009
provides:
  - EventStore.commit_bulk() — summary-only event metadata for batch ingestion
  - POST /api/commands/bulk platform endpoint
  - SDK CommandClient.bulk() async context manager with per-add permission enforcement
key_files:
  - backend/app/events/models.py
  - backend/app/events/store.py
  - backend/app/commands/router.py
  - backend/app/commands/schemas.py
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/tests/test_bulk_eventstore.py
key_decisions:
  - Bulk event uses BULK_EVENT_TYPE (sempkm:BulkEvent) distinct from EVENT_TYPE (sempkm:Event) for queryability
  - _BulkCollector is a separate class (not inline in context manager) for clean permission delegation
patterns_established:
  - Bulk summary metadata pattern: ~10 triples (type, timestamp, actor, role, label, summary, source, opCount, affectedCount) vs ~5N for standard commit
  - SDK context manager pattern for batched operations with fail-fast permission enforcement
observability_surfaces:
  - sempkm:BulkEvent type distinguishes bulk from standard events in SPARQL queries
  - sempkm:operationCount and sempkm:affectedCount provide batch size introspection
  - ValueError on >1000 ops includes actual count for diagnostics
duration: 25m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Bulk EventStore commit and SDK bulk context manager

**Added `commit_bulk()` to EventStore with summary-only metadata (~10 triples per batch), bulk commands endpoint, and SDK `bulk()` context manager with per-add permission enforcement.**

## What Happened

1. Added 5 bulk event vocabulary constants to `events/models.py`: `BULK_EVENT_TYPE`, `BULK_SUMMARY`, `BULK_SOURCE`, `BULK_OP_COUNT`, `BULK_AFFECTED_COUNT`.

2. Added `commit_bulk()` to `EventStore` — mirrors `commit()` for data triples and materialization (INSERT/DELETE into current state graph), but creates summary-only event metadata: one `sempkm:BulkEvent` with summary, source, operation count, and affected count. Enforces 1000-operation batch limit with `ValueError`. Runs everything in a single transaction with rollback on failure.

3. Added `POST /api/commands/bulk` endpoint to the commands router. Accepts `BulkCommandRequest` (commands list + summary + source), dispatches each through the standard handler pipeline, collects `Operation` objects, calls `commit_bulk()`. Returns event IRI and operation count.

4. Added `bulk()` async context manager to SDK `CommandClient`. Returns a `_BulkCollector` with `add(command_type, params)`. Each `add()` enforces command whitelist and IRI prefix checks immediately (fail fast). On `__aexit__`, posts collected commands to `/api/commands/bulk`. Empty batches skip the HTTP call.

5. Wrote 16 tests covering: BulkEvent type creation, summary metadata presence, no per-operation metadata leakage, materialization insert/delete ordering, single transaction, batch size limits (>1000 fails, =1000 succeeds), empty operations, rollback on failure, SDK bulk collection and posting, empty batch skip, permission enforcement per-add (command whitelist, IRI prefix, no-whitelist passthrough).

## Verification

- `cd backend && python -m pytest tests/test_bulk_eventstore.py -v` — 16/16 passed
- `cd backend && python -m pytest tests/test_app_permissions.py -v` — 26/26 passed (T01 tests unbroken)
- All 5 modified Python files parse cleanly (ast.parse)

### Slice-level verification status (T02 checkpoint):
- ✅ `tests/test_app_permissions.py` — 26 passed
- ✅ `tests/test_bulk_eventstore.py` — 16 passed
- ⏳ `tests/test_browser_visible.py` — not yet created (T03)
- ⏳ `tests/test_app_scheduler.py` — not yet created (T04)
- ⏳ `tests/test_app_admin.py` — exists, not yet extended (T04)

## Diagnostics

- SPARQL: `SELECT ?e ?s ?c WHERE { ?e a <urn:sempkm:BulkEvent> ; <urn:sempkm:summary> ?s ; <urn:sempkm:operationCount> ?c }` — lists all bulk events with summary and count
- `ValueError` on oversized batch includes actual count: "Bulk commit limited to 1000 operations, got {N}"
- SDK `PermissionError` on `bulk().add()` includes the offending command/IRI and the allowed list/prefix

## Deviations

- Added `BulkCommandRequest` and `BulkCommandResponse` Pydantic models to `schemas.py` for type-safe request parsing (plan didn't specify, but needed for proper FastAPI integration).

## Known Issues

None.

## Files Created/Modified

- `backend/app/events/models.py` — added 5 bulk event vocabulary constants
- `backend/app/events/store.py` — added `commit_bulk()` method to EventStore
- `backend/app/commands/schemas.py` — added `BulkCommandRequest` and `BulkCommandResponse` models
- `backend/app/commands/router.py` — added `POST /api/commands/bulk` endpoint, updated imports
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — added `_BulkCollector` class and `bulk()` context manager
- `backend/tests/test_bulk_eventstore.py` — new, 16 tests covering commit_bulk, endpoint, and SDK bulk
