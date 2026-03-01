---
phase: 28-ui-polish-integration-testing
plan: "02"
subsystem: ui, testing
tags: [playwright, e2e, contextual-panel, css, javascript, webdav, sparql, fts]

# Dependency graph
requires:
  - phase: 28-01
    provides: "[data-panel-name] attributes on sidebar panel <details> elements, drag-and-drop CSS framework"
  - phase: 23
    provides: SPARQL console (Yasgui embed) — tested by sparql-console.spec.ts
  - phase: 24
    provides: FTS keyword search API — tested by fts-search.spec.ts
  - phase: 26
    provides: VFS WebDAV endpoint — tested by vfs-webdav.spec.ts
provides:
  - "POLSH-03: Teal accent bar on Relations and Lint panel headers when object is active in editor"
  - "POLSH-04: Three Playwright E2E test files for SPARQL, FTS, and WebDAV features"
  - "setContextualPanelActive() JS function toggled via sempkm:tab-activated / sempkm:tabs-empty custom events"
  - "workspace-layout.js dispatches custom events on tab switch and tab removal"
affects: [29, testing, e2e]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Custom DOM events (sempkm:tab-activated, sempkm:tabs-empty) decouple workspace.js from workspace-layout.js"
    - "E2E test files use test.skip() with explanation for graceful degradation when features not yet active"
    - "Contextual panel indicator applied via CSS class toggle on [data-panel-name] elements"

key-files:
  created:
    - e2e/tests/sparql-console.spec.ts
    - e2e/tests/fts-search.spec.ts
    - e2e/tests/vfs-webdav.spec.ts
  modified:
    - frontend/static/css/workspace.css
    - frontend/static/js/workspace.js
    - frontend/static/js/workspace-layout.js
    - docs/guide/04-workspace-interface.md

key-decisions:
  - "POLSH-03: Custom event approach used to decouple workspace.js and workspace-layout.js — sempkm:tab-activated dispatched from both openTab() (new tab) and switchTabInGroup() (tab switch)"
  - "POLSH-03: setTimeout(0) deferred check restores contextual panel state on page load after workspace-layout.js sets window._workspaceLayout"
  - "POLSH-04: All E2E test files use test.skip() graceful degradation so they are syntactically valid and committable before dependent phases complete"

patterns-established:
  - "Custom DOM event pattern: workspace-layout.js dispatches events, workspace.js listens — clean separation without global function coupling"
  - "E2E test skip pattern: check feature availability first (count elements or probe API), call test.skip(true, reason) with descriptive message if not available"

requirements-completed: [POLSH-03, POLSH-04]

# Metrics
duration: 25min
completed: 2026-03-01
---

# Phase 28 Plan 02: Object-contextual panel indicator and E2E integration test files

**Teal 3px accent bar on Relations/Lint panel headers when editor has active object tab, plus Playwright E2E test files for SPARQL Console, FTS search, and WebDAV VFS**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-01T11:00:00Z
- **Completed:** 2026-03-01T11:25:00Z
- **Tasks:** 5
- **Files modified:** 7

## Accomplishments
- Object-contextual panel indicator (POLSH-03): teal border-left on Relations and Lint panel headers when any editor group has an active tab, disappears when all tabs are closed
- Custom DOM event architecture: workspace-layout.js dispatches `sempkm:tab-activated` and `sempkm:tabs-empty`; workspace.js listens and calls `setContextualPanelActive()`
- Three E2E test files created for SPARQL Console, FTS Keyword Search, and VFS WebDAV — all syntactically valid with test.skip() graceful degradation
- User guide updated with contextual panel indicator tip

## Task Commits

Each task was committed atomically:

1. **Task 1: Object-contextual panel indicator CSS and JS (POLSH-03)** - `4914cdc` (feat)
2. **Task 2: sparql-console.spec.ts E2E test file (POLSH-04)** - `6a4f9fe` (feat)
3. **Task 3: fts-search.spec.ts E2E test file (POLSH-04)** - `a6d9b7a` (feat)
4. **Task 4: vfs-webdav.spec.ts E2E test file (POLSH-04)** - `c350571` (feat)
5. **Task 5: User guide docs update** - `efa02dc` (docs)

## Files Created/Modified
- `frontend/static/css/workspace.css` - Added `.contextual-panel-active > summary.right-section-header` rule with 3px teal border-left
- `frontend/static/js/workspace.js` - Added `setContextualPanelActive()` function, event listeners, deferred init check, window export
- `frontend/static/js/workspace-layout.js` - Dispatches `sempkm:tab-activated` from `switchTabInGroup()`, dispatches `sempkm:tabs-empty` from `removeTabFromGroup()` when all groups empty
- `e2e/tests/sparql-console.spec.ts` - 6 tests: bottom panel open, SPARQL tab activation, Yasgui load, query execution, IRI link rendering, localStorage persistence
- `e2e/tests/fts-search.spec.ts` - 7 tests: Ctrl+K palette, text input, API endpoint, result fields, UI integration, result click
- `e2e/tests/vfs-webdav.spec.ts` - 7 tests: OPTIONS response, PROPFIND 207, directory listing, object .md file GET, frontmatter structure, PUT 405, pure HTTP access
- `docs/guide/04-workspace-interface.md` - Added tip about teal accent bar indicator for contextual panels

## Decisions Made
- Custom DOM event approach used for POLSH-03: `workspace-layout.js` dispatches `sempkm:tab-activated` / `sempkm:tabs-empty`, `workspace.js` listens — cleaner than direct function coupling between separate IIFE scripts
- Dispatch added to both `openTab()` (new tab creation) in workspace.js AND `switchTabInGroup()` in workspace-layout.js to cover all tab activation paths
- `setTimeout(0)` deferred check in workspace.js init block ensures `window._workspaceLayout` is populated by workspace-layout.js before the contextual state restore runs
- E2E test files use `test.skip(true, reason)` pattern so they are valid TypeScript and committable before Phases 23, 24, 26 complete — tests activate automatically when features are live

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- POLSH-03 and POLSH-04 complete; Phase 28 is 2/4 plans done
- E2E test files ready to run against Docker stack — will skip gracefully until Phase 23/24/26 features are active
- Phase 28 Plan 03 and 04 (remaining polish items) can proceed

---
*Phase: 28-ui-polish-integration-testing*
*Completed: 2026-03-01*
