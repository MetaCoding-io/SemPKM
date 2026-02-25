---
phase: 18-tutorials-and-documentation
plan: "02"
subsystem: workspace-ui
tags: [driver.js, tutorials, guided-tour, htmx-gated, lazy-element]
dependency_graph:
  requires: [18-01]
  provides: [DOCS-03, DOCS-04, startWelcomeTour, startCreateObjectTour]
  affects: [frontend/static/js/tutorials.js, backend/app/templates/base.html]
tech_stack:
  added: []
  patterns: [Driver.js lazy element function form, htmx:afterSwap target-identity guard, centered popover (no element)]
key_files:
  created:
    - frontend/static/js/tutorials.js
  modified:
    - backend/app/templates/base.html
decisions:
  - "Read/edit toggle selector is .mode-toggle (not [data-action=toggle-edit] as in RESEARCH.md) — confirmed from object_tab.html template inspection"
  - "getActiveEditorArea() and showTypePicker() both already exposed as window globals — no changes to workspace.js needed"
  - "htmx:afterSwap handler attached to document.body (not document) for consistency with htmx event bubbling"
metrics:
  duration: "2min"
  completed: "2026-02-24"
  tasks: 2
  files: 2
---

# Phase 18 Plan 02: Driver.js Guided Tours Summary

Driver.js guided tours implemented in `tutorials.js`: a 10-step "Welcome to SemPKM" workspace orientation tour and a 4-step "Creating Your First Object" htmx-gated tutorial, both exposed as global functions called by the Docs & Tutorials page Start Tour buttons.

## What Was Built

### Task 1: Create tutorials.js with Welcome Tour and Create Object Tour

**DOM Selectors Confirmed (from template inspection):**

| Step | Selector | Source | Notes |
|------|----------|--------|-------|
| Welcome 1 | `#app-sidebar` | `_sidebar.html` line 1 | Always-present sidebar root |
| Welcome 2 | `#nav-pane` | `workspace.html` line 7 | Always-present nav pane |
| Welcome 3+4 | `#section-objects` | `workspace.html` line 12 | Always-present, used for two steps |
| Welcome 5 | `#editor-pane` | `workspace.html` line 38 | Always-present editor pane |
| Welcome 6 | `.mode-toggle` (lazy) | `object_tab.html` line 15 | Only present when object tab is open |
| Welcome 7 | `#right-pane` | `workspace.html` line 96 | Always-present right pane |
| Welcome 8 | `ninja-keys` (lazy) | `workspace.html` line 123 | Custom element, lazy form used |
| Welcome 9+10 | (none — centered) | — | No element for save/done steps |
| Create 1 | `#section-objects` | `workspace.html` line 12 | Tour start anchor |
| Create 2 | `.type-picker` (lazy) | `type_picker.html` line 8 | Loaded via htmx:afterSwap |
| Create 3 | `#object-form` (lazy) | `object_form.html` line 39 | Loaded after type selection |
| Create 4 | `#object-form button[type="submit"]` (lazy) | `object_form.html` | Save button inside form |

**htmx:afterSwap Gating (Create Object Tour Step 1):**

```javascript
onNextClick: function () {
  var editorArea = typeof window.getActiveEditorArea === 'function'
    ? window.getActiveEditorArea()
    : document.getElementById('editor-area-group-1');

  if (typeof window.showTypePicker === 'function') {
    window.showTypePicker();
  }

  function afterSwapHandler(e) {
    if (e.detail && e.detail.target && editorArea && e.detail.target === editorArea) {
      document.body.removeEventListener('htmx:afterSwap', afterSwapHandler);
      driverObj.moveNext();
    }
  }
  document.body.addEventListener('htmx:afterSwap', afterSwapHandler);
}
```

Target identity check (`e.detail.target === editorArea`) prevents spurious advances from unrelated htmx swaps elsewhere on the page.

**base.html addition:**
```html
<script src="/js/tutorials.js"></script>
```
Added after `driver.js.iife.js` CDN tag so `window['driver.js']` is available when tutorials.js loads.

### Task 2: Visual Verification (Checkpoint)

**Status: auto-approved (user pre-authorized)**

Both tours implemented as specified. Tour progression:
- Welcome tour: 10 steps, steps 6 and 8 use lazy function form, steps 9 and 10 are centered with no element target
- Create Object tour: step 1 onNextClick calls `showTypePicker()` and awaits `htmx:afterSwap` before calling `driverObj.moveNext()`; steps 2-4 use lazy element resolution

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected read/edit toggle CSS selector**
- **Found during:** Task 1 DOM inspection
- **Issue:** RESEARCH.md and plan suggested `[data-action="toggle-edit"]` or `.toggle-edit-btn`. Template inspection of `object_tab.html` revealed the actual button uses class `.mode-toggle` with no `data-action` attribute.
- **Fix:** Used `.mode-toggle` as the lazy element selector for Welcome tour step 6.
- **Files modified:** `frontend/static/js/tutorials.js`
- **Commit:** d6c9785

**2. [Observation] getActiveEditorArea and showTypePicker already global**
- **Found during:** Task 1 — pre-implementation check
- **Status:** No action needed. Both `window.getActiveEditorArea` (workspace-layout.js line 1029) and `window.showTypePicker` (workspace.js line 1283) already exposed. Plan noted to "expose as window.getActiveEditorArea in workspace.js if it doesn't already exist" — it exists, so no change made.

## Self-Check: PASSED

- FOUND: `frontend/static/js/tutorials.js` (273 lines)
- FOUND: `window.startWelcomeTour` at tutorials.js line 57
- FOUND: `window.startCreateObjectTour` at tutorials.js line 187
- FOUND: `<script src="/js/tutorials.js">` in base.html after driver.js.iife.js
- Commit d6c9785 present in git log
