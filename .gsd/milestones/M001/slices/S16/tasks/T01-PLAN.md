# T01: 16-event-log-explorer 01

**Slice:** S16 — **Milestone:** M001

## Description

Build the EventQueryService backend and wire the event log timeline into the bottom panel.

Purpose: Expose the existing immutable event store as a browsable, paginated timeline that loads on demand inside the already-built #panel-event-log pane.
Output: EventQueryService with SPARQL list_events(), GET /browser/events route, event_log.html partial, and workspace.js lazy-load trigger.

## Must-Haves

- [ ] "Opening the Event Log panel tab loads a timeline of events in reverse chronological order"
- [ ] "Each event row shows operation type badge, affected object label, user, and timestamp"
- [ ] "Timeline is cursor-paginated (page 50 loads as fast as page 1)"
- [ ] "Activating the Event Log bottom panel tab triggers a lazy htmx load of the event timeline"

## Files

- `backend/app/events/query.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/event_log.html`
- `frontend/static/js/workspace.js`
