# Phase 28: UI Polish + Integration Testing - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix visual rough edges (expander icon visibility), add drag-and-drop sidebar panel rearrangement in the object browser, add a teal accent bar indicator for object-contextual panels, and write dedicated Playwright E2E test files for each v2.2 feature area (SPARQL, FTS, VFS). Depends on Phases 23, 24, 26 being complete so E2E tests can exercise real features.

</domain>

<decisions>
## Implementation Decisions

### Expander Icon Fix (POLSH-01)
- Expander/collapse icons in the sidebar nav tree are not visible on some theme combinations
- Fix by ensuring icons use token-referenced colors (not hardcoded) and have sufficient contrast in both light and dark themes
- Part of Phase 25 CSS token work may already address this — Phase 28 verifies and patches any remaining cases

### Panel Rearrangement Mechanism (POLSH-02)
- **Drag-and-drop**: User drags a panel header to the opposite sidebar to move it
- Not a context menu or settings-page toggle — in-place drag feels native to VS Code users
- Implementation WITHOUT dockview-core (Phase A dockview migration is v2.3):
  - Use HTML5 drag-and-drop API (same approach as workspace tab drag-and-drop in Phase 14)
  - Panels have drag handles on their headers
  - Dropping in the opposite sidebar reinserts the panel DOM there
  - Position (left/right) persists in localStorage per panel ID
- Scope: sidebar panels in the object browser only (e.g., Relations panel, Lint panel) — NOT the main editor groups

### Object-Contextual Indicator (POLSH-03)
- **Teal accent bar**: a thin `3px` `border-left` using `var(--color-accent)` on the panel header element
- Applied when the panel's data is scoped to the currently open object (e.g., Relations panel shows this object's relations)
- Global panels (e.g., a panel showing workspace-level info) have no accent bar
- Subtle, consistent with existing teal accent used for active tabs

### E2E Test Files (POLSH-04)
Three new Playwright test files in `e2e/tests/`:

**`sparql-console.spec.ts`:**
- Open bottom panel, switch to SPARQL tab
- Yasgui loads successfully (query editor visible)
- Execute a simple SELECT query, results render
- SemPKM IRI in results renders as a clickable link
- Clicking IRI opens object in active editor group
- localStorage persistence: query survives page reload

**`fts-search.spec.ts`:**
- Open Ctrl+K command palette
- Type keyword that matches a seeded object's literal property
- FTS results appear (type icon, label, snippet visible)
- Clicking result opens object in editor group
- Non-label property value match: object surfaces via property content search

**`vfs-webdav.spec.ts`:**
- WebDAV endpoint `/dav/` responds (HTTP 207 Multi-Status for PROPFIND)
- Directory listing contains model/type folders
- Object `.md` file content matches expected frontmatter and body
- Read-only enforcement: PUT attempt returns 405
- (Note: uses API token auth — test setup generates a token first)

### Claude's Discretion
- Whether POLSH-01 (expander icons) and POLSH-02/03 (panel features) go in a single plan or split into two
- Exact drag-and-drop implementation detail (dragstart/dragenter/drop handlers on panel header vs drag handle element)
- Whether to add panel rearrangement to ALL object browser sidebar panels or only specific ones

</decisions>

<specifics>
## Specific Ideas

- Phase 14 (Split Panes) implemented HTML5 drag-and-drop for workspace tabs — the same drag pattern and `isDragging` guard can be adapted for sidebar panels
- The Relations panel and Lint panel are the primary candidates for left↔right rearrangement
- Teal accent: `var(--color-accent)` is already defined in theme.css — no new tokens needed

</specifics>

<deferred>
## Deferred Ideas

- Full dockview-core panel system — v2.3 Phase A
- Context menu "move to right sidebar" as alternative to drag — simpler fallback, not needed if drag works
- Floating/detached panels — future

</deferred>

---

*Phase: 28-ui-polish-integration-testing*
*Context gathered: 2026-02-28*
