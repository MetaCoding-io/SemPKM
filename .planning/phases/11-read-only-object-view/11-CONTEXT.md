# Phase 11: Read-Only Object View - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Objects open in a styled read-only presentation by default. Users see formatted property key-value pairs and rendered Markdown body. An edit toggle switches to the existing edit mode. Reference properties are clickable links. Newly created objects open in edit mode. Sidebar, navigation, and dark mode are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Property presentation
- Two-column table layout: labels on left, values on right (like VS Code details panel or GitHub issue sidebar)
- Labels styled bold, normal case — clear hierarchy, document-like feel
- Empty optional properties are hidden entirely — only properties with values display
- Type-specific value formatting: dates as human-readable (e.g., "Feb 23, 2026"), booleans as check/x icons, URIs as clickable links

### Mode switching feel
- Edit/Done toggle button positioned top-right of content area
- Horizontal flip animation (card rotates on vertical axis) when transitioning between read-only and edit mode
- Edit mode indicated by a subtle background tint (e.g., faint blue) so user knows they're in editing state
- Switching from edit to read-only with unsaved changes prompts "Discard changes?" confirmation
- Newly created objects open directly in edit mode (no flip needed)
- Ctrl+E keyboard shortcut toggles mode

### Markdown body rendering
- GitHub-style rendering: proportional font, generous spacing, clear heading hierarchy
- Syntax-highlighted code blocks with code font and subtle background (like GitHub fenced blocks)
- Thin horizontal rule as visual separator between property table and Markdown body
- Images rendered inline where they appear in the Markdown text

### Reference link behavior
- Reference values displayed as pill/badge style — rounded pill with subtle background, visually distinct from plain text
- Each pill shows a type icon (or colored dot) + object name — visual hint of the linked object's type
- Hovering a reference pill shows a tooltip preview with the linked object's type and key properties
- Clicking a reference pill opens the target object in a new tab
- Multiple references on a property wrap inline as a pill row (like tags), flowing naturally

### Claude's Discretion
- Exact flip animation duration and easing
- Specific color values for edit-mode background tint
- Markdown rendering library choice (marked, markdown-it, etc.)
- Syntax highlighting library choice (highlight.js, Prism, etc.)
- Tooltip preview layout and which properties to show
- Type icon mapping (until Phase 15 icon system exists, use simple colored dots or generic icons)
- Exact spacing and padding in the two-column table

</decisions>

<specifics>
## Specific Ideas

- "It would be cool to do a flip type animation to go to edit mode" — horizontal card flip on vertical axis
- Property table should feel like GitHub's sidebar details — clean, scannable
- Markdown rendering should feel like a GitHub README — familiar, polished
- Reference pills similar to tag/label UI patterns — small, rounded, inline-wrapping

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-read-only-object-view*
*Context gathered: 2026-02-23*
