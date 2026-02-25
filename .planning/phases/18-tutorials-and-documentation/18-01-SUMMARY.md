---
phase: 18-tutorials-and-documentation
plan: "01"
subsystem: workspace-ui
tags: [driver.js, tutorials, docs-tab, special-tab, cdn, htmx-fragment]
dependency_graph:
  requires: []
  provides: [DOCS-01, DOCS-02, special:docs-tab, Driver.js-global]
  affects: [base.html, browser/router.py, workspace.js, workspace-layout.js, workspace.css, main.py, docker-compose.yml]
tech_stack:
  added: [Driver.js 1.4.0 (jsDelivr CDN)]
  patterns: [special-tab pattern (mirrors special:settings), StaticFiles mount with is_dir() guard]
key_files:
  created:
    - backend/app/templates/browser/docs_page.html
  modified:
    - backend/app/templates/base.html
    - backend/app/browser/router.py
    - backend/app/main.py
    - docker-compose.yml
    - backend/app/templates/components/_sidebar.html
    - frontend/static/js/workspace.js
    - frontend/static/js/workspace-layout.js
    - frontend/static/css/workspace.css
decisions:
  - "special:docs tab follows the exact special:settings pattern (same openDocsTab/openSettingsTab structure, same isSpecial guard extension)"
  - "StaticFiles mount guarded by is_dir() check to prevent startup crash when docs/ not mounted"
  - "Driver.js CSS link placed before JS script tag in base.html (prevents unstyled overlay flash per RESEARCH.md Pitfall 4)"
  - "jsDelivr CDN used for Driver.js (consistent with marked/DOMPurify pattern in project)"
metrics:
  duration: "4min"
  completed: "2026-02-25"
  tasks: 2
  files: 8
---

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
