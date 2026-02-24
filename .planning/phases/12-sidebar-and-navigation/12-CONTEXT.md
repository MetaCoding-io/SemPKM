# Phase 12: Sidebar and Navigation - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize the existing sidebar into grouped, collapsible sections with a collapse-to-icon-rail toggle (Ctrl+B) and a user menu popover at the bottom. Replace Unicode emoji icons with Lucide SVG icons. Admin becomes a section with sub-items; admin dashboard page removed in favor of direct nav links.

</domain>

<decisions>
## Implementation Decisions

### Sidebar sections & grouping
- Collapsible section headers: each group (Admin, Meta, Apps, Debug) has a clickable header that toggles show/hide of its items
- Home nav item removed entirely -- clicking the SemPKM brand logo navigates home
- Admin becomes a section header with sub-items (Users, Teams, Mental Models) rather than a single link to /admin/
- The /admin/ dashboard page is removed since its content is now accessible via direct sidebar nav links
- Lucide icons (SVG) replace all Unicode emoji icons -- same library planned for Phase 15 node type icons, loaded via CDN

### Collapse-to-icon-rail behavior
- Ctrl+B toggles sidebar between 220px expanded and 48px icon rail
- Hovering over an icon in collapsed mode shows a tooltip with the item name (VS Code activity bar style)
- Toggle button lives at the top of the sidebar (next to or below the brand logo area)
- Thin horizontal divider lines separate sections even in collapsed icon rail mode
- Collapsed/expanded state persists across page reloads via localStorage

### User menu & popover
- User area pinned to the bottom of the sidebar shows: colored initials avatar circle + display name (no role badge)
- Avatar: first letter(s) of user's name on a colored circle background (Google/Slack style)
- Clicking the user area opens a popover with: Settings link (opens settings tab placeholder), Theme toggle (placeholder for Phase 13), and Logout button
- When sidebar is collapsed to icon rail, user area shows just the small avatar circle -- clicking opens the same popover

### Visual style & density
- Compact (VS Code-like) density: tight spacing, small text (12-13px), fits many items without scrolling
- Active nav item indicated by subtle background highlight only -- no left border accent
- Section headers: normal case labels (not uppercase) with a subtle divider line below
- Sidebar width stays at 220px expanded

### Claude's Discretion
- Exact Lucide icon choices for each nav item
- Exact spacing/padding values within compact constraints
- Popover positioning and animation
- Collapse/expand CSS transition timing
- How section collapse state interacts with sidebar collapse state

</decisions>

<specifics>
## Specific Ideas

- VS Code activity bar as the reference for icon rail tooltips and compact density
- Google/Slack as the reference for colored initials avatar circles
- Section headers should feel lighter than VS Code's uppercase convention -- normal case with subtle divider is the preference

</specifics>

<deferred>
## Deferred Ideas

- Removing/replacing the admin dashboard page may surface items that need new homes -- capture as todos if discovered during implementation
- Settings page itself is Phase 15 scope -- the Settings link in the popover is a placeholder for now

</deferred>

---

*Phase: 12-sidebar-and-navigation*
*Context gathered: 2026-02-23*
