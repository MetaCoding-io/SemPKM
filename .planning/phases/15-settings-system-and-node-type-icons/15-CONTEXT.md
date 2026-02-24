# Phase 15: Settings System and Node Type Icons - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

A layered settings infrastructure (system defaults → mental model defaults → user overrides) with a Settings page UI, and type-specific Lucide icons with color coding in the explorer tree, graph view, and editor tabs. Mental models can contribute settings and icon/color mappings via their manifest. Dark mode is the first and only real setting wired up this phase; the system is built to expand later.

</domain>

<decisions>
## Implementation Decisions

### Settings Page Layout
- Two-column layout: category sidebar on the left, settings detail panel on the right (VS Code / macOS System Preferences style)
- Settings are accessible via both `Ctrl+,` (global shortcut, works from anywhere) and the user menu
- Search filter works in-place: non-matching settings hide, categories collapse if all their settings are filtered out
- Apply is instant — no Save button; changes dispatch `sempkm:setting-changed` immediately on change

### Modified Indicators
- Both a badge ("Modified") and a per-setting reset button appear when a value differs from its default
- Per-setting reset plus a "Reset all to defaults" option per category and globally

### Setting Input Types
- All four input types required: toggle (boolean), dropdown/select, text input, color picker
- Initial settings scope: dark mode only — the system is wired up and ready to expand, but only dark mode is a real setting in this phase

### Persistence
- User overrides stored server-side in the database (not localStorage)
- Syncs across browsers/devices

### Icon Visual Treatment
- Each node type gets a distinct color (defined in the mental model manifest per type)
- Same icon and same color used consistently in explorer tree, graph view, and editor tab headers
- Icons appear on object tab headers: icon + object name
- Fallback for unmapped types: a generic neutral icon (e.g., circle/dot) in a neutral color
- Manifest supports icon, color, and size per context (tree vs. graph vs. tab) — granular per-context control

### Mental Model Contributions
- Model-contributed settings appear under a category named after the model in the sidebar (e.g., "Zettelkasten" section)
- When a model is removed, its contributed user overrides are also removed from the database (clean slate)
- Icon/color manifest entries can specify different values per view context: `{ type, icon, color, size }` per context

### Claude's Discretion
- Exact spacing, typography, and visual polish of the Settings page
- Progress indicator or loading state when settings are first fetched
- How color picker component is implemented (library choice or custom)
- Exact manifest JSON schema details beyond the per-context structure

</decisions>

<specifics>
## Specific Ideas

- Dark mode was explicitly called out as the first and only real settings consumer for phase 15; the system should be built to accommodate future settings without requiring another infrastructure pass
- Icon fallback should feel intentional (neutral circle/dot), not broken

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-settings-system-and-node-type-icons*
*Context gathered: 2026-02-24*
