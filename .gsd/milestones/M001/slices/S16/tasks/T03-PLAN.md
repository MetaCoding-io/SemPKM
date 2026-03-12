# T03: 16-event-log-explorer 03

**Slice:** S16 — **Milestone:** M001

## Description

Implement inline diff view for object.patch/body.set events and undo functionality for reversible events.

Purpose: Close the loop on the event log — users can not only see what happened but understand exactly what changed and reverse mistakes.
Output: EventQueryService extended with diff reconstruction and undo logic; event_detail.html diff partial; Diff and Undo buttons in event_log.html rows; POST undo endpoint.

## Must-Haves

- [ ] "Clicking an object.patch or body.set event row expands an inline diff below that row"
- [ ] "object.patch diff shows a before/after table of property changes"
- [ ] "body.set diff shows line-by-line added/removed/context lines with green/red coloring"
- [ ] "Reversible events (object.patch, body.set, edge.create, edge.patch) show an Undo button"
- [ ] "Clicking Undo shows window.confirm(); on confirmation, POSTs to /browser/events/{iri}/undo and reloads the event log"
- [ ] "Undo creates a new compensating event — it does NOT delete or modify the original event"

## Files

- `backend/app/events/query.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/event_detail.html`
- `backend/app/templates/browser/event_log.html`
- `frontend/static/css/workspace.css`
