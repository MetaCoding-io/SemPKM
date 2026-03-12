---
id: S18
parent: M001
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
# S18: Tutorials And Documentation

**# Phase 18 Plan 01: Driver.js CDN and Docs & Tutorials Tab Summary**

## What Happened

# Phase 18 Plan 01: Driver.js CDN and Docs & Tutorials Tab Summary

Driver.js 1.4.0 CDN integrated via jsDelivr, Docs & Tutorials special tab created mirroring the `special:settings` pattern, docs_page.html fragment implemented, and Driver.js popover CSS themed with project token variables.

## What Was Built

### Task 1: Driver.js CDN Integration and Docs Page Backend

**base.html CDN links added:**
```html
<!-- Driver.js guided tours (Phase 18) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/driver.js@1.4.0/dist/driver.css">
<script src="https://cdn.jsdelivr.net/npm/driver.js@1.4.0/dist/driver.js.iife.js"></script>
```
Placed after Lucide script, before `{% block head %}`. CSS before JS (per Pitfall 4).

**GET /browser/docs route** added to `backend/app/browser/router.py` after the settings_page endpoint. Static content, depends only on `get_current_user` (no DB session).

**docs_page.html fragment** created at `backend/app/templates/browser/docs_page.html`. No `{% extends %}` (bare htmx fragment matching settings_page.html pattern). Contains:
- Two tutorial cards: "Welcome to SemPKM" (`startWelcomeTour()`) and "Creating Your First Object" (`startCreateObjectTour()`)
- Six documentation links: workspace interface guide, working with objects guide, full user guide README, ReDoc, Swagger, and Health Check
- Inline script for Lucide icon re-initialization after htmx swap

**main.py StaticFiles mount:**
```python
_docs_guide_path = Path(__file__).parent.parent.parent / "docs" / "guide"
if _docs_guide_path.is_dir():
    app.mount("/docs/guide", StaticFiles(directory=_docs_guide_path), name="docs_guide")
```
Path resolves to `docs/guide/` at repo root. `is_dir()` guard prevents startup crash if volume not mounted.

**docker-compose.yml volume:**
```yaml
- ./docs:/app/docs:ro
```
Added to api service volumes, maps repo-root docs/ into container at /app/docs.

### Task 2: Special Docs Tab Wiring and Driver.js CSS Theming

**_sidebar.html** — Docs & Tutorials link changed from `disabled` anchor with `/docs` href to active `onclick="openDocsTab(); return false;"`. The `disabled` class removed, `href="#"` as fallback.

**workspace.js** — `openDocsTab()` added after `window.openSettingsTab = openSettingsTab`:
- Uses `tabKey = 'special:docs'`
- Checks for existing tab to prevent duplicates (focuses if found)
- Creates tabDef with `isSpecial: true, specialType: 'docs'`
- Exported as `window.openDocsTab`

**workspace-layout.js** — Two changes:
1. New `else if` branch in URL dispatch (after settings branch):
   ```javascript
   } else if (tabId === 'special:docs' || (tab && tab.specialType === 'docs')) {
     url = '/browser/docs';
   }
   ```
2. Extended `isSpecial` guard:
   ```javascript
   var isSpecial = tabId === 'special:settings' || (tab && tab.specialType === 'settings')
                || tabId === 'special:docs' || (tab && tab.specialType === 'docs');
   ```

**workspace.css** — Appended Driver.js popover theming (`.driver-popover`, `.driver-popover-title`, `.driver-popover-description`, `.driver-popover-footer`, `.driver-popover-progress-text`, `.driver-popover-next-btn/.driver-popover-done-btn`, `.driver-popover-prev-btn/.driver-popover-close-btn`, `.driver-overlay`) using `var(--color-*)` tokens for auto dark/light adaptation. Also appended docs page layout styles (`.docs-page`, `.docs-page-header`, `.docs-card`, `.docs-links`, `.docs-link-item`, etc.).

## Plan 02 Selector Notes

Key selectors confirmed for Plan 02's tour implementations:
- **Active editor area ID:** `#editor-area-{groupId}` (dynamic per group — Plan 02 tours should target stable semantic IDs inside the loaded content, not the editor-area container itself)
- **Sidebar nav links:** `.sidebar-nav .nav-link`
- **Sidebar groups:** `.sidebar-group[data-group="admin"]`, `.sidebar-group[data-group="meta"]`, etc.
- **Nav tree:** `#nav-tree` in the workspace left pane
- **Tab bar:** `.tab-bar` (rendered per group by `renderGroupTabBar`)
- **Driver.js global:** `window['driver.js'].driver` (IIFE export name)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- FOUND: `backend/app/templates/browser/docs_page.html`
- FOUND: `driver.js@1.4.0` in base.html (2 occurrences — CSS and JS)
- FOUND: `@router.get("/docs")` in browser/router.py
- FOUND: `mount("/docs/guide"` in main.py
- FOUND: `./docs:/app/docs:ro` in docker-compose.yml
- FOUND: `openDocsTab` in workspace.js (2 occurrences — definition + export)
- FOUND: `special:docs` in workspace-layout.js (2 occurrences — URL branch + isSpecial guard)
- FOUND: `.driver-popover` in workspace.css (11 occurrences)
- Commits: 8ed09a9, ed7b4ae both present in git log

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
