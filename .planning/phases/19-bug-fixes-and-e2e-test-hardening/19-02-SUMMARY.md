---
phase: 19-bug-fixes-and-e2e-test-hardening
plan: "02"
subsystem: workspace-ui
tags: [bug-fix, ui, javascript, css, templates, tooltip, tag-pills]
dependency_graph:
  requires: []
  provides: [tab-active-guard, tag-pill-display, nav-tree-tooltip, graph-node-tooltip-confirmation]
  affects: [workspace-layout.js, workspace.js, graph.js, workspace.css, object_read.html, _field.html, tree_children.html, router.py]
tech_stack:
  added: []
  patterns:
    - tag-pill CSS class for plain-string multi-value properties with pill visual
    - event-delegated nav tree tooltip with position:fixed for overflow escape
    - type_label added to tree_children endpoint context for tooltip display
key_files:
  created: []
  modified:
    - frontend/static/js/workspace-layout.js
    - frontend/static/js/workspace.js
    - frontend/static/js/graph.js
    - frontend/static/css/workspace.css
    - backend/app/templates/browser/object_read.html
    - backend/app/templates/forms/_field.html
    - backend/app/templates/browser/tree_children.html
    - backend/app/browser/router.py
decisions:
  - Tab active guard added directly inside switchTabInGroup after the group null-check
  - Tag pill match uses 'tags' in prop.path — matches bpkm:tags IRI (urn:sempkm:model:basic-pkm:tags)
  - Nav tree tooltip uses event delegation with a single shared tooltip element (not per-leaf)
  - type_label resolved server-side via label_service.resolve_batch — reuses existing LabelService call pattern
  - Graph node hover confirmed working — typeLabel already populated from backend, no changes needed
metrics:
  duration: "28min"
  completed: "2026-02-26"
  tasks: 2
  files: 8
---

# Phase 19 Plan 02: UI Bug Fixes and Tooltip/Tag-Pill Improvements Summary

Surgical fixes for 6 user-facing UI bugs plus tag pill display and nav tree + graph node tooltip improvements. All changes are targeted to the exact function, template section, or CSS rule causing the issue.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | workspace-layout.js fixes (tab active guard, split investigation) | 3b9ec72 | workspace-layout.js |
| 2 | workspace.js, graph.js, CSS, templates (all remaining fixes) | bd421be | workspace.js, graph.js, workspace.css, object_read.html, _field.html, tree_children.html, router.py |

## Bug Fix Details

### Fix 1 — Tab Active Guard in switchTabInGroup

**Root cause:** `switchTabInGroup()` in workspace-layout.js had no early-return check for the currently active tab. Clicking an already-active tab triggered a full `htmx.ajax()` reload, clearing in-progress edits.

**Fix:** Added one-line guard after the `if (!group) return;` check:
```javascript
if (group.activeTabId === tabId) return;  // no-op: tab already active
```

**File:** `frontend/static/js/workspace-layout.js`, line 874 (now line ~880 after comment)

---

### Fix 2 — Split Content Bleed Investigation

**Investigation:** Traced `splitRight()` → `addGroup()` → `recreateGroupSplit()` sequence. The DOM for `#editor-area-{newGroupId}` is created synchronously by `recreateGroupSplit()`. `loadTabInGroup(newGroupId, dupTab.id)` uses the `newGroupId` parameter directly — not `layout.activeGroupId` or any dynamic lookup. The duplicate tab is pushed into `newGroup.tabs` before `loadTabInGroup` fires, so the tab lookup succeeds.

**Finding:** No timing issue or groupId reference bug exists. The split sequence is correct. A detailed code comment was added to `splitRight()` documenting this finding.

---

### Fix 3 — Docs Tab Open

**Investigation:** `_sidebar.html` calls `openDocsTab()` via onclick. The function is defined in workspace.js and exposed as `window.openDocsTab`. `loadTabInGroup` resolves `'special:docs'` to `/browser/docs` (workspace-layout.js line ~726). The implementation follows the same pattern as `openSettingsTab()` confirmed correct in Phase 18-01.

**Finding:** No bug found. Investigation comment added to workspace.js.

---

### Fix 4 — Tutorial Launch from Docs Page

**Investigation:** `docs_page.html` buttons already use `if(typeof window.startWelcomeTour==='function')` guards. `tutorials.js` correctly exposes `window.startWelcomeTour` and `window.startCreateObjectTour`. Both files load synchronously in base.html.

**Finding:** No bug found. Implementation is correct.

---

### Fix 5 — Edit Button First-Touch

**Investigation:** Traced safe_id encoding: `object_tab.html` computes `{{ object_iri | urlencode | replace('%', '_') }}` and passes it to both the button onclick and the window key assignment. `toggleObjectMode` in workspace.js uses the same value. The `_initEditMode_` function is registered synchronously in the IIFE during htmx swap, before any user click is possible.

**Finding:** No encoding mismatch or timing issue. Investigation comment added to workspace.js documenting the confirmed-correct implementation.

---

### Fix 6 — Autocomplete Dropdown Position

**Investigation:** `workspace.css` already uses `position:fixed; z-index:9999` for `.suggestions-dropdown`. `object_form.html` positions it via `getBoundingClientRect()` in the `htmx:afterSwap` handler, and has a scroll/resize reposition handler.

**Finding:** Already fixed (Phase 10-02 decision). Investigation comment added to workspace.js.

---

## Tag Pill Implementation

### Read-Only View (object_read.html)

**Property path IRI:** `urn:sempkm:model:basic-pkm:tags` — confirmed from installed model at `/app/models/basic-pkm/shapes/basic-pkm.jsonld`. The property has `sh:datatype xsd:string` (not `sh:class`) making it a plain string multi-value field.

**Match condition:** `{% elif 'tags' in prop.path %}` — matches the substring 'tags' in the full IRI. Placed after `anyURI` branch, before the plain-string fallback.

**Rendering:** Each string value renders as `<span class="tag-pill">#{{ v }}</span>`.

### Edit Form View (forms/_field.html)

**Match condition:** Same `'tags' in prop.path` condition.

**Styling:** `tag-pill-item` class added to each `.multi-value-item` div for both the `{% if values %}` loop and the empty-state single-item div.

The `.tag-pill-item` CSS uses transparent background input inside a pill container, matching the read-only pill visual while keeping the input editable.

---

## Nav Tree Tooltip Implementation

**Backend change:** `router.py` `/tree/{type_iri}` endpoint now calls `label_service.resolve_batch([decoded_iri])` to resolve the type label and passes `type_label` to the template context.

**Template change:** `tree_children.html` adds `data-tooltip-label="{{ obj.label }}"` and `data-tooltip-type="{{ type_label | default('') }}"` to each `.tree-leaf` div.

**JavaScript:** `initNavTreeTooltips()` in `workspace.js` creates one shared `.nav-tree-tooltip` div appended to `document.body`. Uses event delegation (`document.addEventListener('mouseover', ...)`) so it works for dynamically loaded nav tree content loaded via htmx. Positions the tooltip to the right of the hovered item using `getBoundingClientRect()` with viewport overflow protection.

**CSS:** `.nav-tree-tooltip`, `.tooltip-type`, `.tooltip-label` styles match graph-popover format.

---

## Graph Node Hover Tooltip

**Confirmed working:** `_showNodePopover()` in `graph.js` already uses `.graph-popover-type` and `.graph-popover-label`. `typeLabel` is populated from backend `node.type_label` which is resolved in `views/service.py` via `LabelService.resolve_batch()` for all node type IRIs. The `if (d.typeLabel)` guard conditionally shows the type span. No structural changes needed.

A confirmation comment was added near `_showNodePopover()` documenting this verification.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing context] Added type_label to tree_children router endpoint context**
- **Found during:** Task 2, nav tree tooltip implementation
- **Issue:** `type_label` was not passed to `tree_children.html` template context — it would render empty without it
- **Fix:** Added `label_service.resolve_batch([decoded_iri])` call and `type_label` to context dict in `router.py`
- **Files modified:** `backend/app/browser/router.py`
- **Commit:** bd421be (included in Task 2 commit)

### Findings That Were No-Op Fixes

The following items were documented as "investigation required" but were found to be already correct:
- Docs tab open: `openDocsTab()` correctly wired, no bug
- Tutorial launch: buttons already have `typeof` guards, `tutorials.js` exposes functions on window
- Edit button first-touch: safe_id encoding matches, no timing issue
- Autocomplete dropdown: already uses `position:fixed` from Phase 10-02 fix

In all cases, code comments were added to document the investigation outcome.

## Self-Check: PASSED

All 8 modified files exist on disk. Both task commits (3b9ec72, bd421be) confirmed in git log.
