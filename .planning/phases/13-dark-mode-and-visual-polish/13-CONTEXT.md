# Phase 13: Dark Mode and Visual Polish - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Tri-state theme system (System/Light/Dark) with consistent dark styling across all UI components including third-party libraries, rounded tabs, and styled 403 error panels. Light mode gets a refresh to share the same CSS custom property token system.

</domain>

<decisions>
## Implementation Decisions

### Color palette & feel
- Inspired by VS Code Dark+ but softer — warmer grays, less saturated accents
- Teal/cyan accent colors (not pure blue) for links, active states, focus rings
- Subtle but visible borders between all regions — no "flat sea of darkness." Every panel edge (sidebar, editor, right panel, tab bar) should be delineated with 1px borders ~10-15% lighter than surface
- Light mode also gets refreshed to use the same CSS custom property token system (both themes share tokens)

### Theme toggle UX
- Toggle lives in both the user menu popover AND the command palette
- User popover shows a 3-icon row: Sun / Monitor / Moon — click to select
- Theme changes use a quick ~150ms crossfade transition on background and text colors
- "System" mode reads OS preference on page load only — does not react to mid-session OS prefers-color-scheme changes
- Preference persists in localStorage; anti-FOUC inline script applies theme before first paint

### Tab rounding & chrome
- Subtle 4px top border-radius on tabs — minimal change from current flat tabs
- Active tab gets both a lighter background (matching editor area) AND a teal bottom accent line
- Inactive tabs are muted/recessed
- Tab bar has a recessed/darker background behind the tabs, making tabs pop forward
- Close button (x) shows on hover only; active tab always shows close button

### Claude's Discretion
- Exact color hex values within the "softer Dark+" direction
- Anti-FOUC script implementation details
- How to handle CodeMirror theme compartment reconfiguration
- Cytoscape and ninja-keys dark mode integration approach
- 403 error panel layout and copy (roadmap says: lock icon, role explanation, navigation buttons)
- Split.js gutter styling in dark mode

</decisions>

<specifics>
## Specific Ideas

- Dark mode should never feel like a "flat sea of darkness" — visible borders are essential for spatial orientation
- High-contrast themes were cited as a good reference for border visibility
- Teal/cyan gives SemPKM a more unique identity vs generic blue IDE feel

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-dark-mode-and-visual-polish*
*Context gathered: 2026-02-23*
