# Phase 32: Carousel Views and View Bug Fixes - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Object types with multiple manifest-declared views expose a carousel tab bar for instant view switching. Concept cards group-by is fixed. Broken graph/card/table view switch buttons are removed. The carousel tab bar is the sole view-switching affordance.

</domain>

<decisions>
## Implementation Decisions

### Tab Bar Appearance
- Position: Directly above the view body, below the object header (from Phase 31)
- Active tab indicator: Bottom border accent (colored bottom border on active tab)
- Only render the tab bar when the type has multiple views in the manifest; single-view types show no tab bar
- Tab labels: Prettified display names derived from manifest view keys (e.g., `cards_view` → "Cards View")

### View Switching UX
- Instant swap — no animation or transition when clicking a tab
- While a view fetches server data (e.g., graph view loading relationships), show a spinner in the view body area; tab bar stays interactive
- Default view on first visit: first view listed in the manifest (manifest order = priority)
- Remove the old broken graph/card/table view switch buttons and their code entirely — the carousel tab bar replaces them

### Cards Group-By Display
- Collapsible accordion sections — each group is a collapsible section with a header
- All groups expanded by default; users can collapse groups they don't need
- Objects missing the group-by predicate value appear in an "Ungrouped" section at the bottom
- Group headers show a count of cards in the group (e.g., "Philosophy (5)")

### Persistence
- Active tab selection persists per type IRI (not per individual object) — switching to "Graph" on any Concept remembers "Graph" for all Concepts
- Storage: localStorage, consistent with existing `sempkm_panel_positions` pattern
- If the manifest changes and the saved view no longer exists, fall back to the first available view silently (no error/toast)
- Accordion collapse/expand state does NOT persist — resets to all-expanded each session

### Claude's Discretion
- Exact tab bar styling, colors, spacing, and typography
- Spinner implementation details
- localStorage key naming convention
- Accordion expand/collapse animation details

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-carousel-views-and-view-bug-fixes*
*Context gathered: 2026-03-03*
