# S16: Event Log Explorer

**Goal:** Build the EventQueryService backend and wire the event log timeline into the bottom panel.
**Demo:** Build the EventQueryService backend and wire the event log timeline into the bottom panel.

## Must-Haves


## Tasks

- [x] **T01: 16-event-log-explorer 01** `est:12min`
  - Build the EventQueryService backend and wire the event log timeline into the bottom panel.

Purpose: Expose the existing immutable event store as a browsable, paginated timeline that loads on demand inside the already-built #panel-event-log pane.
Output: EventQueryService with SPARQL list_events(), GET /browser/events route, event_log.html partial, and workspace.js lazy-load trigger.
- [x] **T02: 16-event-log-explorer 02** `est:2min`
  - Add filter controls, filter chips, styled event rows, and all CSS for the event log timeline.

Purpose: Make the event log actionable — users can narrow the timeline to the operations they care about, see visually distinct operation type badges, and paginate through long histories without page jumps.
Output: Complete filter UI in event_log.html and all event log CSS in workspace.css.
- [x] **T03: 16-event-log-explorer 03**
  - Implement inline diff view for object.patch/body.set events and undo functionality for reversible events.

Purpose: Close the loop on the event log — users can not only see what happened but understand exactly what changed and reverse mistakes.
Output: EventQueryService extended with diff reconstruction and undo logic; event_detail.html diff partial; Diff and Undo buttons in event_log.html rows; POST undo endpoint.

## Files Likely Touched

- `backend/app/events/query.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/event_log.html`
- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/event_log.html`
- `frontend/static/css/workspace.css`
- `backend/app/events/query.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/event_detail.html`
- `backend/app/templates/browser/event_log.html`
- `frontend/static/css/workspace.css`
