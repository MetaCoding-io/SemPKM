---
id: T02
parent: S01
milestone: M003
provides:
  - Explorer mode dropdown in OBJECTS section header with htmx-wired mode switching
  - "#explorer-tree-body" swap target for all explorer mode content
  - refreshNavTree() respects current mode selection
key_files:
  - backend/app/templates/browser/workspace.html
  - frontend/static/css/workspace.css
  - frontend/static/js/workspace.js
  - backend/app/templates/browser/explorer_placeholder.html
key_decisions:
  - Placed <select> outside .explorer-header-actions span so it's always visible (not hidden behind hover-reveal opacity:0)
  - Mode dropdown uses hx-include="this" to pass mode param as query string
patterns_established:
  - Explorer mode dropdown lives in the section header at the same level as .explorer-header-actions, not inside it
  - htmx swap target is #explorer-tree-body (the .explorer-section-body div)
  - refreshNavTree() reads current mode from #explorer-mode-select and routes through /browser/explorer/tree?mode=X
observability_surfaces:
  - "document.getElementById('explorer-mode-select').value shows current mode"
  - "#explorer-tree-body innerHTML shows rendered content for current mode"
  - htmx swap failures appear in browser console
duration: 25min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Add mode dropdown to workspace UI and wire htmx swap

**Added explorer mode dropdown to OBJECTS section header with htmx swap wiring — By Type, Hierarchy, and By Tag modes switch tree content via /browser/explorer/tree endpoint.**

## What Happened

Added a `<select id="explorer-mode-select">` dropdown to the OBJECTS section header in workspace.html with three options (By Type, Hierarchy, By Tag). The dropdown is wired with htmx attributes (`hx-get`, `hx-target="#explorer-tree-body"`, `hx-trigger="change"`) to swap the explorer tree content on mode change. Added `id="explorer-tree-body"` to the `.explorer-section-body` div as the swap target.

The dropdown is placed outside `.explorer-header-actions` (which has hover-reveal `opacity: 0`) so it's always visible. `onclick="event.stopPropagation()"` prevents the section expand/collapse toggle from firing. `hx-on::after-swap` re-initializes Lucide icons after content swap.

Updated `explorer_placeholder.html` to include `data-testid="explorer-placeholder"` for E2E targeting.

Added CSS `.explorer-mode-select` styles — compact, borderless, transparent background matching the explorer header aesthetic.

Updated `refreshNavTree()` in workspace.js to read the current mode from `#explorer-mode-select` and route refresh requests through `/browser/explorer/tree?mode=X` instead of the hardcoded `/browser/nav-tree` path.

## Verification

- **Unit tests:** `python -m pytest tests/test_explorer_modes.py -v` — 8/8 passed (mode registry, handlers, dispatch)
- **Browser — dropdown visible:** Confirmed `#explorer-mode-select` renders in OBJECTS header with "By Type" selected by default
- **Browser — mode switch to Hierarchy:** Selected "Hierarchy", confirmed `[data-testid="explorer-placeholder"]` visible with "Hierarchy mode — coming soon" text and Lucide compass SVG
- **Browser — mode switch to By Tag:** Selected "By Tag", confirmed placeholder with "Tag mode — coming soon" and lucide-tag SVG class
- **Browser — switch back to By Type:** Confirmed `[data-testid="nav-section"]` elements restored, type nodes (Project Shape, Person Shape, etc.) visible
- **Browser — lazy expansion after swap:** Clicked Project Shape after switching back to By Type, children loaded correctly via htmx
- **Browser — stopPropagation:** Clicked dropdown, verified `#section-objects` remains `.expanded` (class unchanged)
- **Browser — Lucide re-init:** Verified `<svg class="lucide lucide-tag">` rendered inside placeholder after swap
- **Browser — DOM IDs preserved:** `#section-objects`, `#explorer-tree-body` confirmed present
- **Browser — `data-testid` preserved:** `nav-section` and `nav-item` attributes present in by-type tree after expansion
- **Console logs:** No htmx errors from mode switching

### Slice-level verification status

- ✅ `python -m pytest tests/test_explorer_modes.py -v` — 8/8 passed
- ⏳ `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — stubs exist (test.fixme), implementation deferred to T04
- ✅ Manual: by-type returns nav tree HTML (verified via browser)
- ✅ Manual: hierarchy returns placeholder HTML (verified via browser)
- ⏳ Manual: invalid mode returns 400 (verified in T01 unit tests, curl blocked by auth redirect)

## Diagnostics

- `document.getElementById('explorer-mode-select').value` — shows current mode
- `#explorer-tree-body` innerHTML — shows rendered content for current mode
- Browser console shows htmx swap failures if endpoint is unreachable
- Server-side: DEBUG log `"Explorer tree requested: mode=%s"` on every dispatch (from T01)

## Deviations

- Moved `<select>` outside `.explorer-header-actions` span instead of inside it (plan said "inside the `.explorer-header-actions` span, before the action buttons"). The hover-reveal `opacity: 0` on that span made the dropdown invisible. Placing it as a sibling keeps it always visible while action buttons remain hover-revealed.
- Updated `refreshNavTree()` in workspace.js to respect the mode dropdown — not explicitly in the plan but necessary for correct refresh behavior.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/workspace.html` — added mode dropdown, `id="explorer-tree-body"` on section body
- `frontend/static/css/workspace.css` — added `.explorer-mode-select` styles (compact, borderless, theme-matched)
- `frontend/static/js/workspace.js` — updated `refreshNavTree()` to read mode from dropdown and route through explorer/tree endpoint
- `backend/app/templates/browser/explorer_placeholder.html` — added `data-testid="explorer-placeholder"` attribute
