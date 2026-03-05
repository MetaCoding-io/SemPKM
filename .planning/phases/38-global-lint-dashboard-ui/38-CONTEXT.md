# Phase 38: Global Lint Dashboard UI - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can see all SHACL validation results across all objects from a single filterable, sortable view. Includes a persistent health indicator and support for large result sets (100+ results). Click-to-edit triage workflow is a future phase (LINT-11 through LINT-13).

</domain>

<decisions>
## Implementation Decisions

### Dashboard location
- Bottom panel tab alongside Event Log, Inference, AI Copilot
- Non-contextual view (content does not depend on focused object tab)
- Tab label: "LINT" (consistent with existing tab naming)

### Access methods
- Click the LINT tab in the bottom panel
- Command Palette action "Toggle Lint Dashboard"
- No dedicated keyboard shortcut (Ctrl+J already toggles bottom panel; user switches tabs)

### Claude's Discretion

All remaining UI decisions delegated to Claude:

**Health indicator (LINT-03):**
- Claude decides placement (status bar badge vs sidebar icon vs bottom panel tab badge)
- Claude decides what states to show (pass/violations count/warnings count)
- Guidance: should be visible without opening the lint panel

**Result table design (LINT-04, LINT-05, LINT-06, LINT-07):**
- Claude decides columns, density, and grouping strategy
- Claude decides filter control placement (inline toolbar vs sidebar filters)
- Claude decides sort interaction (clickable column headers vs dropdown)
- Claude decides pagination vs virtual-scroll for large result sets
- Guidance: follow existing per-object lint panel patterns (severity icons, message, path) but at workspace scale

**Click-to-navigate behavior:**
- Claude decides what happens when user clicks a lint result row
- Guidance: opening the object in dockview is the obvious choice; scrolling to field is future (LINT-11)

**Auto-refresh behavior (LINT-02 from Phase 37 API):**
- Claude decides refresh mechanism (htmx polling, SSE, or manual refresh button)
- Guidance: match the per-object lint panel's `hx-trigger="every 10s"` pattern for consistency

</decisions>

<specifics>
## Specific Ideas

No specific requirements — user locked the bottom panel location and access methods, delegated all other UI decisions to Claude.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/templates/browser/lint_panel.html`: Per-object lint panel with severity icons (●▲ℹ), message/path rendering, auto-refresh, jumpToField() click handler
- Bottom panel tab infrastructure: `.bottom-panel`, `.panel-tab[data-panel]`, toggle/maximize/close buttons
- `frontend/static/js/workspace.js`: dockview panel creation, tab metadata registry
- `backend/app/services/validation.py`: ValidationService with get_latest_summary(), get_report_by_event()

### Established Patterns
- Bottom panel tabs: HTML structure in workspace.html, JS switching via data-panel attributes
- htmx polling: `hx-trigger="every 10s"` for auto-refresh (used in per-object lint panel)
- Severity icons: `&#9679;` (violation/red), `&#9650;` (warning/yellow), `&#9432;` (info/blue)
- Non-contextual views: settings page, docs tab — content independent of focused object

### Integration Points
- Phase 37 API endpoints (must exist before Phase 38 UI can consume them)
- `AsyncValidationQueue` fires after EventStore.commit() — drives auto-refresh
- Sidebar badge/health indicator connects to validation summary data
- Command Palette registration for "Toggle Lint Dashboard" action

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 38-global-lint-dashboard-ui*
*Context gathered: 2026-03-05*
