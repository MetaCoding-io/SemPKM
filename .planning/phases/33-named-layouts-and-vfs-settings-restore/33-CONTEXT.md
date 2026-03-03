# Phase 33: Named Layouts and VFS Settings Restore - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Two capabilities: (1) Users can save, restore, and delete named workspace layouts from the Command Palette and the lower-left user menu; layouts persist across sessions. (2) VFS mount configuration (token generation/revocation) is accessible from the Settings page.

</domain>

<decisions>
## Implementation Decisions

### Layout save/restore flow
- Save full workspace snapshot: dockview panel geometry + open tabs/content per panel
- Auto-persist last layout on close/reload (unnamed, automatic) — this is the "current state" that survives refresh
- Named saves are separate explicit snapshots on top of auto-save
- Naming via text input inline in Command Palette (no modal)
- Restore replaces current layout entirely, no confirmation dialog
- Best-effort restore for stale data: restore geometry always, open tabs that still exist, show brief toast listing any skipped objects

### Command Palette interaction
- Flat "Layout: ..." commands as top-level palette items: "Layout: Save As...", "Layout: Restore...", "Layout: Delete..."
- Selecting Restore or Delete replaces palette contents with list of saved layout names
- User picks from the list and action happens immediately

### Access points
- Command Palette (primary)
- Lower-left user menu (secondary) — layout management submenu for discoverability

### Storage and persistence
- localStorage only (consistent with existing `sempkm_` key patterns like carousel view persistence)
- Key namespace: `sempkm_layouts` for named saves, `sempkm_layout_current` for auto-save
- No hard limit on saved layouts (localStorage budget is ample for JSON layout data)

### Claude's Discretion
- Delete confirmation UX (inline confirm vs no confirm)
- Whether to show active layout name indicator anywhere
- Overwrite behavior when saving with an existing name (prompt vs silent replace)
- Exact toast duration and styling for stale-data warnings

### VFS Settings UI
- Controls: token generation, masked token display, revocation — matching success criteria
- Token shown in full only on creation (copy-to-clipboard), masked after (e.g., `sk-...abc3`)
- Placement and section naming within Settings page — Claude picks based on existing layout
- Connection status display — Claude decides based on what's feasible with current backend

</decisions>

<specifics>
## Specific Ideas

- User mentioned wanting layout access from the lower-left user menu in addition to Command Palette
- Existing patterns to follow: `sempkm_` localStorage namespace, Command Palette already exists in workspace, dockview `toJSON()`/`fromJSON()` for serialization

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-named-layouts-and-vfs-settings-restore*
*Context gathered: 2026-03-03*
