---
estimated_steps: 5
estimated_files: 4
skills_used: []
---

# T02: Scope change propagation between views via sempkm:scope-changed event

**Slice:** S03 — Cross-View Drag & Composable Planning
**Milestone:** M034

## Description

Views currently operate in isolation — changing the scope query (saved query filter) in one view's toolbar only updates that specific panel via `applyScopeQuery()`, which does an htmx re-swap targeting `.group-editor-area`. Sibling views in other dockview panels are unaware of the change.

This task introduces a `sempkm:scope-changed` custom event that propagates scope filter changes to all listening views. Each view type (calendar, kanban) registers a listener and re-fetches its data with the new scope query. A panel identity check prevents self-triggered re-fetches.

**Current `applyScopeQuery` implementation** (workspace.js ~line 3487):
```javascript
function applyScopeQuery(queryId, renderer, selectedType) {
    var url = '/browser/views/generic/' + encodeURIComponent(renderer);
    var params = [];
    if (selectedType) params.push('type=' + encodeURIComponent(selectedType));
    if (queryId) params.push('scope_query=' + encodeURIComponent(queryId));
    if (params.length) url += '?' + params.join('&');
    var target = document.querySelector('.group-editor-area');
    if (target && typeof htmx !== 'undefined') {
        htmx.ajax('GET', url, { target: target, swap: 'innerHTML' });
    }
}
```

This re-swaps the ACTIVE panel content only. The `sempkm:scope-changed` event is the new piece for sibling panels.

**Scope select `onchange`** is in `view_toolbar.html`:
```html
onchange="applyScopeQuery(this.value, '{{ renderer | default('table') }}', '{{ selected_type | default('') }}')"
```

## Steps

1. **Dispatch `sempkm:scope-changed` from `applyScopeQuery`** — In `workspace.js`, modify `applyScopeQuery(queryId, renderer, selectedType)` to dispatch a `sempkm:scope-changed` event on `document` BEFORE doing the htmx re-swap. The event detail should include `{ scopeQuery: queryId, renderer: renderer, selectedType: selectedType, sourcePanel: sourcePanelId }`. The `sourcePanel` should be derived from the element that triggered the change — add an optional 4th parameter `sourceEl` to `applyScopeQuery`, then compute `sourceEl ? sourceEl.closest('.dv-panel')?.id || '' : ''`.

2. **Update view_toolbar.html to pass `this` to applyScopeQuery** — Change the `onchange` to `applyScopeQuery(this.value, '{{ renderer | default('table') }}', '{{ selected_type | default('') }}', this)` so the source element is available for panel ID lookup.

3. **Calendar listens for `sempkm:scope-changed`** — In `calendar.js` (created by T01), add a `document.addEventListener('sempkm:scope-changed', function(e) { ... })` inside the init function. When fired:
   - Compute own panel ID: find the calendar container's closest `.dv-panel` ancestor and get its `id`
   - Skip if `e.detail.sourcePanel === ownPanelId` (self-triggered)
   - Re-fetch calendar data: construct the data URL with the new `scope_query` parameter, fetch, then `calendar.removeAllEvents()` + loop `calendar.addEvent()` for each event in the response
   - Log `[calendar] scope sync: scopeQuery=<id> from panel=<sourcePanel>`

4. **Kanban listens for `sempkm:scope-changed`** — In `kanban.js`, add a `document.addEventListener('sempkm:scope-changed', function(e) { ... })` (outside the IIFE or within a `DOMContentLoaded` listener). When fired:
   - Compute own panel ID from the kanban board's closest `.dv-panel` ancestor
   - Skip if `e.detail.sourcePanel === ownPanelId`
   - Find the kanban board element — if it exists, determine its type (from the board's context or the event's `selectedType`)
   - Trigger an htmx re-swap: `htmx.ajax('GET', '/browser/views/generic/kanban?scope_query=' + e.detail.scopeQuery + '&type=' + encodeURIComponent(typeIri), { target: boardEl.closest('.group-editor-area') || boardEl.parentElement, swap: 'innerHTML' })`
   - Log `[kanban] scope sync: scopeQuery=<id> from panel=<sourcePanel>`

5. **Add CSS for scope sync indicator** — Optional but helpful: briefly flash a `.scope-syncing` class on the view container when a scope sync occurs (200ms animation) to give visual feedback that the sibling view updated.

## Must-Haves

- [ ] `sempkm:scope-changed` event dispatched on `document` when scope select changes
- [ ] Event detail contains `scopeQuery`, `renderer`, `selectedType`, `sourcePanel`
- [ ] Calendar listener re-fetches data with new scope query (skip if self-triggered)
- [ ] Kanban listener triggers htmx re-swap with new scope query (skip if self-triggered)
- [ ] Self-triggering prevention via panel ID comparison works correctly

## Verification

- `grep -q "sempkm:scope-changed" frontend/static/js/workspace.js` — event dispatched
- `grep -q "sempkm:scope-changed" frontend/static/js/calendar.js` — calendar listens
- `grep -q "sempkm:scope-changed" frontend/static/js/kanban.js` — kanban listens
- `grep -q "sourcePanel" frontend/static/js/workspace.js` — panel identity included
- `grep -q "sourcePanel" frontend/static/js/calendar.js` — self-skip logic present

## Inputs

- `frontend/static/js/workspace.js` — current `applyScopeQuery` function (~line 3487)
- `frontend/static/js/calendar.js` — T01's extracted calendar module (needs listener added)
- `frontend/static/js/kanban.js` — T01's enriched kanban module (needs listener added)
- `backend/app/templates/browser/view_toolbar.html` — scope select onchange handler

## Expected Output

- `frontend/static/js/workspace.js` — modified: `applyScopeQuery` dispatches `sempkm:scope-changed`
- `frontend/static/js/calendar.js` — modified: scope-changed listener added
- `frontend/static/js/kanban.js` — modified: scope-changed listener added
- `backend/app/templates/browser/view_toolbar.html` — modified: passes `this` to `applyScopeQuery`

## Observability Impact

- **New console signal:** `[scope] propagated: scopeQuery=<id> renderer=<r> sourcePanel=<panelId>` — logged on every scope change dispatch in workspace.js. Confirms the event fired and which panel originated it.
- **Calendar sync signal:** `[calendar] scope sync: scopeQuery=<id> from panel=<panelId>` — logged when calendar processes a scope-changed event. `[calendar] scope sync complete: N events` on success, `[calendar] scope sync failed:` on fetch error.
- **Kanban sync signal:** `[kanban] scope sync: scopeQuery=<id> from panel=<panelId>` — logged when kanban processes a scope-changed event.
- **Inspection surface:** `document.addEventListener('sempkm:scope-changed', e => console.log(e.detail))` — attaching this in dev console shows every scope propagation event with full detail payload.
- **Visual indicator:** `.scope-syncing` CSS class briefly flashes an accent outline on the synced view container (300ms animation), providing visual confirmation the sync was received.
- **Failure visibility:** Calendar scope sync errors appear as `[calendar] scope sync failed:` in console. Kanban scope sync failures surface through htmx error handling.
