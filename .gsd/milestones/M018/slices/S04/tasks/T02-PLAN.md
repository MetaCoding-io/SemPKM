---
estimated_steps: 5
estimated_files: 2
---

# T02: Recurrence exception linking in pull_sync

**Slice:** S04 — RSVP push-back + recurrence handling
**Milestone:** M018

## Description

Add recurrence exception→master linking to pull_sync. Currently, the field mapper stores `bpkm:recurringEventId` as a string property on exception events (the Google master event ID), and `bpkm:recurrenceRule` on master events. What's missing is the **edge** from exception Event objects to master Event objects — this linking resolves `recurringEventId` (a Google ID string) into a SemPKM IRI via SPARQL lookup.

Key constraints from research:
- Google's `recurringEventId` on an exception event equals the master event's `id` field (stored as `bpkm:externalId` on the master)
- The SPARQL lookup must match `recurringEventId` value against `bpkm:externalId` of existing events
- Edge predicate is `bpkm:recurringEventId` (from exception to master)
- Orphan exceptions (master not yet synced) must be handled gracefully — log warning, skip edge creation
- Self-links must be skipped (edge case where recurringEventId == own externalId)

## Steps

1. **Track events with recurringEventId during pull_sync processing loop.** In the per-event loop inside pull_sync, after processing properties, check if the event dict has a `recurringEventId` key. If so, record a mapping: `{slug: recurringEventId_value}` in a new dict `recurrence_links`. This captures both new and updated events that are recurrence exceptions.

2. **Add `_find_event_by_external_id()` helper to sync_engine.py.** SPARQL query that finds a bpkm:Event with a specific `bpkm:externalId` value and `externalProvider = "google-calendar"`. Returns `{"iri": ...}` or None. This is similar to `_find_existing_event()` but matches on externalId instead of slug.

3. **Add recurrence linking phase after phase 2 in pull_sync.** After the existing phase 2 (body.set + edge.create for attendees), iterate `recurrence_links`. For each `(slug, recurring_event_id)`:
   - Look up the exception event's IRI via `_find_existing_event(graph_client, slug)`
   - Look up the master event's IRI via `_find_event_by_external_id(graph_client, recurring_event_id)`
   - If both found and they're different IRIs, create an `edge.create` command: `source=exception_iri, predicate=bpkm:recurringEventId, target=master_iri`
   - If master not found, log warning and skip
   - If same IRI (self-link), skip
   - Submit all recurrence edge commands in a batch

4. **Add recurrence linking tests to test_gcal_sync_engine.py.** New test class `TestRecurrenceLinking` with ≥10 tests:
   - Master event synced, then exception with recurringEventId → edge created linking exception to master
   - Orphan exception (master not synced) → no edge, no error
   - Self-link skipped (recurringEventId matches own externalId)
   - Multiple exceptions linking to same master → multiple edges created
   - Event without recurringEventId → no linking attempted
   - `_find_event_by_external_id` returns correct IRI
   - `_find_event_by_external_id` returns None for missing event
   - Full pull_sync with mixed master + exceptions produces correct edges
   - Recurrence linking errors don't block the sync (error isolation)
   - Edge command uses correct predicate and source/target

5. **Verify full test suite.** Run `pytest -x` to confirm no regressions.

## Must-Haves

- [ ] `_find_event_by_external_id()` resolves Google event ID to SemPKM Event IRI
- [ ] pull_sync creates `edge.create` commands from exception events to master events
- [ ] Orphan exceptions (master not found) handled gracefully — warning logged, no error
- [ ] Self-links (recurringEventId == own externalId) skipped
- [ ] ≥10 new tests pass

## Verification

- `pytest backend/tests/test_gcal_sync_engine.py -v` — all tests pass including recurrence linking
- `pytest -x` — full suite stays green
- Total new tests in T02 ≥ 10

## Inputs

- `apps/google-calendar/services/sync_engine.py` — pull_sync() from S03 + push_sync from T01; _find_existing_event() pattern for SPARQL lookup
- `backend/tests/test_gcal_sync_engine.py` — existing test infrastructure (MockStateClient, MockGraphClient, MockExternalHttpClient); T01 additions for push tests
- S03 Forward Intelligence: sync engine already handles `recurringEventId` as a property — this task adds the edge linking logic
- Research constraint: Google `recurringEventId` equals master event's `id` field (stored as `bpkm:externalId`)

## Expected Output

- `apps/google-calendar/services/sync_engine.py` — gains `_find_event_by_external_id()` (~25 lines), recurrence linking phase in pull_sync (~30 lines), `recurrence_links` tracking in processing loop (~5 lines)
- `backend/tests/test_gcal_sync_engine.py` — gains TestRecurrenceLinking class + TestFindEventByExternalId class (~180 lines)

## Observability Impact

- **Logs:** `google_calendar.sync` logger at INFO for recurrence linking phase (count of links resolved, edges created). WARNING when a master event is not found for a `recurringEventId` (orphan exception).
- **Pull result:** `last_pull_result` state key gains a `recurrence_edges` count field in the returned dict, allowing inspection of how many exception→master edges were created.
- **Failure visibility:** Errors during the recurrence linking phase are captured per-event and do not block the overall sync. Orphan exceptions (master not yet synced) produce a warning log with the orphan slug and the unresolved `recurringEventId`.
