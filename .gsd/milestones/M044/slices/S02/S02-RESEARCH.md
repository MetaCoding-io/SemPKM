# S02 Research — Event Listener & Timer Leak Fixes

## Summary

This slice fixes memory/resource leaks caused by event listeners, timers, library instances, and body-appended elements that survive dockview panel destruction or htmx re-swaps. The existing `registerCleanup()` infrastructure (cleanup.js) only fires on `htmx:beforeCleanupElement` — it does NOT fire when dockview removes a panel via its tab close button. The fix requires two complementary strategies: (1) adding `dispose()` methods to dockview content renderers in workspace-layout.js, and (2) ensuring each view module properly cleans up its own resources.

## Recommendation

**Targeted approach — three tasks:**

1. **Upgrade cleanup.js + workspace-layout.js** — Add a `dispose()` method to each content renderer that triggers cleanup for the panel's element tree. Wire `onDidRemovePanel` or the renderer's `dispose()` to call `runCleanup()` on the panel's container element. This gives every view module a single hook point.

2. **Fix per-view leaks** — Add `registerCleanup()` calls in graph.js (already partial), calendar.js (FullCalendar instance + document listeners), canvas.js (window/document listeners on remount), and the SPARQL console's cytoscape instance popover. Fix the federation.js interval (store handle, clear on page unload). Fix the context-indicator SSE reconnection guard.

3. **Verify** — Count event listeners before/after open→close→reopen cycles using browser DevTools `getEventListeners()` or a simple counter harness.

## Implementation Landscape

### Files That Need Changes

| File | LOC | What Leaks | Fix |
|------|-----|-----------|-----|
| `frontend/static/js/cleanup.js` | 57 | Only hooks htmx events, not dockview | Add MutationObserver or export `runCleanup()` for dispose calls |
| `frontend/static/js/workspace-layout.js` | 626 | Content renderers lack `dispose()` | Add `dispose()` to object-editor, view-panel, special-panel renderers |
| `frontend/static/js/graph.js` | 1020 | registerCleanup works for htmx, not dockview close; document-level theme listener safe (singleton) | Verify registerCleanup fires from dispose(); already mostly correct |
| `frontend/static/js/calendar.js` | 276 | FullCalendar instance never destroyed; `sempkm:command-executed` + `sempkm:scope-changed` document listeners accumulate on reinit | Add registerCleanup on container; destroy cal instance; use named handlers + removeEventListener |
| `frontend/static/js/canvas.js` | 1787 | `bindEvents()` adds window.pointermove/pointerup + 5 document listeners on every remount without removing old ones | Add `unbindEvents()` called before `bindEvents()`; register cleanup for dockview |
| `frontend/static/js/federation.js` | 325 | `setInterval(updateInboxBadge, 60000)` never cleared | Store interval handle; not panel-scoped (workspace-level) so minor, but should clear on unload |
| `frontend/static/js/context-indicator.js` | 252 | SSE EventSource reconnect creates new listeners without closing old connection | Already has `if (_sse) _sse.close()` guard — actually fine |
| `frontend/static/js/copilot.js` | 1768 | Singleton via `_copilotInit` flag — no per-panel leak | No changes needed |
| `frontend/static/js/sparql-console.js` | 1741 | Singleton; cytoscape properly destroyed before recreate; CodeMirror is single instance | No changes needed (theme listener is module-scope singleton) |

### Files That Are Fine (No Changes)

| File | Why |
|------|-----|
| `kanban.js` | Element-scoped listeners GC'd with DOM elements; scope-changed is module-scope singleton |
| `bmc.js` | Debounce timers properly cleared; scope-changed is module-scope singleton |
| `okr.js` | Same pattern as bmc.js — all safe |
| `quadrant.js` | Same pattern as kanban.js — all safe |
| `decision-matrix.js` | Same pattern — module-scope singleton listeners only |
| `vfs-browser.js` | Properly removes document mousemove/mouseup in cleanup handlers |
| `editor.js` | Already uses registerCleanup for CodeMirror6 destroy |

### Existing Cleanup Infrastructure

**cleanup.js** provides:
- `window.registerCleanup(elementId, fn)` — registers a teardown function for an element ID
- `window._sempkmCleanup` — the registry (elementId → [fn, fn, ...])
- `runCleanup(elementId)` — runs all registered fns and deletes the entry
- `htmx:beforeCleanupElement` listener — auto-runs cleanup when htmx removes elements, including descendants

**Gap:** `runCleanup()` is only called from the htmx event handler. It's not exported/callable from dockview's `dispose()`. The fix is to export it (or call it from the renderer dispose).

**Current registerCleanup users:**
- `graph.js` line 399 — registers cy.destroy(), popover removal, global reference nulling
- `editor.js` line 109 — registers CodeMirror instance destroy

### Dockview Content Renderer Lifecycle

dockview-core 4.11 `IContentRenderer` interface:
```
{ element: HTMLElement, init(params): void, dispose?(): void }
```

- `element` is appended to the panel container DOM
- `init(params)` is called once when the panel is created
- `dispose()` is called when the panel is removed — **but only if defined**

Current renderers in workspace-layout.js:
- **object-editor** (line 155): `element` + `init` — NO `dispose`
- **view-panel** (line 191): `element` + `init` — NO `dispose`
- **special-panel** (line 207): `element` + `init` — NO `dispose`

The fix: add `dispose: function() { ... }` to each renderer that calls `runCleanup(el.id)` or iterates `el.querySelectorAll('[id]')` to fire registered cleanup handlers.

### Leak Detail: calendar.js

Every `initCalendar()` call:
1. Creates a new FullCalendar instance — old instance leaked (never `.destroy()`)
2. Adds `document.addEventListener('sempkm:command-executed', ...)` — anonymous fn, can't remove
3. Adds `document.addEventListener('sempkm:scope-changed', ...)` — anonymous fn, can't remove
4. Adds element-scoped dragover/dragleave/drop on the container — these GC with the element (OK)
5. Stores reference in `window._sempkmCalendar` — overwritten, old instance orphaned

Fix: Use named handler functions stored in a closure. Before init, destroy previous instance and remove old document listeners. Register cleanup via `registerCleanup(containerId, ...)`.

### Leak Detail: canvas.js

The `htmx:afterSwap` handler on line 1781 resets `state.mounted = false` and calls `mountCanvas()` → `bindEvents()`. Each `bindEvents()` call adds:
- `window.addEventListener('pointermove', onPointerMove)` — accumulates
- `window.addEventListener('pointerup', onPointerUp)` — accumulates
- `document.addEventListener('dragover', onDragOver, true)` — accumulates
- `document.addEventListener('dragleave', onDragLeave, true)` — accumulates
- `document.addEventListener('drop', onDrop, true)` — accumulates
- `document.addEventListener('dragend', onDragEnd, true)` — accumulates
- `document.addEventListener('keydown', onKeyDown)` — accumulates

Fix: Add `unbindEvents()` that removes all named handlers. Call it before `bindEvents()` in the remount path, and register it via `registerCleanup()`.

### Leak Detail: federation.js

`setInterval(updateInboxBadge, 60000)` at module scope — runs forever. Since federation.js is loaded once per page in workspace.html, this is a workspace-lifetime interval. Not a panel leak, but:
- No `clearInterval` on unload
- If workspace page is kept open for hours, this polls `/api/inbox` every 60s indefinitely

Fix: Store the interval handle. Add beforeunload cleanup. Low priority — it's a single interval at workspace scope.

### Dead Code: `_cytoscapeInstances`

workspace-layout.js lines 198-199 reference `window._cytoscapeInstances` for the view-panel visibility handler, but this object is never created or populated anywhere in the codebase. Dead code that should be removed (or wired to graph.js if the intent was to track per-panel cy instances).

## Risks & Constraints

1. **Dockview dispose timing** — `dispose()` is called synchronously when the panel is removed. Any async cleanup (e.g., aborting in-flight fetches) must be fire-and-forget.

2. **Element ID requirement** — `registerCleanup()` keys on element ID. The `group-editor-area` divs created by content renderers don't have IDs by default. The dispose function needs to either (a) assign IDs to these elements during init, or (b) call cleanup on all descendant IDs.

3. **Anonymous vs named handlers** — calendar.js uses anonymous functions for document-level event listeners. These can't be removed with `removeEventListener()`. The fix requires refactoring to named handler references.

4. **Canvas state.mounted guard** — The `if (state.mounted) return` guard is bypassed by the htmx:afterSwap handler which resets `state.mounted = false`. The unbind-before-bind pattern is the correct fix.

## Verification Strategy

1. **Static analysis** — grep for `addEventListener` calls on `document` or `window` without matching `removeEventListener`. After the fix, every such pair should be balanced or registered via `registerCleanup`.

2. **Runtime verification** — Open graph view → close panel → reopen graph view → check that `window._sempkmGraph` is null between close and reopen. Repeat for calendar.

3. **Listener count check** — In browser devtools: `getEventListeners(document)` before and after open→close→reopen cycles. Count should not increase.

4. **Federation interval** — Verify `clearInterval` fires on page unload.

5. **E2E regression** — Full test suite must pass. View open/close behavior unchanged from user perspective.
