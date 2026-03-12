# T01: 52-bug-fixes-security 01

**Slice:** S52 — **Milestone:** M001

## Description

Fix two known regressions: (1) lint dashboard filter controls overflow on narrow viewports, and (2) event log fails to render badges, diffs, and undo for compound operation types like "body.set,object.create". Also implement undo for object.create events via compensating event (soft-archive).

Purpose: Close FIX-01 and FIX-02 requirements — known bugs that degrade the event log and lint dashboard UX.
Output: Responsive lint filters, compound event display, and object.create undo.

## Must-Haves

- [ ] "Lint dashboard filter controls wrap to a second line on narrow viewports without overflow"
- [ ] "Compound events (e.g. body.set,object.create) show the primary operation badge and an expandable detail of secondary operations"
- [ ] "Diff button works for compound event types (shows creation triples or body diff as appropriate)"
- [ ] "Undo button appears and functions for object.create events (removes triples from materialized state via compensating event)"

## Files

- `frontend/static/css/workspace.css`
- `backend/app/events/query.py`
- `backend/app/templates/browser/event_log.html`
- `backend/app/templates/browser/event_detail.html`
- `backend/app/browser/router.py`
