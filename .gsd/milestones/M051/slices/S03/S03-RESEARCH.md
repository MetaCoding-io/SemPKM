# S03 Research: Command Palette & Persona/Layout Dialog UX

## Summary

Four issues in this slice, all frontend-only, touching `workspace.js`, one admin template, and CSS. The codebase already has every pattern needed — `showConfirmDialog()` for dialogs, `open()`/`close()` patches on ninja-keys for lifecycle hooks, and `position: fixed` popover positioning from graph.js. No new libraries, no backend changes, no unfamiliar technology.

**Calibration: Light research.** All patterns are well-established in this codebase. The only moderate complexity is the ninja-keys shadow DOM interaction for the scroll-jump fix.

## Recommendation

Three tasks:
1. **Command palette scroll jump fix (#24)** — Add `document.body.style.overflow = 'hidden'` on palette open, restore on close. Single-file change to `workspace.js` in the existing open/close patch at lines 1513-1516. Verify with existing E2E test that opens command palette (e2e/tests/08-search/fts-search.spec.ts).
2. **Persona create + Layout save dialog (#33, #34, #35)** — Replace both "type above then select" antipatterns with proper `<dialog>` modals. Create a new `showInputDialog(title, placeholder, onConfirm, confirmText)` function modeled on `showConfirmDialog()` (line 3385). Replace `persona-create-confirm` handler (line 1740) and `layout-save-confirm` handler (line 1683) to close palette → open dialog → call existing `createNewPersona(name)` / `window.SemPKMLayouts.save(name)`. Also improve help text: rename command palette sections from "Persona"/"Layout" to clearer labels, and add subtitle text to the commands. All changes in `workspace.js`.
3. **Admin graph popover positioning (#42)** — The bug is a coordinate system mismatch: `.graph-popover` has `position: fixed` (from views.css line 603) but the positioning JS in `model_ontology_diagram.html` calculates coordinates relative to the panel. Fix: use `containerRect.left + pos.x + 16` (viewport-relative) instead of `containerRect.left - panelRect.left + pos.x + 16` (panel-relative). Single-file change to the inline `<script>` in `model_ontology_diagram.html`.

## Implementation Landscape

### File Map

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `frontend/static/js/workspace.js:1513-1516` | ninja-keys open/close patch | Add body overflow toggle |
| `frontend/static/js/workspace.js:1740-1758` | persona-create-confirm handler | Replace with dialog call |
| `frontend/static/js/workspace.js:1683-1709` | layout-save-confirm handler | Replace with dialog call |
| `frontend/static/js/workspace.js:3385-3428` | `showConfirmDialog()` | Reference for new `showInputDialog()` |
| `frontend/static/js/workspace.js:1677-1680` | layout-save-as command entry | Remove `children: ['layout-save-confirm']`, add direct handler |
| `frontend/static/js/workspace.js:1734-1737` | persona-create command entry | Remove `children: ['persona-create-confirm']`, add direct handler |
| `backend/app/templates/admin/model_ontology_diagram.html:215-231` | Popover positioning JS | Fix coordinate calculation |
| `frontend/static/css/views.css:603` | `.graph-popover { position: fixed }` | No change needed (already correct) |

### Issue #24 — Command Palette Scroll Jump

**Root cause:** `ninja-action.js:27` calls `this.scrollIntoView({block: 'nearest'})` when an action is selected/highlighted. This `scrollIntoView` can propagate to the page body because the ninja-keys modal overlay (`.modal` in shadow DOM) has `overflow: auto`. When the modal content is shorter than the full-height overlay, the scroll propagates to `document.body`.

**Fix approach:** In the existing `ninja.open()` / `ninja.close()` patch (workspace.js:1513-1516), save `document.body.style.overflow`, set to `'hidden'`, and restore on close. This is the standard modal-open pattern.

```javascript
// Enhanced open/close patch
var _savedOverflow = '';
ninja.open = function (options) {
    _savedOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    _origOpen(options);
    ninja.setAttribute('opened', '');
};
ninja.close = function () {
    document.body.style.overflow = _savedOverflow;
    _origClose();
    ninja.removeAttribute('opened');
};
```

**Verification:** Open workspace → scroll down → press F1 → use arrow keys to navigate items → page should not scroll. The existing E2E test `e2e/tests/08-search/fts-search.spec.ts` opens the command palette and can be extended with a scroll-position assertion.

### Issues #33/#34 — Persona Create & Layout Save Dialog

**Current antipattern (both identical):** User selects "Persona: Create New..." → drills into child item → sees "Type a persona name above, then select this item to save" → types in ninja-keys search input → selects the confirm item → handler extracts name from `ninjaEl.shadowRoot.querySelector('input[type="text"]').value`.

Problems: (1) confusing UX — user must type name in a search field, (2) fragile — depends on ninja-keys shadow DOM internals, (3) the search text filters the action list while typing, so only partial names work.

**Fix approach:** Create `showInputDialog(title, placeholder, onConfirm, confirmText)` — a simple `<dialog>` with a text input, modeled on `showConfirmDialog()`. Change the command palette entries from parent-with-children to direct handlers that close the palette and open the dialog.

```javascript
// New function — parallel to showConfirmDialog
function showInputDialog(title, placeholder, onConfirm, confirmText) {
    confirmText = confirmText || 'Save';
    var dialog = document.createElement('dialog');
    dialog.className = 'confirm-dialog'; // reuse existing dialog styling
    // ... input + cancel/confirm buttons ...
    dialog.showModal();
}

// Persona: Create New entry — direct handler, no children
{
    id: 'persona-create',
    title: 'Persona: Create New...',
    section: 'Persona',
    handler: function () {
        showInputDialog('Create Persona', 'Persona name', function(name) {
            createNewPersona(name);
        }, 'Create');
    }
}
```

The `persona-create-confirm` and `layout-save-confirm` child entries are removed entirely.

**Issue #35 (minimal clarification):** Add subtitle/hint text to persona and layout commands. Persona commands get subtitle "Server-synced workspace profiles (tabs, layout, sidebar)". Layout commands get subtitle "Local panel arrangements only". This is done via the `icon` or custom HTML in ninja-keys entries. Alternatively, if full merge is deferred, just keep the sections as-is with better titles.

### Issue #42 — Admin Graph Popover Positioning

**Root cause:** Coordinate system mismatch. The `.graph-popover` class in `views.css:603` declares `position: fixed`. The positioning code in `model_ontology_diagram.html:218-221` computes:
```javascript
var left = (containerRect.left - panelRect.left) + pos.x + 16;
var top = (containerRect.top - panelRect.top) + pos.y - 12;
```

This subtraction `containerRect - panelRect` produces panel-relative coordinates, which would be correct for `position: absolute` within the panel. But `position: fixed` needs viewport-relative coordinates.

**Fix:** Use viewport coordinates directly:
```javascript
var left = containerRect.left + pos.x + 16;
var top = containerRect.top + pos.y - 12;
```

And update the overflow checks to use viewport bounds instead of panel bounds:
```javascript
if (pRect.right > window.innerWidth - 8) {
    popover.style.left = (containerRect.left + pos.x - pRect.width - 12) + 'px';
}
if (pRect.bottom > window.innerHeight - 8) {
    popover.style.top = (containerRect.top + pos.y - pRect.height + 12) + 'px';
}
```

**Note:** `evt.renderedPosition` from Cytoscape returns coordinates in the canvas viewport space (pixels from canvas top-left). `containerRect` from `getBoundingClientRect()` gives the canvas's viewport position. So `containerRect.left + pos.x` correctly gives viewport-relative pixel position.

### Existing Patterns Used

| Pattern | Source | Applied To |
|---------|--------|------------|
| `showConfirmDialog()` dialog | `workspace.js:3385` | New `showInputDialog()` for #33/#34 |
| ninja-keys open/close patch | `workspace.js:1513-1516` | Scroll jump fix #24 |
| `position: fixed` popover with viewport coords | `graph.js:488-626` | Admin popover fix #42 |
| `.confirm-dialog` CSS | `workspace.css` (search for confirm-dialog) | Reused for input dialog |

### Verification Strategy

1. **Scroll jump (#24):** F1 → arrow-key through items → verify page scroll position unchanged. Testable via `page.evaluate(() => window.scrollY)` before/after in E2E.
2. **Persona dialog (#33):** F1 → "Persona: Create New..." → verify `<dialog>` appears → type name → Create → verify persona via API. Check the existing E2E test in `e2e/tests/29-personas/personas.spec.ts` line 110 — it verifies command palette persona commands exist; extend with dialog interaction.
3. **Layout dialog (#34):** F1 → "Layout: Save As..." → verify dialog → type name → Save → verify layout in localStorage.
4. **Admin popover (#42):** Navigate to admin model detail → Relationships tab → hover over a node → popover appears near the node, not offset. This is on the admin page at `/admin/models/<id>`, not the workspace.

### Risk Assessment

All four issues are low-risk. The scroll fix is 3 lines. The dialog replacement is a well-understood pattern with a reference implementation 50 lines away in the same file. The popover fix is arithmetic correction. No new dependencies, no backend changes (except the inline template script), no cross-cutting concerns.

### Skills

No specialized skills needed. All work is vanilla JS/CSS within established patterns.
