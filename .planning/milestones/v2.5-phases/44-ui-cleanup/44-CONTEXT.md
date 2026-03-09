# Phase 44: UI Cleanup - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix VFS browser rendering issues and address a set of specific UI bugs/polish items across the workspace. No new features -- this is a cleanup and consistency pass.

</domain>

<decisions>
## Implementation Decisions

### VFS Browser Fixes
- CodeMirror editor text is too large -- no explicit font-size set, defaults to 14px while surrounding UI is 0.8-0.85rem. Set explicit font-size to match.
- All text in the CodeMirror editor is underlined -- likely CSS bleeding from a parent `<a>` tag or `.markdown-body` link styles. Investigate and fix.
- Rendered markdown preview is not visible at all -- this is a bug, it should exist but doesn't show. Fix so users see rendered markdown (not just raw source).

### VFS CodeMirror Theming
- CodeMirror currently uses hardcoded Atom One Dark / light colors (lines 293-305 of vfs-browser.js)
- Switch to SemPKM's CSS variable tokens so it follows light/dark mode automatically
- Should match the app theme, not look like a separate embedded editor

### Tab Type Icons
- Dockview editor tabs should show the type-specific Lucide icon for the object (Note, Person, Concept, etc.)
- Same icons already used in the nav tree (IconService reads manifest icon declarations)
- Wire the existing icon system into tab rendering

### Sidebar Accent Color
- Sidebar contextual panels (lint, relations) currently show a fixed teal accent
- Change to match the active tab's type-specific color (e.g. blue for Note, green for Person)
- The per-group accent color system already exists (Phase 39 work set `--tab-accent-color` on groups)

### Helptext Required Validation Bug
- Expanding the helptext on a Note's title field, then clicking elsewhere, eventually triggers a false "field is required" validation error even though the field is filled
- Only confirmed on title field so far, may affect other fields
- Likely a focus/blur event handler issue with the helptext expand/collapse interaction

### Keyboard Shortcuts Flakey
- All shortcuts (Ctrl+K, Ctrl+B, Ctrl+J, etc.) intermittently stop working
- They work on fresh page load, then stop, then work again if pressed repeatedly
- Suggests a timing issue -- possibly event listeners being removed/re-added by htmx swaps, or focus stealing
- Investigation needed to find root cause (htmx swap removing listeners, dockview focus management, etc.)

### Event Console Form Visibility
- On the /events page, when it initially loads showing object.create events, the form/filter area is not visible
- Becomes visible when the user switches the dropdown to a different event type and back
- Likely a CSS display or htmx swap timing issue on initial page load

### Claude's Discretion
- Exact CodeMirror font-size value (should visually match surrounding UI)
- Order of fixes within the phase
- Whether to batch related CSS fixes or address individually

</decisions>

<specifics>
## Specific Ideas

- Tab icons should use the same IconService that powers the nav tree -- no new icon system needed
- Sidebar accent should reuse the `--tab-accent-color` CSS variable pattern from Phase 39
- VFS CodeMirror theme should use CSS variables from theme.css, not hardcoded hex values

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IconService` (backend): reads manifest icon/color declarations, already wired into explorer tree, editor tabs (partially), and Cytoscape graph
- `--tab-accent-color` CSS variable: set per-group on `panel.group.element` in workspace-layout.js
- `.panel-btn svg` pattern: reference for Lucide icon sizing in flex containers (flex-shrink: 0)
- Theme CSS variables: `--color-bg`, `--color-text`, `--color-surface`, etc. in theme.css

### Established Patterns
- Dark/light theme via `data-theme` attribute on `<html>`, CSS variables respond automatically
- CodeMirror elsewhere in app (SPARQL console) may have theme patterns to copy
- `sempkm:tab-activated` custom event decouples tab focus from panel updates

### Integration Points
- VFS browser CSS: `frontend/static/css/vfs-browser.css` (490 lines)
- VFS browser JS: `frontend/static/js/vfs-browser.js` (CodeMirror init lines 293-340)
- Workspace CSS: `frontend/static/css/workspace.css` (markdown-body styles ~lines 1739-1806)
- workspace-layout.js: `createComponentFn` where tabs are created (icon injection point)
- Event console: `backend/app/templates/events/` templates

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 44-ui-cleanup*
*Context gathered: 2026-03-08*
