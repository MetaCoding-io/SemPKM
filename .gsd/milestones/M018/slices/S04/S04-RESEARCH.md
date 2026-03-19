# S04: RSVP Push-Back + Recurrence Handling — Research

**Date:** 2026-03-18

## Summary

S04 adds two well-scoped features to the Google Calendar sync app: RSVP push-back (GCAL-05) and recurrence handling (GCAL-06). Both follow established patterns from GitHub sync (M017) and the existing S03 pull sync pipeline. The work is straightforward — no new technology, no unfamiliar APIs, no architectural novelty.

**RSVP push-back** mirrors GitHub's push_sync pattern exactly: SPARQL finds changed events → reverse map `bpkm:responseStatus` → PATCH Google Calendar API → update `lastSyncedAt` to prevent loop. The Google Calendar Events.patch endpoint accepts a partial attendees array with the self-attendee's `responseStatus` updated. The `attendeesOmitted: true` flag tells the API that the partial array is intentional — only the self-attendee entry needs to be sent.

**Recurrence handling** is mostly already done. The field mapper in S03 already stores `bpkm:recurrenceRule` on master events and `bpkm:recurringEventId` on exception instances. What's missing is the **edge linking** — creating an `bpkm:recurringEventId` edge from exception Event objects to the master Event object's IRI (discovered via SPARQL). The pull sync needs a post-processing pass after Phase 1/2 to resolve these links.

## Recommendation

Build in two tasks:

1. **RSVP push-back** (push_sync + reverse mapping + GCalClient.patch_event + loop prevention in pull) — follows the GitHub push_sync pattern line-for-line. This is the higher-value feature and should land first.
2. **Recurrence exception linking** (post-pull edge creation + pull_sync loop prevention for recurring events) — narrower scope, builds on pull_sync infrastructure from S03.

Wire both into `app.py` (replace the push-changes placeholder, add push to sync-now and poll-events handlers).

## Implementation Landscape

### Key Files

- `apps/google-calendar/services/sync_engine.py` — Add `push_sync()` function following GitHub sync pattern, add `_find_changed_events()` SPARQL query, add recurrence exception linking in pull_sync post-processing
- `apps/google-calendar/services/field_mapper.py` — Add `REVERSE_RESPONSE_STATUS_MAP` and `build_event_patch()` for RSVP reverse mapping
- `apps/google-calendar/services/gcal_client.py` — Add `patch_event()` method using `_request("PATCH", ...)` — follows same pattern as `GitHubClient.patch_issue()`
- `apps/google-calendar/app.py` — Replace `push_changes` placeholder with real push_sync call, add push to `sync_now` and `poll_events` handlers
- `backend/tests/test_gcal_sync_engine.py` — Add push_sync tests (~20-25), recurrence linking tests (~10-15)
- `backend/tests/test_gcal_field_mapper.py` — Add reverse mapping tests (~5-8)

### Reference Files (read, don't modify)

- `apps/github-sync/services/sync_engine.py` lines 181-373 — `_find_changed_tasks()` and `push_sync()` are the reference implementation for the push pipeline
- `apps/github-sync/services/field_mapper.py` line 298 — `build_issue_patch()` is the reference for reverse field mapping

### Build Order

**Task 1: RSVP push-back.** Higher business value, more complex, and unblocks S05 E2E testing of the push flow. Pieces:
1. `REVERSE_RESPONSE_STATUS_MAP` + `build_event_patch()` in field_mapper.py
2. `GCalClient.patch_event(calendar_id, event_id, data)` in gcal_client.py
3. `_find_changed_events()` SPARQL query in sync_engine.py
4. `push_sync(ctx)` function in sync_engine.py
5. Loop prevention in `pull_sync()` — skip events where `updated <= lastSyncedAt`
6. Wire push into app.py handlers (sync_now, poll_events, push_changes)
7. Tests for all of the above

**Task 2: Recurrence exception linking.** Narrower scope, purely pull-side. Pieces:
1. After phase 1+2 in `pull_sync()`, find newly created events with `bpkm:recurringEventId` property (non-null)
2. For each, SPARQL-lookup the master event by its Google Calendar ID (`bpkm:externalId`)
3. Create `edge.create` command linking exception → master via `bpkm:recurringEventId` predicate
4. Tests for recurrence linking (master+exception created, exception linked, orphan exception handled gracefully)

### Verification Approach

- `pytest tests/test_gcal_field_mapper.py -v` — reverse mapping tests
- `pytest tests/test_gcal_sync_engine.py -v` — push_sync + recurrence tests
- `pytest -x` — full suite stays green (currently 1603 tests)
- Target: ≥30 new tests (push pipeline ~20, recurrence ~10)

## Constraints

- **Google Events.patch RSVP semantics:** The PATCH endpoint for RSVP requires sending the attendees array with at least the self-attendee entry and the updated `responseStatus`. Set `attendeesOmitted: true` to signal the partial array is intentional (otherwise the API treats missing attendees as removed). The PATCH URL is `PATCH /calendars/{calendarId}/events/{eventId}`.
- **RSVP reverse mapping is narrow.** Per D213, only `bpkm:responseStatus` changes are pushed. Title, description, time edits are NOT pushed. The `build_event_patch()` function should only map responseStatus.
- **calendarId is needed for PATCH.** The Google Calendar PATCH endpoint requires `calendarId` in the URL. The changed-events SPARQL query must return `bpkm:calendarName` (or we need to store the calendar ID separately). Currently `bpkm:calendarName` stores the display name, not the ID. We need `bpkm:externalId` (the Google event ID) and the calendar ID. The sync engine stores `selected_calendars` in state — we can iterate those, or store `calendar_id` as a property on each Event during pull. The simplest approach: add the calendar ID to the event properties during pull (store in a new or repurposed property). Alternatively, parse it from the slug key structure.
- **calendarId resolution approach:** The `compute_event_slug()` function takes `calendar_id` and `event_id`. The slug is a SHA-256 hash — not reversible. Better approach: the field mapper already stores `bpkm:calendarName` as the calendar display name. For push, store the actual calendar ID too. Options: (a) store calendar ID in `bpkm:calendarName` instead of display name (breaking change), (b) add a new property, or (c) store it in state keyed by event externalId. Simplest: store `calendarId` as another property on the event. The SHACL shape doesn't have a dedicated property for this, but `bpkm:calendarName` currently stores the calendar_id (the sync engine passes `calendar_id` as `calendar_name`). This is actually already correct — the pull sync passes `calendar_id` as `calendar_name` since the human-readable name isn't fetched per-event. So `bpkm:calendarName` already contains the calendar ID.
- **Mock response queue alignment** (from S03 forward intelligence): Adding `patch_event()` HTTP calls to push_sync tests requires mock responses in the right queue position. Follow the pattern from GitHub sync tests.
- **Loop prevention must exist in pull_sync** before push_sync is active. Without it, a pushed RSVP change triggers a Google `updated` timestamp change, which the next pull_sync sees as "modified" and re-imports, which triggers another push, ad infinitum.

## Common Pitfalls

- **Google RSVP responseStatus uses camelCase, bpkm uses kebab-case.** The reverse map must convert back: `accepted`→`accepted`, `declined`→`declined`, `tentative`→`tentative`, `needs-action`→`needsAction`. The forward `RESPONSE_STATUS_MAP` already handles the forward direction.
- **attendeesOmitted flag.** Without `attendeesOmitted: true` in the PATCH body, Google treats the submitted attendees array as the complete list and may remove other attendees. This is critical for RSVP-only push.
- **Recurring event exception IRI discovery.** Exception events have `recurringEventId` set to the Google Calendar master event ID (a string like `abc123_20260301`). The master event's `bpkm:externalId` is just `abc123`. The linking SPARQL must match the `recurringEventId` property value against existing events' `bpkm:externalId` values. Note: `recurringEventId` in Google's API refers to the *master* event ID, not the exception — so `event.recurringEventId == master.id`.
- **Self-attendee email needed for PATCH.** The PATCH body needs `[{email: "user@example.com", self: true, responseStatus: "accepted"}]`. The user's Google email is stored in state as `google_email` (set during OAuth callback). Pull this from state, not from the event properties.

## Sources

- Google Calendar Events.patch endpoint: `PATCH /calendars/{calendarId}/events/{eventId}` with partial event resource
- `attendeesOmitted` flag documented in Google Calendar Events resource schema
- GitHub sync push_sync implementation: `apps/github-sync/services/sync_engine.py` lines 181-373
- Design doc: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §5 — responseStatus bidirectional (↔), recurrence handling strategy
