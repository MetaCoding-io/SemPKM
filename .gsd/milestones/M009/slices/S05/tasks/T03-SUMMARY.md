---
id: T03
parent: S05
milestone: M009
provides:
  - EventStore.commit_bulk() with BulkEvent type and summary metadata (~7-8 triples per batch)
  - POST /api/commands/bulk endpoint for batch command execution
  - SDK CommandClient.bulk() async context manager for accumulating and submitting batches
  - Bulk vocabulary constants (BulkEvent, summary, source, operationCount, affectedCount)
key_files:
  - backend/app/events/store.py
  - backend/app/events/models.py
  - backend/app/commands/router.py
  - backend/sdk/sempkm_app_sdk/clients/commands.py (worktree)
  - backend/tests/test_bulk_eventstore.py
key_decisions:
  - Bulk metadata records only summary-level triples (~7-8) not per-operation metadata — fixes O(N) overhead for batch imports
  - Batch size limit set to 1000 operations (ValueError beyond) — prevents unbounded memory use
  - SDK bulk() context manager discards batch silently on exception — no partial commits
patterns_established:
  - BulkAccumulator pattern separates permission checking (synchronous, on add()) from network submission (async, on context exit)
  - Permission check delegation — BulkAccumulator._check_permissions delegates to CommandClient._check_permissions to avoid duplicating validation logic
observability_surfaces:
  - Logger app.events.store at INFO on bulk commit completion with operation count, affected count, and source
  - POST /api/commands/bulk returns operation_count and affected_count in response JSON
  - BulkEvent typed events (sempkm:BulkEvent) distinguishable from regular sempkm:Event in SPARQL queries
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Bulk EventStore extension and SDK bulk context manager

**Added commit_bulk() with BulkEvent summary metadata, POST /api/commands/bulk endpoint, and SDK bulk() context manager — 18 tests pass**

## What Happened

Added bulk event support across three layers:

1. **EventStore.commit_bulk()** — same transactional pattern as commit() but writes ~7-8 summary triples per batch (type, timestamp, actor, summary, source, operationCount, affectedCount) instead of ~5N per-operation metadata. Data triple materialization is identical. Batch size capped at 1000.

2. **POST /api/commands/bulk** — new endpoint accepting `{commands: [...], summary, source}`. Validates each command through existing Command schema, dispatches through dispatcher, routes through commit_bulk(). Returns event_iri, timestamp, operation_count, affected_count.

3. **SDK CommandClient.bulk()** — async context manager yielding a BulkAccumulator. `add()` runs permission checks synchronously (command whitelist + IRI prefix). On clean exit, POSTs accumulated batch to /api/commands/bulk. On exception, discards batch. Empty batches skip the POST.

Refactored CommandClient permission logic into a shared `_check_permissions()` method used by both `execute()` and `BulkAccumulator.add()`.

## Verification

- `cd backend && .venv/bin/pytest tests/test_bulk_eventstore.py -v` — 18/18 pass
- `cd backend && .venv/bin/pytest tests/ -v` — 1344/1344 pass, zero failures

Slice-level verification (partial — T03 is intermediate):
- ✅ `test_bulk_eventstore.py` — 18 pass (summary metadata, batch size, operation counts, rollback, SDK context manager)
- ✅ `test_app_scheduler.py` — passes (T01)
- ✅ `test_sdk_permissions.py` — passes (T02)
- ⏳ `test_browser_visible.py` — not yet created (T04)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/pytest tests/test_bulk_eventstore.py -v` | 0 | ✅ pass | 0.28s |
| 2 | `cd backend && .venv/bin/pytest tests/ -v` | 0 | ✅ pass | 39.8s |

## Diagnostics

- **Logger:** `app.events.store` at INFO level on bulk commit — logs event IRI, operation count, affected count, and source.
- **API response:** `POST /api/commands/bulk` returns `{event_iri, timestamp, operation_count, affected_count}` — inspect client-side.
- **RDF audit:** Bulk events are typed `sempkm:BulkEvent` (not `sempkm:Event`), queryable via `SELECT ?e WHERE { GRAPH ?g { ?e a <urn:sempkm:BulkEvent> } }`.
- **Metadata predicates:** `sempkm:summary`, `sempkm:source`, `sempkm:operationCount`, `sempkm:affectedCount` on the bulk event IRI.
- **Error shapes:** Batch >1000 → HTTP 400 `"Bulk batch size N exceeds limit of 1000"`. Invalid command → HTTP 400 with command details. Transaction failure → full rollback, HTTP 500.

## Deviations

- Refactored CommandClient to extract `_check_permissions()` as a shared method (plan only mentioned adding `bulk()`, not refactoring execute's permission logic). Necessary to avoid duplicating the whitelist + IRI prefix validation in BulkAccumulator.

## Known Issues

None.

## Files Created/Modified

- `backend/app/events/models.py` — added 5 bulk vocabulary constants (BULK_EVENT_TYPE, EVENT_SUMMARY, EVENT_SOURCE, EVENT_OPERATION_COUNT, EVENT_AFFECTED_COUNT)
- `backend/app/events/store.py` — added commit_bulk() method, logging import
- `backend/app/commands/router.py` — added BulkCommandRequest model, POST /api/commands/bulk endpoint
- `backend/sdk/sempkm_app_sdk/clients/commands.py` (worktree) — added BulkAccumulator class, bulk() context manager, refactored _check_permissions()
- `backend/tests/test_bulk_eventstore.py` — new, 18 tests covering metadata, counts, limits, materialization, rollback, SDK context manager
