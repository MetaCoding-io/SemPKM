---
id: T03
parent: S16
milestone: M001
provides: []
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 
verification_result: passed
completed_at: 
blocker_discovered: false
---
# T03: 16-event-log-explorer 03

**# Phase 16 Plan 03: Inline Diff View and Undo Summary**

## What Happened

# Phase 16 Plan 03: Inline Diff View and Undo Summary

Inline diff view for object.patch/body.set events and undo functionality for reversible events, using backward SPARQL reconstruction and Python difflib unified diff.

## What Was Built

### EventQueryService Extensions (query.py)

Added `EventDetail` dataclass with `data_triples`, `before_values`, `new_values`, and `body_diff` fields.

Added four new methods to `EventQueryService`:

- **`get_event_detail(event_iri)`**: Queries the event named graph for metadata and data triples, reconstructs before/after values via backward SPARQL search, computes body diff for `body.set` events. Returns `EventDetail` or `None` if event not found.
- **`_query_before_value(subject_iri, predicate_iri, timestamp)`**: Per-predicate backward SPARQL scan finding the most recent prior value before the given event's timestamp. Wrapped in try/except for graceful degradation.
- **`_compute_body_diff(old_body, new_body)`**: Uses Python `difflib.unified_diff` to produce `[{type, text}]` line diff list, skipping `+++`/`---`/`@@` headers.
- **`build_compensation(event_iri, detail)`**: Builds a reversing `Operation` for `object.patch`, `body.set`, `edge.create`, and `edge.patch`. Uses concrete `Literal` values (not `Variable` patterns) in `materialize_deletes` to delete specific old values.

### New Routes (router.py)

- **`GET /browser/events/{event_iri:path}/detail`**: Returns `event_detail.html` partial for htmx injection into `.event-diff-container`.
- **`POST /browser/events/{event_iri:path}/undo`**: Builds and commits a compensating event via `EventStore.commit()`. Returns `{"status": "ok"}` on success or 400/404 errors.

### Diff Template (event_detail.html)

71-line htmx partial (no base template) with three rendering branches:
- **`body.set`**: Line-by-line diff with `+`/`-` markers and green/red background tinting
- **`object.patch` / `edge.patch`**: Property before/after table with predicate label, old value (red), new value (green)
- **`object.create` / `edge.create`**: Created triples list (no before column)

### Event Log Template Updates (event_log.html)

- Wrapped each `.event-row` in `.event-row-wrapper` with `data-event-iri` attribute
- Added `.event-diff-container` after each `.event-row` (empty by default, hidden via `:empty { display: none }`)
- Added `.event-row-actions` div with context-sensitive Diff and Undo buttons
- Diff button: `hx-get` to detail endpoint, `hx-target="#diff-{{ loop.index }}"`, `hx-swap="innerHTML"`
- Undo button: `onclick="sempkmUndoEvent('...', this)"` — only shown for reversible events
- Updated "Load more" `hx-select` to `.event-row-wrapper`

### Client-Side (workspace.js + workspace.css)

Added `window.sempkmUndoEvent(eventIri, btn)`:
- Shows `window.confirm()` dialog warning about subsequent-change impact
- Disables button during request with "Undoing..." text
- POSTs to `/browser/events/{iri}/undo` (no CSRF header — FastAPI uses cookie auth)
- On success: `htmx.ajax('GET', '/browser/events', ...)` reloads event log panel
- On error: restores button state, shows alert with server error message

Appended 110 lines of diff CSS using CSS custom property tokens (light/dark compatible): container styles, diff table, line diff, creation diff, action buttons.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed as written with minor adaptations noted in decisions.

### Adaptations (not deviations)

**1. loop.index IDs instead of hx-target="next"**
- **Context**: Plan mentioned both `hx-target="next .event-diff-container"` and the loop.index fallback approach
- **Choice**: Used `id="diff-{{ loop.index }}"` + `hx-target="#diff-{{ loop.index }}"` for all htmx versions compatibility
- **Why**: htmx 2.0.4 supports `next`, but stable ID approach avoids any DOM-traversal ambiguity with nested structure

**2. _query_before_value as separate async method**
- **Context**: Plan showed the backward query inline in get_event_detail
- **Choice**: Extracted to `_query_before_value()` for clarity and per-predicate exception isolation
- **Why**: Allows individual predicate lookups to fail gracefully without affecting others

**3. Concrete literals in materialize_deletes**
- **Context**: Plan used `Literal(new_val)` in `materialize_deletes` for compensation
- **Choice**: Matched this exactly — concrete values, not `Variable` patterns
- **Why**: Undo must target specific known values. Using `Variable` would delete ALL values for that predicate, which is incorrect behavior for undo.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| backend/app/templates/browser/event_detail.html | FOUND |
| backend/app/events/query.py | FOUND |
| backend/app/browser/router.py | FOUND |
| backend/app/templates/browser/event_log.html | FOUND |
| frontend/static/js/workspace.js | FOUND |
| frontend/static/css/workspace.css | FOUND |
| .planning/phases/16-event-log-explorer/16-03-SUMMARY.md | FOUND |
| commit d939b09 (Task 1) | FOUND |
| commit a54391c (Task 2) | FOUND |
