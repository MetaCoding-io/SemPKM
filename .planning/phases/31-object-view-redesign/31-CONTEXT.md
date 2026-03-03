# Phase 31: Object View Redesign - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Redesign the object tab so the Markdown body is the primary content in both view AND edit modes, with RDF properties hidden behind a toggle. Users can expand/collapse properties with a single click, and their preference is remembered per object IRI. The existing CSS 3D flip between view/edit modes must remain unaffected. Both sides of the flip card share the same body-first, properties-collapsed pattern.

</domain>

<decisions>
## Implementation Decisions

### Properties toggle design
- Toggle badge positioned in the header toolbar, grouped with other controls on the right side
- Clicking the badge slides properties down inline, pushing the body content down with a smooth CSS transition
- Badge shows "N properties" with the actual count (e.g. "5 properties")
- Expanded properties list appears between the fixed header and the body content area
- **Same pattern on both sides of the flip card:** view mode shows read-only properties; edit mode shows the existing editable fieldsets (collapsible fieldsets already exist — reuse them inside the toggle)

### Body presentation
- Markdown body (view mode) or Markdown editor (edit mode) fills the full width of the dockview panel with comfortable padding
- Fixed header at top; body content scrolls independently beneath it
- When an object has no Markdown body (empty or missing): show subtle muted placeholder text ("No content") AND auto-expand properties by default
- Typography matches existing app styles — no special reading-mode treatment

### Edit mode consistency
- Edit mode mirrors the same layout: body editor is primary, properties hidden behind toggle
- The toggle in edit mode expands the existing editable fieldsets (same collapsible fieldsets that currently exist, just collapsed by default)
- Collapse preference is shared per object IRI — if user expanded properties in view mode, they stay expanded after flipping to edit mode (and vice versa)

### View header layout
- Title on the left, controls (properties badge + edit button) grouped on the right — standard toolbar pattern
- Small muted type label (e.g. "Note", "Person", "Concept") displayed next to the title as a chip or muted text
- No modified-date in the header — keep it minimal; date is available in properties when expanded
- Edit button keeps its current style unchanged — do not modify the 3D flip trigger

### Collapse state behavior
- Default state depends on body content: collapsed if body exists (body-first), expanded if body is empty
- Collapse preference stored in localStorage per object IRI — same pattern as existing panel position storage (`sempkm_panel_positions`)
- No bulk reset / "collapse all" feature — per-object only
- If localStorage is cleared, falls back to the body-aware default logic (collapsed if body, expanded if empty)

### Claude's Discretion
- Visual style of the properties badge (pill, chip, button variant — whatever fits the existing design system)
- Exact CSS transition duration and easing for the slide-down animation
- Spacing and padding values within the properties list
- localStorage key naming convention for collapse preferences

</decisions>

<specifics>
## Specific Ideas

- The properties badge should feel like a natural toolbar element, not a separate UI widget — it belongs with the edit button
- Auto-expanding properties on empty-body objects prevents the view from feeling broken or empty
- The fixed header with scrollable body ensures the toggle is always one click away, even on long Markdown documents

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 31-object-view-redesign*
*Context gathered: 2026-03-02*
